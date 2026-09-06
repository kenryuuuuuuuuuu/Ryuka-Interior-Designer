"""Independent reference, time-zone boundaries and solar provenance safeguards."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'unreal'))
from solar_position import position, make_case, validate_case, apply_case, matches

SITE=dict(schemaVersion='1.0.0',latitudeDeg=35,longitudeDeg=135,
          planNorthAzimuthDeg=0,locationStatus='estimated',northStatus='estimated',
          note='Synthetic test site; unrelated to the building site.')


class SolarTests(unittest.TestCase):
    def test_independent_spa_reference(self):
        # NREL TP-560-34302 (2008), Appendix A.5. SPA includes refraction and
        # topocentric correction; this geometric approximation is checked to 0.05°.
        # https://docs.nlr.gov/docs/fy08osti/34302.pdf
        result=position('2003-10-17T12:30:30-07:00',39.742476,-105.1786)
        self.assertAlmostEqual(result['trueAzimuthDeg'],194.34024,delta=.05)
        self.assertAlmostEqual(result['elevationDeg'],90-50.11162,delta=.05)

    def test_same_instant_across_year_and_leap_day(self):
        for a,b in [('2026-01-01T01:00:00+09:00','2025-12-31T16:00:00+00:00'),
                    ('2024-03-01T01:00:00+09:00','2024-02-29T16:00:00+00:00')]:
            self.assertEqual(position(a,35,135),position(b,35,135))

    def test_north_correction_and_metadata(self):
        site=dict(SITE,planNorthAzimuthDeg=30)
        case=make_case(site,'2026-12-22T12:00:00+09:00')
        self.assertAlmostEqual((case['trueAzimuthDeg']-case['azimuthDeg'])%360,30)
        self.assertNotIn('latitudeDeg',case)
        state=apply_case(dict(variant='warm',sunLux=45000,camera={'test':True}),case)
        self.assertEqual(state['sunLux'],45000)
        self.assertTrue(matches(case,state))
        self.assertFalse(matches(case,dict(state,elevationDeg=60)))
        validate_case(case)
        damaged=copy.deepcopy(case); damaged['azimuthDeg']+=1
        with self.assertRaises(ValueError): validate_case(damaged)

    def test_night_is_reported_and_rejected(self):
        case=make_case(SITE,'2026-12-22T00:00:00+09:00')
        self.assertFalse(case['usable']); self.assertIsNotNone(case['reason'])
        validate_case(case)
        with self.assertRaises(ValueError): apply_case({},case)

    def test_reject_ambiguous_inputs(self):
        for time in ['2026-12-22T12:00:00','2100-01-01T12:00:00Z','invalid']:
            with self.subTest(time=time),self.assertRaises(ValueError): position(time,35,135)
        for key,value in [('latitudeDeg',True),('longitudeDeg',float('nan')),
                          ('planNorthAzimuthDeg',-1),('northStatus','unknown'),('note','')]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                make_case(dict(SITE,**{key:value}),'2026-12-22T12:00:00+09:00')


if __name__=='__main__': unittest.main()
