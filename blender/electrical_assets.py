"""W06: electrical fixture placement + lighting-bindings.json resolution.

Reuses the SAME wall/ceiling/mountHeight contract data/electrical.json and
data/electrical-catalog.json already define for the Three.js editor (see
interior-white-model.html's placeElectricalItem()/electricalGroupY()), but
resolves the actual (possibly sloped) ceiling height at the fixture's point
via interior_geometry.ceiling_y() -- electricalGroupY() uses a flat CEIL_H,
which does not match a sloped-ceiling room like room-1f-06 and must not be
copied here (W06 spec section 1). The light's own illumination direction is
always resolved separately from the fixture's mounting/facing rotation, and
for ceiling mounts is always fixed straight down regardless of the mount
surface's own slope.

Pure Python; no bpy dependency (mirrors interior_geometry.py). Only the
mesh/lamp-creation step below needs Blender's own block()/mesh() helpers,
passed in by the caller (build_interior.py) -- same injection pattern
guest_decor.build() already uses.
"""
import math
from interior_geometry import ceiling_y

LIGHTING_CATEGORY = 'lighting'
# W06 spec section 1: required this round. light-exterior/light-indirect are
# explicitly out of scope (see data/visual/lighting-settings.json's
# unsupportedTypes) and must stop the build with the fixture id, not be
# silently skipped.
SUPPORTED_LIGHTING_MOUNTS = ('wall', 'ceiling')


def merged_item(item, catalog_by_type):
    """item (data/electrical.json) + its type's catalog profile, with any
    per-instance *Override applied -- the exact same precedence
    scripts/build-web-data.mjs's buildElectricalItems() uses for the Web
    editor (width/depth/height/mountHeight: instance override ?? catalog)."""
    profile = catalog_by_type.get(item['type'])
    if profile is None:
        raise ValueError(f"electrical.json: {item['id']} references unknown type '{item['type']}'")
    return dict(item, category=profile['category'], mount=profile['mount'], heightRef=profile['heightRef'],
        shape=profile['shape'],
        width=item.get('widthOverride', profile['width']), depth=item.get('depthOverride', profile['depth']),
        height=item.get('heightOverride', profile['height']),
        mountHeight=item.get('mountHeightOverride', profile['mountHeight']))


def ceiling_height_at(data, x, z):
    """Actual ceiling height above GL (source metres) at (x, z) -- the same
    per-point slopedCeilingPieces lookup build_envelope() itself uses to
    build the ceiling geometry (generated/visual-envelope.json, shared with
    the Web editor's slopedCeilingHeightAt()), not a flat assumed height."""
    for piece in data['envelope']['slopedCeilingPieces']:
        if piece['x0']-1e-6 <= x <= piece['x1']+1e-6 and piece['z0']-1e-6 <= z <= piece['z1']+1e-6:
            return ceiling_y(data, piece if piece['sloped'] else None, z)
    return data['levels']['fl1'] + data['defaults']['ceilingHeight']


def resolve_mount(data, merged):
    """(x, y, z) absolute GL position (source metres, x east/y up/z south --
    same convention as the rest of this project's JSON) + rotYDeg (the
    fixture MESH's own facing rotation, source degrees clockwise from +x
    toward +z -- purely visual) + directionVector (the LIGHT's resolved
    illumination direction, same x/y/z convention, a unit vector; DECOUPLED
    from rotYDeg -- see module docstring)."""
    level = merged['level']
    base_y = data['levels'][f"fl{level}"]
    mount = merged['mount']
    if mount == 'wall':
        x = merged['center'] if merged['orientation'] == 'H' else merged['wallAt']
        z = merged['wallAt'] if merged['orientation'] == 'H' else merged['center']
        y = base_y + merged['mountHeight']
        rot_y_deg = (0.0 if merged['side'] > 0 else 180.0) if merged['orientation'] == 'H' else (90.0 if merged['side'] > 0 else -90.0)
    elif mount == 'ceiling':
        x, z = merged['x'], merged['z']
        y = ceiling_height_at(data, x, z) - merged['mountHeight']
        rot_y_deg = 0.0
    else:
        raise ValueError(f"Unsupported lighting mount '{mount}' (only wall/ceiling are resolved)")
    return dict(positionM=[x, y, z], rotYDeg=rot_y_deg)


def _rotate_direction(local, rot_y_deg):
    """Rotate a fixture-LOCAL direction (its own +z = the fixture's forward
    axis) by the mesh's facing rotation about the vertical (y) axis, into the
    world x/y/z convention. Matches the same rotation sense build_furniture()
    uses for furniture.json's `rotation` (source +z maps to +x at +90deg)."""
    theta = math.radians(rot_y_deg)
    lx, ly, lz = local
    return [lx*math.cos(theta) + lz*math.sin(theta), ly, -lx*math.sin(theta) + lz*math.cos(theta)]


def build_lighting_bindings(data, electrical, catalog, settings, room_id):
    """Resolve every lighting-category fixture belonging to `room_id` into
    lighting-bindings.json's fixtures list. Raises ValueError (naming the
    fixture id) on anything unresolvable -- unknown type, an unsupported
    lighting type (light-exterior/light-indirect), a missing profile, or an
    unsupported/unresolvable mount -- so the build stops before Blender does
    any more work, per W06 spec section 4."""
    catalog_by_type = {t['type']: t for t in catalog['types']}
    profiles = settings['profiles']
    unsupported = settings.get('unsupportedTypes', {})
    fixtures = []
    for item in electrical['items']:
        if item.get('room') != room_id:
            continue
        profile_type = catalog_by_type.get(item['type'])
        if profile_type is None:
            raise ValueError(f"electrical.json: {item['id']} references unknown type '{item['type']}'")
        if profile_type['category'] != LIGHTING_CATEGORY:
            continue
        if item['type'] in unsupported:
            raise ValueError(f"{item['id']}: lighting type '{item['type']}' is not supported by W06 ({unsupported[item['type']]})")
        profile = profiles.get(item['type'])
        if profile is None:
            raise ValueError(f"lighting-settings.json is missing a profile for type '{item['type']}' (fixture {item['id']})")
        merged = merged_item(item, catalog_by_type)
        if merged['mount'] not in SUPPORTED_LIGHTING_MOUNTS:
            raise ValueError(f"{item['id']}: lighting mount '{merged['mount']}' is not supported by W06")
        mount = resolve_mount(data, merged)
        direction = _rotate_direction(profile['directionLocal'], mount['rotYDeg'])
        fixtures.append(dict(id=item['id'], type=item['type'], label=item.get('label', profile_type['label']),
            status=item.get('status', 'estimated'),
            positionM=mount['positionM'], directionVector=direction,
            source=profile['source'], lumens=profile['lumens'], temperatureK=profile['temperatureK'],
            spotAngleDeg=profile.get('spotAngleDeg'),
            profileStatus=profile.get('status', 'estimated'), profileNote=profile.get('note')))
    if not fixtures:
        raise ValueError(f'No supported lighting fixtures found for room {room_id}')
    return dict(schemaVersion='1.0.0', roomId=room_id, fixtures=fixtures)


def create_fixture_mesh(binding, merged, mats, block, item):
    """A deliberately simple placeholder (W06 spec: '高精細な器具モデリング
    は今回対象外') -- a flat disc/box at the resolved mount point. Ceiling
    fixtures with a mountHeight (pendant) also get a thin drop rod from the
    ceiling down to the shade, so the drop is visible, not just implied by
    numbers in JSON."""
    x, y, z = binding['positionM']
    w, d, h = merged['width'], merged['depth'], merged['height']
    fixture_mat = mats.get('metal', mats['frame'])
    created = []
    if merged['mount'] == 'ceiling':
        created.append(block(f"lighting.{item['id']}.shade", x-w/2, x+w/2, z-d/2, z+d/2, y, y+h, fixture_mat, .01, item))
        if merged['mountHeight'] > h:
            ceiling = y + h + (merged['mountHeight'] - h)
            rod_w = min(.02, w*.1)
            created.append(block(f"lighting.{item['id']}.rod", x-rod_w/2, x+rod_w/2, z-rod_w/2, z+rod_w/2,
                y+h, ceiling, mats['frame'], 0, item))
    else:
        # W06: no light-bracket instance exists in data/electrical.json yet
        # (see lighting-settings.json's note) -- this placeholder stays a
        # plain axis-aligned box, matching the "壁付けは小さな座標テストで可"
        # scope (position is what matters; visual wall-facing rotation of
        # this placeholder is not required this round).
        created.append(block(f"lighting.{item['id']}.body", x-w/2, x+w/2, z-d/2, z+d/2, y-h/2, y+h/2, fixture_mat, .005, item))
    return created
