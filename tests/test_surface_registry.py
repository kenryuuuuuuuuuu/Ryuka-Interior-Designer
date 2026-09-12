"""W03-C: persistent surface identities -- registration validation and
resolution against the current house.json shape. Representative normal path
and simple failure paths, per docs/tasks/W03-C-surface-identities.md's
lightweight acceptance scope."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import surface_registry as sr


def room(id,polygon,status='estimated',ceiling=None):
    r=dict(id=id,level='1F',label=id,polygon=polygon,status=status,note='')
    if ceiling: r['ceiling']=ceiling
    return r

def wall(id,room_id,edge,label='Wall'):
    return dict(id=id,roomId=room_id,kind='wall',label=label,note='',edge=edge)

def floor(id,room_id,label='Floor'):
    return dict(id=id,roomId=room_id,kind='floor',label=label,note='')

def ceiling(id,room_id,label='Ceiling'):
    return dict(id=id,roomId=room_id,kind='ceiling',label=label,note='')


SQUARE_A=[[0,0],[2,0],[2,2],[0,2]]  # room-a: 4 edges


class SurfaceRegistryTests(unittest.TestCase):
    def test_real_registry_resolves_against_real_house(self):
        # W07-G1: 8 (LDK) + 8 (洋室). W07-G3: + 6 rooms x (4 walls + floor +
        # ceiling) = 36 more;玄関/ホール/トイレ/洗面脱衣/UB/収納 are all
        # 4-vertex rectangles. Every registered surface must still resolve.
        result=sr.resolve_from(ROOT)
        self.assertEqual(result['issues'],[])
        self.assertEqual(len(result['surfaces']),216)
        self.assertTrue(all(s['status']=='resolved' for s in result['surfaces']))

    # --- acceptance 2: reorder/reversed vertices, shared-wall two rooms ---

    def test_vertex_order_and_endpoint_reversal_keep_the_same_id_resolved(self):
        registry=dict(schemaVersion='1.0.0',surfaces=[wall('w1','room-a',[[2,0],[2,2]])])  # reversed endpoint order
        reordered=list(reversed(SQUARE_A))  # polygon starts at a different vertex, reverse winding
        rooms=[room('room-a',reordered)]
        result=sr.resolve(registry,rooms)
        self.assertEqual(result['issues'],[])
        self.assertEqual(result['surfaces'][0]['status'],'resolved')

    def test_shared_wall_both_room_sides_resolve_as_distinct_ids(self):
        # Two adjacent rooms sharing the edge (2,0)-(2,2); each registers its
        # own id under its own roomId with the same coordinates.
        registry=dict(schemaVersion='1.0.0',surfaces=[
            wall('w-a','room-a',[[2,0],[2,2]]),
            wall('w-b','room-b',[[2,0],[2,2]]),
        ])
        rooms=[room('room-a',SQUARE_A),room('room-b',[[2,0],[4,0],[4,2],[2,2]])]
        result=sr.resolve(registry,rooms)
        self.assertEqual(result['issues'],[])
        ids_status={s['id']:s['status'] for s in result['surfaces']}
        self.assertEqual(ids_status,{'w-a':'resolved','w-b':'resolved'})

    # --- acceptance 3: edge move/split -> unresolved, then explicit update resolves ---

    def test_moved_wall_is_unresolved_until_registry_is_updated(self):
        registry=dict(schemaVersion='1.0.0',surfaces=[wall('w1','room-a',[[0,0],[2,0]])])
        moved=[[0,0],[2,0.5],[2,2],[0,2]]  # that edge no longer exists at the old coordinates
        result=sr.resolve(registry,[room('room-a',moved)])
        self.assertEqual(result['surfaces'][0]['status'],'unresolved')
        self.assertEqual(len(result['issues']),1)
        self.assertIn('w1',result['issues'][0]['id'])
        # Explicit registry update to the new edge resolves it again, same id.
        registry['surfaces'][0]['edge']=[[0,0],[2,0.5]]
        result2=sr.resolve(registry,[room('room-a',moved)])
        self.assertEqual(result2['surfaces'][0]['status'],'resolved')
        self.assertEqual(result2['issues'],[])

    def test_split_wall_leaves_old_id_unresolved_not_auto_migrated(self):
        registry=dict(schemaVersion='1.0.0',surfaces=[wall('w1','room-a',[[0,0],[2,0]])])
        split=[[0,0],[1,0],[2,0],[2,2],[0,2]]  # the (0,0)-(2,0) edge is now two edges
        result=sr.resolve(registry,[room('room-a',split)])
        self.assertEqual(result['surfaces'][0]['status'],'unresolved')

    def test_removed_room_is_unresolved(self):
        registry=dict(schemaVersion='1.0.0',surfaces=[wall('w1','room-gone',[[0,0],[2,0]])])
        result=sr.resolve(registry,[room('room-a',SQUARE_A)])
        self.assertEqual(result['surfaces'][0]['status'],'unresolved')
        self.assertIn('room-gone',result['issues'][0]['reason'])

    # --- acceptance 3: one simple duplicate-id failure ---

    def test_duplicate_id_is_rejected(self):
        registry=dict(schemaVersion='1.0.0',surfaces=[
            wall('dup','room-a',[[0,0],[2,0]]),
            floor('dup','room-a'),
        ])
        with self.assertRaises(ValueError):
            sr.resolve(registry,[room('room-a',SQUARE_A)])

    def test_duplicate_wall_edge_in_same_room_is_rejected(self):
        registry=dict(schemaVersion='1.0.0',surfaces=[
            wall('w1','room-a',[[0,0],[2,0]]),
            wall('w2','room-a',[[2,0],[0,0]]),  # same edge, reversed
        ])
        with self.assertRaises(ValueError):
            sr.resolve(registry,[room('room-a',SQUARE_A)])

    def test_unregistered_other_room_is_not_an_error(self):
        registry=dict(schemaVersion='1.0.0',surfaces=[floor('f-a','room-a')])
        result=sr.resolve(registry,[room('room-a',SQUARE_A),room('room-b',SQUARE_A)])
        self.assertEqual(result['issues'],[])

    def test_missing_or_malformed_registry_is_a_hard_error_not_empty_success(self):
        with self.assertRaises(ValueError): sr.resolve(dict(schemaVersion='9.9.9',surfaces=[]),[room('room-a',SQUARE_A)])
        with self.assertRaises(ValueError): sr.resolve(dict(schemaVersion='1.0.0'),[room('room-a',SQUARE_A)])

    def test_floor_and_ceiling_track_current_room_shape(self):
        registry=dict(schemaVersion='1.0.0',surfaces=[floor('f1','room-a'),ceiling('c1','room-a')])
        bigger=[[0,0],[3,0],[3,3],[0,3]]
        result=sr.resolve(registry,[room('room-a',bigger,ceiling='sloped')])
        f=next(s for s in result['surfaces'] if s['id']=='f1')
        c=next(s for s in result['surfaces'] if s['id']=='c1')
        self.assertEqual(f['status'],'resolved'); self.assertEqual(f['polygon'],bigger)
        self.assertEqual(c['ceiling'],'sloped')


if __name__=='__main__': unittest.main()
