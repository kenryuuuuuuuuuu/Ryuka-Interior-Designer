"""Run in a generated UE project: real material switching, state export and restoration."""
import copy
import json
from pathlib import Path
import unreal
import study_controls as controls

project=Path(unreal.Paths.project_dir()).resolve()
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Generated/House')
original=controls.current_state()
actors=controls.scene()
meshes=[a for a in actors.values() if isinstance(a,unreal.StaticMeshActor)]
before={a.get_actor_label():[list(v.to_tuple()) for v in a.get_actor_bounds(False)] for a in meshes}
bindings=controls.read('study-bindings.json')
def check_variant(name):
    assert all(actors[label].static_mesh_component.get_material(int(slot)).get_name()==f'M_{name}_{role}'
        for label,slots in bindings.items() for slot,role in slots.items())

try:
    menu=controls.register_menu()
    assert unreal.ToolMenus.get().find_menu('LevelEditor.MainMenu.Tools.RyukaStudy') is not None
    controls.set_variant('warm'); check_variant('warm')
    controls.set_elevation(60)
    state=controls.current_state()
    camera=copy.deepcopy(original['camera']); camera['locationCm'][0]+=20
    state['camera']=camera
    controls.apply_state(state)
    controls.save()
    saved=controls.read('study-state.json')
    assert saved['variant']=='warm' and abs(saved['elevationDeg']-60)<.001
    assert saved['camera']['locationCm']==camera['locationCm']
    assert all(abs(a-b)<1e-6 for a,b in zip(saved['camera']['rotationDeg'],camera['rotationDeg'])), 'Camera rotation order changed'
    assert saved['exposureEV100']==original['exposureEV100']
    (project/'Saved/transfer-state.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
    invalid=dict(saved,variant='nonexistent')
    try:
        controls.apply_state(invalid)
        raise AssertionError('Invalid variant accepted')
    except ValueError: pass
    check_variant('warm')
    for actor in meshes:
        assert [list(v.to_tuple()) for v in actor.get_actor_bounds(False)]==before[actor.get_actor_label()]
    controls.set_variant('natural'); check_variant('natural')
    actors['Sun_manual_angle'].light_component.set_intensity(45000)
    controls.set_elevation(30)
    assert controls.current_state()['sunLux']==45000, 'Manual change lost on next menu action'
    result=dict(materialSlots=sum(len(v) for v in bindings.values()),geometryUnchanged=True,
                invalidStateRejected=True,menuRegistered=True,exportedState=saved)
    (project/'Saved/controls-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
finally:
    controls.apply_state(original); controls.save()
    restored=controls.read('study-state.json')
    assert restored['camera']['locationCm']==original['camera']['locationCm']
    assert all(abs(a-b)<1e-6 for a,b in zip(restored['camera']['rotationDeg'],original['camera']['rotationDeg']))
unreal.log('STUDY_CONTROLS_VERIFIED')
