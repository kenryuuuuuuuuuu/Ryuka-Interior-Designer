"""Editor-only study controls. Generated actor bindings are validated before any edit."""
import copy
import hashlib
import json
import math
from pathlib import Path
import unreal
from study_state import default_state, validate_state
from solar_position import apply_case, matches, validate_cases

_state=None


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


def apply_state(state):
    global _state
    state=validate_state(copy.deepcopy(state),read('SourcePackage/study.json'))
    context_path=project()/'site-context.json'
    if state.get('siteContextSHA256') and not context_path.exists():
        raise ValueError('Saved conditions require site context; regenerate with --context')
    if context_path.exists(): state['siteContextSHA256']=hashlib.sha256(context_path.read_bytes()).hexdigest()
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
    sun=actors['Sun_manual_angle']; post=actors['Fixed_exposure']; camera=actors['Camera_guest_LDK']
    with unreal.ScopedEditorTransaction('内装比較条件の変更'):
        for component,slot,material in planned:
            component.modify(); component.set_material(slot,material)
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
    menus.refresh_all_widgets()
    return menu
