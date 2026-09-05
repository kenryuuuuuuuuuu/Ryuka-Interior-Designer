"""Regression cases for GL height, piecewise tops, arches, and shared ceiling areas."""
import json
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
from interior_geometry import arch_top, ceiling_y, height_runs, point_in_room, wall_polygons


class InteriorGeometryTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'data/house.json').read_text(encoding='utf-8'))
        self.data['envelope']=json.loads((ROOT/'generated/visual-envelope.json').read_text(encoding='utf-8'))

    def test_absolute_gl_height_and_piecewise_wall(self):
        p=next(p for p in self.data['envelope']['slopedCeilingPieces'] if p['roomId']=='room-1f-06')
        self.assertAlmostEqual(ceiling_y(self.data,p,6.37),4.2055)
        wall=dict(orientation='V',x0=7.28,z0=.91,z1=6.37,level=1)
        runs=height_runs(self.data,wall)
        self.assertAlmostEqual(runs[0][2],3.107)
        self.assertAlmostEqual(runs[-1][3],4.2055)
        self.assertTrue(any(abs(r[1]-2.73)<1e-6 for r in runs))

    def test_ceiling_area_matches_room(self):
        for room in self.data['rooms']:
            if room.get('ceiling')!='sloped': continue
            polygon=room['polygon']
            expected=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(polygon,polygon[1:]+polygon[:1])))/2
            pieces=[p for p in self.data['envelope']['slopedCeilingPieces'] if p['roomId']==room['id']]
            self.assertAlmostEqual(sum((p['x1']-p['x0'])*(p['z1']-p['z0']) for p in pieces),expected)
        hole=self.data['stairs'][0]['opening']
        for slab in self.data['envelope']['slabs']:
            if slab['level']!=2: continue
            self.assertFalse(min(slab['x1'],hole['x1'])>max(slab['x0'],hole['x0']) and
                             min(slab['z1'],hole['z1'])>max(slab['z0'],hole['z0']))

    def test_arch_is_open_below_and_solid_above(self):
        o=dict(start=0,end=.91,bottom=.707,top=2.807,operation='open-arch',archRise=.3)
        self.assertAlmostEqual(arch_top(o,.455),2.807)
        self.assertAlmostEqual(arch_top(o,0),2.507)
        wall=dict(level=2,orientation='H',x0=0,x1=.91,z0=0)
        # Synthetic floor at .707 isolates the arch shape from the real building.
        data=dict(self.data,levels=dict(self.data['levels'],fl2=.707))
        polys=wall_polygons(data,wall,[o])
        self.assertTrue(polys)
        self.assertTrue(all(y>=arch_top(o,x)-1e-6 for poly in polys for x,y in poly))
        self.assertTrue(any(y>2.9 for poly in polys for x,y in poly))

    def test_room_membership_respects_concave_notch(self):
        room=next(r for r in self.data['rooms'] if r['id']=='room-1f-06')
        self.assertTrue(point_in_room(2.2,3.1,room['polygon']))
        self.assertTrue(point_in_room(5,5,room['polygon']))
        self.assertFalse(point_in_room(5,3.1,room['polygon']))
        self.assertFalse(point_in_room(8,5,room['polygon']))

    def test_floating_point_seams_do_not_make_zero_width_solids(self):
        w=dict(level=2,orientation='H',x0=0,x1=3,z0=0)
        ops=[dict(start=.8,end=1.6,bottom=3.439,top=5.439),
             dict(start=1.6000000000000003,end=2.4,bottom=3.439,top=5.439)]
        polys=wall_polygons(self.data,w,ops)
        self.assertTrue(all(max(x for x,y in p)-min(x for x,y in p)>=1e-6 for p in polys))


if __name__=='__main__': unittest.main()
