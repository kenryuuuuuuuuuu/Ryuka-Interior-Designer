import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'blender'))
from guest_decor import resolve


class GuestDecor(unittest.TestCase):
    def setUp(self):
        self.data = dict(rooms=[dict(id='room', level=1, polygon=[[0,0],[5,0],[5,4],[0,4]])],
                         levels=dict(fl1=.7), defaults=dict(wallThickness=.2, interiorWallThickness=.1))
        self.furniture = [dict(id='table', x=2, z=2, rotation=0, level=1)]
        self.openings = [dict(id='window', face='S', level=1, exterior=True, type='window-waist',
                             start=1, end=3, bottom=1.7, top=2.7, at=4)]
        self.doc = dict(schemaVersion='0.1.0', roomId='room', items=[
            dict(id='rug', kind='rug', furnitureId='table', width=1.6, depth=1.2),
            dict(id='blind', kind='blind', openingId='window', dropFraction=.22),
            dict(id='slat', kind='slat', furnitureId='table', width=.95, height=1.1, bottom=1.15)])
        for item in self.doc['items']:
            item.update(status='estimated', note='Test provisional dimensions')

    def test_follows_source_changes(self):
        first = resolve(self.doc, self.data, self.furniture, self.openings)
        self.furniture[0].update(x=2.5, rotation=90)
        self.openings[0].update(start=2, end=4.5, top=3)
        self.data['rooms'][0]['polygon'][0][1] = .3
        self.data['rooms'][0]['polygon'][1][1] = .3
        second = resolve(self.doc, self.data, self.furniture, self.openings)
        self.assertEqual(second[0]['x'], 2.5)
        self.assertEqual(second[0]['rotation'], 90)
        self.assertAlmostEqual(second[1]['width']-first[1]['width'], .5)
        self.assertAlmostEqual(second[1]['drop'], 1.3*.22)
        self.assertEqual(second[1]['top'], 3)
        self.assertAlmostEqual(second[2]['z']-first[2]['z'], .3)
        self.assertEqual(second[2]['x'], 2.5)

    def test_deleted_anchors_fail_and_explicit_removal_works(self):
        for furniture, openings in (([], self.openings), (self.furniture, [])):
            with self.assertRaises(ValueError):
                resolve(self.doc, self.data, furniture, openings)
        self.doc['items'] = []
        self.assertEqual(resolve(self.doc, self.data, [], []), [])

    def test_invalid_or_unsupported_configuration_fails(self):
        for index, key, value in [(0,'width',float('nan')), (0,'depth',True), (1,'dropFraction',1.1),
                                  (2,'height',0), (2,'note',''), (2,'id','rug'), (2,'kind','unknown')]:
            doc=copy.deepcopy(self.doc); doc['items'][index][key]=value
            with self.assertRaises(ValueError): resolve(doc,self.data,self.furniture,self.openings)
        self.openings[0]['face']='N'
        with self.assertRaises(ValueError): resolve(self.doc,self.data,self.furniture,self.openings)

    def test_ornament_requires_wall_wide_enough(self):
        self.furniture[0]['x']=.2
        with self.assertRaises(ValueError): resolve(self.doc,self.data,self.furniture,self.openings)


if __name__ == '__main__':
    unittest.main()
