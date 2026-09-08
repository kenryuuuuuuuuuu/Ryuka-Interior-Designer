"""Editor-only study controls. Generated actor bindings are validated before any edit."""
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import unreal
from study_state import default_state, validate_state
from solar_position import apply_case, matches, validate_cases
from material_builder import rgb
from surface_finish_overrides import resolve_finish, resolve_overrides

_state=None
_selected_surface=None  # surfaceId currently targeted by the 面編集 menu
_compare=None  # A/B comparison in progress: dict(fixed=..,before=..,a=..,b=..,current=..,names=..)


def project(): return Path(unreal.Paths.project_dir()).resolve()
def read(name): return json.loads((project()/name).read_text(encoding='utf-8'))
def write(name,value):
    path=project()/name
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)


def initial_state():
    study=read('SourcePackage/study.json')
    initial=read('study-state.json') if (project()/'study-state.json').exists() else default_state(study,read('import-job.json'))
    return copy.deepcopy(initial)


def current_state():
    return scene_state(_state if _state is not None else initial_state())


def scene():
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split('.')[0] != '/Game/Generated/House':
        raise RuntimeError('Open /Game/Generated/House before using the study controls.')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    labels=[a.get_actor_label() for a in actors]
    if len(set(labels))!=len(labels): raise RuntimeError('Duplicate actor labels; cannot safely bind the study.')
    return {a.get_actor_label():a for a in actors}


def surface_bindings():
    path=project()/'surface-bindings.json'
    return read('surface-bindings.json') if path.exists() else dict(schemaVersion='1.0.0',surfaces={})


def apply_state(state):
    global _state
    study=read('SourcePackage/study.json')
    state=validate_state(copy.deepcopy(state),study)
    context_path=project()/'site-context.json'
    expected=state.get('siteContextSHA256')
    # W04 review R2: this state may come from anywhere -- a named scenario, a
    # runtime save, an A/B comparison's stashed a/b state -- that was saved
    # against a DIFFERENT site-context.json than this project currently has.
    # Silently substituting the current project's hash here (the old
    # behaviour) would make an incompatible surroundings condition look like
    # it always matched; refuse instead, the same way retained_inputs()/
    # scenario_inputs() do for the CLI paths. Nothing is mutated before this
    # check runs.
    if context_path.exists():
        actual=hashlib.sha256(context_path.read_bytes()).hexdigest()
        if expected is not None and expected!=actual:
            raise ValueError('この比較条件は別の周辺条件（site-context.json）で保存されたものです。現在のプロジェクトには適用できません。')
        state['siteContextSHA256']=actual
    elif expected:
        raise ValueError('この比較条件は周辺条件（site-context.json）を必要としますが、現在のプロジェクトにはありません。')
    actors=scene()
    bindings=read('study-bindings.json')
    planned=[]
    for label,slots in bindings.items():
        if label not in actors: raise RuntimeError('Missing generated actor: '+label)
        component=actors[label].static_mesh_component
        for slot,role in slots.items():
            path=f"/Game/Generated/Finishes/M_{state['variant']}_{role}"
            material=unreal.load_asset(path)
            if material is None: raise RuntimeError('Missing finish: '+path)
            if int(slot)>=component.get_num_materials(): raise RuntimeError('Material slots changed: '+label)
            planned.append((component,int(slot),material))
    # W04: per-surface overrides, applied ON TOP of the whole-scene role
    # materials above (priority: base variant -> surfaceOverrides). A stale/
    # orphaned override (unknown id, or a registered id with no real bound
    # geometry) stops the whole apply rather than silently dropping it --
    # the caller sees exactly why, and nothing gets half-applied since this
    # is all still resolved before the single transaction below runs.
    surfaces=surface_bindings()['surfaces']
    usable,issues=resolve_overrides(state['surfaceOverrides'],dict(surfaces=surfaces),room_id=state['roomId'])
    if issues: raise RuntimeError('surfaceOverrides: '+'; '.join(i['reason'] for i in issues))
    finish_document=read('finish-settings.json')
    surface_planned=[]
    for surface_id,info in surfaces.items():
        if info['status']!='bound': continue
        finish=resolve_finish(finish_document,study['settings']['variants'],info['kind'],state['variant'],usable.get(surface_id))
        # W04 review v2 R1: load the parent by (surface, EFFECTIVE variant) --
        # finish['variant'] -- instead of reusing whatever's currently in the
        # slot. Each variant's own pattern (planks/tile/plain noise) is baked
        # into that variant's own marker material at import time; reusing
        # "whatever parent happens to be there" only ever changes Color/
        # Roughness on top of the PREVIOUS variant's pattern, never the
        # pattern itself.
        base_asset=unreal.load_asset(f"/Game/Generated/Finishes/M_Surf_{surface_id}_{finish['variant']}")
        if base_asset is None: raise RuntimeError(f'Missing marker material for surface {surface_id} variant {finish["variant"]}')
        for mesh_ref in info['meshes']:
            actor=actors.get(mesh_ref['actor'])
            if actor is None: raise RuntimeError('Missing generated actor: '+mesh_ref['actor'])
            component=actor.static_mesh_component
            surface_planned.append((component,mesh_ref['slot'],base_asset,finish))
    sun=actors['Sun_manual_angle']; post=actors['Fixed_exposure']; camera=actors['Camera_guest_LDK']
    with unreal.ScopedEditorTransaction('内装比較条件の変更'):
        for component,slot,material in planned:
            component.modify(); component.set_material(slot,material)
        for component,slot,base_asset,finish in surface_planned:
            component.modify()
            # create_dynamic_material_instance() both makes the MID (from the
            # plain parametric marker asset in that slot) and assigns it back
            # to the same slot.
            mid=component.create_dynamic_material_instance(slot,base_asset)
            mid.set_vector_parameter_value('Color',unreal.LinearColor(*rgb(finish['colorHex']),1))
            mid.set_scalar_parameter_value('Roughness',finish['roughness'])
        az=math.radians(state['azimuthDeg']); el=math.radians(state['elevationDeg'])
        direction=unreal.Vector(-math.sin(az)*math.cos(el),math.cos(az)*math.cos(el),-math.sin(el))
        sun.modify(); sun.light_component.modify()
        sun.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(unreal.Vector(),direction),False)
        sun.light_component.set_intensity(state['sunLux'])
        post.modify(); pp=post.get_editor_property('settings')
        for key in ('auto_exposure_min_brightness','auto_exposure_max_brightness'):
            pp.set_editor_property('override_'+key,True); pp.set_editor_property(key,state['exposureEV100'])
        post.set_editor_property('settings',pp)
        if state['camera']:
            c=state['camera']; camera.modify(); camera.get_cine_camera_component().modify()
            camera.set_actor_location(unreal.Vector(*c['locationCm']),False,False)
            pitch,yaw,roll=c['rotationDeg']
            camera.set_actor_rotation(unreal.Rotator(pitch=pitch,yaw=yaw,roll=roll),False)
            camera.get_cine_camera_component().set_editor_property('current_focal_length',c['lensMm'])
    _state=state
    mode=state['solar']['localTimestamp'] if state.get('solar') else '手動角度'
    unreal.log(f"内装比較: {state['variant']} / 太陽高度 {state['elevationDeg']}° / EV100 {state['exposureEV100']}（{mode}・照度未校正）")


def set_variant(name):
    state=current_state(); state['variant']=name; apply_state(state)


def set_elevation(degrees):
    state=current_state(); state.pop('solar',None); state['elevationDeg']=degrees; apply_state(state)


def set_sun_case(index):
    cases=validate_cases(read('sun-cases.json'))['cases']
    if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(cases):
        raise ValueError('Invalid solar case index')
    apply_state(apply_case(current_state(),cases[index]))


def fixed_view():
    camera=scene()['Camera_guest_LDK']
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).pilot_level_actor(camera)


def remember_view():
    position,rotation=unreal.EditorLevelLibrary.get_level_viewport_camera_info()
    state=current_state()
    camera=scene()['Camera_guest_LDK']
    state['camera']=dict(locationCm=list(position.to_tuple()),rotationDeg=[rotation.pitch,rotation.yaw,rotation.roll],
        lensMm=camera.get_cine_camera_component().get_editor_property('current_focal_length'))
    apply_state(state)


def scene_state(base):
    # Read actual scene properties, including manual light/camera changes and Undo.
    actors=scene(); state=copy.deepcopy(base)
    bindings=read('study-bindings.json'); variants=read('SourcePackage/study.json')['settings']['variants']
    matching=[]
    for variant in variants:
        if all(actors[label].static_mesh_component.get_material(int(slot)).get_name()==f'M_{variant}_{role}'
               for label,slots in bindings.items() for slot,role in slots.items()): matching.append(variant)
    if len(matching)!=1: raise RuntimeError('Mixed/custom finishes cannot be exported as a named variant.')
    state['variant']=matching[0]
    # W04: study-bindings.json (the whole-scene role map above) never lists
    # surface-marker slots -- those are tracked separately in
    # surface-bindings.json and never touched by the loop above -- so this
    # "exactly one variant everywhere" check is unaffected by per-surface
    # overrides existing. Rather than re-deriving overrides from scene
    # material inspection (fragile: a MID's parameters aren't a stable
    # per-material identity the way a swapped asset name is), this trusts
    # the already-managed state every apply_state() call goes through and
    # just re-validates its shape below.
    state['surfaceOverrides']=copy.deepcopy(base.get('surfaceOverrides',{}))
    # W04 review R3: _state/base is a plain Python dict, invisible to Unreal's
    # own Undo system -- if the operator presses Ctrl+Z after a surface
    # override was applied, the SCENE's material reverts but this dict does
    # not. Re-deriving overrides from scene inspection instead is fragile (a
    # MID's parameters do not reveal whether the original override was a
    # named variant preset or an explicit colour that happens to match one),
    # so this still trusts the dict for its CONTENT, but verifies the live
    # scene actually matches it before letting anything be saved from it --
    # an unmanaged/undone change is refused with a reason, not silently
    # saved as if the override were still in effect.
    surfaces=surface_bindings()['surfaces']
    bound_surfaces={sid:info for sid,info in surfaces.items() if info['status']=='bound'}
    if bound_surfaces:
        finish_document=read('finish-settings.json')
        for surface_id,info in bound_surfaces.items():
            finish=resolve_finish(finish_document,variants,info['kind'],state['variant'],
                state['surfaceOverrides'].get(surface_id))
            expected_color=rgb(finish['colorHex'])
            expected_parent=f"/Game/Generated/Finishes/M_Surf_{surface_id}_{finish['variant']}"
            for mesh_ref in info['meshes']:
                actor=actors.get(mesh_ref['actor'])
                if actor is None: continue
                live=actor.static_mesh_component.get_material(mesh_ref['slot'])
                mismatch=not isinstance(live,unreal.MaterialInstanceDynamic)
                if not mismatch:
                    # W04 review v2 R1: the PARENT must also match the
                    # effective variant, not just Color/Roughness -- a wrong
                    # parent (stale pattern) can still show the right colour.
                    parent=live.get_editor_property('parent')
                    mismatch=parent is None or parent.get_path_name().split('.')[0]!=expected_parent
                if not mismatch:
                    color=live.get_vector_parameter_value('Color')
                    roughness=live.get_scalar_parameter_value('Roughness')
                    mismatch=(abs(color.r-expected_color[0])>1e-3 or abs(color.g-expected_color[1])>1e-3
                        or abs(color.b-expected_color[2])>1e-3 or abs(roughness-finish['roughness'])>1e-3)
                if mismatch:
                    raise RuntimeError(f'面{surface_id}の材質が保存内容と一致しません（Undo等の影響が考えられます）。'
                        '比較条件を再適用してから保存してください。')
    direction=actors['Sun_manual_angle'].get_actor_forward_vector()
    state['azimuthDeg']=math.degrees(math.atan2(-direction.x,direction.y))%360
    state['elevationDeg']=round(math.degrees(math.asin(max(-1,min(1,-direction.z)))),8)
    state['sunLux']=actors['Sun_manual_angle'].light_component.get_editor_property('intensity')
    pp=actors['Fixed_exposure'].get_editor_property('settings')
    low=pp.get_editor_property('auto_exposure_min_brightness'); high=pp.get_editor_property('auto_exposure_max_brightness')
    if abs(low-high)>1e-6: raise RuntimeError('Use a fixed exposure before saving comparison conditions.')
    state['exposureEV100']=low
    camera=actors['Camera_guest_LDK']; rotation=camera.get_actor_rotation()
    state['camera']=dict(locationCm=list(camera.get_actor_location().to_tuple()),rotationDeg=[rotation.pitch,rotation.yaw,rotation.roll],
        lensMm=camera.get_cine_camera_component().get_editor_property('current_focal_length'))
    if state.get('solar') and not matches(state['solar'],state): state.pop('solar')
    state['schemaVersion']='1.1.0'  # W04: this shape always carries surfaceOverrides now, even when empty
    validate_state(state,read('SourcePackage/study.json'))
    return state


def save():
    state=scene_state(current_state())
    if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level(): raise RuntimeError('Level save failed')
    write('study-state.json',state)
    global _state
    _state=state
    unreal.log('比較条件を study-state.json に保存しました。次回生成の --state で引き継げます。')


def start_walkthrough():
    import subprocess
    if not (project()/'walkthrough-verification.json').exists():
        raise RuntimeError('先に enable-unreal-walkthrough.py を実行してください。')
    save()
    executable=Path(unreal.Paths.engine_dir()).resolve()/'Binaries/Win64/UnrealEditor.exe'
    subprocess.Popen([str(executable),str(project()/'RyukaInterior.uproject'),
        '/Game/Generated/House','-game','-sm6','-windowed','-ResX=1600','-ResY=900','-NoSourceControl',
        '-DDC=InstalledNoZenLocalFallback','-LocalDataCachePath='+read('walkthrough.json')['cachePath']],
        cwd=project(),creationflags=subprocess.CREATE_NO_WINDOW)


def load_walkthrough():
    state=read('Saved/walkthrough-state.json')
    apply_state(state)
    save()
    fixed_view()


# --- W04: per-surface finish editing, named-scenario save/load, A/B compare ---
# A menu click is the whole interaction model here (matching the entries
# above); free text (a colour, a scenario name) is the one thing a menu
# click can't provide, so those few prompts use a native Windows input box
# via PowerShell -- still no Python console or JSON hand-edit for the
# operator.

def _prompt(title, message, default=''):
    script=('[System.Reflection.Assembly]::LoadWithPartialName("Microsoft.VisualBasic")|Out-Null;'
        f'[Microsoft.VisualBasic.Interaction]::InputBox([string]"{message}",[string]"{title}",[string]"{default}")')
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
        capture_output=True,text=True,timeout=180)
    return result.stdout.strip()


def _repo_root():
    info=project()/'repo-root.json'
    if not info.exists(): raise RuntimeError('repo-root.json is missing; regenerate this project to use named scenarios from the editor.')
    return Path(json.loads(info.read_text(encoding='utf-8'))['root'])


def _surface_label(surface_id, info):
    return info.get('label') or surface_id


def select_surface(surface_id):
    global _selected_surface
    surfaces=surface_bindings()['surfaces']
    if surface_id not in surfaces or surfaces[surface_id]['status']!='bound':
        raise RuntimeError('この面は現在の対象にできません（no-surfaceまたは未登録）: '+surface_id)
    _selected_surface=surface_id
    entry=surfaces[surface_id]
    live=scene()
    targets=[live[m['actor']] for m in entry['meshes'] if m['actor'] in live]
    if targets:
        unreal.get_editor_subsystem(unreal.EditorActorSubsystem).set_selected_level_actors(targets)
    # W04 review R3: an Actor selection outlines the whole wall mesh -- both
    # the room-facing cap this operates on AND the opposite side/back face of
    # the same thin prism -- so the outline alone cannot show which face is
    # actually the target. Say so explicitly every time.
    unreal.log(f"選択中の面: {_surface_label(surface_id,entry)}（{entry['kind']}・変更対象は部屋側の面のみです）")
    register_menu()  # refresh the 面編集 submenu's status entry


def _apply_override(update):
    if _selected_surface is None: raise RuntimeError('先に面を選択してください（面編集の一覧から）。')
    state=current_state()
    overrides=dict(state['surfaceOverrides'])
    if update is None:
        overrides.pop(_selected_surface,None)
    else:
        # W04 review R3: merge into whatever this surface already has,
        # instead of replacing it outright -- picking a colour after a
        # variant preset must not silently drop that preset (or vice versa),
        # and giving just a colour must not silently drop a roughness set
        # earlier (or vice versa).
        merged=dict(overrides.get(_selected_surface,{}))
        merged.update(update)
        overrides[_selected_surface]=merged
    state['surfaceOverrides']=overrides
    apply_state(state)
    register_menu()


def apply_preset_to_selected(variant): _apply_override(dict(variant=variant))
def reset_selected(): _apply_override(None)


def apply_color_to_selected():
    hex_value=_prompt('面の色','16進カラー（#なし、例 c7beb0。空欄でroughnessのみ変更）','').strip().lstrip('#')
    roughness_text=_prompt('面のroughness','0〜1の数値（空欄で変更なし）','').strip()
    # W04 review R3: colour and roughness are independent -- leaving the
    # colour box empty must still let a roughness-only change through
    # (previously the function returned immediately whenever colorHex was
    # blank, making a roughness-only edit impossible from this dialog).
    update={}
    if hex_value: update['colorHex']=hex_value
    if roughness_text: update['roughness']=float(roughness_text)
    if not update: return  # both left blank: nothing to apply
    _apply_override(update)


def reset_all_overrides():
    state=current_state(); state['surfaceOverrides']={}
    apply_state(state)
    register_menu()


def apply_preset_to_room(variant):
    room_id=read('SourcePackage/study.json')['roomId']
    state=current_state(); overrides=dict(state['surfaceOverrides'])
    for surface_id,info in surface_bindings()['surfaces'].items():
        if info['roomId']==room_id and info['status']=='bound':
            overrides[surface_id]=dict(variant=variant)
    state['surfaceOverrides']=overrides
    apply_state(state)
    register_menu()


def _refresh_inputs():
    # W03-A's own scripts/refresh_inputs.py (scenario_inputs/save_scenario_package),
    # imported from the ACTUAL repo, in-process. Not a subprocess: inside UE's
    # embedded Python, sys.executable is UnrealEditor(-Cmd).exe itself, not a
    # plain `python script.py` launcher (W04 review R3), and this module is
    # pure Python (no bpy/unreal dependency) so importing it directly is safe.
    root=_repo_root()
    for sub in ('scripts','unreal'):
        path=str(root/sub)
        if path not in sys.path: sys.path.insert(0,path)
    import refresh_inputs
    return refresh_inputs


def save_scenario():
    name=_prompt('案の保存','案の名前','')
    if not name: return
    note=_prompt('案の保存','メモ（任意）','')
    save()
    refresh_inputs=_refresh_inputs()
    root=_repo_root()
    scenarios=root/'build/scenarios'
    slug=''.join(c if c.isalnum() else '-' for c in name).strip('-') or 'scenario'
    output=scenarios/slug; n=1
    while output.exists(): n+=1; output=scenarios/f'{slug}-{n}'
    try:
        scenario,output=refresh_inputs.save_scenario_package(project(),name,note,output)
    except ValueError as error:
        raise RuntimeError('案の保存に失敗しました: '+str(error))
    unreal.log('案を保存しました: '+str(output))
    register_menu()  # refresh so the new scenario appears in 読込/比較 without reopening the editor


def _scenario_dirs():
    scenarios=_repo_root()/'build/scenarios'
    if not scenarios.is_dir(): return []
    return sorted(p for p in scenarios.iterdir() if p.is_dir() and (p/'scenario.json').is_file())


def list_scenarios():
    dirs=_scenario_dirs()
    unreal.log('保存済みの案:\n'+'\n'.join(f'{i}: {p.name}' for i,p in enumerate(dirs)) if dirs else '保存済みの案はありません。')


def _load_scenario_state(refresh_inputs, index, dirs):
    # W04 review R2: reuse W03-A's own scenario_inputs() -- the same
    # hash/schema/room/variant/site-context self-consistency check the CLI
    # (--scenario) path already applies -- rather than reading
    # study-state.json out of the package directly. A stale/corrupted/
    # tampered scenario package is refused here, before apply_state() ever
    # runs, and stays listed (not removed) so the operator can still see it.
    try:
        paths,_=refresh_inputs.scenario_inputs(dirs[index])
    except ValueError as error:
        raise RuntimeError(f'案「{dirs[index].name}」は現在の状態と整合しません: {error}')
    return json.loads(paths['state'].read_text(encoding='utf-8'))


def _context_compatible(state):
    """Pure check -- no mutation, no scene access -- for whether `state`'s
    siteContextSHA256 expectation matches the CURRENT project's
    site-context.json presence/hash. W04 review v2 R2: unlike apply_state()'s
    own bootstrap-friendly auto-adopt (needed so a state that has never yet
    been through this project's apply_state() at all -- e.g. default_state()
    on a brand new WITH-context project -- can be applied the first time),
    a state coming from ELSEWHERE (a saved scenario, --previous) must agree
    with the current project on BOTH "has a context" and "which one", not
    merely avoid an explicit conflict. A state saved with no context at all
    (expected is None) is therefore INCOMPATIBLE with a current project that
    does have one, not silently treated as compatible with anything."""
    context_path=project()/'site-context.json'
    expected=state.get('siteContextSHA256')
    if context_path.exists():
        return expected==hashlib.sha256(context_path.read_bytes()).hexdigest()
    return not expected


def load_scenario(index):
    dirs=_scenario_dirs()
    if not 0<=index<len(dirs): raise RuntimeError('案が見つかりません。')
    state=_load_scenario_state(_refresh_inputs(),index,dirs)
    if not _context_compatible(state):
        raise RuntimeError(f'案「{dirs[index].name}」は現在のプロジェクトの周辺条件（site-context.json）と一致しません。')
    apply_state(state)
    unreal.log('案を読み込みました: '+dirs[index].name)
    register_menu()


def start_compare(index_a, index_b):
    dirs=_scenario_dirs()
    if not (0<=index_a<len(dirs) and 0<=index_b<len(dirs)): raise RuntimeError('案が見つかりません。')
    refresh_inputs=_refresh_inputs()
    # Both scenarios validated BEFORE anything is touched -- an A/B compare
    # must not start half-usable, and a broken B must not leave A already applied.
    state_a=_load_scenario_state(refresh_inputs,index_a,dirs)
    state_b=_load_scenario_state(refresh_inputs,index_b,dirs)
    for name,state in ((dirs[index_a].name,state_a),(dirs[index_b].name,state_b)):
        if not _context_compatible(state):
            raise RuntimeError(f'案「{name}」は現在のプロジェクトの周辺条件（site-context.json）と一致しません。')
    base=current_state()
    fixed=dict(azimuthDeg=base['azimuthDeg'],elevationDeg=base['elevationDeg'],
        sunLux=base['sunLux'],exposureEV100=base['exposureEV100'],camera=base['camera'])
    global _compare
    _compare=dict(fixed=fixed,before=base,a=state_a,b=state_b,
        names=(dirs[index_a].name,dirs[index_b].name),current=None)
    show_compare('a')


def show_compare(which):
    if _compare is None: raise RuntimeError('A/B比較を先に開始してください（比較開始）。')
    # The scenario's own camera/sun/exposure -- and any date/time provenance
    # tied to those angles -- are deliberately NOT what gets shown here; only
    # its variant/surfaceOverrides are, under the CURRENT fixed conditions.
    # apply_state() itself still re-checks this project's site-context.json
    # against whichever of A/B is about to be shown (W04 review R2).
    state=dict(_compare[which]); state.update(_compare['fixed']); state.pop('solar',None)
    apply_state(state)
    _compare['current']=which
    unreal.log(f"比較中：{_compare['names'][0 if which=='a' else 1]}（視点・太陽・露出は比較開始時点で固定）")
    register_menu()


def show_compare_a(): show_compare('a')
def show_compare_b(): show_compare('b')


def end_compare():
    global _compare
    if _compare is None: return
    apply_state(_compare['before'])
    _compare=None
    unreal.log('A/B比較を終了し、比較開始前の状態に戻しました。')
    register_menu()


_compare_pick_a=None


def pick_compare_a(index):
    global _compare_pick_a
    _compare_pick_a=index
    unreal.log('比較A: '+_scenario_dirs()[index].name+'。続けて比較Bを選んでください。')
    register_menu()


def pick_compare_b(index):
    if _compare_pick_a is None: raise RuntimeError('先に比較Aを選んでください。')
    start_compare(_compare_pick_a,index)


def _selected_surface_status_text():
    # W04 review R3: this is shown as a menu LABEL (register_menu() rebuilds
    # it after every mutating action below), not just logged -- selection
    # state must be visible on the normal Tools menu, not only in the
    # Output Log.
    if _selected_surface is None:
        return '選択中の面：なし'
    info=surface_bindings()['surfaces'].get(_selected_surface,{})
    return f'選択中の面：{_surface_label(_selected_surface,info)}［{info.get("kind","?")}・部屋側の面のみ対象］'


def show_selected_surface(): unreal.log(_selected_surface_status_text())


def _compare_status_text():
    if _compare is None:
        return '比較中の案：なし'
    which=_compare.get('current')
    shown={'a':'A','b':'B'}.get(which,'未表示')
    fixed=_compare['fixed']
    return (f"A/B比較中（表示中：{shown}）　A＝{_compare['names'][0]}　B＝{_compare['names'][1]}　"
        f"固定条件＝太陽高度{fixed['elevationDeg']:.0f}°・方位{fixed['azimuthDeg']:.0f}°・"
        f"露出EV{fixed['exposureEV100']:.1f}・視点固定")


def show_compare_status(): unreal.log(_compare_status_text())


def register_menu():
    menus=unreal.ToolMenus.get()
    parent=menus.extend_menu('LevelEditor.MainMenu.Tools')
    menu=parent.add_sub_menu('RyukaStudy','RyukaStudy','RyukaStudy','内装比較','仮仕上げ・手動太陽角度の比較')
    entries=[('Natural','白壁・ナチュラルオーク',"set_variant('natural')"),
             ('Warm','グレージュ・ウォルナット',"set_variant('warm')"),
             ('Reference','石調の床・木板天井',"set_variant('reference')"),
             ('Sun30','太陽高度30°（手動）','set_elevation(30)'),
             ('Sun60','太陽高度60°（手動）','set_elevation(60)'),
             ('View','比較カメラを見る','fixed_view()'),
             ('Remember','現在の視点を比較カメラにする','remember_view()'),
             ('Save','比較条件とレベルを保存','save()')]
    if (project()/'walkthrough.json').exists():
        entries += [('Walk','内覧を別ウィンドウで開始','start_walkthrough()'),
                    ('WalkLoad','内覧で保存した視点・条件を反映','load_walkthrough()')]
    if (project()/'sun-cases.json').exists():
        for index,case in enumerate(validate_cases(read('sun-cases.json'))['cases']):
            if case['usable']:
                provenance='概算' if 'estimated' in (case['locationStatus'],case['northStatus']) else '入力確認済み'
                entries.append(('Date'+str(index),case['localTimestamp']+'（'+provenance+'）',f'set_sun_case({index})'))
    if 'reference' not in read('SourcePackage/study.json')['settings']['variants']:
        entries=[entry for entry in entries if entry[0]!='Reference']
    for name,label,command in entries:
        entry=unreal.ToolMenuEntry(name='Ryuka'+name,type=unreal.MultiBlockType.MENU_ENTRY)
        entry.set_label(label)
        entry.set_string_command(unreal.ToolMenuStringCommandType.PYTHON,'','import study_controls; study_controls.'+command)
        menu.add_menu_entry('Study',entry)

    def add(target,section,name,label,command):
        entry=unreal.ToolMenuEntry(name='Ryuka'+name,type=unreal.MultiBlockType.MENU_ENTRY)
        entry.set_label(label)
        entry.set_string_command(unreal.ToolMenuStringCommandType.PYTHON,'','import study_controls; study_controls.'+command)
        target.add_menu_entry(section,entry)

    # W04: per-surface editing. Listed only for surfaces that actually
    # resolved to real bound geometry this generation (see
    # surface-bindings.json); a registered-but-no-surface id never appears
    # here to be targeted by mistake.
    surfaces=surface_bindings()['surfaces'] if (project()/'surface-bindings.json').exists() else {}
    bound=sorted((sid,info) for sid,info in surfaces.items() if info['status']=='bound')
    if bound:
        surface_menu=parent.add_sub_menu('RyukaSurfaces','RyukaSurfaces','RyukaSurfaces','面編集','壁・床・天井ごとの仕上げ')
        add(surface_menu,'Status','SurfaceStatus',_selected_surface_status_text(),'show_selected_surface()')
        for sid,info in bound:
            add(surface_menu,'Select','SurfaceSelect'+sid,f"選択：[{info['kind']}] {_surface_label(sid,info)}",f'select_surface("{sid}")')
        for name,label,command in [('Natural','選択面をnaturalへ',"apply_preset_to_selected('natural')"),
                ('Warm','選択面をwarmへ',"apply_preset_to_selected('warm')"),
                ('Reference','選択面をreferenceへ',"apply_preset_to_selected('reference')"),
                ('Color','選択面の色・roughnessを指定','apply_color_to_selected()'),
                ('ResetOne','選択面を基準に戻す','reset_selected()'),
                ('ResetAll','上書きをすべて解除','reset_all_overrides()')]:
            add(surface_menu,'Actions','Surface'+name,label,command)
        for name,label,command in [('RoomNatural','部屋全体（登録面）へnaturalを適用',"apply_preset_to_room('natural')"),
                ('RoomWarm','部屋全体（登録面）へwarmを適用',"apply_preset_to_room('warm')"),
                ('RoomReference','部屋全体（登録面）へreferenceを適用',"apply_preset_to_room('reference')")]:
            add(surface_menu,'Room','Surface'+name,label,command)

    # W04: named scenarios (save/load, reusing W03-A's own script/validation)
    # and A/B comparison under the current fixed view/sun/exposure.
    scenario_menu=parent.add_sub_menu('RyukaScenarios','RyukaScenarios','RyukaScenarios','案の保存・比較','名前付き案の保存・読込・A/B比較')
    add(scenario_menu,'Status','ScenarioStatus',_compare_status_text(),'show_compare_status()')
    add(scenario_menu,'Save','ScenarioSave','名前を付けて保存','save_scenario()')
    add(scenario_menu,'Save','ScenarioList','一覧をログへ表示','list_scenarios()')
    dirs=_scenario_dirs() if (project()/'repo-root.json').exists() else []
    for i,d in enumerate(dirs[:20]):
        add(scenario_menu,'Load',f'ScenarioLoad{i}','読込：'+d.name,f'load_scenario({i})')
    for i,d in enumerate(dirs[:20]):
        add(scenario_menu,'CompareA',f'ScenarioPickA{i}','比較A：'+d.name,f'pick_compare_a({i})')
    for i,d in enumerate(dirs[:20]):
        add(scenario_menu,'CompareB',f'ScenarioPickB{i}','比較B：'+d.name,f'pick_compare_b({i})')
    add(scenario_menu,'Compare','ScenarioShowA','比較Aを表示','show_compare_a()')
    add(scenario_menu,'Compare','ScenarioShowB','比較Bを表示','show_compare_b()')
    add(scenario_menu,'Compare','ScenarioEndCompare','比較を終了（元の状態へ）','end_compare()')

    menus.refresh_all_widgets()
    return menu
