"""Portable comparison state. Pure Python; shared by the CLI and UE editor."""
import math
from solar_position import validate_case, matches

SUPPORTED_SCHEMA_VERSIONS = ('1.0.0', '1.1.0', '1.2.0')


def validate_lighting(lighting):
    """Structural/type validation only -- same split as
    validate_surface_overrides()/surface_finish_overrides.resolve_overrides():
    whether a fixture id actually exists in the CURRENT model is a separate,
    model-dependent check (see lighting.resolve_fixture_overrides()), kept out
    of this function so a state carrying a now-removed fixture still parses
    and can be listed/explained rather than rejected outright here."""
    if not isinstance(lighting, dict):
        raise ValueError('lighting must be an object')
    if lighting.get('mode') not in ('day', 'night'):
        raise ValueError('Invalid lighting mode')
    fixtures = lighting.get('fixtures')
    if not isinstance(fixtures, dict):
        raise ValueError('lighting.fixtures must be an object')
    for fixture_id, override in fixtures.items():
        if not isinstance(fixture_id, str) or not fixture_id:
            raise ValueError('Invalid lighting.fixtures key')
        if not isinstance(override, dict):
            raise ValueError(f'lighting.fixtures[{fixture_id}] must be an object')
        unknown = set(override) - {'on', 'dimming', 'temperatureK'}
        if unknown:
            raise ValueError(f'lighting.fixtures[{fixture_id}] has unknown fields: {sorted(unknown)}')
        if 'on' in override and isinstance(override['on'], bool) is False:
            raise ValueError(f'lighting.fixtures[{fixture_id}].on must be a boolean')
        if 'dimming' in override:
            value = override['dimming']
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f'lighting.fixtures[{fixture_id}].dimming must be a finite number in [0, 1]')
        if 'temperatureK' in override:
            value = override['temperatureK']
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 1800 <= value <= 10000:
                raise ValueError(f'lighting.fixtures[{fixture_id}].temperatureK must be a finite number in [1800, 10000]')
    return lighting


def validate_surface_overrides(overrides, study):
    """Structural/type validation only -- whether a surfaceId still exists and
    is bound to real geometry is a separate, model-dependent check (see
    surface_finish_overrides.resolve_overrides), kept out of this function so
    a saved state with a now-orphaned reference still parses and can be
    listed/explained rather than rejected outright."""
    if not isinstance(overrides, dict): raise ValueError('surfaceOverrides must be an object')
    variants = study['settings']['variants']
    for surface_id, override in overrides.items():
        if not isinstance(surface_id, str) or not surface_id: raise ValueError('Invalid surfaceOverrides key')
        if not isinstance(override, dict): raise ValueError(f'surfaceOverrides[{surface_id}] must be an object')
        unknown = set(override) - {'variant', 'colorHex', 'roughness'}
        if unknown: raise ValueError(f'surfaceOverrides[{surface_id}] has unknown fields: {sorted(unknown)}')
        if 'variant' in override and override['variant'] not in variants:
            raise ValueError(f'surfaceOverrides[{surface_id}]: unknown variant')
        if 'colorHex' in override:
            value = override['colorHex']
            if not isinstance(value, str) or len(value) != 6 or any(c not in '0123456789abcdefABCDEF' for c in value):
                raise ValueError(f'surfaceOverrides[{surface_id}]: colorHex must be 6 hex characters, no #')
        if 'roughness' in override:
            value = override['roughness']
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f'surfaceOverrides[{surface_id}]: roughness must be a finite number in [0, 1]')
    return overrides


def validate_state(state, study):
    if not isinstance(state, dict): raise ValueError('Invalid comparison state')
    if state.get('schemaVersion') not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError('Unsupported comparison state schema')
    # 1.0.0 states predate per-surface overrides; tolerate the field being
    # totally absent (or explicitly None) there, reading it as carrying none.
    # Writers should stamp 1.1.0 once the state actually has overrides, but
    # this function does not rewrite schemaVersion -- it only normalizes the
    # in-memory field so every caller can rely on state['surfaceOverrides']
    # existing without an extra schemaVersion branch of their own.
    #
    # W04 review R4: this must be schema-gated, not a blanket `or {}` -- that
    # silently turned a 1.1.0 state's null/[]/false/'' surfaceOverrides into
    # an empty dict too, masking a real type error a 1.1.0 state (which is
    # always supposed to carry this field) should never have in the first
    # place. Only 1.0.0's specific "field predates this schema" absence is
    # tolerated; anything else -- present-but-wrong-type, in either schema --
    # still reaches validate_surface_overrides() and is rejected there.
    raw_overrides = state.get('surfaceOverrides')
    if state.get('schemaVersion') == '1.0.0' and raw_overrides is None:
        raw_overrides = {}
    state['surfaceOverrides'] = validate_surface_overrides(raw_overrides, study)
    # W06: lighting is REQUIRED and strictly validated from 1.2.0 onward -- a
    # 1.2.0 state with lighting missing/malformed is a hard error, never
    # silently treated as a pre-1.2.0 state. Anything OLDER than 1.2.0
    # predates lighting entirely and is normalized to day + all fixtures off,
    # preserving that state's historical (daytime, unlit) appearance rather
    # than inventing a lit night scene for it.
    if state.get('schemaVersion') == '1.2.0':
        state['lighting'] = validate_lighting(state.get('lighting'))
    else:
        state['lighting'] = dict(mode='day', fixtures={})
    if state.get('roomId') != study['roomId']:
        raise ValueError('Comparison state belongs to another room')
    if state.get('variant') not in study['settings']['variants']:
        raise ValueError('Unknown finish variant')
    for key, low, high in [('azimuthDeg',0,360),('elevationDeg',1,89),
                           ('sunLux',1,150000),('exposureEV100',-5,20)]:
        value=state.get(key)
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not low<=value<=high:
            raise ValueError(f'Invalid {key}: expected a finite number in [{low}, {high}]')
    camera=state.get('camera')
    if state.get('solar') is not None:
        case=validate_case(state['solar'])
        if not case['usable'] or not matches(case,state):
            raise ValueError('Solar provenance does not match scene angles')
    if camera is not None:
        if not isinstance(camera,dict): raise ValueError('Invalid camera')
        for key in ('locationCm','rotationDeg'):
            values=camera.get(key)
            if not isinstance(values,list) or len(values)!=3 or any(
                isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in values):
                raise ValueError('Invalid camera '+key)
        lens=camera.get('lensMm')
        if isinstance(lens,bool) or not isinstance(lens,(float,int)) or not 12<=lens<=120:
            raise ValueError('Invalid camera lens')
    return state


def default_state(study, job):
    return validate_state(dict(schemaVersion='1.0.0',roomId=study['roomId'],
        variant=study['variant'],azimuthDeg=study['lighting']['azimuthDeg'],
        elevationDeg=study['lighting']['elevationDeg'],sunLux=job['sunLux'],
        exposureEV100=job['exposureEV100'],camera=None),study)
