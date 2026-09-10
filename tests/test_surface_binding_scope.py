"""W07-G3 review R1: the surface REGISTRY always validates in full (every
entry must resolve against the current house.json), but SurfaceBinder only
emits an EDITABLE binding for a surface whose room is in the current edit
scope. A narrower scope (guest-pilot's 2 rooms) must not carry bindings for
玄関/ホール/... -- study.roomStates has no entry for them, so the UE import
(`study['roomStates'][roomId]['variant']`) and study_controls would KeyError.
"""
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
# build_interior imports bpy/bmesh/mathutils at module load; SurfaceBinder
# itself only needs the pure-Python finish resolution + a material() factory
# whose return value it just stores, so a stub is enough for this test.
for _m in ('bpy', 'bmesh', 'mathutils'):
    sys.modules.setdefault(_m, mock.MagicMock())
sys.path.insert(0, str(ROOT / 'blender'))
sys.path.insert(0, str(ROOT / 'unreal'))
sys.path.insert(0, str(ROOT / 'scripts'))

import build_interior as bi
import multi_room_state as mrs
from surface_registry import resolve_from


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


class SurfaceBindingScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolved = resolve_from(ROOT)['surfaces']
        cls.scopes = mrs.validate_scopes(_load('data/visual/study-scopes.json'))
        cls.finish_doc = _load('data/visual/unreal-finishes.json')
        cls.variants = _load('data/visual/guest-ldk-study.json')['variants']
        cls.house = _load('data/house.json')

    def _bindings_for(self, scope_id):
        scope = mrs.resolve_scope(self.scopes, scope_id)
        variant_by_room = {r: mrs.BASE_VARIANT for r in scope['roomIds']}
        binder = bi.SurfaceBinder(self.house, self.resolved, {}, self.finish_doc, self.variants, variant_by_room)
        return scope, binder.bindings_json()['surfaces']

    def test_full_registry_still_resolves(self):
        self.assertEqual(len(self.resolved), 52)
        self.assertTrue(all(s['status'] == 'resolved' for s in self.resolved))

    def test_pilot_scope_only_binds_its_two_rooms(self):
        scope, surfaces = self._bindings_for('guest-pilot')
        self.assertEqual(len(surfaces), 16)
        self.assertEqual(sorted({s['roomId'] for s in surfaces.values()}), sorted(scope['roomIds']))

    def test_ldk_scope_only_binds_the_ldk(self):
        scope, surfaces = self._bindings_for('guest-ldk')
        self.assertEqual(sorted({s['roomId'] for s in surfaces.values()}), scope['roomIds'])

    def test_guest_scope_binds_all_eight_rooms(self):
        scope, surfaces = self._bindings_for('guest')
        self.assertEqual(len(surfaces), 52)
        self.assertEqual(sorted({s['roomId'] for s in surfaces.values()}), sorted(scope['roomIds']))

    def test_no_binding_references_a_room_outside_its_scope(self):
        for scope_id in ('guest-pilot', 'guest-ldk', 'guest'):
            scope, surfaces = self._bindings_for(scope_id)
            for sid, info in surfaces.items():
                self.assertIn(info['roomId'], scope['roomIds'], (scope_id, sid))


if __name__ == '__main__':
    unittest.main()
