"""W06: lighting-settings.json/lighting-bindings.json validation and the
model-dependent fixture-override resolution (unreal/lighting.py)."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
from lighting import (validate_lighting_settings, validate_lighting_bindings,
    resolve_fixture_overrides, effective_fixture, kelvin_to_rgb)

SETTINGS=json.loads((ROOT/'data/visual/lighting-settings.json').read_text(encoding='utf-8'))

BINDINGS=dict(schemaVersion='1.0.0',roomId='room-1f-06',fixtures=[
    dict(id='elec-008',type='light-ceiling',label='シーリングライト',status='estimated',
         positionM=[4.65,3.93,4.55],emitPositionM=[4.65,3.81,4.55],
         directionVector=[0,-1,0],source='point',lumens=3800,temperatureK=3000)])


class LightingSettingsTests(unittest.TestCase):
    def test_repo_lighting_settings_valid(self):
        validate_lighting_settings(SETTINGS)  # the actual checked-in file

    def test_rejects_missing_required_profile(self):
        doc=json.loads(json.dumps(SETTINGS))
        del doc['profiles']['light-bracket']
        with self.assertRaises(ValueError): validate_lighting_settings(doc)

    def test_rejects_bad_profile_fields(self):
        base=json.loads(json.dumps(SETTINGS))
        def mutate(**kw):
            doc=json.loads(json.dumps(base)); doc['profiles']['light-downlight'].update(kw); return doc
        for kw in [dict(source='laser'), dict(lumens=-1), dict(temperatureK=500),
                   dict(spotAngleDeg=200), dict(directionLocal=[1,1,1]), dict(status='guessed'), dict(note='')]:
            with self.subTest(kw=kw), self.assertRaises(ValueError): validate_lighting_settings(mutate(**kw))

    def test_point_profile_rejects_spot_angle(self):
        doc=json.loads(json.dumps(SETTINGS))
        doc['profiles']['light-ceiling']['spotAngleDeg']=45
        with self.assertRaises(ValueError): validate_lighting_settings(doc)

    def test_rejects_duplicate_or_empty_group(self):
        doc=json.loads(json.dumps(SETTINGS))
        doc['groups'].append(dict(doc['groups'][0]))
        with self.assertRaises(ValueError): validate_lighting_settings(doc)
        doc=json.loads(json.dumps(SETTINGS)); doc['groups'][0]['fixtureIds']=[]
        with self.assertRaises(ValueError): validate_lighting_settings(doc)


class LightingBindingsTests(unittest.TestCase):
    def test_valid_bindings(self):
        validate_lighting_bindings(BINDINGS)

    def test_rejects_bad_fixture(self):
        for bad in [dict(BINDINGS['fixtures'][0],lumens=-1), dict(BINDINGS['fixtures'][0],temperatureK=99999),
                    dict(BINDINGS['fixtures'][0],source='laser'), dict(BINDINGS['fixtures'][0],directionVector=[1,1,1]),
                    dict(BINDINGS['fixtures'][0],emitPositionM=[0,0])]:
            doc=dict(BINDINGS,fixtures=[bad])
            with self.subTest(bad=bad), self.assertRaises(ValueError): validate_lighting_bindings(doc)

    def test_rejects_empty_or_duplicate(self):
        with self.assertRaises(ValueError): validate_lighting_bindings(dict(BINDINGS,fixtures=[]))
        with self.assertRaises(ValueError): validate_lighting_bindings(dict(BINDINGS,fixtures=BINDINGS['fixtures']*2))


class ResolveFixtureOverridesTests(unittest.TestCase):
    def test_known_and_unknown_ids(self):
        usable,issues=resolve_fixture_overrides({'elec-008':{'on':True},'elec-ghost':{'on':True}},BINDINGS)
        self.assertEqual(usable,{'elec-008':{'on':True}})
        self.assertEqual(len(issues),1); self.assertEqual(issues[0]['id'],'elec-ghost')

    def test_empty_bindings_rejects_everything(self):
        usable,issues=resolve_fixture_overrides({'elec-008':{'on':True}},dict(fixtures=[]))
        self.assertEqual(usable,{}); self.assertEqual(len(issues),1)

    def test_vacuous_true_for_no_overrides(self):
        usable,issues=resolve_fixture_overrides({},BINDINGS)
        self.assertEqual((usable,issues),({},[]))


class EffectiveFixtureTests(unittest.TestCase):
    def test_default_is_off(self):
        result=effective_fixture(BINDINGS['fixtures'][0],None)
        self.assertEqual(result,dict(on=False,dimming=1.0,temperatureK=3000,effectiveLumens=0.0))

    def test_on_with_dimming_and_temperature_override(self):
        result=effective_fixture(BINDINGS['fixtures'][0],dict(on=True,dimming=0.5,temperatureK=2700))
        self.assertEqual(result,dict(on=True,dimming=0.5,temperatureK=2700,effectiveLumens=1900.0))

    def test_on_without_dimming_uses_full_lumens(self):
        result=effective_fixture(BINDINGS['fixtures'][0],dict(on=True))
        self.assertEqual(result['effectiveLumens'],3800.0)


class KelvinToRgbTests(unittest.TestCase):
    def test_warm_is_more_orange_than_cool(self):
        warm=kelvin_to_rgb(2700); cool=kelvin_to_rgb(6500)
        self.assertGreater(warm[0]/warm[2], cool[0]/cool[2])  # warm: stronger red/blue ratio

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError): kelvin_to_rgb(500)
        with self.assertRaises(ValueError): kelvin_to_rgb(20000)


if __name__=='__main__': unittest.main()
