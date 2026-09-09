"""Reject misleading comparison matrices and escape local gallery labels."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('comparison',ROOT/'scripts/compare-unreal-studies.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.case=dict(azimuthDeg=180,elevationDeg=30,localTimestamp='2026-12-22T12:00:00+09:00',
                       locationStatus='estimated',northStatus='estimated')
        self.report=dict(levelFileUnchanged=True,comparisonState=dict(
            azimuthDeg=180,elevationDeg=30,solar=self.case,camera={'lensMm':20},sunLux=50000,
            exposureEV100=7.5,scopeId='guest-ldk',activeRoomId='room-1f-06',
            roomStates={'room-1f-06':{'variant':'natural'}}),width=1600,height=900,
            finishSettingsSHA256='settings',floorShaderSHA256='shader',siteContext=None,hardwareRayTracingEnabled=True)

    def test_finish_change_allowed_but_camera_and_exposure_locked(self):
        changed=copy.deepcopy(self.report); changed['comparisonState']['roomStates']['room-1f-06']['variant']='warm'
        module.check_capture(changed,self.case,'warm',self.report)
        for key,value in [('camera',{'lensMm':35}),('exposureEV100',8),('sunLux',45000)]:
            bad=copy.deepcopy(changed); bad['comparisonState'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): module.check_capture(bad,self.case,'warm',self.report)

    def test_wrong_sun_missing_provenance_and_scene_change_rejected(self):
        for key,value in [('elevationDeg',60),('solar',None)]:
            bad=copy.deepcopy(self.report); bad['comparisonState'][key]=value
            with self.assertRaises(ValueError): module.check_capture(bad,self.case,'natural')
        bad=dict(self.report,siteContext={'sha256':'different'})
        with self.assertRaises(ValueError): module.check_capture(bad,self.case,'natural',self.report)

    def test_gallery_escapes_labels_and_omits_incomplete_images(self):
        report=copy.deepcopy(self.report)
        report['comparisonState']['solar']['localTimestamp']='<script>alert(1)</script>'
        page=module.gallery(dict(captures=[dict(status='pending'),dict(status='complete',report=report,
                                  image='safe.png',conditions='safe.json')]))
        self.assertNotIn('<script>',page); self.assertIn('&lt;script&gt;',page)
        self.assertEqual(page.count('<figure>'),1)


if __name__=='__main__': unittest.main()
