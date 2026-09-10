"""W07-G2: guest circulation -- door/room connectivity resolved purely from
house.json's current room polygons and interior-doors.json's own
(orientation, wallAt, center, width) geometry, never from either file's
label text (several existing guest-area door labels are stale after the
hall was split out of the old genkan room; see
docs/tasks/W07-G2-guest-circulation.md section 1).

Pure Python; shared by Blender (build_interior.py, which turns a resolved
connection into real openable-leaf geometry), scripts/enable-unreal-
walkthrough.py (which turns the same connections into walkthrough.json's
`connections` list for the native C++ walkthrough), and study_controls.py/
tests (doorStates existence/consistency checks). Mirrors surface_registry.py/
electrical_assets.py's own split: structural geometry resolution lives here;
model-dependent "does this state's doorStates key name a real door"
resolution is resolve_door_overrides() below, called once per apply.
"""
import math

DOOR_BINDINGS_SCHEMA = '1.0.0'
PROFILES_SCHEMA = '1.0.0'
# Only these catalog `operation`s are in scope for W07-G2 (spec section 2:
# "今回必要なswing/slide/double-swingとopenを対象にします...自宅のfold等まで
# 今回一般化する必要はありません"). 'open' has no leaf/no door state at all --
# always passable -- everything else here has a real, closeable leaf.
SUPPORTED_OPERATIONS = ('swing', 'double-swing', 'slide', 'open')
OPENABLE_OPERATIONS = ('swing', 'double-swing', 'slide')


def _room_edges(polygon):
    n = len(polygon)
    return [(polygon[i], polygon[(i + 1) % n]) for i in range(n)]


def room_boundary_contains_span(polygon, horizontal, at, lo, hi, eps=1e-6):
    """True if `polygon` has an edge lying exactly on the line (z=at for a
    horizontal wall, x=at for vertical) whose own extent covers [lo, hi]
    (with a small tolerance for floating-point round-trip, not for genuinely
    mismatched geometry)."""
    for a, b in _room_edges(polygon):
        if horizontal:
            if abs(a[1] - at) < eps and abs(b[1] - at) < eps:
                elo, ehi = sorted((a[0], b[0]))
                if elo - eps <= lo and hi <= ehi + eps:
                    return True
        else:
            if abs(a[0] - at) < eps and abs(b[0] - at) < eps:
                elo, ehi = sorted((a[1], b[1]))
                if elo - eps <= lo and hi <= ehi + eps:
                    return True
    return False


def merged_door(item, catalog_by_type):
    """Same override precedence as blender/electrical_assets.py's
    merged_item(): catalog defaults, then this instance's own explicit
    `*Override` fields only (never a bare same-named field on the instance,
    which the schema does not use for doors)."""
    catalog = catalog_by_type.get(item.get('type'))
    if catalog is None:
        raise ValueError(f"Unknown door type {item.get('type')!r} ({item.get('id')})")
    merged = dict(catalog)
    for key in ('id', 'orientation', 'wallAt', 'center', 'hingeSide', 'swingDir', 'slideDir'):
        if key in item:
            merged[key] = item[key]
    for key in ('width', 'height', 'sill'):
        override = item.get(key + 'Override')
        if override is not None:
            merged[key] = override
    return merged


def resolve_connections(rooms_by_id, interior_doors, catalog_by_type, room_ids):
    """Connections among `room_ids` (a set of house.json room ids), derived
    purely from geometry. Returns a list of dicts (one per door that
    actually joins exactly two of `room_ids`): id, level, operation,
    roomIds (sorted pair), orientation, wallAt, center, width, height, sill,
    hingeSide, swingDir, slideDir.

    A door touching fewer than two of `room_ids` (a self-house door, or one
    whose far side is simply out of THIS profile) is skipped, not an error
    -- W07-G1's own "対象外室は生成全体を止めない" precedent. A door matching
    MORE than two rooms in scope is a real data problem (an edge shared by
    three+ room polygons at once) and does raise, since a door cannot
    physically connect more than two spaces."""
    room_ids = set(room_ids)
    connections = []
    for item in interior_doors:
        orientation = item.get('orientation')
        if orientation not in ('H', 'V'):
            continue  # diagonal frameless openings (orientation 'D') are unrelated self-house fixtures
        merged = merged_door(item, catalog_by_type)
        operation = merged.get('operation')
        if operation not in SUPPORTED_OPERATIONS:
            continue
        at, center, width = merged['wallAt'], merged['center'], merged['width']
        lo, hi = center - width / 2, center + width / 2
        horizontal = orientation == 'H'
        matches = sorted(room_id for room_id in room_ids
                          if room_id in rooms_by_id
                          and room_boundary_contains_span(rooms_by_id[room_id]['polygon'], horizontal, at, lo, hi))
        if len(matches) < 2:
            continue
        if len(matches) > 2:
            raise ValueError(f"door {item['id']!r} matches more than two rooms in scope: {matches}")
        # W07-G2 review R3: which way a SWING leaf opens is derived from
        # GEOMETRY, not the door instance's own swingDir/hingeSide fields
        # (authored for exterior openings, and -- like several guest door
        # LABELS -- not reliable for interior use). A swing leaf opens TOWARD
        # whichever of the two rooms reaches FURTHER from the shared wall (a
        # door into a room, never into a narrow hall). `swingToward`: '+' =
        # toward the larger-perpendicular-coordinate side of the wall.
        # (A slide leaf's along-wall tuck direction is separate --
        # slide_open_offset() keeps using slideDir.)
        perp_index = 1 if horizontal else 0
        def _reach(room_id):
            coords = [p[perp_index] for p in rooms_by_id[room_id]['polygon']]
            return max(max(coords) - at, 0.0), max(at - min(coords), 0.0)  # (reach on + side, reach on - side)
        reach_a, reach_b = _reach(matches[0]), _reach(matches[1])
        reach_plus = max(reach_a[0], reach_b[0])
        reach_minus = max(reach_a[1], reach_b[1])
        swing_toward = '+' if reach_plus >= reach_minus else '-'
        conn = dict(id=item['id'], level=item.get('floor'), operation=operation, roomIds=matches,
            orientation=orientation, wallAt=at, center=center, width=width, height=merged['height'],
            sill=merged.get('sill', 0), hingeSide=merged.get('hingeSide'), swingDir=merged.get('swingDir'),
            slideDir=merged.get('slideDir'), swingToward=swing_toward)
        # W07-G2 review-v3 R1: the SAFE open angle (a fixed leaf cannot swing
        # through a fixed building wall) is resolved HERE, once, as a
        # generation condition -- 85 deg unless a wall of the room the leaf
        # opens into cuts the arc short. Every consumer (Blender bake, UE
        # import, editor apply_state, native walkthrough) then applies the
        # SAME closed/open transforms; the runtime interference check only
        # has to watch for FURNITURE / a person / another leaf between two
        # poses that are both already known wall-safe.
        if operation in ('swing', 'double-swing'):
            swing_room = matches[0] if _reach(matches[0])[0 if swing_toward == '+' else 1] >= \
                _reach(matches[1])[0 if swing_toward == '+' else 1] else matches[1]
            conn['maxSwingDeltaDeg'] = _wall_limited_swing_deg(
                conn, rooms_by_id[swing_room]['polygon'], BASE_SWING_DEG)
        connections.append(conn)
    return connections


BASE_SWING_DEG = 85.0  # a few degrees short of 90 so an open leaf clears a flush frame


def _seg_seg_distance(p1, p2, p3, p4):
    """Minimum distance between segment p1p2 and segment p3p4 (0 if they
    cross). Pure 2D."""
    import math

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    if ((cross(p3, p4, p1) > 0) != (cross(p3, p4, p2) > 0)
            and (cross(p1, p2, p3) > 0) != (cross(p1, p2, p4) > 0)):
        return 0.0

    def pt_seg(p, a, b):
        ax, ay, bx, by = a[0], a[1], b[0], b[1]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))
    return min(pt_seg(p1, p3, p4), pt_seg(p2, p3, p4),
              pt_seg(p3, p1, p2), pt_seg(p4, p1, p2))


def _wall_limited_swing_deg(connection, swing_room_polygon, ideal_deg):
    """Largest opening angle (<= ideal_deg) at which the leaf -- a segment
    from its hinge, ~one opening-width long -- does not cross a boundary
    wall of the room it swings into. The wall the door is MOUNTED in (the
    polygon edge collinear with `wallAt`) is excluded; the leaf swings away
    from it. Pure 2D, source metres. Conservative: a small inset keeps a
    leaf flush in its own jamb from counting, and 2-3 deg of margin is
    dropped so the runtime pose (measured against real geometry) is never
    tighter than this."""
    import math
    at = connection['wallAt']
    lo = connection['center'] - connection['width'] / 2
    hi = connection['center'] + connection['width'] / 2
    horizontal = connection['orientation'] == 'H'
    toward_plus = connection['swingToward'] == '+'
    edges = [(swing_room_polygon[i], swing_room_polygon[(i + 1) % len(swing_room_polygon)])
             for i in range(len(swing_room_polygon))]
    # drop edges collinear with the mounting wall (perp coord == at)
    def _on_mount(e):
        (ax, az), (bx, bz) = e
        return (abs((az if horizontal else ax) - at) < 1e-6
                and abs((bz if horizontal else bx) - at) < 1e-6)
    edges = [e for e in edges if not _on_mount(e)]

    def hinge_and_free(hinge_side):
        u_h = lo if hinge_side != 'R' else hi
        u_f = hi if hinge_side != 'R' else lo
        hinge = (u_h, at) if horizontal else (at, u_h)
        free = (u_f, at) if horizontal else (at, u_f)
        return hinge, free

    hinge_sides = ['L', 'R'] if connection['operation'] == 'double-swing' \
        else [connection.get('hingeSide') or 'L']
    # wall half-thickness (~0.06) + leaf half-thickness (~0.02) + clearance
    margin = 0.10
    limit = ideal_deg
    for hs in hinge_sides:
        hinge, free_closed = hinge_and_free(hs)
        vx, vy = free_closed[0] - hinge[0], free_closed[1] - hinge[1]
        vlen = math.hypot(vx, vy)
        vx, vy = vx / vlen, vy / vlen
        radius = connection['width']

        def seg_at(dirx, diry):
            return ((hinge[0] + dirx * radius * 0.3, hinge[1] + diry * radius * 0.3),
                    (hinge[0] + dirx * radius, hinge[1] + diry * radius))
        # Edges the CLOSED leaf already lies flush against belong to the
        # doorway itself (far jamb / opening frame); the leaf only moves AWAY
        # from them as it swings in, so they are not obstacles.
        closed_a, closed_b = seg_at(vx, vy)
        active = [e for e in edges
                  if _seg_seg_distance(closed_a, closed_b, e[0], e[1]) > margin + 0.06]
        # rotation sense that carries the free end toward `swingToward`
        sense = 1.0
        for rot_sign in (1.0, -1.0):
            th = math.radians(5.0) * rot_sign
            c, s = math.cos(th), math.sin(th)
            comp = ((vx * s + vy * c) - vy) if horizontal else ((vx * c - vy * s) - vx)
            if (comp > 0) == toward_plus:
                sense = rot_sign
                break
        cleared = ideal_deg
        for deg in range(5, int(ideal_deg) + 1):
            th = math.radians(deg) * sense
            c, s = math.cos(th), math.sin(th)
            seg_a, seg_b = seg_at(vx * c - vy * s, vx * s + vy * c)
            if any(_seg_seg_distance(seg_a, seg_b, e[0], e[1]) < margin for e in active):
                cleared = deg - 3.0  # 3 deg safety margin below the first contact
                break
        limit = min(limit, max(cleared, 0.0))
    return round(limit, 1)


def validate_profiles(document):
    if not isinstance(document, dict) or document.get('schemaVersion') != PROFILES_SCHEMA:
        raise ValueError('Unsupported walkthrough-profiles schema')
    profiles = document.get('profiles')
    if not isinstance(profiles, list) or not profiles:
        raise ValueError('walkthrough-profiles.json must have a non-empty profiles list')
    seen = set()
    for profile in profiles:
        profile_id = profile.get('profileId')
        if not isinstance(profile_id, str) or not profile_id:
            raise ValueError('Invalid profileId')
        if profile_id in seen:
            raise ValueError(f'Duplicate profileId: {profile_id}')
        seen.add(profile_id)
        if not isinstance(profile.get('scopeId'), str) or not profile['scopeId']:
            raise ValueError(f'{profile_id}: invalid scopeId')
        room_ids = profile.get('roomIds')
        if not isinstance(room_ids, list) or not room_ids or len(set(room_ids)) != len(room_ids):
            raise ValueError(f'{profile_id}: roomIds must be a non-empty list of unique room ids')
        if profile.get('entryRoomId') not in room_ids:
            raise ValueError(f'{profile_id}: entryRoomId must be one of roomIds')
    return document


def resolve_profile_for_scope(document, scope_id):
    validate_profiles(document)
    for profile in document['profiles']:
        if profile['scopeId'] == scope_id:
            return profile
    raise ValueError(f'No walkthrough profile for scope {scope_id!r}')


def validate_door_bindings(document):
    if not isinstance(document, dict) or document.get('schemaVersion') != DOOR_BINDINGS_SCHEMA:
        raise ValueError('Unsupported door-bindings schema')
    doors = document.get('doors')
    if not isinstance(doors, dict):
        raise ValueError('door-bindings.json must have a doors object')
    for door_id, info in doors.items():
        if not isinstance(info, dict):
            raise ValueError(f'doors[{door_id}] must be an object')
        if info.get('operation') not in SUPPORTED_OPERATIONS:
            raise ValueError(f'doors[{door_id}]: invalid operation')
        if not isinstance(info.get('roomIds'), list) or len(info['roomIds']) != 2:
            raise ValueError(f'doors[{door_id}]: roomIds must name exactly two rooms')
        if not isinstance(info.get('openable'), bool):
            raise ValueError(f'doors[{door_id}]: invalid openable flag')
        if info['openable']:
            if not info.get('leaves'):
                raise ValueError(f'doors[{door_id}]: openable door must have at least one leaf')
            for leaf in info['leaves']:
                # W07-G2 review R1: each leaf's INITIAL pose (this generation's
                # own render, and what UE actually imports) must now match the
                # state doorStates given to Blender, not always start closed --
                # `bakedOpen` records which one generation actually chose.
                if not isinstance(leaf, dict) or not isinstance(leaf.get('bakedOpen'), bool):
                    raise ValueError(f'doors[{door_id}]: each leaf must record bakedOpen (bool)')
                # W07-G2 review-v2 R1: a sliding leaf's IMMUTABLE closed
                # world location. Absent in the raw Blender output (Blender
                # only knows its own coordinate space); import_study.py
                # captures it once on the fresh imported scene and stamps it
                # here, and from then on every consumer references THIS fixed
                # value instead of re-estimating a baseline from a live pose.
                # So: optional (raw bindings pass), but if present it must be
                # a 3-number vector.
                if 'closedLocationCm' in leaf:
                    v = leaf['closedLocationCm']
                    if (not isinstance(v, list) or len(v) != 3
                            or not all(isinstance(c, (int, float)) for c in v)):
                        raise ValueError(f'doors[{door_id}]: closedLocationCm must be [x, y, z]')
    return document


def resolve_door_overrides(door_states, door_bindings):
    """Model-dependent split of a (already structurally-valid) doorStates
    dict, mirroring surface_finish_overrides.resolve_overrides()/
    lighting.resolve_fixture_overrides(): usable entries (name a real,
    currently-openable door) vs. issues (unknown id, or a real door that has
    no leaf at all -- e.g. an 'open' operation door, which carries no state
    by definition). Never raises -- the caller decides whether ANY issue
    stops the whole apply (W07-G2 spec section 4: "未知ID、非対象ID...は適用
    前に拒否")."""
    doors = door_bindings.get('doors', {}) if door_bindings else {}
    usable, issues = {}, []
    for door_id, override in door_states.items():
        info = doors.get(door_id)
        if info is None:
            issues.append(dict(id=door_id, reason=f'Unknown door id: {door_id}'))
        elif not info.get('openable'):
            issues.append(dict(id=door_id, reason=f'Door {door_id} has no leaf to open/close'))
        else:
            usable[door_id] = override
    return usable, issues


def effective_door_open(door_id, door_states):
    """A door with no entry in doorStates reads as closed (W07-G2 spec
    section 4: "扉指定なしは閉状態")."""
    return bool(door_states.get(door_id, {}).get('open', False))


# --------------------------------------------------------------------------
# Leaf transform geometry (swing hinge / slide offset), source metres.
# --------------------------------------------------------------------------

def swing_hinge_and_delta(connection, room_polygon_for_swing_side):
    """For a single-leaf swing door: (hinge_point, open_yaw_delta_deg).
    hinge_point is the (x, z) end of the opening span the leaf is hinged at
    (hingeSide 'L' = the lower-coordinate end along the wall, 'R' = the
    higher one -- an explicit, self-consistent convention recorded here
    since interior-doors.json's hingeSide/swingDir were authored for
    exterior openings only; W07-G2 spec section 2 explicitly allows this
    kind of documented estimate). `room_polygon_for_swing_side` is unused by
    single-leaf swing (kept for symmetry with double_swing_hinges_and_deltas,
    which needs it) and may be None."""
    lo, hi = connection['center'] - connection['width'] / 2, connection['center'] + connection['width'] / 2
    hinge_lo = connection.get('hingeSide') != 'R'
    at = connection['wallAt']
    if connection['orientation'] == 'H':
        hinge = (lo if hinge_lo else hi, at)
    else:
        hinge = (at, lo if hinge_lo else hi)
    delta = _swing_delta_deg(connection)
    return hinge, delta


def _swing_delta_deg(connection, sign=1.0):
    """Signed yaw delta (Blender-space, source degrees about +Y-equivalent)
    applied when opening. The leaf swings toward `swingToward` -- the side of
    the wall (larger perpendicular coord = '+') that resolve_connections()
    derived from GEOMETRY as the room reaching furthest from the wall (a door
    into a room, not into a narrow hall). Never into the wall itself; falls
    back to the door instance's own swingDir only for a connection that
    predates swingToward."""
    # W07-G2 review-v3 R1: the magnitude is the SAFE open angle resolved once
    # in resolve_connections() against the fixed building walls -- 85 unless a
    # wall of the room the leaf opens into cuts the arc short (e.g. door-002,
    # limited by the LDK's west wall). One value, shared by every consumer.
    base = min(85.0, connection.get('maxSwingDeltaDeg', 85.0))
    toward = connection.get('swingToward')
    toward_positive = (toward == '+') if toward in ('+', '-') else (connection.get('swingDir') != 'in')
    # hingeSide determines which end is fixed; the leaf always sweeps AWAY
    # from its own hinge, so the rotation sign also depends on which end
    # that is (Ln hinge sweeps toward +u, R hinge sweeps toward -u, for the
    # "toward larger coordinate" case).
    hinge_lo = connection.get('hingeSide') != 'R'
    magnitude = base if (toward_positive == hinge_lo) else -base
    # W07-G2 review-v2 R3: for an H wall the leaf lies along x and swings in
    # z; for a V wall it lies along z and swings in x. The wall-sweep axis
    # and the along-wall axis are swapped, and one of the two (Blender/UE Y)
    # is the reflected one, so the yaw sign that sends a leaf toward
    # `swingToward` is INVERTED between the two orientations. The formula
    # above was derived (and verified against door-002, an H wall opening
    # into the LDK) for H; flip it for V (verified against door-024, the
    # 洋室/収納 double-swing, which otherwise opened into the closet).
    if connection.get('orientation') == 'V':
        magnitude = -magnitude
    return magnitude * sign


def double_swing_hinges_and_deltas(connection):
    """For a double-swing door (door-catalog operation 'double-swing', e.g.
    a closet): two independent leaves, each hinged at its OWN outer edge of
    the opening, each covering half the width, BOTH swinging toward the
    SAME target room (spec: "両開きは2葉の回転で開閉"). Returns
    [(hinge_left, delta_left, 'left'), (hinge_right, delta_right, 'right')].

    W07-G2 review R3: a leaf's sign convention already flips with its own
    hingeSide inside _swing_delta_deg() (a hinge at the 'lo' end and one at
    the 'hi' end need OPPOSITE-signed yaw deltas to sweep into the SAME
    room -- mirrored hinges, mirrored rotation direction, same destination).
    Calling it plainly for both leaves (each with its own correct hingeSide)
    already produces that opposite-sign pair; the previous code ALSO passed
    sign=-1.0 for the right leaf, double-flipping it back to the SAME sign
    as the left leaf -- which sends the two leaves toward DIFFERENT rooms
    (confirmed against the real door-024 data: both leaves got the same
    openYawDeltaDeg=-85, one swinging toward 洋室, the other toward 収納)."""
    lo, hi = connection['center'] - connection['width'] / 2, connection['center'] + connection['width'] / 2
    at = connection['wallAt']
    horizontal = connection['orientation'] == 'H'
    left_hinge = (lo, at) if horizontal else (at, lo)
    right_hinge = (hi, at) if horizontal else (at, hi)
    left = dict(connection, hingeSide='L')
    right = dict(connection, hingeSide='R')
    return [(left_hinge, _swing_delta_deg(left), 'left'), (right_hinge, _swing_delta_deg(right), 'right')]


def swing_leaf_free_end_travel(connection, hinge_xy, delta_deg):
    """The (dx, dz) SOURCE-space displacement of a swing leaf's free end when
    it opens by `delta_deg` -- used to check the leaf actually swings toward
    `connection['swingToward']` and not into the wall/closet.

    Model: the leaf lies flat in the wall when closed (its free end one
    opening-width from the hinge along the wall). build_interior.py applies
    the open pose in BLENDER as rotation_euler[2] = radians(-delta_deg), and
    Blender axes are (X = source x, Y = -(source z)); so this reproduces that
    exact rotation and maps the result back to source space."""
    import math
    at = connection['wallAt']
    lo = connection['center'] - connection['width'] / 2
    hi = connection['center'] + connection['width'] / 2
    hx, hz = hinge_xy
    # free end (closed), source space: the OTHER end of the opening span
    if connection['orientation'] == 'H':
        fx, fz = (hi if abs(hx - lo) < abs(hx - hi) else lo), at
    else:
        fx, fz = at, (hi if abs(hz - lo) < abs(hz - hi) else lo)
    # closed free-end offset from hinge, in Blender coords (X=x, Y=-z)
    bx, by = fx - hx, -(fz - hz)
    theta = math.radians(-delta_deg)
    rx = bx * math.cos(theta) - by * math.sin(theta)
    ry = bx * math.sin(theta) + by * math.cos(theta)
    # back to source: dx = rx - bx (Blender X == source x); dz = -(ry - by)
    return (rx - bx, -(ry - by))


def slide_open_offset(connection):
    """(dx, dz) in source metres to add to the leaf's spawn (closed)
    position when open -- a pure translation along the wall, magnitude one
    full leaf width, direction from slideDir ('L' = toward lower coordinate
    along the wall, 'R' = toward higher)."""
    sign = -1.0 if connection.get('slideDir') != 'R' else 1.0
    distance = connection['width'] * sign
    if connection['orientation'] == 'H':
        return (distance, 0.0)
    return (0.0, distance)
