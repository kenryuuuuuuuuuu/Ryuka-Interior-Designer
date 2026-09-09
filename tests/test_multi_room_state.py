"""W07-G1 review v1 R2: unreal/multi_room_state.py's partial_apply() must
carry the CALLER's target scopeId through (never the incoming/migrated
state's own, possibly narrower, scopeId), and must reject -- not silently
drop -- an incoming room outside the target scope."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
import multi_room_state as mrs

SCOPES=dict(schemaVersion='1.0.0',scopes=[
    dict(scopeId='guest-ldk',label='LDK単室',roomIds=['room-1f-06'],defaultRoomId='room-1f-06'),
    dict(scopeId='guest-pilot',label='LDK+洋室',roomIds=['room-1f-06','room-1f-05'],defaultRoomId='room-1f-06'),
])
VARIANTS=['natural','warm','reference']


def room_state(variant='natural'):
    return dict(variant=variant,surfaceOverrides={},fixtures={})


def state(scope_id,room_states,active_room_id=None):
    return dict(schemaVersion='2.0.0',scopeId=scope_id,activeRoomId=active_room_id or next(iter(room_states)),
        activeLevel=1,camera=None,azimuthDeg=180,elevationDeg=30,sunLux=50000,exposureEV100=7.5,
        lighting=dict(mode='day'),roomStates=room_states)


class PartialApplyScopeTests(unittest.TestCase):
    def test_merged_scope_id_is_the_target_not_incoming(self):
        # `incoming` is a migrated legacy single-room scenario -- its own
        # scopeId resolves to the SMALLEST scope containing just that room
        # (guest-ldk), same as migrate_legacy_state()/scope_for_room() would
        # produce. Merging it into the wider guest-pilot scope must not let
        # that narrower scopeId leak into the result.
        previous=state('guest-pilot',{'room-1f-06':room_state('natural'),'room-1f-05':room_state('warm')})
        incoming=state('guest-ldk',{'room-1f-06':room_state('reference')})
        merged=mrs.partial_apply(previous,incoming,['room-1f-06','room-1f-05'],'guest-pilot')
        self.assertEqual(merged['scopeId'],'guest-pilot')
        self.assertEqual(merged['roomStates']['room-1f-06']['variant'],'reference')  # replaced
        self.assertEqual(merged['roomStates']['room-1f-05']['variant'],'warm')  # preserved

    def test_merged_state_revalidates_against_its_own_declared_scope(self):
        # The concrete failure the review reproduced: re-validating the
        # merged output via validate_state_own_scope() (as a re-save/next
        # refresh legitimately does) must succeed, not raise "roomStates
        # references room(s) outside the current scope".
        previous=state('guest-pilot',{'room-1f-06':room_state('natural'),'room-1f-05':room_state('warm')})
        incoming=state('guest-ldk',{'room-1f-06':room_state('reference')})
        merged=mrs.partial_apply(previous,incoming,['room-1f-06','room-1f-05'],'guest-pilot')
        legacy_study=dict(variants={v:{} for v in VARIANTS})
        revalidated=mrs.validate_state_own_scope(merged,SCOPES,legacy_study,VARIANTS)
        self.assertEqual(set(revalidated['roomStates']),{'room-1f-06','room-1f-05'})

    def test_rejects_incoming_room_outside_target_scope(self):
        # A room `incoming` covers that is NOT in room_ids must stop the
        # merge outright, never be silently dropped.
        previous=state('guest-ldk',{'room-1f-06':room_state('natural')})
        incoming=state('guest-pilot',{'room-1f-06':room_state('reference'),'room-1f-05':room_state('warm')})
        with self.assertRaises(ValueError) as ctx:
            mrs.partial_apply(previous,incoming,['room-1f-06'],'guest-ldk')
        self.assertIn('room-1f-05',str(ctx.exception))


if __name__=='__main__': unittest.main()
