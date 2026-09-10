"""W07-G2: door/room connectivity must resolve from geometry alone, never
from interior-doors.json's own (partly stale) label text -- see
docs/tasks/W07-G2-guest-circulation.md section 1's door-002/004 example."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'unreal'))
import circulation as circ

GUEST_ROOM_IDS = ['room-1f-02', 'room-1f-24', 'room-1f-06', 'room-1f-05',
                  'room-1f-01', 'room-1f-03', 'room-1f-04', 'room-1f-23']


class RealDataConnectivityTests(unittest.TestCase):
    """Against the actual repo data -- the representative normal case."""

    def setUp(self):
        house = json.loads((ROOT / 'data/house.json').read_text(encoding='utf-8'))
        self.rooms_by_id = {r['id']: r for r in house['rooms']}
        self.doors = json.loads((ROOT / 'data/interior-doors.json').read_text(encoding='utf-8'))['items']
        self.catalog = {t['type']: t for t in json.loads((ROOT / 'data/door-catalog.json').read_text(encoding='utf-8'))['types']}
        self.connections = circ.resolve_connections(self.rooms_by_id, self.doors, self.catalog, GUEST_ROOM_IDS)
        self.by_id = {c['id']: c for c in self.connections}

    def test_all_eight_guest_rooms_are_connected_via_seven_doors(self):
        self.assertEqual(len(self.connections), 7)
        rooms_touched = {r for c in self.connections for r in c['roomIds']}
        self.assertEqual(rooms_touched, set(GUEST_ROOM_IDS))

    def test_mislabelled_doors_resolve_by_geometry_not_label(self):
        # door-002's label says 玄関⟷洗面脱衣室 but its actual coordinates
        # sit on the hall/LDK boundary; door-004's label says 玄関⟷LDK張り出し
        # but it actually sits on the hall/洗面脱衣 boundary (spec section 1).
        self.assertEqual(self.by_id['door-002']['roomIds'], sorted(['room-1f-24', 'room-1f-06']))
        self.assertEqual(self.by_id['door-004']['roomIds'], sorted(['room-1f-24', 'room-1f-03']))
        # door-001's label says トイレ⟷玄関 but it actually sits on the
        # hall/toilet boundary (room-1f-02, the genkan, does not reach z=2.33).
        self.assertEqual(self.by_id['door-001']['roomIds'], sorted(['room-1f-24', 'room-1f-01']))

    def test_ldk_and_western_room_connect_only_via_the_hall(self):
        # No direct opening between LDK and the western room was fabricated.
        direct = [c for c in self.connections if set(c['roomIds']) == {'room-1f-06', 'room-1f-05'}]
        self.assertEqual(direct, [])

    def test_operations_match_catalog(self):
        self.assertEqual(self.by_id['door-002']['operation'], 'swing')
        self.assertEqual(self.by_id['door-001']['operation'], 'slide')
        self.assertEqual(self.by_id['door-024']['operation'], 'double-swing')
        self.assertEqual(self.by_id['door-025']['operation'], 'open')

    def test_a_door_entirely_outside_the_profile_is_skipped_not_an_error(self):
        # door-009 ("SC⟷LDK") sits far outside this profile's room set.
        self.assertNotIn('door-009', self.by_id)

    def test_unknown_door_type_raises(self):
        bad_doors = self.doors + [dict(id='door-x', type='door-does-not-exist', orientation='H',
                                        wallAt=2.73, center=2.26, floor=1)]
        with self.assertRaises(ValueError):
            circ.resolve_connections(self.rooms_by_id, bad_doors, self.catalog, GUEST_ROOM_IDS)

    def test_double_swing_leaves_open_toward_the_same_room_not_opposite_rooms(self):
        # W07-G2 review R3: the previous code gave door-024's two leaves the
        # SAME signed openYawDeltaDeg (both -85), which sends one leaf toward
        # 洋室 and the other toward 収納 (mirrored hinges swinging the same
        # angular direction end up in DIFFERENT rooms) -- both must swing
        # into the SAME target room instead, which for mirrored hinges means
        # OPPOSITE-signed deltas of equal magnitude.
        hinges_and_deltas = circ.double_swing_hinges_and_deltas(self.by_id['door-024'])
        deltas = {kind: delta for _, delta, kind in hinges_and_deltas}
        self.assertEqual(abs(deltas['left']), abs(deltas['right']))
        self.assertNotEqual(deltas['left'], deltas['right'])
        self.assertEqual(deltas['left'], -deltas['right'])


class SyntheticGeometryTests(unittest.TestCase):
    """Small synthetic fixtures for edge cases the real data does not cover."""

    def test_span_wider_than_room_edge_is_not_a_match(self):
        rooms = {'a': dict(polygon=[[0, 0], [2, 0], [2, 2], [0, 2]]),
                 'b': dict(polygon=[[2, 0], [4, 0], [4, 2], [2, 2]])}
        # A door whose span exceeds the room edge's own extent must not match.
        self.assertFalse(circ.room_boundary_contains_span(rooms['a']['polygon'], False, 2, 1.5, 2.5))
        self.assertTrue(circ.room_boundary_contains_span(rooms['a']['polygon'], False, 2, 0.5, 1.5))

    def test_reversed_edge_winding_still_matches(self):
        polygon = list(reversed([[0, 0], [2, 0], [2, 2], [0, 2]]))
        self.assertTrue(circ.room_boundary_contains_span(polygon, False, 2, 0.5, 1.5))

    def test_door_touching_only_one_room_in_scope_is_skipped(self):
        rooms_by_id = {'a': dict(polygon=[[0, 0], [2, 0], [2, 2], [0, 2]]),
                       'b': dict(polygon=[[2, 0], [4, 0], [4, 2], [2, 2]])}
        catalog = {'door-hinged': dict(type='door-hinged', operation='swing', width=0.8, height=2, sill=0)}
        doors = [dict(id='door-x', type='door-hinged', orientation='V', wallAt=2, center=1, floor=1)]
        self.assertEqual(circ.resolve_connections(rooms_by_id, doors, catalog, ['a']), [])

    def test_door_matching_three_rooms_raises(self):
        # A degenerate/malformed layout where three room polygons all share
        # the same edge span -- a door cannot physically connect three rooms.
        rooms_by_id = {'a': dict(polygon=[[0, 0], [2, 0], [2, 2], [0, 2]]),
                       'b': dict(polygon=[[2, 0], [4, 0], [4, 2], [2, 2]]),
                       'c': dict(polygon=[[2, 0], [4, 0], [4, 2], [2, 2]])}
        catalog = {'door-hinged': dict(type='door-hinged', operation='swing', width=0.8, height=2, sill=0)}
        doors = [dict(id='door-x', type='door-hinged', orientation='V', wallAt=2, center=1, floor=1)]
        with self.assertRaises(ValueError):
            circ.resolve_connections(rooms_by_id, doors, catalog, ['a', 'b', 'c'])


class DoorOverridesTests(unittest.TestCase):
    def setUp(self):
        self.bindings = dict(schemaVersion='1.0.0', doors={
            'door-002': dict(operation='swing', roomIds=['room-1f-06', 'room-1f-24'], openable=True,
                              leaves=[dict(actor='opening_door-002_closed-leaf', kind='single', openYawDeltaDeg=85.0)]),
            'door-025': dict(operation='open', roomIds=['room-1f-02', 'room-1f-24'], openable=False, leaves=[]),
        })

    def test_usable_and_unknown_split(self):
        usable, issues = circ.resolve_door_overrides(
            {'door-002': dict(open=True), 'door-does-not-exist': dict(open=True)}, self.bindings)
        self.assertEqual(usable, {'door-002': dict(open=True)})
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]['id'], 'door-does-not-exist')

    def test_non_openable_door_is_an_issue_not_silently_accepted(self):
        usable, issues = circ.resolve_door_overrides({'door-025': dict(open=True)}, self.bindings)
        self.assertEqual(usable, {})
        self.assertEqual(len(issues), 1)

    def test_effective_open_defaults_closed(self):
        self.assertFalse(circ.effective_door_open('door-002', {}))
        self.assertTrue(circ.effective_door_open('door-002', {'door-002': dict(open=True)}))


class ValidateDoorBindingsTests(unittest.TestCase):
    def test_rejects_openable_door_with_no_leaves(self):
        with self.assertRaises(ValueError):
            circ.validate_door_bindings(dict(schemaVersion='1.0.0', doors={
                'door-002': dict(operation='swing', roomIds=['a', 'b'], openable=True, leaves=[])}))

    def test_valid_document_passes(self):
        doc = dict(schemaVersion='1.0.0', doors={
            'door-025': dict(operation='open', roomIds=['a', 'b'], openable=False, leaves=[])})
        self.assertEqual(circ.validate_door_bindings(doc), doc)

    def test_rejects_leaf_missing_baked_open(self):
        # W07-G2 review R1: a leaf's INITIAL pose must be traceable back to
        # what generation actually baked, regardless of whichever doorStates
        # happens to be active later -- bakedOpen is required, not optional.
        with self.assertRaises(ValueError):
            circ.validate_door_bindings(dict(schemaVersion='1.0.0', doors={
                'door-002': dict(operation='swing', roomIds=['a', 'b'], openable=True,
                    leaves=[dict(actor='x', kind='single', openYawDeltaDeg=85.0)])}))

    def test_accepts_leaf_with_baked_open(self):
        doc = dict(schemaVersion='1.0.0', doors={
            'door-002': dict(operation='swing', roomIds=['a', 'b'], openable=True,
                leaves=[dict(actor='x', kind='single', openYawDeltaDeg=85.0, bakedOpen=True)])})
        self.assertEqual(circ.validate_door_bindings(doc), doc)


class ValidateProfilesTests(unittest.TestCase):
    def test_entry_room_must_be_in_room_ids(self):
        with self.assertRaises(ValueError):
            circ.validate_profiles(dict(schemaVersion='1.0.0', profiles=[
                dict(profileId='x', scopeId='guest-pilot', roomIds=['a', 'b'], entryRoomId='c')]))

    def test_resolve_profile_for_scope(self):
        doc = dict(schemaVersion='1.0.0', profiles=[
            dict(profileId='guest-circulation', scopeId='guest-pilot', roomIds=['a', 'b'], entryRoomId='a'),
            dict(profileId='guest-ldk-solo', scopeId='guest-ldk', roomIds=['a'], entryRoomId='a')])
        self.assertEqual(circ.resolve_profile_for_scope(doc, 'guest-ldk')['profileId'], 'guest-ldk-solo')
        with self.assertRaises(ValueError):
            circ.resolve_profile_for_scope(doc, 'unknown-scope')


if __name__ == '__main__':
    unittest.main()
