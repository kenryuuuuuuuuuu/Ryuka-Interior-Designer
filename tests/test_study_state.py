"""Reject incompatible or invalid saved conditions before creating a project."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
from study_state import default_state, validate_state


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


if __name__=='__main__': unittest.main()
