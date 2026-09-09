"""Reject incompatible or invalid saved conditions before creating a project."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
from study_state import default_state, validate_state
from solar_position import make_case, apply_case


class StateTests(unittest.TestCase):
    def setUp(self):
        settings=json.loads((ROOT/'data/visual/guest-ldk-study.json').read_text(encoding='utf-8'))
        self.study=dict(roomId=settings['roomId'],settings=settings,variant='natural',lighting=settings['lighting'])
        self.state=default_state(self.study,dict(sunLux=50000,exposureEV100=7.5))

    def test_incompatible_state(self):
        for key,value in [('roomId','room-other'),('variant','missing'),('schemaVersion','2.0.0')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_state(dict(self.state,**{key:value}),self.study)

    def test_numbers_and_camera(self):
        for value in (float('nan'),float('inf'),True,'30',0,90):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_state(dict(self.state,elevationDeg=value),self.study)
        with self.assertRaises(ValueError):
            validate_state(dict(self.state,camera=dict(locationCm=[1,2],rotationDeg=[0,0,0],lensMm=20)),self.study)

    def test_roundtrip(self):
        state=copy.deepcopy(self.state)
        state.update(variant='warm',elevationDeg=60,camera=dict(locationCm=[213,425,225.7],rotationDeg=[-2,11,0],lensMm=20))
        self.assertEqual(validate_state(json.loads(json.dumps(state)),self.study),state)

    def test_solar_provenance(self):
        site=dict(schemaVersion='1.0.0',latitudeDeg=35,longitudeDeg=135,
                  planNorthAzimuthDeg=0,locationStatus='estimated',northStatus='estimated',note='Synthetic test')
        state=apply_case(self.state,make_case(site,'2026-12-22T12:00:00+09:00'))
        validate_state(state,self.study)
        with self.assertRaises(ValueError): validate_state(dict(state,elevationDeg=60),self.study)
        with self.assertRaises(ValueError): validate_state(dict(state,solar={}),self.study)

    # --- W06: lighting (1.2.0 required/strict, older schemas normalized) ---

    def test_pre_1_2_0_state_normalized_to_day_off(self):
        # default_state() already round-trips through validate_state() once
        # (stamping day/no-fixtures onto this 1.0.0 state); a state that
        # instead ARRIVES already carrying a night/on `lighting` (e.g. hand-
        # edited, or forwarded from a genuinely different schema) must still
        # be normalized to day + no fixture overrides once its own
        # schemaVersion is older than 1.2.0 -- older schemas never trust an
        # incoming `lighting` field, they always get the safe default.
        raw=dict(self.state,lighting=dict(mode='night',fixtures={'elec-008':{'on':True}}))
        result=validate_state(raw,self.study)
        self.assertEqual(result['lighting'],dict(mode='day',fixtures={}))
        result_1_1_0=validate_state(dict(raw,schemaVersion='1.1.0'),self.study)
        self.assertEqual(result_1_1_0['lighting'],dict(mode='day',fixtures={}))

    def test_1_2_0_requires_well_formed_lighting(self):
        # Unlike 1.0.0/1.1.0, a 1.2.0 state that omits/malforms `lighting`
        # is a hard error -- never silently treated as a pre-1.2.0 state.
        without_lighting={k:v for k,v in self.state.items() if k!='lighting'}
        state=dict(without_lighting,schemaVersion='1.2.0')
        with self.assertRaises(ValueError): validate_state(dict(state),self.study)  # no lighting field at all
        with self.assertRaises(ValueError): validate_state(dict(state,lighting=dict(mode='dusk',fixtures={})),self.study)
        with self.assertRaises(ValueError): validate_state(dict(state,lighting=dict(mode='night',fixtures='bad')),self.study)
        good=validate_state(dict(state,lighting=dict(mode='night',fixtures={})),self.study)
        self.assertEqual(good['lighting'],dict(mode='night',fixtures={}))

    def test_lighting_fixture_override_validation(self):
        state=dict(self.state,schemaVersion='1.2.0')
        def with_fixtures(fixtures):
            return validate_state(dict(state,lighting=dict(mode='night',fixtures=fixtures)),self.study)
        # Valid: sparse, any subset of on/dimming/temperatureK.
        with_fixtures({'elec-008':{'on':True,'dimming':0.7,'temperatureK':2700}})
        with_fixtures({'elec-008':{}})
        for bad in [{'elec-008':{'on':'yes'}}, {'elec-008':{'dimming':1.5}}, {'elec-008':{'dimming':-0.1}},
                    {'elec-008':{'temperatureK':1000}}, {'elec-008':{'temperatureK':20000}},
                    {'elec-008':{'unknownField':1}}, {123:{'on':True}}, 'not-a-dict']:
            with self.subTest(bad=bad), self.assertRaises(ValueError): with_fixtures(bad)


if __name__=='__main__': unittest.main()
