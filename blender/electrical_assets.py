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


def ceiling_height_at(data, x, z, room_id):
    """Actual ceiling height above GL (source metres) at (x, z), for a
    fixture belonging to `room_id`. A room NOT marked ceiling:sloped uses the
    flat default directly -- that is a legitimate flat ceiling, not a lookup
    "miss". A room marked ceiling:sloped (e.g. room-1f-06) MUST resolve to
    one of ITS OWN registered pieces in generated/visual-envelope.json's
    slopedCeilingPieces (build_envelope() itself uses the same per-point
    lookup to build the ceiling geometry, shared with the Web editor's
    slopedCeilingHeightAt()); a sloped room's point matching no piece at all
    is a genuine, distinct failure (a data problem -- the fixture sits
    outside the room's own decomposed ceiling coverage) and must be raised,
    never silently treated the same as an ordinary flat ceiling (W06-v1
    review R1)."""
    room = next((r for r in data['rooms'] if r['id'] == room_id), None)
    if room is None:
        raise ValueError(f'Unknown room for ceiling height resolution: {room_id}')
    flat_default = data['levels'][f"fl{room['level']}"] + data['defaults']['ceilingHeight']
    if room.get('ceiling') != 'sloped':
        return flat_default
    for piece in data['envelope']['slopedCeilingPieces']:
        if piece.get('roomId') != room_id:
            continue
        if piece['x0']-1e-6 <= x <= piece['x1']+1e-6 and piece['z0']-1e-6 <= z <= piece['z1']+1e-6:
            return ceiling_y(data, piece, z) if piece['sloped'] else flat_default
    raise ValueError(f'Could not resolve ceiling height for room {room_id} at ({x}, {z}): '
        'point is outside every registered ceiling piece for this sloped-ceiling room')


def resolve_mount(data, merged):
    """(x, y, z) absolute GL position (source metres, x east/y up/z south --
    same convention as the rest of this project's JSON) + rotYDeg (the
    fixture MESH's own facing rotation, source degrees clockwise from +x
    toward +z -- purely visual) + directionVector (the LIGHT's resolved
    illumination direction, same x/y/z convention, a unit vector; DECOUPLED
    from rotYDeg -- see module docstring).

    `positionM` is the fixture's MOUNT ORIGIN -- for ceiling mounts this is
    its structural TOP (matching data/electrical-catalog.json's own
    heightRef:ceiling definition: mountHeight is the drop from the ceiling
    surface to this origin; a flush-mounted downlight's origin therefore
    sits right at the ceiling). `emitPositionM` is the actual light-emitting
    point used for the PointLight/SpotLight itself (not the mesh) -- the
    underside of the fixture's own housing, so the light is never placed
    inside the ceiling void or its own opaque body (W06-v1 review R2). For
    a wall mount, `positionM` is already the housing's CENTRE (same
    convention as the Web editor), which needs no separate offset."""
    level = merged['level']
    base_y = data['levels'][f"fl{level}"]
    mount = merged['mount']
    if mount == 'wall':
        x = merged['center'] if merged['orientation'] == 'H' else merged['wallAt']
        z = merged['wallAt'] if merged['orientation'] == 'H' else merged['center']
        y = base_y + merged['mountHeight']
        rot_y_deg = (0.0 if merged['side'] > 0 else 180.0) if merged['orientation'] == 'H' else (90.0 if merged['side'] > 0 else -90.0)
        emit_y = y
    elif mount == 'ceiling':
        x, z = merged['x'], merged['z']
        y = ceiling_height_at(data, x, z, merged['room']) - merged['mountHeight']
        rot_y_deg = 0.0
        emit_y = y - merged['height']
    else:
        raise ValueError(f"Unsupported lighting mount '{mount}' (only wall/ceiling are resolved)")
    return dict(positionM=[x, y, z], emitPositionM=[x, emit_y, z], rotYDeg=rot_y_deg)


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
            positionM=mount['positionM'], emitPositionM=mount['emitPositionM'], directionVector=direction,
            source=profile['source'], lumens=profile['lumens'], temperatureK=profile['temperatureK'],
            spotAngleDeg=profile.get('spotAngleDeg'),
            profileStatus=profile.get('status', 'estimated'), profileNote=profile.get('note')))
    if not fixtures:
        raise ValueError(f'No supported lighting fixtures found for room {room_id}')
    # W06-v2 review 必須修正A: lighting-settings.json's groups are a common
    # operating shortcut (Blender's own build never uses them itself), but a
    # group referencing a fixture id that this resolution does not produce
    # (removed from data/electrical.json, wrong room, unsupported type) must
    # stop HERE too -- the same "before Blender does more work" contract as
    # every other unresolvable id above, not left to be discovered later as
    # a silently-partial group in the UE editor.
    known_ids = {f['id'] for f in fixtures}
    for group in settings.get('groups', []):
        unknown = [fid for fid in group.get('fixtureIds', []) if fid not in known_ids]
        if unknown:
            raise ValueError(f"lighting-settings.json group '{group.get('id')}' references fixture id(s) "
                f"not resolvable for room {room_id}: " + ', '.join(unknown))
    return dict(schemaVersion='1.0.0', roomId=room_id, fixtures=fixtures)


def create_fixture_mesh(binding, merged, mats, block, item, ceiling_height=None):
    """A deliberately simple placeholder (W06 spec: '高精細な器具モデリング
    は今回対象外') -- a flat disc/box at the resolved mount point. `positionM`
    is the fixture's structural TOP for a ceiling mount (see resolve_mount()),
    so the housing hangs DOWN from it (W06-v1 review R2: the previous version
    built it upward, into the ceiling void). Fixtures with a visible drop
    below their own housing (pendant) also get a thin rod from the actual
    ceiling surface (`ceiling_height`, the raw pre-mountHeight value) down to
    the housing top, so the drop is visible, not just implied by numbers in
    JSON."""
    x, y, z = binding['positionM']
    w, d, h = merged['width'], merged['depth'], merged['height']
    fixture_mat = mats.get('metal', mats['frame'])
    created = []
    if merged['mount'] == 'ceiling':
        created.append(block(f"lighting.{item['id']}.shade", x-w/2, x+w/2, z-d/2, z+d/2, y-h, y, fixture_mat, .01, item))
        if ceiling_height is not None and ceiling_height - y > 1e-6:
            rod_w = min(.02, w*.1)
            created.append(block(f"lighting.{item['id']}.rod", x-rod_w/2, x+rod_w/2, z-rod_w/2, z+rod_w/2,
                y, ceiling_height, mats['frame'], 0, item))
    else:
        # W06: no light-bracket instance exists in data/electrical.json yet
        # (see lighting-settings.json's note) -- this placeholder stays a
        # plain axis-aligned box, matching the "壁付けは小さな座標テストで可"
        # scope (position is what matters; visual wall-facing rotation of
        # this placeholder is not required this round).
        created.append(block(f"lighting.{item['id']}.body", x-w/2, x+w/2, z-d/2, z+d/2, y-h/2, y+h/2, fixture_mat, .005, item))
    return created
