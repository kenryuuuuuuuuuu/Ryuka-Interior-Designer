"""W06: night lighting profiles/groups and comparison-state fixture overrides.
Pure Python; shared by Blender (blender/electrical_assets.py), the UE editor
(study_controls.py), and the one-time UE import (import_study.py) -- mirrors
surface_finish_overrides.py's split exactly: structural/type validation of a
comparison state's `lighting` field lives in study_state.py (schema only, no
model access), while resolving those fixture ids against what actually exists
in the CURRENT model (lighting-bindings.json, generated at build time) lives
here, so a stale/orphaned fixture id is explained, not silently dropped or
allowed to crash a later stage.
"""
import math

LIGHTING_CATEGORY = 'lighting'
REQUIRED_LIGHTING_TYPES = ('light-downlight', 'light-ceiling', 'light-bracket', 'light-pendant')
DEFAULT_FIXTURE_STATE = dict(on=False, dimming=1.0)


def _number(value, low, high):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and low <= value <= high


def validate_lighting_settings(document):
    """data/visual/lighting-settings.json: per-type optical profiles (used to
    resolve a fixture's light, never its position/dimensions -- those stay in
    data/electrical.json/data/electrical-catalog.json) and named comparison
    groups (an operating shortcut over fixture ids, not an electrical circuit)."""
    if not isinstance(document, dict) or document.get('schemaVersion') != '1.0.0':
        raise ValueError('Unsupported lighting-settings schema')
    profiles = document.get('profiles')
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError('lighting-settings.json requires at least one profile')
    for missing in set(REQUIRED_LIGHTING_TYPES) - set(profiles):
        raise ValueError('lighting-settings.json is missing a required profile: ' + missing)
    for type_name, profile in profiles.items():
        if not isinstance(type_name, str) or not type_name:
            raise ValueError('Invalid lighting-settings profile key')
        if profile.get('source') not in ('point', 'spot'):
            raise ValueError(f'{type_name}: source must be point or spot')
        if not _number(profile.get('lumens'), 0, 100000):
            raise ValueError(f'{type_name}: invalid lumens')
        if not _number(profile.get('temperatureK'), 1800, 10000):
            raise ValueError(f'{type_name}: invalid temperatureK')
        spot_angle = profile.get('spotAngleDeg')
        if profile['source'] == 'spot':
            if not _number(spot_angle, 1, 170):
                raise ValueError(f'{type_name}: spot profiles require a spotAngleDeg in [1, 170]')
        elif spot_angle is not None:
            raise ValueError(f'{type_name}: spotAngleDeg only applies to spot profiles')
        direction = profile.get('directionLocal')
        if (not isinstance(direction, list) or len(direction) != 3
                or not all(_number(v, -1, 1) for v in direction)
                or abs(math.sqrt(sum(v*v for v in direction)) - 1) > 1e-6):
            raise ValueError(f'{type_name}: directionLocal must be a unit vector')
        if profile.get('status') not in ('estimated', 'verified'):
            raise ValueError(f'{type_name}: invalid status')
        if not isinstance(profile.get('note'), str) or not profile['note'].strip():
            raise ValueError(f'{type_name}: requires a provenance note')
    groups = document.get('groups')
    if not isinstance(groups, list) or not groups:
        raise ValueError('lighting-settings.json requires at least one group')
    seen_ids = set()
    for group in groups:
        group_id = group.get('id')
        if not isinstance(group_id, str) or not group_id or group_id in seen_ids:
            raise ValueError('Invalid or duplicate group id')
        seen_ids.add(group_id)
        if not isinstance(group.get('label'), str) or not group['label']:
            raise ValueError(f'{group_id}: requires a label')
        fixture_ids = group.get('fixtureIds')
        if not isinstance(fixture_ids, list) or not fixture_ids or not all(isinstance(f, str) and f for f in fixture_ids):
            raise ValueError(f'{group_id}: fixtureIds must be a non-empty list of ids')
    return document


def validate_lighting_bindings(document):
    """The generated, per-room, per-generation artifact (positions/directions
    already resolved -- see blender/electrical_assets.py). Never hand-edited;
    validated on read the same as any other generated contract this project
    passes between Blender and UE (cf. surface-bindings.json)."""
    if not isinstance(document, dict) or document.get('schemaVersion') != '1.0.0':
        raise ValueError('Unsupported lighting-bindings schema')
    if not isinstance(document.get('roomId'), str) or not document['roomId']:
        raise ValueError('lighting-bindings.json requires a roomId')
    fixtures = document.get('fixtures')
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError('lighting-bindings.json requires at least one fixture')
    seen = set()
    for fixture in fixtures:
        fid = fixture.get('id')
        if not isinstance(fid, str) or not fid or fid in seen:
            raise ValueError('Invalid or duplicate fixture id in lighting-bindings.json')
        seen.add(fid)
        position = fixture.get('positionM')
        if not isinstance(position, list) or len(position) != 3 or not all(_number(v, -1000, 1000) for v in position):
            raise ValueError(f'{fid}: invalid positionM')
        direction = fixture.get('directionVector')
        if (not isinstance(direction, list) or len(direction) != 3
                or not all(_number(v, -1, 1) for v in direction)
                or abs(math.sqrt(sum(v*v for v in direction)) - 1) > 1e-6):
            raise ValueError(f'{fid}: invalid directionVector')
        if fixture.get('source') not in ('point', 'spot'):
            raise ValueError(f'{fid}: invalid source')
        if not _number(fixture.get('lumens'), 0, 100000):
            raise ValueError(f'{fid}: invalid lumens')
        if not _number(fixture.get('temperatureK'), 1800, 10000):
            raise ValueError(f'{fid}: invalid temperatureK')
    return document


def resolve_fixture_overrides(fixtures, bindings):
    """state['lighting']['fixtures'] (already structurally validated by
    study_state.validate_lighting()) resolved against the CURRENT model's
    lighting-bindings.json. Returns (usable, issues) -- same shape/contract
    as surface_finish_overrides.resolve_overrides(): usable is the subset
    whose id actually names a fixture in the current room, issues explains
    every excluded one. Never raises; a stale/orphaned fixture override must
    still be listable, not rejected outright by this function alone -- a
    caller about to *apply* a state treats a non-empty issues list as a stop
    condition, same as the surfaceOverrides precedent."""
    known = {f['id'] for f in bindings.get('fixtures', [])} if bindings else set()
    usable, issues = {}, []
    for fixture_id, override in fixtures.items():
        if fixture_id not in known:
            issues.append(dict(id=fixture_id, reason=f'照明{fixture_id}は現在のモデルに存在しません。'))
        else:
            usable[fixture_id] = override
    return usable, issues


def effective_fixture(binding_fixture, override):
    """Merge one fixture's binding (id/profile: source/lumens/temperatureK/
    directionVector/positionM) with its state override (on/dimming/
    temperatureK, any subset) -- default is OFF, full dimming, profile colour
    (W06 spec: 'fixturesは器具IDをキーにした疎な上書きで、欠落器具の既定値は
    off・調光率1・プロファイル色温度')."""
    override = override or {}
    on = override.get('on', DEFAULT_FIXTURE_STATE['on'])
    dimming = override.get('dimming', DEFAULT_FIXTURE_STATE['dimming'])
    temperature_k = override.get('temperatureK', binding_fixture['temperatureK'])
    lumens = binding_fixture['lumens'] * dimming if on else 0.0
    return dict(on=on, dimming=dimming, temperatureK=temperature_k, effectiveLumens=lumens)


def kelvin_to_rgb(temperature_k):
    """Tanner Helland's widely-used blackbody approximation, clamped to this
    project's supported [1800, 10000] K range. An approximation for Blender's
    render only (Blender light Data.color takes plain RGB, not a Kelvin
    value) -- the UE side instead uses the engine's own native light
    Temperature property (LightComponent.use_temperature/.temperature) for a
    physically-modelled conversion, so the two renderers are NOT expected to
    match pixel-for-pixel (same convention as this project's solar/exposure
    approximations)."""
    if not _number(temperature_k, 1800, 10000):
        raise ValueError('Invalid colour temperature')
    t = temperature_k / 100
    if t <= 66:
        r = 255
        g = 99.4708025861 * math.log(t) - 161.1195681661
    else:
        r = 329.698727446 * (t - 60) ** -0.1332047592
        g = 288.1221695283 * (t - 60) ** -0.0755148492
    if t >= 66:
        b = 255
    elif t <= 19:
        b = 0
    else:
        b = 138.5177312231 * math.log(t - 10) - 305.0447927307
    return tuple(min(1.0, max(0.0, v / 255)) for v in (r, g, b))
