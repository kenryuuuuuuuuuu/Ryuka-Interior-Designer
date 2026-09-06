import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from furniture_assets import sofa_parts, validate_bindings, round_table_parts, chair_parts


class FurnitureAssets(unittest.TestCase):
    def test_dining_assets(self):
        for factory,dimensions,count in [(round_table_parts,(.9,.9,.72),5),(chair_parts,(.45,.48,.85),9)]:
            self.assertEqual(len(factory(*dimensions)),count)
            for bad in [(0,.8,.8),(.8,float('nan'),.8),(.8,.8,3)]:
                with self.assertRaises(ValueError):factory(*bad)
        rail=chair_parts(.45,.48,.85)[-1]
        self.assertEqual(rail['kind'],'polygon')
        self.assertEqual(len(rail['polygon']),66)
    def setUp(self):
        self.bindings=json.loads((ROOT/'data/visual/asset-bindings.json').read_text(encoding='utf-8'))
        self.items=json.loads((ROOT/'data/furniture.json').read_text(encoding='utf-8'))['items']
        self.catalog=json.loads((ROOT/'data/furniture-catalog.json').read_text(encoding='utf-8'))

    def test_dimensions_and_fixed_joinery(self):
        for w,d,h in [(1.2,.7,.65),(1.7,.78,.78),(2.4,1.05,1)]:
            parts=sofa_parts(w,d,h)
            self.assertEqual(len({p['name'] for p in parts}),len(parts))
            for p in parts:
                x0,x1,z0,z1,y0,y1=p['bounds']
                self.assertTrue(-w/2<=x0<x1<=w/2)
                self.assertTrue(-d/2<=z0<z1<=d/2)
                self.assertTrue(0<=y0<y1<=h)
            post=parts[0]['bounds']
            self.assertAlmostEqual(post[1]-post[0],.045)
        for dims in [(1,.8,.8),(1.7,.3,.8),(1.7,.8,2),(float('nan'),.8,.8)]:
            with self.assertRaises(ValueError): sofa_parts(*dims)

    def test_assignment_move_resize_and_removal(self):
        validate_bindings(self.bindings,self.items,self.catalog)
        item=next(i for i in self.items if i['id']=='fur-011')
        item.update(x=4,z=5,rotation=90,widthOverride=2,elevation=.2)
        self.assertIn('fur-011',validate_bindings(self.bindings,self.items,self.catalog))
        self.items.remove(item)
        with self.assertRaisesRegex(ValueError,'orphan'): validate_bindings(self.bindings,self.items,self.catalog)
        self.bindings['bindings']=[]
        self.assertEqual(validate_bindings(self.bindings,self.items,self.catalog),{})

    def test_reject_ambiguous_or_incompatible_bindings(self):
        duplicate=copy.deepcopy(self.bindings)
        duplicate['bindings']*=2
        with self.assertRaisesRegex(ValueError,'Duplicate'): validate_bindings(duplicate,self.items,self.catalog)
        for field,value in [('assetId','missing'),('sizing','stretch'),('furnitureId','fur-045')]:
            wrong=copy.deepcopy(self.bindings);wrong['bindings'][0][field]=value
            with self.assertRaises(ValueError): validate_bindings(wrong,self.items,self.catalog)


if __name__=='__main__': unittest.main()
