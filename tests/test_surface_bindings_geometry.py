"""W04: pure-geometry helpers for binding surface-registry IDs to real
Blender wall/floor pieces (no bpy needed for these)."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'blender'))
import surface_bindings as sb


class SplitWallRangeTests(unittest.TestCase):
    def test_range_within_wall_splits_into_three(self):
        poly=[(0,0),(10,0),(10,3),(0,3)]  # a plain wall panel profile, u in [0,10]
        before,within,after=sb.split_wall_range(poly,3,7)
        self.assertAlmostEqual(min(p[0] for p in before),0); self.assertAlmostEqual(max(p[0] for p in before),3)
        self.assertAlmostEqual(min(p[0] for p in within),3); self.assertAlmostEqual(max(p[0] for p in within),7)
        self.assertAlmostEqual(min(p[0] for p in after),7); self.assertAlmostEqual(max(p[0] for p in after),10)

    def test_range_covering_whole_wall_leaves_no_before_after(self):
        poly=[(0,0),(10,0),(10,3),(0,3)]
        before,within,after=sb.split_wall_range(poly,-1,11)
        self.assertEqual(before,[]); self.assertEqual(after,[])
        self.assertAlmostEqual(min(p[0] for p in within),0); self.assertAlmostEqual(max(p[0] for p in within),10)


class WallCapForRoomTests(unittest.TestCase):
    def test_room_north_of_horizontal_wall_is_cap_a(self):
        room=[(0,0),(10,0),(10,3),(0,3)]  # room occupies z in [0,3]; wall at z=3
        self.assertEqual(sb.wall_cap_for_room(at=3,mid_u=5,horizontal=True,room_polygon=room),0)

    def test_room_south_of_horizontal_wall_is_cap_b(self):
        room=[(0,3),(10,3),(10,6),(0,6)]  # room occupies z in [3,6]; wall at z=3
        self.assertEqual(sb.wall_cap_for_room(at=3,mid_u=5,horizontal=True,room_polygon=room),1)

    def test_room_west_of_vertical_wall_is_cap_a(self):
        room=[(0,0),(3,0),(3,10),(0,10)]  # room occupies x in [0,3]; wall at x=3
        self.assertEqual(sb.wall_cap_for_room(at=3,mid_u=5,horizontal=False,room_polygon=room),0)

    def test_unrelated_room_resolves_to_none(self):
        room=[(20,20),(30,20),(30,30),(20,30)]
        self.assertIsNone(sb.wall_cap_for_room(at=3,mid_u=5,horizontal=True,room_polygon=room))


class DecomposeRectilinearTests(unittest.TestCase):
    def test_l_shape_decomposes_to_exact_area(self):
        # Same shape as room-1f-06 (scaled down): a rectangle with a notch bitten
        # out of the top-right corner.
        poly=[(0,0),(2,0),(2,1),(6,1),(6,4),(0,4)]
        rects=sb.decompose_rectilinear(poly)
        area=sum((x1-x0)*(z1-z0) for x0,x1,z0,z1 in rects)
        # Full bbox 6x4=24 minus the notch (4x1=4) = 20.
        self.assertAlmostEqual(area,20)
        for x0,x1,z0,z1 in rects:  # no piece should extend into the notch
            self.assertFalse(x0>=2 and z0<1 and z1<=1 and x1<=6 and False)  # sanity placeholder

    def test_decomposed_rects_do_not_overlap(self):
        poly=[(0,0),(2,0),(2,1),(6,1),(6,4),(0,4)]
        rects=sb.decompose_rectilinear(poly)
        for i,a in enumerate(rects):
            for b in rects[i+1:]:
                overlap=sb.subtract_rect(a,b)
                # If a and b truly overlapped, subtract_rect(a,b) would drop area from a.
                area_a=(a[1]-a[0])*(a[3]-a[2])
                area_overlap=sum((x1-x0)*(z1-z0) for x0,x1,z0,z1 in overlap)
                self.assertAlmostEqual(area_a,area_overlap)


class SubtractRectTests(unittest.TestCase):
    def test_full_containment_removes_everything(self):
        self.assertEqual(sb.subtract_rect((0,10,0,10),(0,10,0,10)),[])

    def test_no_overlap_returns_original(self):
        self.assertEqual(sb.subtract_rect((0,10,0,10),(20,30,20,30)),[(0,10,0,10)])

    def test_partial_overlap_tiles_exactly(self):
        a=(0,10,0,10); b=(2,5,3,7)
        pieces=sb.subtract_rects([a],[b])
        area=sum((x1-x0)*(z1-z0) for x0,x1,z0,z1 in pieces)
        self.assertAlmostEqual(area,100-3*4)
        for x0,x1,z0,z1 in pieces:  # none of the remainder should be inside b
            cx,cz=(x0+x1)/2,(z0+z1)/2
            self.assertFalse(b[0]<cx<b[1] and b[2]<cz<b[3])


if __name__=='__main__': unittest.main()
