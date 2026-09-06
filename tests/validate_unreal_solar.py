"""UE commandlet integration: solar direction, provenance, save and restoration."""
import json
from pathlib import Path
import unreal
import study_controls as controls
from solar_position import matches

project=Path(unreal.Paths.project_dir()).resolve()
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Generated/House')
original=controls.current_state()
cases=controls.read('sun-cases.json')['cases']
verified=[]
try:
    for index,case in enumerate(cases):
        if not case['usable']:
            before=controls.current_state()
            try:
                controls.set_sun_case(index)
                raise AssertionError('Night case accepted')
            except ValueError: pass
            assert controls.current_state()==before
            continue
        controls.set_sun_case(index)
        actual=controls.current_state()
        assert matches(case,actual) and actual['solar']==case
        for key in ('camera','variant','sunLux','exposureEV100'):
            assert actual[key]==original[key],key
        controls.save()
        saved=controls.read('study-state.json')
        assert matches(case,saved) and saved['solar']==case
        (project/'Saved/solar-transfer-state.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
        controls.apply_state(saved)
        assert controls.current_state()['solar']==case
        verified.append(dict(index=index,azimuthDeg=actual['azimuthDeg'],elevationDeg=actual['elevationDeg']))
    controls.set_variant('warm')
    assert 'solar' in controls.current_state()
    controls.set_elevation(45)
    assert 'solar' not in controls.current_state()
    controls.set_sun_case(0)
    controls.scene()['Sun_manual_angle'].set_actor_rotation(unreal.Rotator(pitch=-40,yaw=20,roll=0),False)
    assert 'solar' not in controls.current_state(), 'Manual rotation retains misleading date'
    controls.set_variant('natural')
    assert 'solar' not in controls.current_state()
    result=dict(cases=verified,nightRejected=True,manualRotationClearsProvenance=True,
                finishExposureCameraPreserved=True,siteDaylightCalibrated=False)
    (project/'Saved/solar-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
finally:
    controls.apply_state(original); controls.save()
unreal.log('SOLAR_CONTROLS_VERIFIED')
