"""W06: electrical fixture mount resolution (blender/electrical_assets.py) --
the wall/ceiling contract data/electrical.json already defines for the Web
editor, but resolved against the ACTUAL (possibly sloped) ceiling height,
never a flat assumption. Pure Python; no bpy needed for these functions."""
import json
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
sys.path.insert(0,str(ROOT/'unreal'))
from electrical_assets import merged_item, ceiling_height_at, resolve_mount, build_lighting_bindings
from interior_geometry import ceiling_y


class ElectricalAssetsTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'data/house.json').read_text(encoding='utf-8'))
        self.data['envelope']=json.loads((ROOT/'generated/visual-envelope.json').read_text(encoding='utf-8'))
        self.electrical=json.loads((ROOT/'data/electrical.json').read_text(encoding='utf-8'))
        self.catalog=json.loads((ROOT/'data/electrical-catalog.json').read_text(encoding='utf-8'))
        self.catalog_by_type={t['type']:t for t in self.catalog['types']}
        self.settings=json.loads((ROOT/'data/visual/lighting-settings.json').read_text(encoding='utf-8'))

    def test_merged_item_applies_catalog_defaults_and_overrides(self):
        item=next(i for i in self.electrical['items'] if i['id']=='elec-008')  # no overrides
        merged=merged_item(item,self.catalog_by_type)
        self.assertEqual(merged['mount'],'ceiling'); self.assertEqual(merged['mountHeight'],0)
        item=next(i for i in self.electrical['items'] if i['id']=='elec-201')  # mountHeightOverride=1.9
        merged=merged_item(item,self.catalog_by_type)
        self.assertEqual(merged['mountHeight'],1.9)

    def test_merged_item_rejects_unknown_type(self):
        with self.assertRaises(ValueError):
            merged_item(dict(id='x',type='light-does-not-exist'),self.catalog_by_type)

    def test_ceiling_height_matches_shared_ceiling_y(self):
        piece=next(p for p in self.data['envelope']['slopedCeilingPieces'] if p['roomId']=='room-1f-06')
        self.assertAlmostEqual(ceiling_height_at(self.data,4.65,4.55,'room-1f-06'),ceiling_y(self.data,piece,4.55))

    def test_ceiling_height_flat_room_uses_default_directly(self):
        # A room NOT marked ceiling:sloped is a legitimate flat ceiling --
        # resolved directly from defaults, no piece lookup/raise involved.
        flat_room=next(r for r in self.data['rooms'] if r.get('ceiling')!='sloped')
        expected=self.data['levels'][f"fl{flat_room['level']}"]+self.data['defaults']['ceilingHeight']
        # Any (x,z) at all -- even one nowhere near this room -- must resolve
        # for a flat room, since ceiling_height_at() never searches pieces for it.
        self.assertAlmostEqual(ceiling_height_at(self.data,-500,-500,flat_room['id']),expected)

    def test_ceiling_height_unresolved_point_in_sloped_room_raises(self):
        # W06-v1 review R1: a point OUTSIDE every one of room-1f-06's own
        # registered pieces must be a distinct, loud failure -- never quietly
        # treated the same as an ordinary flat ceiling.
        with self.assertRaises(ValueError):
            ceiling_height_at(self.data,-500,-500,'room-1f-06')

    def test_resolve_mount_ceiling_matches_known_real_values(self):
        # Cross-checked once against a real Blender build (W06 report AC1).
        item=next(i for i in self.electrical['items'] if i['id']=='elec-008')
        merged=merged_item(item,self.catalog_by_type)
        mount=resolve_mount(self.data,merged)
        x,y,z=mount['positionM']
        self.assertAlmostEqual(x,4.65); self.assertAlmostEqual(z,4.55); self.assertAlmostEqual(y,3.9325)
        self.assertEqual(mount['rotYDeg'],0.0)
        # W06-v1 review R2: the light's own position is the housing's
        # underside (positionM minus the fixture's own height), never the
        # mount origin/top itself -- avoids embedding the light in the ceiling.
        self.assertAlmostEqual(mount['emitPositionM'][1],y-merged['height'])
        self.assertEqual(mount['emitPositionM'][0],x); self.assertEqual(mount['emitPositionM'][2],z)

    def test_resolve_mount_ceiling_pendant_honours_override(self):
        item=next(i for i in self.electrical['items'] if i['id']=='elec-201')
        merged=merged_item(item,self.catalog_by_type)
        mount=resolve_mount(self.data,merged)
        piece=next(p for p in self.data['envelope']['slopedCeilingPieces'] if p['roomId']=='room-1f-06')
        expected_y=ceiling_y(self.data,piece,merged['z'])-1.9
        self.assertAlmostEqual(mount['positionM'][1],expected_y)
        self.assertAlmostEqual(mount['emitPositionM'][1],expected_y-merged['height'])

    def test_resolve_mount_wall_representative_coordinates(self):
        # W06 AC1: "壁付けは小さな座標テストで可" -- no light-bracket instance
        # exists in data/electrical.json yet, so this exercises the wall
        # contract directly with a synthetic instance covering both
        # orientations/sides.
        base=dict(id='synthetic-bracket',type='light-bracket',level=1,orientation='H',
            wallAt=2.0,center=5.0,side=1)
        merged=merged_item(base,self.catalog_by_type)
        mount=resolve_mount(self.data,merged)
        self.assertEqual(mount['positionM'],[5.0,self.data['levels']['fl1']+merged['mountHeight'],2.0])
        self.assertEqual(mount['rotYDeg'],0.0)
        # A wall mount's positionM is already the housing's centre -- no
        # separate emission offset needed (unlike a ceiling mount).
        self.assertEqual(mount['emitPositionM'],mount['positionM'])
        mount_side_negative=resolve_mount(self.data,dict(merged,side=-1))
        self.assertEqual(mount_side_negative['rotYDeg'],180.0)
        merged_v=merged_item(dict(base,orientation='V',side=1),self.catalog_by_type)
        mount_v=resolve_mount(self.data,merged_v)
        self.assertEqual(mount_v['positionM'],[2.0,self.data['levels']['fl1']+merged['mountHeight'],5.0])
        self.assertEqual(mount_v['rotYDeg'],90.0)
        mount_v_negative=resolve_mount(self.data,dict(merged_v,side=-1))
        self.assertEqual(mount_v_negative['rotYDeg'],-90.0)

    def test_resolve_mount_rejects_unsupported_mount(self):
        merged=dict(mount='exterior',level=1,mountHeight=0)
        with self.assertRaises(ValueError): resolve_mount(self.data,merged)

    def test_build_lighting_bindings_room_1f_06(self):
        bindings=build_lighting_bindings(self.data,self.electrical,self.catalog,self.settings,'room-1f-06')
        self.assertEqual(sorted(f['id'] for f in bindings['fixtures']),['elec-008','elec-200','elec-201'])
        for fixture in bindings['fixtures']:
            # W06 spec: ceiling fixtures' light direction is always straight
            # down (source convention: x east/y UP/z south, so "down" is a
            # negative Y component -- W06-v1 review R2 caught an earlier
            # version of this test asserting the wrong [0,0,-1], which is
            # horizontal), decoupled from the (sloped) mount surface's own tilt.
            self.assertEqual(fixture['directionVector'],[0.0,-1.0,0.0])
            self.assertIn('emitPositionM',fixture)

    def test_build_lighting_bindings_rejects_unsupported_lighting_type(self):
        electrical=dict(self.electrical,items=self.electrical['items']+[
            dict(id='test-exterior',type='light-exterior',level=1,room='room-1f-06',face='N',offset=0,label='x',status='estimated')])
        with self.assertRaises(ValueError):
            build_lighting_bindings(self.data,electrical,self.catalog,self.settings,'room-1f-06')

    def test_build_lighting_bindings_rejects_missing_profile(self):
        settings=json.loads(json.dumps(self.settings))
        del settings['profiles']['light-ceiling']
        with self.assertRaises(ValueError):
            build_lighting_bindings(self.data,self.electrical,self.catalog,settings,'room-1f-06')

    def test_build_lighting_bindings_rejects_unknown_type(self):
        electrical=dict(self.electrical,items=self.electrical['items']+[
            dict(id='test-unknown',type='light-does-not-exist',level=1,room='room-1f-06',x=0,z=0,label='x',status='estimated')])
        with self.assertRaises(ValueError):
            build_lighting_bindings(self.data,electrical,self.catalog,self.settings,'room-1f-06')

    def test_build_lighting_bindings_empty_room_rejected(self):
        with self.assertRaises(ValueError):
            build_lighting_bindings(self.data,self.electrical,self.catalog,self.settings,'room-does-not-exist')


if __name__=='__main__': unittest.main()
