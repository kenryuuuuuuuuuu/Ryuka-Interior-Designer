"""W04: surfaceOverrides structural validation (study_state.py) and finish
resolution / bound-target checking (surface_finish_overrides.py)."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
import study_state as ss
import surface_finish_overrides as sfo

STUDY=dict(roomId='room-1f-06',settings=dict(variants=dict(
    natural=dict(wall='e5dfd2',ceiling='eeeae1',wood='ae8153',fabric='9b998f',cabinet='c9b9a0'),
    warm=dict(wall='bcb0a0',ceiling='e5dfd3',wood='71513c',fabric='827468',cabinet='95836d'),
    reference=dict(floor='d7cdbc',wall='e5dece',ceiling='b99263',wood='b18c5b',fabric='c9c2b2',cabinet='b99b74'))))

FINISH_DOC=dict(schemaVersion='1.0.0',roles=dict(
    floor=dict(paletteRole='wood',roughness=.55,status='estimated',note='x',
        planks=dict(widthCm=15,lengthCm=180,seamCm=.08,rotationDeg=0)),
    wall=dict(roughness=.82,noiseScalePerCm=[3,3,3],colorMin=.97,colorMax=1.0),
    ceiling=dict(roughness=.87,noiseScalePerCm=[2,2,2],colorMin=.98,colorMax=1.0),
    wood=dict(roughness=.55,noiseScalePerCm=[.007,.18,.18],colorMin=.84,colorMax=1.02),
    fabric=dict(roughness=.95,noiseScalePerCm=[5,5,5],colorMin=.9,colorMax=1.02),
    cabinet=dict(roughness=.48,noiseScalePerCm=[.02,.6,.6],colorMin=.94,colorMax=1.0)),
    variantOverrides=dict(reference=dict(
        floor=dict(paletteRole='floor',roughness=.72,status='estimated',note='x',
            pattern=dict(kind='tile',widthCm=60,lengthCm=60,seamCm=.2,rotationDeg=0)),
        ceiling=dict(paletteRole='ceiling',roughness=.65,status='estimated',note='x',
            pattern=dict(kind='boards',widthCm=10,lengthCm=360,seamCm=.12,rotationDeg=0)))))

def base_state(overrides=None):
    return dict(schemaVersion='1.1.0',roomId='room-1f-06',variant='natural',
        azimuthDeg=180,elevationDeg=30,sunLux=50000,exposureEV100=7.5,camera=None,
        surfaceOverrides=overrides or {})


class SurfaceOverrideValidationTests(unittest.TestCase):
    def test_1_0_0_state_normalizes_to_empty_overrides(self):
        state=dict(schemaVersion='1.0.0',roomId='room-1f-06',variant='natural',
            azimuthDeg=180,elevationDeg=30,sunLux=50000,exposureEV100=7.5,camera=None)
        result=ss.validate_state(state,STUDY)
        self.assertEqual(result['surfaceOverrides'],{})

    def test_valid_override_round_trips(self):
        state=base_state({'surf-guest-wall-001':{'variant':'warm','colorHex':'c7beb0','roughness':.8}})
        result=ss.validate_state(state,STUDY)
        self.assertEqual(result['surfaceOverrides']['surf-guest-wall-001']['colorHex'],'c7beb0')

    def test_rejects_unknown_variant(self):
        with self.assertRaises(ValueError):
            ss.validate_state(base_state({'s1':{'variant':'unknown-variant'}}),STUDY)

    def test_rejects_bad_colorhex(self):
        for bad in ('#c7beb0','c7be','zzzzzz','c7beb0c7'):
            with self.assertRaises(ValueError): ss.validate_state(base_state({'s1':{'colorHex':bad}}),STUDY)

    def test_rejects_out_of_range_roughness(self):
        for bad in (-.1,1.1,True,'0.5'):
            with self.assertRaises(ValueError): ss.validate_state(base_state({'s1':{'roughness':bad}}),STUDY)

    def test_rejects_unknown_field(self):
        with self.assertRaises(ValueError):
            ss.validate_state(base_state({'s1':{'texture':'marble'}}),STUDY)

    def test_rejects_non_dict_overrides(self):
        with self.assertRaises(ValueError): ss.validate_state(base_state('nope'),STUDY)


class ResolveFinishTests(unittest.TestCase):
    def test_no_override_matches_plain_base_variant(self):
        finish=sfo.resolve_finish(FINISH_DOC,STUDY['settings']['variants'],'wall','natural')
        self.assertEqual(finish['colorHex'],'e5dfd2'); self.assertAlmostEqual(finish['roughness'],.82)

    def test_floor_uses_wood_palette_role_for_non_reference(self):
        finish=sfo.resolve_finish(FINISH_DOC,STUDY['settings']['variants'],'floor','warm')
        self.assertEqual(finish['colorHex'],'71513c')  # warm's wood colour, not a distinct floor colour

    def test_floor_uses_its_own_palette_role_for_reference_with_pattern(self):
        finish=sfo.resolve_finish(FINISH_DOC,STUDY['settings']['variants'],'floor','reference')
        self.assertEqual(finish['colorHex'],'d7cdbc'); self.assertIsNotNone(finish['pattern'])

    def test_explicit_color_and_roughness_override_win(self):
        finish=sfo.resolve_finish(FINISH_DOC,STUDY['settings']['variants'],'wall','natural',
            dict(colorHex='ff2222',roughness=.3))
        self.assertEqual(finish['colorHex'],'ff2222'); self.assertAlmostEqual(finish['roughness'],.3)

    def test_variant_override_switches_palette_without_explicit_color(self):
        finish=sfo.resolve_finish(FINISH_DOC,STUDY['settings']['variants'],'ceiling','natural',dict(variant='warm'))
        self.assertEqual(finish['colorHex'],'e5dfd3')  # warm's ceiling colour


class ResolveOverridesTests(unittest.TestCase):
    def setUp(self):
        self.bindings=dict(surfaces={
            'surf-guest-wall-001':dict(status='bound',kind='wall',roomId='room-1f-06'),
            'surf-guest-wall-002':dict(status='no-surface',kind='wall',roomId='room-1f-06')})

    def test_bound_override_is_usable(self):
        usable,issues=sfo.resolve_overrides({'surf-guest-wall-001':{'colorHex':'ff2222'}},self.bindings)
        self.assertEqual(list(usable),['surf-guest-wall-001']); self.assertEqual(issues,[])

    def test_no_surface_override_is_an_issue_not_a_crash(self):
        usable,issues=sfo.resolve_overrides({'surf-guest-wall-002':{'colorHex':'ff2222'}},self.bindings)
        self.assertEqual(usable,{}); self.assertEqual(len(issues),1)

    def test_unknown_id_override_is_an_issue(self):
        usable,issues=sfo.resolve_overrides({'surf-does-not-exist':{'colorHex':'ff2222'}},self.bindings)
        self.assertEqual(usable,{}); self.assertEqual(len(issues),1)

    def test_other_room_override_is_an_issue_not_silently_applied(self):
        # W04 review R4: a registered+bound id belonging to a DIFFERENT room
        # than the one being applied to must not be treated as usable.
        usable,issues=sfo.resolve_overrides({'surf-guest-wall-001':{'colorHex':'ff2222'}},
            self.bindings,room_id='room-1f-99')
        self.assertEqual(usable,{}); self.assertEqual(len(issues),1)

    def test_matching_room_override_is_still_usable(self):
        usable,issues=sfo.resolve_overrides({'surf-guest-wall-001':{'colorHex':'ff2222'}},
            self.bindings,room_id='room-1f-06')
        self.assertEqual(list(usable),['surf-guest-wall-001']); self.assertEqual(issues,[])


class ResolveFinishDetailTests(unittest.TestCase):
    def test_detail_carries_pattern_for_marker_material_reuse(self):
        # W04 review R1: resolve_finish() must expose the same per-kind/
        # variant detail dict (pattern/planks/noise) used for the
        # whole-scene role materials, so a marker material can reuse it and
        # keep its texture instead of going flat.
        finish=sfo.resolve_finish(FINISH_DOC,STUDY['settings']['variants'],'floor','reference')
        self.assertIn('pattern',finish['detail']); self.assertEqual(finish['detail']['pattern']['kind'],'tile')

    def test_detail_carries_noise_for_non_pattern_roles(self):
        finish=sfo.resolve_finish(FINISH_DOC,STUDY['settings']['variants'],'wall','natural')
        self.assertIn('noiseScalePerCm',finish['detail'])


class SurfaceOverride110StrictnessTests(unittest.TestCase):
    # W04 review R4: study_state.py's `state.get('surfaceOverrides') or {}`
    # silently masked a 1.1.0 state's null/[]/false surfaceOverrides into an
    # empty dict. Only 1.0.0's total absence is meant to be tolerated.
    def test_1_1_0_missing_surface_overrides_is_rejected(self):
        state=dict(schemaVersion='1.1.0',roomId='room-1f-06',variant='natural',
            azimuthDeg=180,elevationDeg=30,sunLux=50000,exposureEV100=7.5,camera=None)
        with self.assertRaises(ValueError): ss.validate_state(state,STUDY)

    def test_1_1_0_null_surface_overrides_is_rejected(self):
        # Built directly, not via base_state(): that helper's own `overrides
        # or {}` would mask exactly the falsy values this test needs to send through.
        state=dict(schemaVersion='1.1.0',roomId='room-1f-06',variant='natural',
            azimuthDeg=180,elevationDeg=30,sunLux=50000,exposureEV100=7.5,camera=None,surfaceOverrides=None)
        with self.assertRaises(ValueError): ss.validate_state(state,STUDY)

    def test_1_1_0_list_surface_overrides_is_rejected(self):
        state=dict(schemaVersion='1.1.0',roomId='room-1f-06',variant='natural',
            azimuthDeg=180,elevationDeg=30,sunLux=50000,exposureEV100=7.5,camera=None,surfaceOverrides=[])
        with self.assertRaises(ValueError): ss.validate_state(state,STUDY)

    def test_1_0_0_missing_surface_overrides_still_normalizes_to_empty(self):
        state=dict(schemaVersion='1.0.0',roomId='room-1f-06',variant='natural',
            azimuthDeg=180,elevationDeg=30,sunLux=50000,exposureEV100=7.5,camera=None)
        result=ss.validate_state(state,STUDY)
        self.assertEqual(result['surfaceOverrides'],{})

    def test_1_0_0_explicit_garbage_surface_overrides_is_still_rejected(self):
        # "だけ" -- only the field's total ABSENCE is tolerated for 1.0.0, not
        # an explicit wrong-type value someone hand-edited in.
        state=dict(schemaVersion='1.0.0',roomId='room-1f-06',variant='natural',
            azimuthDeg=180,elevationDeg=30,sunLux=50000,exposureEV100=7.5,camera=None,
            surfaceOverrides=[])
        with self.assertRaises(ValueError): ss.validate_state(state,STUDY)


if __name__=='__main__': unittest.main()
