"""W07-G1: multi-room study scope, comparison-state schema 2.0.0
(roomStates keyed by roomId), migration from the legacy single-room
schemas (1.0.0/1.1.0/1.2.0), and shared partial-apply logic for a
--scenario/--previous save that only covers a SUBSET of the current
scope's rooms.

Pure Python; shared by Blender (build_interior.py), the UE editor
(study_controls.py), the one-time UE import (import_study.py), and every
CLI script that touches comparison state (scripts/refresh_inputs.py,
build-visual-twin.py, build-unreal-study.py, refresh-visual-study.py,
compare-unreal-daylight.py, save-study-scenario.py). Mirrors
study_state.py/surface_finish_overrides.py/lighting.py's existing split:
structural validation lives here, model-dependent resolution (does a
surface/fixture id actually exist in the CURRENT model) stays with each
domain's own module and is called once per room by the caller.
"""
import math
from study_state import validate_state as _validate_legacy_state, validate_surface_overrides

SCHEMA_VERSION = '2.0.0'
LEGACY_SCHEMA_VERSIONS = ('1.0.0', '1.1.0', '1.2.0')
SCOPES_SCHEMA = '1.0.0'
ROOM_RENDER_SCHEMA = '1.0.0'
# Baseline finish for geometry that belongs to no in-scope room (exterior
# walls/roof, out-of-scope rooms, the un-marked thin side faces of an
# otherwise-marked wall panel) -- W07-G1 spec section 3: "対象外室/外皮は
# 既存の基準材質を維持". Fixed, not derived from any room's current state,
# so switching a room's variant never touches anything outside that room's
# own registered surfaces/furniture.
BASE_VARIANT = 'natural'
DEFAULT_FIXTURE_STATE = dict(on=False, dimming=1.0)


# --------------------------------------------------------------------------
# study-scopes.json
# --------------------------------------------------------------------------

def validate_scopes(document):
    if not isinstance(document, dict) or document.get('schemaVersion') != SCOPES_SCHEMA:
        raise ValueError('Unsupported study-scopes schema')
    scopes = document.get('scopes')
    if not isinstance(scopes, list) or not scopes:
        raise ValueError('study-scopes.json requires at least one scope')
    seen = set()
    for s in scopes:
        if not isinstance(s, dict):
            raise ValueError('study-scopes.json: entry is not an object')
        scope_id = s.get('scopeId')
        if not isinstance(scope_id, str) or not scope_id:
            raise ValueError('study-scopes.json: invalid scopeId')
        if scope_id in seen:
            raise ValueError(f'study-scopes.json: duplicate scopeId "{scope_id}"')
        seen.add(scope_id)
        if not isinstance(s.get('label'), str) or not s['label']:
            raise ValueError(f'{scope_id}: requires a label')
        room_ids = s.get('roomIds')
        if (not isinstance(room_ids, list) or not room_ids
                or len(set(room_ids)) != len(room_ids)
                or not all(isinstance(r, str) and r for r in room_ids)):
            raise ValueError(f'{scope_id}: roomIds must be a non-empty list of unique ids')
        if s.get('defaultRoomId') not in room_ids:
            raise ValueError(f'{scope_id}: defaultRoomId must be one of roomIds')
    return document


def resolve_scope(document, scope_id):
    """document: a validated study-scopes.json. Raises ValueError naming the
    scope id if unknown -- never returns a partial/guessed scope."""
    for s in document['scopes']:
        if s['scopeId'] == scope_id:
            return s
    raise ValueError(f'Unknown scope: {scope_id}')


def scope_for_room(document, room_id):
    """The smallest (fewest roomIds) scope containing `room_id`, used to give
    a legacy single-room state a stable scopeId on migration (W07-G1 spec:
    "旧W06案はroom-1f-06だけを持つ案として扱います"). Raises if no scope
    contains it."""
    candidates = [s for s in document['scopes'] if room_id in s['roomIds']]
    if not candidates:
        raise ValueError(f'No scope contains room {room_id}')
    return min(candidates, key=lambda s: len(s['roomIds']))


def validate_scope_rooms(scope, house_rooms):
    """Model-dependent check: every roomId in `scope` actually exists in the
    CURRENT data/house.json. Raises ValueError naming the missing id(s) --
    kept separate from validate_scopes() so a structurally-valid scope
    definition can still be listed/explained even if the house shape moved
    on since it was written."""
    known = {r['id'] for r in house_rooms}
    missing = sorted(set(scope['roomIds']) - known)
    if missing:
        raise ValueError(f"Scope {scope['scopeId']} references unknown room id(s): " + ', '.join(missing))


# --------------------------------------------------------------------------
# room-render-settings.json (+ guest-ldk-study.json read adapter)
# --------------------------------------------------------------------------

def validate_room_render_settings(document):
    if not isinstance(document, dict) or document.get('schemaVersion') != ROOM_RENDER_SCHEMA:
        raise ValueError('Unsupported room-render-settings schema')
    rooms = document.get('rooms')
    if not isinstance(rooms, dict) or not rooms:
        raise ValueError('room-render-settings.json requires at least one room')
    for room_id, entry in rooms.items():
        if not isinstance(entry, dict):
            raise ValueError(f'{room_id}: invalid entry')
        camera = entry.get('camera')
        if not isinstance(camera, dict):
            raise ValueError(f'{room_id}: invalid camera')
        for key in ('position', 'target'):
            values = camera.get(key)
            if (not isinstance(values, list) or len(values) != 3
                    or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values)):
                raise ValueError(f'{room_id}: invalid camera {key}')
        lens = camera.get('lensMm')
        if isinstance(lens, bool) or not isinstance(lens, (int, float)) or not 12 <= lens <= 120:
            raise ValueError(f'{room_id}: invalid camera lensMm')
        if not isinstance(entry.get('defaultVariant'), str) or not entry['defaultVariant']:
            raise ValueError(f'{room_id}: requires defaultVariant')
    return document


def room_render(document, room_id, legacy_study=None):
    """document: a validated room-render-settings.json. legacy_study: the
    parsed data/visual/guest-ldk-study.json, used ONLY as a read adapter if
    `room_id` is not (yet) in the new per-room table -- W07-G1 spec section
    1: "旧単室設定は読込アダプターを通して利用可能にします". Raises if
    neither source has this room."""
    entry = document.get('rooms', {}).get(room_id)
    if entry is not None:
        return entry
    if legacy_study is not None and legacy_study.get('roomId') == room_id:
        return dict(camera=legacy_study['camera'], defaultVariant=legacy_study.get('defaultVariant', 'natural'))
    raise ValueError(f'No render settings for room {room_id}')


# --------------------------------------------------------------------------
# Per-room state (variant / surfaceOverrides / fixtures)
# --------------------------------------------------------------------------

def validate_fixture_overrides(fixtures):
    """Structural/type validation of a room's fixtures dict -- same rules as
    study_state.validate_lighting()'s own fixtures block, extracted so a
    room-scoped 2.0.0 roomState (no top-level `mode` any more, that moved to
    whole-house) can reuse it without duplicating the range checks. Whether a
    fixture id actually exists in the CURRENT model is a separate,
    model-dependent check (lighting.resolve_fixture_overrides()), kept out of
    this function so a stale reference still parses and can be explained."""
    if not isinstance(fixtures, dict):
        raise ValueError('fixtures must be an object')
    for fixture_id, override in fixtures.items():
        if not isinstance(fixture_id, str) or not fixture_id:
            raise ValueError('Invalid fixtures key')
        if not isinstance(override, dict):
            raise ValueError(f'fixtures[{fixture_id}] must be an object')
        unknown = set(override) - {'on', 'dimming', 'temperatureK'}
        if unknown:
            raise ValueError(f'fixtures[{fixture_id}] has unknown fields: {sorted(unknown)}')
        if 'on' in override and isinstance(override['on'], bool) is False:
            raise ValueError(f'fixtures[{fixture_id}].on must be a boolean')
        if 'dimming' in override:
            value = override['dimming']
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f'fixtures[{fixture_id}].dimming must be a finite number in [0, 1]')
        if 'temperatureK' in override:
            value = override['temperatureK']
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 1800 <= value <= 10000:
                raise ValueError(f'fixtures[{fixture_id}].temperatureK must be a finite number in [1800, 10000]')
    return fixtures


def validate_room_state(room_state, room_id, variants):
    """One roomStates[room_id] entry: {variant, surfaceOverrides, fixtures}.
    `variants` is the shared palette dict (guest-ldk-study.json's own
    `variants`, reused across every room -- W07-G1 spec section 1: no
    per-room duplicate palette). Structural/type only; whether a
    surfaceId/fixtureId actually resolves against THIS room in the current
    model is the caller's job (surface_finish_overrides.resolve_overrides()/
    lighting.resolve_fixture_overrides(), called once per room)."""
    if not isinstance(room_state, dict):
        raise ValueError(f'roomStates[{room_id}] must be an object')
    unknown = set(room_state) - {'variant', 'surfaceOverrides', 'fixtures'}
    if unknown:
        raise ValueError(f'roomStates[{room_id}] has unknown fields: {sorted(unknown)}')
    if room_state.get('variant') not in variants:
        raise ValueError(f'roomStates[{room_id}]: unknown finish variant')
    # validate_surface_overrides() only needs study['settings']['variants'].
    room_state['surfaceOverrides'] = validate_surface_overrides(
        room_state.get('surfaceOverrides'), dict(settings=dict(variants=variants)))
    room_state['fixtures'] = validate_fixture_overrides(room_state.get('fixtures', {}))
    return room_state


# --------------------------------------------------------------------------
# schemaVersion 2.0.0
# --------------------------------------------------------------------------

def validate_state_v2(state, room_ids, variants):
    """`room_ids`: the CURRENT scope's room ids (state.scopeId is informational
    provenance only -- W07-G1 spec section 2: "異なるscopeIdでも保存室が現在
    scopeの部分集合なら適用可能"). Every key of roomStates must be one of
    `room_ids`; unknown/out-of-scope room keys are rejected here (never
    silently dropped -- the caller decides, via partial_apply(), whether a
    state that only covers a SUBSET of room_ids is acceptable for the
    operation at hand)."""
    if not isinstance(state, dict):
        raise ValueError('Invalid comparison state')
    if state.get('schemaVersion') != SCHEMA_VERSION:
        raise ValueError('Unsupported comparison state schema')
    if not isinstance(state.get('scopeId'), str) or not state['scopeId']:
        raise ValueError('Invalid scopeId')
    room_states = state.get('roomStates')
    if not isinstance(room_states, dict) or not room_states:
        raise ValueError('roomStates must be a non-empty object')
    unknown_rooms = sorted(set(room_states) - set(room_ids))
    if unknown_rooms:
        raise ValueError('roomStates references room(s) outside the current scope: ' + ', '.join(unknown_rooms))
    for room_id, room_state in room_states.items():
        validate_room_state(room_state, room_id, variants)
    if state.get('activeRoomId') not in room_states:
        raise ValueError('activeRoomId must be a key of roomStates')
    if not isinstance(state.get('activeLevel'), int) or isinstance(state.get('activeLevel'), bool):
        raise ValueError('Invalid activeLevel')
    lighting = state.get('lighting')
    if not isinstance(lighting, dict) or lighting.get('mode') not in ('day', 'night'):
        raise ValueError('Invalid lighting.mode')
    if set(lighting) != {'mode'}:
        raise ValueError('lighting has unknown fields (per-fixture state moved to roomStates[*].fixtures)')
    for key, low, high in [('azimuthDeg', 0, 360), ('elevationDeg', 1, 89),
                            ('sunLux', 1, 150000), ('exposureEV100', -5, 20)]:
        value = state.get(key)
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'Invalid {key}: expected a finite number in [{low}, {high}]')
    camera = state.get('camera')
    if camera is not None:
        if not isinstance(camera, dict):
            raise ValueError('Invalid camera')
        for key in ('locationCm', 'rotationDeg'):
            values = camera.get(key)
            if not isinstance(values, list) or len(values) != 3 or any(
                    isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in values):
                raise ValueError('Invalid camera ' + key)
        lens = camera.get('lensMm')
        if isinstance(lens, bool) or not isinstance(lens, (float, int)) or not 12 <= lens <= 120:
            raise ValueError('Invalid camera lens')
    # solar/siteContextSHA256 reuse study_state.py's own case validation via a
    # throwaway legacy-shaped probe would require azimuth/elevation to match
    # (matches()); simplest to inline the same check here directly.
    if state.get('solar') is not None:
        from solar_position import validate_case, matches
        case = validate_case(state['solar'])
        if not case['usable'] or not matches(case, state):
            raise ValueError('Solar provenance does not match scene angles')
    return state


def default_state_v2(scope, room_render_settings, legacy_study, shared_lighting, job):
    """A fresh default 2.0.0 state for `scope`: every room at its own
    defaultVariant, no overrides/fixtures, day mode, no camera (caller's
    initial-camera logic picks one from room_render() when camera is None).
    `shared_lighting` is guest-ldk-study.json's own `lighting` block (shared
    azimuth/elevation default, unchanged by W07-G1)."""
    room_states = {}
    for room_id in scope['roomIds']:
        settings = room_render(room_render_settings, room_id, legacy_study)
        room_states[room_id] = dict(variant=settings['defaultVariant'], surfaceOverrides={}, fixtures={})
    state = dict(schemaVersion=SCHEMA_VERSION, scopeId=scope['scopeId'], activeRoomId=scope['defaultRoomId'],
        activeLevel=1, camera=None, azimuthDeg=shared_lighting['azimuthDeg'], elevationDeg=shared_lighting['elevationDeg'],
        sunLux=job['sunLux'], exposureEV100=job['exposureEV100'], lighting=dict(mode='day'), roomStates=room_states)
    return state


# --------------------------------------------------------------------------
# Migration from 1.0.0/1.1.0/1.2.0
# --------------------------------------------------------------------------

def migrate_legacy_state(state, room_id, scopes_document, variants):
    """`state`: already validated by study_state.validate_state() (so it is
    known-good 1.0.0/1.1.0/1.2.0 shaped) for the single room `room_id`
    (matches its own state['roomId']). Wraps it into a 2.0.0 state whose
    roomStates has ONLY this one room -- W07-G1 spec section 2: "1.0/1.1/1.2
    は既存検証後、roomIdの1室だけのroomStatesへ移行します". Never mutates
    `state` in place and never rewrites any file -- purely an in-memory
    reshape."""
    scope = scope_for_room(scopes_document, room_id)
    room_state = dict(variant=state['variant'], surfaceOverrides=state['surfaceOverrides'],
        fixtures=state['lighting']['fixtures'])
    validate_room_state(room_state, room_id, variants)
    migrated = dict(schemaVersion=SCHEMA_VERSION, scopeId=scope['scopeId'], activeRoomId=room_id,
        activeLevel=1, camera=state.get('camera'), azimuthDeg=state['azimuthDeg'], elevationDeg=state['elevationDeg'],
        sunLux=state['sunLux'], exposureEV100=state['exposureEV100'],
        lighting=dict(mode=state['lighting']['mode']), roomStates={room_id: room_state})
    if state.get('solar') is not None:
        migrated['solar'] = state['solar']
    if state.get('siteContextSHA256') is not None:
        migrated['siteContextSHA256'] = state['siteContextSHA256']
    return migrated


def validate_state_own_scope(state, scopes_document, legacy_study, variants):
    """Same dispatch/migration as validate_state(), but self-determines which
    scope to validate the state's OWN room(s) against, instead of taking an
    external room_ids -- used by callers (scripts/refresh_inputs.py) that are
    only confirming a SAVED state is internally valid and safe to reuse, not
    yet checking it against some OTHER, specific target project's scope
    (that cross-check happens later, when the caller actually merges/applies
    it via partial_apply() against a concrete scope). A 2.0.0 state is
    validated against its own declared scopeId; a legacy state is validated
    against the smallest scope containing its own roomId (matching
    migrate_legacy_state()'s own choice)."""
    if not isinstance(state, dict):
        raise ValueError('Invalid comparison state')
    schema = state.get('schemaVersion')
    if schema == SCHEMA_VERSION:
        scope = resolve_scope(scopes_document, state.get('scopeId'))
        return validate_state_v2(state, scope['roomIds'], variants)
    if schema in LEGACY_SCHEMA_VERSIONS:
        room_id = state.get('roomId')
        scope = scope_for_room(scopes_document, room_id)
        return validate_state(state, scope['roomIds'], variants, scopes_document, legacy_study)
    raise ValueError('Unsupported comparison state schema')


def validate_state(state, room_ids, variants, scopes_document, legacy_study):
    """Top-level dispatcher, used everywhere a caller just wants "the current
    state" without caring which schema it was written in -- ALWAYS returns a
    2.0.0-shaped state. `legacy_study`: guest-ldk-study.json's parsed
    content, needed by study_state.validate_state() for a legacy state's own
    roomId/variant checks (it validates against exactly the room it names,
    not the whole scope)."""
    if not isinstance(state, dict):
        raise ValueError('Invalid comparison state')
    schema = state.get('schemaVersion')
    if schema == SCHEMA_VERSION:
        return validate_state_v2(state, room_ids, variants)
    if schema in LEGACY_SCHEMA_VERSIONS:
        room_id = state.get('roomId')
        if room_id not in room_ids:
            raise ValueError(f'Comparison state room ({room_id}) is outside the current scope')
        legacy = _validate_legacy_state(dict(state), dict(roomId=room_id, settings=legacy_study))
        return migrate_legacy_state(legacy, room_id, scopes_document, variants)
    raise ValueError('Unsupported comparison state schema')


# --------------------------------------------------------------------------
# Partial application (--scenario / --previous / named-scenario load)
# --------------------------------------------------------------------------

def partial_apply(previous_state, incoming_state, room_ids, allow_missing_rooms=False):
    """`previous_state`/`incoming_state`: both already-validated 2.0.0
    states. Applies `incoming_state`'s whole-house fields and ONLY the rooms
    it actually covers; every other in-scope room keeps `previous_state`'s
    own roomState untouched (W07-G1 spec section 2: "全体条件とその案の
    敷地/日時一覧を一組で採用し、LDKのroomStateを置換、洋室のroomStateは
    保持します"). Raises ValueError (naming the missing room ids) if
    `incoming_state` covers only a subset of `room_ids` AND
    `previous_state` has no usable roomState for the rest, unless
    `allow_missing_rooms` is set (a brand-new model with no prior state at
    all -- W07-G1 spec section 2: "新規モデルを作る明示操作に限り、不足室の
    初期状態を使えます", handled by the caller supplying a synthetic
    previous_state built from default_state_v2() in that case, not by this
    function inventing one)."""
    room_states = dict(previous_state['roomStates'])
    missing = []
    for room_id in room_ids:
        if room_id in incoming_state['roomStates']:
            room_states[room_id] = incoming_state['roomStates'][room_id]
        elif room_id not in room_states:
            missing.append(room_id)
    if missing and not allow_missing_rooms:
        raise ValueError('No prior state for room(s) not covered by this scenario: ' + ', '.join(missing))
    merged = dict(incoming_state)
    merged['roomStates'] = {room_id: room_states[room_id] for room_id in room_ids if room_id in room_states}
    if merged.get('activeRoomId') not in merged['roomStates']:
        merged['activeRoomId'] = next(iter(merged['roomStates']))
    return merged
