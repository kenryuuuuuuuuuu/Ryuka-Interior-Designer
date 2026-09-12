"""Geometry helpers for binding surface-registry.json IDs to real Blender
wall/floor/ceiling pieces (W04). Pure Python (no bpy) so it is independently
testable; blender/build_interior.py is the only caller that touches bpy.

Wall pieces already come out of interior_geometry.wall_polygons() as (u,y)
profile polygons per wall entity; a registered wall surface's edge may cover
only part of a merged wall's span, so split_wall_range() reuses
interior_geometry.clip() (the same half-plane clip wall_polygons() already
uses for openings) to carve out just the registered sub-range, rather than
re-implementing polygon clipping. wall_cap_for_room() decides which of the
panel's two big faces (its "cap A" or "cap B", by prism() index) actually
faces the registered room's interior, using point_in_room() -- never the
edge's compass direction.

decompose_rectilinear()/subtract_rect() are a minimal rectangle
decomposition/subtraction pair for splitting a room's own floor polygon out
of the footprint-wide slab rectangle it currently sits inside of, without
touching neighbouring rooms sharing that same slab.
"""
from interior_geometry import clip, point_in_room


def split_wall_range(polygon, lo, hi):
    """polygon: (u,y) points in a wall's own profile space. Returns
    (before, within, after) sub-polygons split at u=lo and u=hi (lo<hi),
    each possibly empty. Uses the same half-plane clip() wall_polygons()
    already applies for opening cuts."""
    before = clip(polygon, lambda p: lo - p[0])
    rest = clip(polygon, lambda p: p[0] - lo)
    within = clip(rest, lambda p: hi - p[0]) if rest else []
    after = clip(rest, lambda p: p[0] - hi) if rest else []
    return before, within, after


def split_wall_at(polygon, breakpoints):
    """polygon: (u,y) points in a wall's own profile space. Splits it at
    EVERY u in `breakpoints` (each an independent half-plane cut, the same
    clip() split_wall_range() uses for a single lo/hi pair), returning the
    resulting sub-polygons in left-to-right u order. A breakpoint outside the
    polygon's own u-range is a no-op for that cut, and duplicate breakpoints
    collapse (a set).

    W07-G1: unlike split_wall_range()'s single lo/hi pair (which assumes only
    ONE room ever registers a marker on a given wall piece), a SHARED wall
    can have two different rooms independently registering their own
    (possibly different) sub-ranges on the SAME wall entity -- one per cap.
    Splitting at the UNION of every registration's boundaries first, then
    classifying each resulting piece, lets both sides' markers land on the
    same piece without one registration's range consuming the other's."""
    pieces = [polygon]
    for bp in sorted(set(breakpoints)):
        next_pieces = []
        for piece in pieces:
            before = clip(piece, lambda p, bp=bp: bp - p[0])
            after = clip(piece, lambda p, bp=bp: p[0] - bp)
            next_pieces += [p for p in (before, after) if p]
        pieces = next_pieces
    return pieces


def wall_cap_for_room(at, mid_u, horizontal, room_polygon, epsilon=0.03):
    """at: the wall's fixed coordinate (z for horizontal, x for vertical).
    mid_u: a point along the wall's span known to be covered by the room's
    registered edge. Returns 0 if the room's interior is on cap A's side
    (the smaller-at side: north for a horizontal wall, west for a vertical
    one -- see prism()'s vertex layout in build_interior.py), 1 if on cap
    B's side (south/east), or None if neither side lands inside the room
    (edge/room mismatch)."""
    def inside(offset):
        x, z = (mid_u, at + offset) if horizontal else (at + offset, mid_u)
        return point_in_room(x, z, room_polygon)
    if inside(-epsilon): return 0
    if inside(epsilon): return 1
    return None


def decompose_rectilinear(polygon, grid_epsilon=1e-6):
    """polygon: a simple, axis-aligned (rectilinear) room polygon, [(x,z),...].
    Returns a list of (x0,x1,z0,z1) rectangles that exactly tile it, using a
    grid built from the polygon's own vertex coordinates (always exact for a
    rectilinear polygon; pieces are not merged across grid lines, which is
    fine -- more, smaller floor/ceiling pieces are still correct, just not
    maximally consolidated)."""
    xs = sorted({p[0] for p in polygon})
    zs = sorted({p[1] for p in polygon})
    rects = []
    for i in range(len(xs)-1):
        for j in range(len(zs)-1):
            x0, x1, z0, z1 = xs[i], xs[i+1], zs[j], zs[j+1]
            if x1-x0 <= grid_epsilon or z1-z0 <= grid_epsilon: continue
            if point_in_room((x0+x1)/2, (z0+z1)/2, polygon):
                rects.append((x0, x1, z0, z1))
    return rects


def subtract_rect(a, b):
    """a, b: (x0,x1,z0,z1). Returns the list of rectangles making up a minus
    (a intersect b) -- up to 4 pieces, an exact tiling, never fewer than
    needed and never overlapping."""
    ax0, ax1, az0, az1 = a
    bx0, bx1, bz0, bz1 = b
    ox0, ox1, oz0, oz1 = max(ax0, bx0), min(ax1, bx1), max(az0, bz0), min(az1, bz1)
    if ox0 >= ox1 or oz0 >= oz1: return [a]
    pieces = []
    if az0 < oz0: pieces.append((ax0, ax1, az0, oz0))
    if oz1 < az1: pieces.append((ax0, ax1, oz1, az1))
    if ax0 < ox0: pieces.append((ax0, ox0, oz0, oz1))
    if ox1 < ax1: pieces.append((ox1, ax1, oz0, oz1))
    return pieces


def intersect_rect(a, b):
    """a, b: (x0,x1,z0,z1). Returns their overlap rectangle, or None."""
    ax0, ax1, az0, az1 = a
    bx0, bx1, bz0, bz1 = b
    x0, x1, z0, z1 = max(ax0, bx0), min(ax1, bx1), max(az0, bz0), min(az1, bz1)
    return (x0, x1, z0, z1) if x1 > x0 and z1 > z0 else None


def subtract_rects(rects, cuts):
    """Subtract every rectangle in `cuts` from every rectangle in `rects`,
    returning the remaining tiling."""
    remaining = list(rects)
    for cut in cuts:
        remaining = [piece for rect in remaining for piece in subtract_rect(rect, cut)]
    return remaining


def partition_room_faces(rect, rooms):
    """Tile a slab without approximating diagonal room boundaries by boxes.

    Split convex cells along nearby room edges, then assign the owner by
    containment. Exterior/unregistered portions retain their base material.
    """
    x0,x1,z0,z1=rect
    nearby=[r for r in rooms if max(p[0] for p in r['polygon'])>x0 and min(p[0] for p in r['polygon'])<x1
            and max(p[1] for p in r['polygon'])>z0 and min(p[1] for p in r['polygon'])<z1]
    cells=[[(x0,z0),(x1,z0),(x1,z1),(x0,z1)]]
    lines=set()
    for r in nearby:
        poly=r['polygon']
        for a,b in zip(poly,poly[1:]+poly[:1]):
            dx,dz=b[0]-a[0],b[1]-a[1]
            length=(dx*dx+dz*dz)**.5
            aa,bb,cc=-dz/length,dx/length,(dz*a[0]-dx*a[1])/length
            if aa<0 or (abs(aa)<1e-9 and bb<0): aa,bb,cc=-aa,-bb,-cc
            key=tuple(round(v,8) for v in (aa,bb,cc))
            if key in lines: continue
            lines.add(key); out=[]
            for cell in cells:
                distances=[aa*p[0]+bb*p[1]+cc for p in cell]
                if min(distances)<-1e-7 and max(distances)>1e-7:
                    out.extend(p for p in (clip(cell,lambda p:aa*p[0]+bb*p[1]+cc),clip(cell,lambda p:-aa*p[0]-bb*p[1]-cc)) if p)
                else: out.append(cell)
            cells=out
    result=[]
    for cell in cells:
        x=sum(p[0] for p in cell)/len(cell);z=sum(p[1] for p in cell)/len(cell)
        owners=[r['id'] for r in nearby if point_in_room(x,z,r['polygon'])]
        if len(owners)>1: raise ValueError('Overlapping room surfaces: '+str(owners))
        result.append((cell,owners[0] if owners else None))
    return result
