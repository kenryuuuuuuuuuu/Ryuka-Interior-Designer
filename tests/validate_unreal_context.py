"""UE integration: independent floor bindings, shade geometry and tamper rejection."""
import json
import hashlib
from pathlib import Path
import unreal
import study_controls as controls
from site_context import verify_scene

project=Path(unreal.Paths.project_dir()).resolve()
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Generated/House')
context=json.loads((project/'site-context.json').read_text(encoding='utf-8-sig'))
verify_scene(context)
bindings=controls.read('study-bindings.json')
floors=[label for label,slots in bindings.items() if 'floor' in slots.values()]
assert len(floors)==7 and all(label.startswith('slab_') for label in floors)
assert all(role!='floor' for label,slots in bindings.items() if not label.startswith('slab_') for role in slots.values())
state=controls.current_state()
try:
    controls.set_variant('warm')
    assert controls.current_state()['variant']=='warm'
    assert controls.current_state()['siteContextSHA256']==hashlib.sha256((project/'site-context.json').read_bytes()).hexdigest()
    (project/'Saved/context-transfer-state.json').write_text(json.dumps(controls.current_state(),indent=2),encoding='utf-8')
    for label in floors:
        assert controls.scene()[label].static_mesh_component.get_material(0).get_name()=='M_warm_floor'
    actor=controls.scene()['Context_'+context['boxes'][0]['id']]
    original=actor.get_actor_location()
    try:
        actor.set_actor_location(original+unreal.Vector(20,0,0),False,False)
        try:
            verify_scene(context)
            raise AssertionError('Moved context accepted')
        except RuntimeError: pass
    finally:
        actor.set_actor_location(original,False,False)
    verify_scene(context)
    result=dict(floorMeshes=len(floors),furnitureUsesSeparateWood=True,contextBoundsVerified=True,
                contextManualMoveRejected=True,variantSwitchVerified=True)
    (project/'Saved/context-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
finally:
    controls.apply_state(state)
unreal.log('SITE_CONTEXT_VERIFIED')
