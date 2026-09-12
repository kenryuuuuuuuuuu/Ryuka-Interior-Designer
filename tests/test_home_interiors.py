"""W07-H: regressions for vertically overlapping rooms and diagonal floors."""
import json,sys,unittest,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name in ('blender','unreal','scripts'):sys.path.insert(0,str(ROOT/name))
from stair_geometry import layout, wall_clearances
from surface_bindings import partition_room_faces
import circulation
from electrical_assets import ceiling_height_at

def read(name):return json.loads((ROOT/name).read_text(encoding='utf8'))
def area(poly):return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2

class HomeInteriorsTests(unittest.TestCase):
 def test_scopes_preserve_guest_and_cover_whole(self):
  s={x['scopeId']:set(x['roomIds']) for x in read('data/visual/study-scopes.json')['scopes']}
  self.assertEqual(len(s['home']),25);self.assertEqual(len(s['guest']),8)
  self.assertFalse(s['home']&s['guest']);self.assertEqual(s['whole'],s['home']|s['guest'])
 def test_all_doors_resolve_on_their_own_floor(self):
  house=read('data/house.json');rooms={r['id']:r for r in house['rooms']}
  doors=read('data/interior-doors.json')['items'];catalog={x['type']:x for x in read('data/door-catalog.json')['types']}
  resolved=circulation.resolve_connections(rooms,doors,catalog,rooms)
  self.assertEqual({x['id'] for x in resolved},{x['id'] for x in doors})
  for c in resolved:self.assertTrue(all(rooms[r]['level']==c['level'] for r in c['roomIds']))
  self.assertEqual(next(c for c in resolved if c['id']=='door-020')['roomIds'],['room-1f-08','room-1f-19'])
 def test_floor_ownership_does_not_round_diagonal(self):
  rooms=[r for r in read('data/house.json')['rooms'] if r['id'] in ('room-1f-08','room-1f-19')]
  cells=partition_room_faces((9.1,10.92,.455,2.73),rooms)
  for room in rooms:self.assertAlmostEqual(sum(area(p) for p,rid in cells if rid==room['id']),area(room['polygon']),places=7)
  self.assertAlmostEqual(sum(area(p) for p,rid in cells),1.82*2.275,places=7)
 def test_stair_lights_mount_to_real_ceiling_not_void(self):
  h=read('data/house.json');h['envelope']=read('generated/visual-envelope.json')
  self.assertAlmostEqual(ceiling_height_at(h,14.11,.91,'room-1f-10'),h['levels']['fl2']+h['defaults']['ceilingHeight'])
  pantry=ceiling_height_at(h,15.02,1.37,'room-1f-21')
  self.assertLess(pantry,h['levels']['fl2']);self.assertGreater(pantry,h['levels']['fl1']+1.8)
 def test_pantry_partition_stops_under_crossing_stair(self):
  h=read('data/house.json')
  walls=read('generated/interior-walls.json')['walls']
  north=next(w for w in walls if w['id']=='wall-1f-auto-019')
  cuts=wall_clearances(north,h)
  self.assertEqual(len(cuts),1)
  self.assertLess(cuts[0]['bottom'],h['levels']['fl1']+h['defaults']['ceilingHeight'])
  self.assertEqual(cuts[0]['derivedFrom'],h['stairs'][0]['id'])
  external=dict(north,id='wall-ext-test')
  self.assertEqual(wall_clearances(external,h),[])
 def test_stairs_keep_source_rise_area_and_pantry_void(self):
  h=read('data/house.json');source=h['stairs'][0];resolved=layout(source,h['levels']);steps=resolved['steps']
  self.assertEqual(len(steps),source['totalSteps']);self.assertEqual(resolved['note'],source['note'])
  self.assertAlmostEqual(steps[-1]['top'],h['levels']['fl2'])
  for i,step in enumerate(steps):
   self.assertGreater(step['top']-step['bottom'],0)
   if i:self.assertAlmostEqual(step['bottom'],steps[i-1]['top'])
   for poly in step['polygons']:self.assertGreater(area(poly),0)
  # Two straight flights and a half-disc: gaps/overlapping turn polygons
  # would change this independently calculated area.
  self.assertAlmostEqual(sum(area(p) for s in steps for p in s['polygons']),2*.91**2+math.pi*.91**2/2,delta=.004)
  last=steps[-1];self.assertGreater(last['bottom']-h['levels']['fl1'],2.4)

if __name__=='__main__':unittest.main()


class HomeFurnitureDetails(unittest.TestCase):
    def test_bed_keeps_source_envelope_and_distinct_mattress(self):
        from furniture_assets import bed_parts
        parts=bed_parts(.97,1.95,.5)
        self.assertEqual(max(p['bounds'][5] for p in parts),.5)
        self.assertEqual(next(p for p in parts if p['name']=='mattress')['material'],'fabric')

    def test_desk_has_open_knee_space(self):
        from furniture_assets import desk_parts
        parts=desk_parts(1.1,.6,.72)
        self.assertEqual(len(parts),5)
        self.assertFalse(any(p['bounds'][0]<0<p['bounds'][1] and p['bounds'][2]<0<p['bounds'][3] and p['bounds'][4]<.4<p['bounds'][5] for p in parts))
