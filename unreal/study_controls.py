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
from solar_position import (apply_case, matches, validate_cases, validate_site,
    cases_match_site, case_matches_site, make_case, season_reference_timestamps, site_sha256)
from material_builder import rgb
from surface_finish_overrides import resolve_finish, resolve_overrides
from lighting import validate_lighting_bindings, resolve_fixture_overrides, effective_fixture

_state=None
_selected_surface=None  # surfaceId currently targeted by the 面編集 menu
_compare=None  # W04 finish A/B in progress: dict(fixed=..,before=..,a=..,b=..,current=..,names=..)
_daylight_compare=None  # W05 datetime A/B in progress: dict(fixed=..,before=..,a=..,b=..,current=..,names=..)
_lighting_compare=None  # W06 night lighting A/B in progress: same shape as _compare
_selected_lighting=None  # fixture id OR group id currently targeted by the 照明 menu


def _active_compare_label():
    # W06-v1 review R5: the three A/B compares (finish, datetime, lighting)
    # shared no mutual-exclusion at all -- starting one while another (even
    # of the same kind) was already active silently clobbered `before`,
    # losing the ability to cleanly restore whichever was overwritten.
    if _compare is not None: return 'A/B比較'
    if _daylight_compare is not None: return '日時比較'
    if _lighting_compare is not None: return '照明比較'
    return None


def _require_no_active_compare():
    label=_active_compare_label()
    if label is not None:
        raise RuntimeError(f'{label}を終了してから操作してください（比較終了）。')


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


def lighting_bindings():
    """The current model's resolved lighting fixtures (see
    blender/electrical_assets.py, W06), or None for a pre-W06 project /
    a project with no supported lighting fixtures at all -- callers treat
    that the same as "nothing to apply/offer", not an error."""
    path=project()/'lighting-bindings.json'
    return validate_lighting_bindings(read('lighting-bindings.json')) if path.exists() else None


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
    # W06: same pre-mutation contract as surfaceOverrides above -- a
    # lighting.fixtures key naming a fixture that does not exist in the
    # CURRENT model (removed from data/electrical.json, wrong room, or a
    # pre-W06 project with no lighting-bindings.json at all) stops the whole
    # apply before anything is touched, rather than being silently dropped.
    bindings=lighting_bindings()
    _,lighting_issues=resolve_fixture_overrides(state['lighting']['fixtures'],bindings or dict(fixtures=[]))
    if lighting_issues: raise RuntimeError('lighting: '+'; '.join(i['reason'] for i in lighting_issues))
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
        # W06: night disables the sun's direct light and the daytime sky
        # (SkyAtmosphere/SkyLight) entirely -- the initial night condition is
        # a common fixed (no-moonlight) environment, fixture lights are the
        # only source -- and day restores both to this state's own sunLux
        # (never a re-derived/guessed value). Fixture lights themselves are
        # independent of mode (a fixture can be on in daytime too); only
        # their own on/dimming/temperatureK decide whether each one lights.
        is_night=state['lighting']['mode']=='night'
        sun.light_component.set_intensity(0 if is_night else state['sunLux'])
        for label in ('Sky','SkyLight'):
            sky_actor=actors.get(label)
            if sky_actor is None: continue
            sky_actor.modify()
            sky_actor.set_actor_hidden_in_game(is_night)
            sky_actor.set_is_temporarily_hidden_in_editor(is_night)
        if bindings:
            for fixture in bindings['fixtures']:
                light_actor=actors.get('Light_'+fixture['id'])
                if light_actor is None: raise RuntimeError('Missing generated actor: Light_'+fixture['id'])
                effective=effective_fixture(fixture,state['lighting']['fixtures'].get(fixture['id']))
                light_actor.modify(); light_actor.light_component.modify()
                light_actor.light_component.set_intensity(effective['effectiveLumens'])
                light_actor.light_component.set_editor_property('temperature',effective['temperatureK'])
    _state=state
    mode=state['solar']['localTimestamp'] if state.get('solar') else '手動角度'
    unreal.log(f"内装比較: {state['variant']} / 太陽高度 {state['elevationDeg']}° / EV100 {state['exposureEV100']}（{mode}・照度未校正）")


def set_variant(name):
    state=current_state(); state['variant']=name; apply_state(state)


def set_elevation(degrees):
    state=current_state(); state.pop('solar',None); state['elevationDeg']=degrees; apply_state(state)


def _verify_case_site(case, label):
    """W05-v1 review R1: cases_match_site()/_sun_cases_status_text() only
    warn in the status label; every path that actually APPLIES a case (UI
    apply, datetime A/B, capture, direct build) must refuse to do so once
    the current site no longer matches it -- otherwise a site change or a
    recompute that the operator hasn't re-applied yet keeps silently taking
    effect. Skipped when no site is currently loaded: legacy sun-cases with
    no retained site snapshot remain usable, per spec."""
    site=current_site()
    if site is None: return
    if not case_matches_site(case,site):
        raise RuntimeError(f'{label}は現在の敷地と一致しません（敷地変更後の再計算・再適用が必要です）。')


def set_sun_case(index):
    cases=validate_cases(read('sun-cases.json'))['cases']
    if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<len(cases):
        raise ValueError('Invalid solar case index')
    case=cases[index]
    _verify_case_site(case,f"日時ケース「{case['localTimestamp']}」")
    apply_state(apply_case(current_state(),case))


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
    # W06: same "trust the dict for content, verify the live scene actually
    # matches it" pattern as surfaceOverrides above -- state['lighting'] is
    # managed exclusively through apply_state() (menu actions, A/B, scenario
    # load), so it is trusted here, not reconstructed from scratch. night
    # mode intentionally zeroes the sun's LIVE intensity (see apply_state()),
    # so sunLux must NOT be read back from that live value while in night
    # mode -- that would silently lose the day sunLux this state is meant to
    # restore on returning to day (W06 spec: 'dayへ戻せば保存された太陽・空の
    # 条件を復元します'). A valid sunLux is always >=1 (validate_state()), so
    # "sun intensity < 1" is an unambiguous night-mode signal.
    sun_intensity=actors['Sun_manual_angle'].light_component.get_editor_property('intensity')
    state['lighting']=copy.deepcopy(base.get('lighting',dict(mode='day',fixtures={})))
    is_night=state['lighting']['mode']=='night'
    state['sunLux']=base['sunLux'] if is_night else sun_intensity
    if is_night and sun_intensity>=1 or not is_night and sun_intensity<1:
        raise RuntimeError('太陽光源の点灯状態が保存内容と一致しません（Undo等の影響が考えられます）。'
            '比較条件を再適用してから保存してください。')
    lighting_binding_doc=lighting_bindings()
    if lighting_binding_doc:
        for fixture in lighting_binding_doc['fixtures']:
            light_actor=actors.get('Light_'+fixture['id'])
            if light_actor is None: continue
            expected=effective_fixture(fixture,state['lighting']['fixtures'].get(fixture['id']))
            live_intensity=light_actor.light_component.get_editor_property('intensity')
            live_temperature=light_actor.light_component.get_editor_property('temperature')
            if abs(live_intensity-expected['effectiveLumens'])>1e-3 or abs(live_temperature-expected['temperatureK'])>1e-3:
                raise RuntimeError(f"照明{fixture['id']}が保存内容と一致しません（Undo等の影響が考えられます）。"
                    '比較条件を再適用してから保存してください。')
    pp=actors['Fixed_exposure'].get_editor_property('settings')
    low=pp.get_editor_property('auto_exposure_min_brightness'); high=pp.get_editor_property('auto_exposure_max_brightness')
    if abs(low-high)>1e-6: raise RuntimeError('Use a fixed exposure before saving comparison conditions.')
    state['exposureEV100']=low
    camera=actors['Camera_guest_LDK']; rotation=camera.get_actor_rotation()
    state['camera']=dict(locationCm=list(camera.get_actor_location().to_tuple()),rotationDeg=[rotation.pitch,rotation.yaw,rotation.roll],
        lensMm=camera.get_cine_camera_component().get_editor_property('current_focal_length'))
    if state.get('solar') and not matches(state['solar'],state): state.pop('solar')
    state['schemaVersion']='1.2.0'  # W06: this shape always carries lighting now, even when day/empty
    validate_state(state,read('SourcePackage/study.json'))
    return state


def save():
    state=scene_state(current_state())
    # W05-v1 review R1: a site change or an explicit recompute_sun_cases()
    # touches site.local.json/sun-cases.json but never the currently-applied
    # scene state -- so "sun-cases now match the new site, but the scene's
    # own solar (still showing an old case) does not" is a normal, reachable
    # state, not an edge case. Block the save itself here (not scene_state(),
    # which current_state()/start_daylight_compare() etc. also call just to
    # read the current condition -- those must keep working on stale-but-
    # readable state so the operator can see and fix it).
    site=current_site()
    if state.get('solar') is not None and site is not None and not case_matches_site(state['solar'],site):
        raise RuntimeError('現在の太陽状態（日時由来）が現在の敷地と一致しません。'
            '日時ケースを現在の敷地で再計算し、再適用してから保存してください。')
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
    # W05-v1 review R2: this helper is still used ONLY by start_compare()
    # (W04's finish A/B), which deliberately fixes sun/camera/exposure and
    # never adopts a scenario's site/sun-cases -- "仕上げだけのA/Bでは敷地を
    # 切り替える必要はなく、モード間の意味を維持します". load_scenario() below
    # (single-案 load) has its own function that also adopts site/sun-cases.
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


def _validate_applicable(state, label):
    """Shared, side-effect-free pre-check (no scene mutation) for whether
    `state` can be applied to the CURRENT project at all: site-context
    compatibility (see _context_compatible) AND every surfaceOverrides key
    actually resolving to a bound surface in this room (resolve_overrides()
    -- the same check apply_state() itself does, just run here BEFORE
    anything is touched). W05: used by every path that must validate two
    candidate states before switching between them (W04's finish A/B, W05's
    datetime A/B, named-scenario load) so a broken second candidate is
    caught up front, not only once the operator actually switches to it."""
    if not _context_compatible(state):
        raise RuntimeError(f'{label}は現在のプロジェクトの周辺条件（site-context.json）と一致しません。')
    surfaces=surface_bindings()['surfaces']
    _,issues=resolve_overrides(state.get('surfaceOverrides') or {},dict(surfaces=surfaces),room_id=state.get('roomId'))
    if issues:
        raise RuntimeError(f'{label}の面別仕上げが現在のモデルと一致しません: '+'; '.join(i['reason'] for i in issues))
    # W06: same idea for lighting.fixtures -- a state saved before a fixture
    # was removed/renamed must not silently apply against the wrong (or no)
    # fixture.
    lighting=state.get('lighting') or dict(fixtures={})
    _,lighting_issues=resolve_fixture_overrides(lighting.get('fixtures',{}),lighting_bindings() or dict(fixtures=[]))
    if lighting_issues:
        raise RuntimeError(f'{label}の照明が現在のモデルと一致しません: '+'; '.join(i['reason'] for i in lighting_issues))


def load_scenario(index):
    dirs=_scenario_dirs()
    if not 0<=index<len(dirs): raise RuntimeError('案が見つかりません。')
    # W05-v1 review R2: scenario_inputs() validates state/site/sun-cases as
    # ONE consistent input set (including, since R1, that state['solar']
    # itself matches the bundled site); take the whole set from `paths`
    # instead of only its state -- previously load_scenario() applied only
    # the state and left whatever site.local.json/sun-cases.json the CURRENT
    # project already had, letting a state/solar loaded from scenario B
    # silently keep pairing with an unrelated site A still on disk.
    try:
        paths,_=_refresh_inputs().scenario_inputs(dirs[index])
    except ValueError as error:
        raise RuntimeError(f'案「{dirs[index].name}」は現在の状態と整合しません: {error}')
    state=json.loads(paths['state'].read_text(encoding='utf-8'))
    _validate_applicable(state,f'案「{dirs[index].name}」')
    # Everything above is read-only (scenario_inputs()/_validate_applicable()
    # touch nothing); only past this point do we start writing, so a failure
    # anywhere above leaves the current site/sun-cases/state exactly as they
    # were -- "検証に失敗した場合は現在の正常な入力/状態を維持してください".
    if 'site' in paths:
        write('site.local.json',json.loads(paths['site'].read_text(encoding='utf-8-sig')))
    elif _site_path().exists():
        _site_path().unlink()  # scenario has no site of its own: revert to "no site", never keep an unrelated one
    if 'sunCases' in paths:
        write('sun-cases.json',json.loads(paths['sunCases'].read_text(encoding='utf-8-sig')))
    elif _sun_cases_path().exists():
        _sun_cases_path().unlink()
    apply_state(state)
    unreal.log('案を読み込みました: '+dirs[index].name)
    register_menu()


def start_compare(index_a, index_b):
    _require_no_active_compare()  # W06-v1 review R5
    dirs=_scenario_dirs()
    if not (0<=index_a<len(dirs) and 0<=index_b<len(dirs)): raise RuntimeError('案が見つかりません。')
    refresh_inputs=_refresh_inputs()
    # Both scenarios validated BEFORE anything is touched -- an A/B compare
    # must not start half-usable, and a broken B must not leave A already applied.
    state_a=_load_scenario_state(refresh_inputs,index_a,dirs)
    state_b=_load_scenario_state(refresh_inputs,index_b,dirs)
    for name,state in ((dirs[index_a].name,state_a),(dirs[index_b].name,state_b)):
        _validate_applicable(state,f'案「{name}」')
    base=current_state()
    # W06 spec: the existing finish A/B fixes lighting too -- only variant/
    # surfaceOverrides switch between A and B.
    fixed=dict(azimuthDeg=base['azimuthDeg'],elevationDeg=base['elevationDeg'],
        sunLux=base['sunLux'],exposureEV100=base['exposureEV100'],camera=base['camera'],lighting=base['lighting'])
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


# --- W05: local site input, datetime solar cases, datetime A/B compare ---
# Same interaction model as the W04 block above: menu clicks plus a few free-
# text prompts (a file path, a date/time, provenance notes) via the same
# PowerShell InputBox _prompt() -- never raw JSON editing or a Python console.

def _site_path(): return project()/'site.local.json'


def current_site():
    """The project's local site snapshot (see solar_position.validate_site()),
    or None if none has been loaded/created yet. Raises if the file exists
    but fails validation -- a corrupted snapshot must not be silently
    treated as absent."""
    if not _site_path().exists(): return None
    return validate_site(read('site.local.json'))


def _site_status_text():
    site=current_site()
    if site is None:
        return '敷地：未設定（「敷地を読み込む」または「敷地を新規作成」を実行してください）'
    precision='概算' if 'estimated' in (site['locationStatus'],site['northStatus']) else '入力確認済み'
    # Local-only display (this editor session's Tools menu, never committed
    # or included in any report) -- W05 spec explicitly requires the actual
    # position/orientation be checkable through normal UI, not JSON/console.
    return (f"敷地：緯度{site['latitudeDeg']:.5f}° 経度{site['longitudeDeg']:.5f}° "
        f"図面北方位{site['planNorthAzimuthDeg']:.1f}°［{precision}］　根拠：{site['note']}")


def show_site_status(): unreal.log(_site_status_text())


def load_site():
    path_text=_prompt('敷地を読み込む','敷地JSONファイルのパス（このworktreeのbuild/配下）','').strip()
    if not path_text: return
    path=Path(path_text)
    if not path.is_absolute(): path=(_repo_root()/path_text).resolve()
    if not path.is_file(): raise RuntimeError('ファイルが見つかりません: '+str(path))
    site=validate_site(json.loads(path.read_text(encoding='utf-8-sig')))
    old_site=current_site()
    write('site.local.json',site)
    if old_site is not None and site_sha256(old_site)!=site_sha256(site) and (project()/'sun-cases.json').exists():
        unreal.log('敷地を変更しました。既存の日時ケースはこの敷地と一致しない可能性があります。'
            '必要なら「日時ケースを現在の敷地で再計算」を実行してください（自動では再計算しません）。')
    unreal.log('敷地を読み込みました: '+str(path))
    register_menu()


def create_site_input():
    lat_text=_prompt('敷地の新規作成 (1/6)','緯度（度。南緯は負の値）例：35.681','').strip()
    lon_text=_prompt('敷地の新規作成 (2/6)','経度（度。西経は負の値）例：139.767','').strip()
    north_text=_prompt('敷地の新規作成 (3/6)','図面北の、真北からの時計回り方位（度、0〜360）例：0','').strip()
    if not (lat_text and lon_text and north_text): return
    location_status=(_prompt('敷地の新規作成 (4/6)','位置の根拠：確認済みなら verified、概算なら estimated',
        'estimated').strip() or 'estimated')
    north_status=(_prompt('敷地の新規作成 (5/6)','真北の根拠：確認済みなら verified、概算なら estimated',
        'estimated').strip() or 'estimated')
    note=_prompt('敷地の新規作成 (6/6)','根拠メモ（資料名・確認方法など、必須）','').strip()
    if not note: raise RuntimeError('根拠メモは必須です。')
    site=validate_site(dict(schemaVersion='1.0.0',latitudeDeg=float(lat_text),longitudeDeg=float(lon_text),
        planNorthAzimuthDeg=float(north_text),locationStatus=location_status,northStatus=north_status,note=note))
    output_text=_prompt('敷地の新規作成','保存先パス（build/配下の新しいファイル名）','build/site.local.json').strip()
    if not output_text: return
    output=Path(output_text)
    if not output.is_absolute(): output=(_repo_root()/output_text).resolve()
    if not output.is_relative_to(_repo_root()/'build'): raise RuntimeError('保存先はこのworktreeのbuild/配下にしてください。')
    if output.exists(): raise RuntimeError('既存ファイルは上書きしません。別のファイル名を指定してください。')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(site,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write('site.local.json',site)
    unreal.log('敷地を新規作成し、読み込みました: '+str(output))
    register_menu()


def _sun_cases_path(): return project()/'sun-cases.json'


def _read_sun_cases_document():
    if _sun_cases_path().exists(): return validate_cases(read('sun-cases.json'))
    return dict(schemaVersion='1.0.0',siteDaylightCalibrated=False,cases=[])


def _require_site():
    site=current_site()
    if site is None: raise RuntimeError('敷地が未設定です。先に「敷地を読み込む」または「敷地を新規作成」を実行してください。')
    return site


def add_datetime_case():
    site=_require_site()
    date_text=_prompt('日時を追加 (1/3)','日付（YYYY-MM-DD）','2026-12-22').strip()
    time_text=_prompt('日時を追加 (2/3)','時刻（HH:MM）','12:00').strip()
    offset_text=_prompt('日時を追加 (3/3)','UTCオフセット（例：+09:00＝JST）','+09:00').strip()
    if not (date_text and time_text and offset_text): return
    case=make_case(site,f'{date_text}T{time_text}:00{offset_text}')
    document=_read_sun_cases_document()
    if any(c['localTimestamp']==case['localTimestamp'] for c in document['cases']):
        raise RuntimeError('同じ日時のケースが既にあります: '+case['localTimestamp'])
    document['cases'].append(case)
    write('sun-cases.json',validate_cases(document))
    detail=f"高度{case['elevationDeg']:.1f}°・方位{case['azimuthDeg']:.1f}°" if case['usable'] else '適用不可：'+case['reason']
    unreal.log(f"日時ケースを追加しました: {case['localTimestamp']}（{detail}）")
    register_menu()


def add_season_cases():
    site=_require_site()
    year_text=_prompt('季節代表日を追加','年（西暦。3/21・6/21・9/21・12/21の9/12/15時、JST基準を追加）','2026').strip()
    if not year_text: return
    document=_read_sun_cases_document()
    existing={c['localTimestamp'] for c in document['cases']}
    added=0
    for iso in season_reference_timestamps(int(year_text)):
        case=make_case(site,iso)
        if case['localTimestamp'] in existing: continue
        document['cases'].append(case); existing.add(case['localTimestamp']); added+=1
    write('sun-cases.json',validate_cases(document))
    unreal.log(f'季節代表日を{added}件追加しました（暦日固定。年ごとの厳密な春分・至日ではありません）。')
    register_menu()


def recompute_sun_cases():
    site=_require_site()
    document=_read_sun_cases_document()
    if not document['cases']: raise RuntimeError('日時ケースがありません。')
    document['cases']=[make_case(site,c['localTimestamp']) for c in document['cases']]
    write('sun-cases.json',validate_cases(document))
    unreal.log('現在の敷地で日時ケースを再計算しました。')
    register_menu()


def _sun_cases_status_text():
    if not _sun_cases_path().exists(): return '日時ケース：なし'
    document=validate_cases(read('sun-cases.json'))
    site=current_site()
    if site is None:
        return f"日時ケース：{len(document['cases'])}件（敷地原本なし・新規計算には敷地入力が必要）"
    if cases_match_site(document['cases'],site):
        return f"日時ケース：{len(document['cases'])}件（現在の敷地と一致）"
    return f"日時ケース：{len(document['cases'])}件（現在の敷地と不一致・再計算が必要）"


def show_sun_cases_status(): unreal.log(_sun_cases_status_text())


def start_daylight_compare(index_a, index_b):
    _require_no_active_compare()  # W06-v1 review R5
    document=_read_sun_cases_document()
    cases=document['cases']
    if not (0<=index_a<len(cases) and 0<=index_b<len(cases)): raise RuntimeError('日時ケースが見つかりません。')
    case_a,case_b=cases[index_a],cases[index_b]
    for case in (case_a,case_b):
        if not case['usable']: raise RuntimeError('適用できない日時です: '+case['reason'])
        _verify_case_site(case,f"日時「{case['localTimestamp']}」")
    base=current_state()
    # W06 spec: date/time comparison only makes sense in day mode (it varies
    # the SUN); starting it from night must stop with guidance, never
    # silently switch the mode back to day on the caller's behalf.
    if base['lighting']['mode']=='night':
        raise RuntimeError('日時比較は昼間モードでのみ開始できます。「照明」メニューから昼間へ戻してください。')
    def with_case(case):
        state=copy.deepcopy(base)
        state['azimuthDeg']=case['azimuthDeg']; state['elevationDeg']=case['elevationDeg']; state['solar']=dict(case)
        return state
    state_a,state_b=with_case(case_a),with_case(case_b)
    # Both candidates validated BEFORE anything is touched -- same shared
    # pre-check as W04's finish A/B and named-scenario load, applied here so
    # a half-started datetime comparison can't happen either.
    for name,state in ((case_a['localTimestamp'],state_a),(case_b['localTimestamp'],state_b)):
        _validate_applicable(state,f'日時「{name}」')
    global _daylight_compare
    # lighting is fixed too (day mode, required above; each candidate's full
    # deepcopy of `base` already carries it through show_daylight_compare()'s
    # direct apply_state(_daylight_compare[which]) -- listed here only for
    # the status label/documentation, not re-applied separately).
    _daylight_compare=dict(fixed=dict(variant=base['variant'],camera=base['camera'],
            exposureEV100=base['exposureEV100'],sunLux=base['sunLux'],lighting=base['lighting']),
        before=base,a=state_a,b=state_b,names=(case_a['localTimestamp'],case_b['localTimestamp']),current=None)
    show_daylight_compare('a')


def show_daylight_compare(which):
    if _daylight_compare is None: raise RuntimeError('日時比較を先に開始してください（比較開始）。')
    apply_state(_daylight_compare[which])
    _daylight_compare['current']=which
    unreal.log(f"日時比較中：{_daylight_compare['names'][0 if which=='a' else 1]}"
        '（仕上げ・視点・露出・光源強度・周辺条件は比較開始時点で固定）')
    register_menu()


def show_daylight_compare_a(): show_daylight_compare('a')
def show_daylight_compare_b(): show_daylight_compare('b')


def end_daylight_compare():
    global _daylight_compare
    if _daylight_compare is None: return
    apply_state(_daylight_compare['before'])
    _daylight_compare=None
    unreal.log('日時比較を終了し、比較開始前の状態に戻しました。')
    register_menu()


_daylight_compare_pick_a=None


def pick_daylight_compare_a(index):
    global _daylight_compare_pick_a
    _daylight_compare_pick_a=index
    unreal.log('日時比較A：ケース'+str(index)+'。続けて比較Bを選んでください。')
    register_menu()


def pick_daylight_compare_b(index):
    if _daylight_compare_pick_a is None: raise RuntimeError('先に日時比較Aを選んでください。')
    start_daylight_compare(_daylight_compare_pick_a,index)


def _daylight_compare_status_text():
    if _daylight_compare is None: return '日時比較：なし'
    which=_daylight_compare.get('current')
    shown={'a':'A','b':'B'}.get(which,'未表示')
    fixed=_daylight_compare['fixed']
    return (f"日時比較中（表示中：{shown}）　A＝{_daylight_compare['names'][0]}　B＝{_daylight_compare['names'][1]}　"
        f"固定条件＝仕上げ{fixed['variant']}・露出EV{fixed['exposureEV100']:.1f}・光源強度{fixed['sunLux']:.0f}lux・視点固定")


def show_daylight_compare_status(): unreal.log(_daylight_compare_status_text())


# --- W06: night lighting (day/night, fixture/group on-off-dimming-colour, night A/B) ---
# Same interaction model as W04/W05 above: menu clicks plus a couple of
# numeric prompts (dimming, colour temperature) via the same _prompt().

def _lighting_status_text():
    # register_menu() (and therefore this label) can run before the level is
    # even open (init_unreal.py at editor startup) -- current_state() calls
    # scene_state(), which requires the live scene and raises otherwise. Use
    # the last-applied in-memory state, or the plain on-disk/default state,
    # neither of which touch the scene (same reasoning as the other W04/W05
    # status labels in this menu, none of which call current_state()).
    lighting=(_state if _state is not None else initial_state())['lighting']
    mode_label='夜間（仮仕様）' if lighting['mode']=='night' else '昼間'
    bindings=lighting_bindings()
    if not bindings:
        return f'照明：{mode_label}（このプロジェクトに対応照明なし）'
    lit=sum(1 for f in bindings['fixtures'] if effective_fixture(f,lighting['fixtures'].get(f['id']))['on'])
    return f'照明：{mode_label}　点灯{lit}/{len(bindings["fixtures"])}灯'


def show_lighting_status(): unreal.log(_lighting_status_text())


def _set_lighting_mode(mode):
    _require_no_active_compare()  # W06-v1 review R5
    state=current_state(); state['lighting']=dict(state['lighting'],mode=mode)
    apply_state(state)
    unreal.log('昼間へ切り替えました（保存された太陽・空の条件を復元）。' if mode=='day'
        else '夜間へ切り替えました（初版は月光なしの固定環境・仮仕様です）。')
    register_menu()


def set_lighting_day(): _set_lighting_mode('day')
def set_lighting_night(): _set_lighting_mode('night')


def _target_fixture_ids(target_id):
    """target_id: a single fixture id, or a lighting-settings.json group id
    (an operating shortcut over fixture ids, not an electrical circuit --
    W06 spec section 1). Raises if it names neither."""
    bindings=lighting_bindings()
    known={f['id'] for f in bindings['fixtures']} if bindings else set()
    if target_id in known: return [target_id]
    settings=read('lighting-settings.json')
    group=next((g for g in settings['groups'] if g['id']==target_id),None)
    if group is None: raise RuntimeError('この照明/グループは現在のモデルにありません: '+target_id)
    stale=[fid for fid in group['fixtureIds'] if fid not in known]
    if stale:
        # W06-v1 review R4: dropping a stale member used to be silent; the
        # operator acting on a group must see that some of its members no
        # longer resolve, every time, not just when the group ends up empty.
        unreal.log(f"警告：グループ「{target_id}」の一部の照明は現在のモデルにありません（無視されます）: "
            +', '.join(stale))
    return [fid for fid in group['fixtureIds'] if fid in known]


def select_lighting(target_id):
    global _selected_lighting
    _target_fixture_ids(target_id)  # raises if unknown; nothing selected on failure
    _selected_lighting=target_id
    unreal.log('選択中の照明: '+target_id)
    register_menu()


def _selected_lighting_effective():
    """Current on/dimming/temperatureK for _selected_lighting (one fixture,
    or a group -- merged with 混在 per field when members disagree). W06-v1
    review R5: the status line and the dimming/temperature prompts must show/
    default to the fixture's ACTUAL current values, not a fixed placeholder."""
    ids=_target_fixture_ids(_selected_lighting)
    bindings=lighting_bindings()
    by_id={f['id']:f for f in bindings['fixtures']} if bindings else {}
    lighting=(_state if _state is not None else initial_state())['lighting']
    effectives=[effective_fixture(by_id[fid],lighting['fixtures'].get(fid)) for fid in ids if fid in by_id]
    if not effectives: return dict(on=False,dimming=1.0,temperatureK=None)
    def merged(field):
        values={e[field] for e in effectives}
        return values.pop() if len(values)==1 else '混在'
    return dict(on=merged('on'),dimming=merged('dimming'),temperatureK=merged('temperatureK'))


def _selected_lighting_status_text():
    if _selected_lighting is None: return '選択中の照明：なし'
    eff=_selected_lighting_effective()
    on_label={True:'点灯',False:'消灯'}.get(eff['on'],str(eff['on']))
    dimming_label=f"{eff['dimming']:.2f}" if isinstance(eff['dimming'],(int,float)) else str(eff['dimming'])
    temp_label=f"{eff['temperatureK']:.0f}K" if isinstance(eff['temperatureK'],(int,float)) else str(eff['temperatureK'])
    return f'選択中の照明：{_selected_lighting}（{on_label}・調光{dimming_label}・{temp_label}）'


def show_selected_lighting(): unreal.log(_selected_lighting_status_text())


def _apply_fixture_update(update):
    _require_no_active_compare()  # W06-v1 review R5
    if _selected_lighting is None: raise RuntimeError('先に照明またはグループを選択してください（照明の一覧から）。')
    ids=_target_fixture_ids(_selected_lighting)
    state=current_state()
    fixtures=dict(state['lighting']['fixtures'])
    for fixture_id in ids:
        merged=dict(fixtures.get(fixture_id,{})); merged.update(update)
        fixtures[fixture_id]=merged
    state['lighting']=dict(state['lighting'],fixtures=fixtures)
    apply_state(state)
    register_menu()


def turn_on_selected_lighting(): _apply_fixture_update(dict(on=True))
def turn_off_selected_lighting(): _apply_fixture_update(dict(on=False))


def set_dimming_selected_lighting():
    default='1'
    if _selected_lighting is not None:
        current=_selected_lighting_effective()['dimming']
        if isinstance(current,(int,float)): default=f'{current:g}'
    text=_prompt('調光率','0（消灯相当）〜1（全光束）の数値',default).strip()
    if not text: return
    _apply_fixture_update(dict(dimming=float(text)))


def set_temperature_selected_lighting():
    default='2700'
    if _selected_lighting is not None:
        current=_selected_lighting_effective()['temperatureK']
        if isinstance(current,(int,float)): default=f'{current:g}'
    text=_prompt('色温度','1800〜10000Kの数値（例：2700＝電球色、6500＝昼白色）',default).strip()
    if not text: return
    _apply_fixture_update(dict(temperatureK=float(text)))


def reset_selected_lighting():
    _require_no_active_compare()  # W06-v1 review R5
    if _selected_lighting is None: raise RuntimeError('先に照明またはグループを選択してください（照明の一覧から）。')
    ids=_target_fixture_ids(_selected_lighting)
    state=current_state(); fixtures=dict(state['lighting']['fixtures'])
    for fixture_id in ids: fixtures.pop(fixture_id,None)
    state['lighting']=dict(state['lighting'],fixtures=fixtures)
    apply_state(state)
    register_menu()


def reset_all_lighting():
    _require_no_active_compare()  # W06-v1 review R5
    state=current_state(); state['lighting']=dict(state['lighting'],fixtures={})
    apply_state(state)
    register_menu()


def start_lighting_compare(index_a, index_b):
    _require_no_active_compare()  # W06-v1 review R5
    dirs=_scenario_dirs()
    if not (0<=index_a<len(dirs) and 0<=index_b<len(dirs)): raise RuntimeError('案が見つかりません。')
    refresh_inputs=_refresh_inputs()
    # Both scenarios validated (and both required to be night) BEFORE
    # anything is touched -- same discipline as W04's finish A/B and W05's
    # datetime A/B.
    state_a=_load_scenario_state(refresh_inputs,index_a,dirs)
    state_b=_load_scenario_state(refresh_inputs,index_b,dirs)
    for name,state in ((dirs[index_a].name,state_a),(dirs[index_b].name,state_b)):
        _validate_applicable(state,f'案「{name}」')
        if state['lighting']['mode']!='night':
            raise RuntimeError(f'案「{name}」は夜間モードではありません。照明A/Bは両案とも夜間の案が必要です。')
    base=current_state()
    # W06 spec: fix current viewpoint/exposure/finish/surroundings/fixture
    # specs -- only each candidate's own `lighting` switches between A/B.
    fixed=dict(variant=base['variant'],surfaceOverrides=base['surfaceOverrides'],
        azimuthDeg=base['azimuthDeg'],elevationDeg=base['elevationDeg'],
        sunLux=base['sunLux'],exposureEV100=base['exposureEV100'],camera=base['camera'])
    if base.get('solar') is not None:
        # W06-v1 review R5: the numeric azimuth/elevation were already fixed
        # above, but the date/time PROVENANCE label was still being dropped
        # unconditionally in show_lighting_compare() below -- keep it fixed
        # too when the base state actually has one.
        fixed['solar']=base['solar']
    global _lighting_compare
    _lighting_compare=dict(fixed=fixed,before=base,a=state_a,b=state_b,
        names=(dirs[index_a].name,dirs[index_b].name),current=None)
    show_lighting_compare('a')


def show_lighting_compare(which):
    if _lighting_compare is None: raise RuntimeError('照明A/Bを先に開始してください（比較開始）。')
    state=dict(_lighting_compare[which]); state.update(_lighting_compare['fixed'])
    if 'solar' not in _lighting_compare['fixed']: state.pop('solar',None)
    apply_state(state)
    _lighting_compare['current']=which
    unreal.log(f"照明比較中：{_lighting_compare['names'][0 if which=='a' else 1]}"
        '（仕上げ・視点・露出・周辺条件・器具仕様は比較開始時点で固定）')
    register_menu()


def show_lighting_compare_a(): show_lighting_compare('a')
def show_lighting_compare_b(): show_lighting_compare('b')


def end_lighting_compare():
    global _lighting_compare
    if _lighting_compare is None: return
    apply_state(_lighting_compare['before'])
    _lighting_compare=None
    unreal.log('照明A/Bを終了し、比較開始前の状態に戻しました。')
    register_menu()


_lighting_compare_pick_a=None


def pick_lighting_compare_a(index):
    global _lighting_compare_pick_a
    _lighting_compare_pick_a=index
    unreal.log('照明比較A：'+_scenario_dirs()[index].name+'。続けて比較Bを選んでください。')
    register_menu()


def pick_lighting_compare_b(index):
    if _lighting_compare_pick_a is None: raise RuntimeError('先に照明比較Aを選んでください。')
    start_lighting_compare(_lighting_compare_pick_a,index)


def _lighting_compare_status_text():
    if _lighting_compare is None: return '照明比較：なし'
    which=_lighting_compare.get('current')
    shown={'a':'A','b':'B'}.get(which,'未表示')
    return (f"照明比較中（表示中：{shown}）　A＝{_lighting_compare['names'][0]}　B＝{_lighting_compare['names'][1]}　"
        '固定条件＝仕上げ・視点・露出・周辺条件・器具仕様')


def show_lighting_compare_status(): unreal.log(_lighting_compare_status_text())


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
    # W05: the日時 list moved into its own「採光」submenu below, alongside
    # site input/season-date management, instead of sitting inline here.
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

    # W05: local site input (position/orientation, confidence, provenance)
    # and datetime solar cases (arbitrary + season-representative), reusing
    # the same status-label/refresh-after-mutation pattern as 面編集/
    # 案の保存・比較 above.
    daylight_menu=parent.add_sub_menu('RyukaDaylight','RyukaDaylight','RyukaDaylight','採光','敷地入力と日時ケース')
    add(daylight_menu,'Site','SiteStatus',_site_status_text(),'show_site_status()')
    add(daylight_menu,'Site','SiteLoad','敷地を読み込む','load_site()')
    add(daylight_menu,'Site','SiteCreate','敷地を新規作成','create_site_input()')
    add(daylight_menu,'Cases','CasesStatus',_sun_cases_status_text(),'show_sun_cases_status()')
    add(daylight_menu,'Cases','CaseAdd','日時を追加','add_datetime_case()')
    add(daylight_menu,'Cases','CaseAddSeason','季節代表日を追加（3/21・6/21・9/21・12/21の9/12/15時）','add_season_cases()')
    add(daylight_menu,'Cases','CaseRecompute','日時ケースを現在の敷地で再計算','recompute_sun_cases()')
    if (project()/'sun-cases.json').exists():
        site_for_labels=current_site()
        for index,case in enumerate(validate_cases(read('sun-cases.json'))['cases']):
            provenance='概算' if 'estimated' in (case['locationStatus'],case['northStatus']) else '入力確認済み'
            label=case['localTimestamp']+'（'+provenance+'）'
            # W05 spec: an out-of-range (night-time etc.) case must still be
            # SHOWN, with its reason, not hidden -- clicking it still goes
            # through set_sun_case(), which raises with that same reason
            # (solar_position.apply_case()) rather than silently rounding
            # into the daylight range.
            if not case['usable']: label += '［適用不可：'+case['reason']+'］'
            # W05-v1 review R1: same treatment for a case whose recorded
            # angle no longer matches the CURRENT site (a site changed since
            # this case was computed, and not yet recomputed) -- shown, with
            # the reason, but set_sun_case() below (_verify_case_site) still
            # refuses to apply it.
            elif site_for_labels is not None and not case_matches_site(case,site_for_labels):
                label += '［適用不可：現在の敷地と不一致］'
            add(daylight_menu,'Apply',f'CaseApply{index}',label,f'set_sun_case({index})')

    # W05: datetime A/B, mirroring W04's finish A/B above but inverted --
    # finish/camera/exposure/light/context are fixed, only the picked
    # datetimes' solar angle switches.
    daylight_compare_menu=parent.add_sub_menu('RyukaDaylightCompare','RyukaDaylightCompare',
        'RyukaDaylightCompare','日時比較','同じ仕上げ・視点での日時A/B比較')
    add(daylight_compare_menu,'Status','DaylightCompareStatus',_daylight_compare_status_text(),'show_daylight_compare_status()')
    if (project()/'sun-cases.json').exists():
        cases=validate_cases(read('sun-cases.json'))['cases']
        site_for_compare=current_site()
        def _pickable(case):
            # W05-v1 review R1: keep an unusable OR site-mismatched case out
            # of the pick lists entirely, the same way an unusable one always
            # was -- both would only raise once picked (start_daylight_compare
            # -> _verify_case_site), so there is no reason to offer them.
            return case['usable'] and (site_for_compare is None or case_matches_site(case,site_for_compare))
        for index,case in enumerate(cases):
            if not _pickable(case): continue
            add(daylight_compare_menu,'PickA',f'DaylightPickA{index}','比較A：'+case['localTimestamp'],f'pick_daylight_compare_a({index})')
        for index,case in enumerate(cases):
            if not _pickable(case): continue
            add(daylight_compare_menu,'PickB',f'DaylightPickB{index}','比較B：'+case['localTimestamp'],f'pick_daylight_compare_b({index})')
    add(daylight_compare_menu,'Show','DaylightShowA','比較Aを表示','show_daylight_compare_a()')
    add(daylight_compare_menu,'Show','DaylightShowB','比較Bを表示','show_daylight_compare_b()')
    add(daylight_compare_menu,'Show','DaylightEnd','比較を終了（元の状態へ）','end_daylight_compare()')

    # W06: night lighting -- day/night, per-fixture/group selection and
    # on/off/dimming/colour temperature, and a night-only A/B over two named
    # scenarios (mirrors W04's 案の保存・比較 A/B but fixes finish/view/
    # exposure/surroundings/fixture specs and switches only `lighting`).
    lighting_bindings_doc=lighting_bindings()
    if lighting_bindings_doc:
        lighting_menu=parent.add_sub_menu('RyukaLighting','RyukaLighting','RyukaLighting','照明','昼夜切替・点灯・調光・色温度')
        add(lighting_menu,'Status','LightingStatus',_lighting_status_text(),'show_lighting_status()')
        add(lighting_menu,'Mode','LightingDay','昼間へ切替','set_lighting_day()')
        add(lighting_menu,'Mode','LightingNight','夜間へ切替（仮仕様）','set_lighting_night()')
        add(lighting_menu,'Select','LightingSelectedStatus',_selected_lighting_status_text(),'show_selected_lighting()')
        settings=read('lighting-settings.json')
        known_ids={f['id'] for f in lighting_bindings_doc['fixtures']}
        for group in settings['groups']:
            if any(fid in known_ids for fid in group['fixtureIds']):
                add(lighting_menu,'Select','LightingSelectGroup'+group['id'],'選択：[グループ] '+group['label'],f'select_lighting("{group["id"]}")')
        for fixture in lighting_bindings_doc['fixtures']:
            add(lighting_menu,'Select','LightingSelectFixture'+fixture['id'],
                f"選択：[{fixture['type']}] {fixture.get('label') or fixture['id']}",f'select_lighting("{fixture["id"]}")')
        for name,label,command in [('On','選択をON',"turn_on_selected_lighting()"),
                ('Off','選択をOFF',"turn_off_selected_lighting()"),
                ('Dimming','選択の調光率を指定','set_dimming_selected_lighting()'),
                ('Temperature','選択の色温度を指定','set_temperature_selected_lighting()'),
                ('ResetOne','選択を既定に戻す','reset_selected_lighting()'),
                ('ResetAll','すべての照明を既定に戻す','reset_all_lighting()')]:
            add(lighting_menu,'Actions','Lighting'+name,label,command)

        lighting_compare_menu=parent.add_sub_menu('RyukaLightingCompare','RyukaLightingCompare',
            'RyukaLightingCompare','照明比較','夜間の名前付き案どうしのA/B比較')
        add(lighting_compare_menu,'Status','LightingCompareStatus',_lighting_compare_status_text(),'show_lighting_compare_status()')
        for i,d in enumerate(dirs[:20]):
            add(lighting_compare_menu,'PickA',f'LightingPickA{i}','比較A：'+d.name,f'pick_lighting_compare_a({i})')
        for i,d in enumerate(dirs[:20]):
            add(lighting_compare_menu,'PickB',f'LightingPickB{i}','比較B：'+d.name,f'pick_lighting_compare_b({i})')
        add(lighting_compare_menu,'Show','LightingShowA','比較Aを表示','show_lighting_compare_a()')
        add(lighting_compare_menu,'Show','LightingShowB','比較Bを表示','show_lighting_compare_b()')
        add(lighting_compare_menu,'Show','LightingEnd','比較を終了（元の状態へ）','end_lighting_compare()')

    menus.refresh_all_widgets()
    return menu
