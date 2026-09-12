import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from furniture_assets import (sofa_parts, validate_bindings, round_table_parts, chair_parts, hood_parts,
                              faucet_parts, air_conditioner_parts, toilet_parts, vanity_parts, washer_parts, bathtub_parts)


class FurnitureAssets(unittest.TestCase):
    def test_platform_mattress_and_work_table(self):
        from furniture_assets import asset_parts
        for asset,dims in [('raised-platform-v1',(1.8,1.8,.3)),('mattress-v1',(.97,1.95,.2)),('sofa-work-table-v1',(.8,.45,.65))]:
            for scale in (1,.5,1.5):
                w,d,h=[v*scale for v in dims]
                parts=asset_parts(asset,w,d,h)
                bounds=[p['bounds'] for p in parts]
                actual=[min(b[i] for b in bounds) if i%2==0 else max(b[i] for b in bounds) for i in range(6)]
                for got,expected in zip(actual,[-w/2,w/2,-d/2,d/2,0,h]):self.assertAlmostEqual(got,expected)
                self.assertTrue(all(b[0]<b[1] and b[2]<b[3] and b[4]<b[5] for b in bounds))
        table=asset_parts('sofa-work-table-v1',.8,.45,.65)
        support=next(p for p in table if p['name']=='support')['bounds']
        self.assertLess(support[3],0)  # room for knees beneath the front of the top

    def test_fixture_dimensions(self):
        for factory,dims,count in [(hood_parts,(.6,.5,.6),3),(faucet_parts,(.1,.18,.3),4),(air_conditioner_parts,(.8,.25,.3),3)]:
            self.assertEqual(len(factory(*dims)),count)
            with self.assertRaises(ValueError): factory(0,dims[1],dims[2])
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

    def test_water_fixtures_dimensions_and_bounds(self):
        cases = [(toilet_parts, (.45, .75, 1.0)), (vanity_parts, (.75, .53, 1.9)),
                 (washer_parts, (.64, .72, 1.05)), (bathtub_parts, (1.82, .8, .6))]
        for factory, (w, d, h) in cases:
            parts = factory(w, d, h)
            self.assertGreaterEqual(len(parts), 2, factory.__name__)  # multi-part: type is readable
            self.assertEqual(len({p['name'] for p in parts}), len(parts))
            for p in parts:
                x0, x1, z0, z1, y0, y1 = p['bounds']
                self.assertLess(x0, x1); self.assertLess(z0, z1); self.assertLess(y0, y1)
                self.assertTrue(-w / 2 - 1e-9 <= x0 and x1 <= w / 2 + 1e-9, (factory.__name__, p['name']))
                # body within height; a protruding tap/faucet may rise a little above the rim
                self.assertTrue(y0 >= -1e-9 and y1 <= h + (.2 if p['name'] in ('tap', 'faucet') else .001),
                                (factory.__name__, p['name']))
                self.assertIn(p['kind'], ('box', 'ellipse', 'polygon', 'disc'))

    def test_vanity_basin_is_not_filled_by_a_solid(self):
        # review R3: the cabinet must leave a cavity under the basin, not a
        # full box the bowl sits buried in.
        w, d, h = .75, .53, 1.9
        parts = {p['name']: p['bounds'] for p in vanity_parts(w, d, h)}
        bx0, bx1, bz0, bz1 = -w * .30, w * .30, -d * .18, d * .30
        cx, cz = (bx0 + bx1) / 2, (bz0 + bz1) / 2
        bottom = parts['basin-bottom']
        cavity_lo, cavity_hi = bottom[5] + .02, min(b[4] for n, b in parts.items() if n.startswith('counter-'))
        self.assertLess(cavity_lo, cavity_hi)  # there IS an open vertical band above the bowl
        for name, (x0, x1, z0, z1, y0, y1) in parts.items():
            if name in ('basin-bottom',) or name.startswith('basin-'):
                continue
            spans_cavity = y0 < cavity_hi - .01 and y1 > cavity_lo + .01
            over_basin = x0 - 1e-9 <= cx <= x1 + 1e-9 and z0 - 1e-9 <= cz <= z1 + 1e-9
            self.assertFalse(spans_cavity and over_basin, name)

    def test_washer_door_opening_faces_front(self):
        # review R3: a circle in the vertical front plane (kind='disc'), and
        # the glass proud of the rim so it reads as a round porthole.
        w, d, h = .64, .72, 1.05
        parts = {p['name']: p for p in washer_parts(w, d, h)}
        rim, glass = parts['door-rim'], parts['door-glass']
        self.assertEqual(rim['kind'], 'disc')
        self.assertEqual(glass['kind'], 'disc')
        self.assertGreater(glass['bounds'][3], rim['bounds'][3])          # glass front is proud of rim front
        self.assertLess(glass['bounds'][1] - glass['bounds'][0], rim['bounds'][1] - rim['bounds'][0])  # smaller
        self.assertGreater(rim['bounds'][3], d / 2 - .05)                 # on the washer's front face

    def test_reject_ambiguous_or_incompatible_bindings(self):
        duplicate=copy.deepcopy(self.bindings)
        duplicate['bindings']*=2
        with self.assertRaisesRegex(ValueError,'Duplicate'): validate_bindings(duplicate,self.items,self.catalog)
        for field,value in [('assetId','missing'),('sizing','stretch'),('furnitureId','fur-045')]:
            wrong=copy.deepcopy(self.bindings);wrong['bindings'][0][field]=value
            with self.assertRaises(ValueError): validate_bindings(wrong,self.items,self.catalog)


if __name__=='__main__': unittest.main()
