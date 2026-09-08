"""Portable comparison state. Pure Python; shared by the CLI and UE editor."""
import math
from solar_position import validate_case, matches

SUPPORTED_SCHEMA_VERSIONS = ('1.0.0', '1.1.0')


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
    # 1.0.0 states predate per-surface overrides; read them as carrying none.
    # Writers should stamp 1.1.0 once the state actually has overrides, but
    # this function does not rewrite schemaVersion -- it only normalizes the
    # in-memory field so every caller can rely on state['surfaceOverrides']
    # existing without an extra schemaVersion branch of their own.
    state['surfaceOverrides'] = validate_surface_overrides(state.get('surfaceOverrides') or {}, study)
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
