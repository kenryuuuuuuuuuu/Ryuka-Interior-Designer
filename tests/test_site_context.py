import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
from site_context import validate_context, expected_bounds, transform
from finish_settings import validate_finishes

BOX=dict(id='example-wall',centerMetres=[5,10,3],sizeMetres=[8,.2,6],
         rotationDeg=90,status='estimated',note='Synthetic test geometry')


class ContextTests(unittest.TestCase):
    def test_mapping_rotation_and_dimensions(self):
        validate_context(dict(schemaVersion='1.0.0',boxes=[BOX]))
        self.assertEqual(transform(BOX)['locationCm'],[500,1000,300])
        for a,b in zip(expected_bounds(BOX),[490,600,0,510,1400,600]):
            self.assertAlmostEqual(a,b)

    def test_reject_bad_geometry_and_missing_provenance(self):
        for key,value in [('sizeMetres',[1,0,1]),('centerMetres',[0,0,float('nan')]),
                          ('rotationDeg',True),('note',''),('id','../unsafe')]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_context(dict(schemaVersion='1.0.0',boxes=[dict(BOX,**{key:value})]))
        with self.assertRaises(ValueError):
            validate_context(dict(schemaVersion='1.0.0',boxes=[BOX,BOX]))

    def test_finish_scales(self):
        source=json.loads((ROOT/'data/visual/unreal-finishes.json').read_text(encoding='utf-8'))
        validate_finishes(source)
        for key,value in [('widthCm',0),('lengthCm',float('inf')),('seamCm',True)]:
            broken=copy.deepcopy(source); broken['roles']['floor']['planks'][key]=value
            with self.assertRaises(ValueError): validate_finishes(broken)


if __name__=='__main__': unittest.main()
