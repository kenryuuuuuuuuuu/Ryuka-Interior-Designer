"""Pure geometry for Blender's wall adapter; all lengths are source metres.

Wall topology comes from generated/exterior-walls.json, never from independently
reconstructing the footprint union here. Keep source records on every fragment.
"""


def wall_segments(length0, length1, y0, height, cuts):
    """Rectangles covering a wall minus openings, clipped to the wall envelope."""
    top = y0 + height
    clipped = []
    for a, b, low, high in cuts:
        a, b = max(length0, a), min(length1, b)
        low, high = max(y0, y0 + low), min(top, y0 + high)
        if b > a and high > low:
            clipped.append((a, b, low, high))
    xs = sorted({length0, length1, *(v for c in clipped for v in c[:2])})
    result = []
    for a, b in zip(xs, xs[1:]):
        active = [c for c in clipped if c[0] < b and c[1] > a]
        ys = sorted({y0, top, *(v for c in active for v in c[2:])})
        for low, high in zip(ys, ys[1:]):
            mx, my = (a + b) / 2, (low + high) / 2
            if not any(c[0] < mx < c[1] and c[2] < my < c[3] for c in active):
                if b - a > 1e-6 and high - low > 1e-6:
                    result.append((a, b, low, high))
    return result


def opening_plane(data, opening):
    """Resolve the current face/offset contract, including explicit 2F wallX."""
    fps = [f for f in data['footprints'] if f['level'] == opening['level']]
    if opening['face'] in ('N', 'S'):
        # Same first-match convention as segAtX() in the web viewer.
        fp = next(f for f in fps if f['x0'] - 1e-6 <= opening['offset'] <= f['x1'] + 1e-6)
        return 'H', fp['z0' if opening['face'] == 'N' else 'z1']
    fallback = (max(f['x1'] for f in fps) if opening['face'] == 'E'
                else min(f['x0'] for f in fps))
    return 'V', opening.get('wallX', fallback)


def exterior_wall_panels(data):
    """Split the shared external wall segments; an opening may cross a zone seam."""
    panels = []
    for wall in data['exteriorWalls']:
        horizontal = wall['orientation'] == 'H'
        at = wall['z0'] if horizontal else wall['x0']
        start, end = (wall['x0'], wall['x1']) if horizontal else (wall['z0'], wall['z1'])
        related = []
        for opening in data['openings']:
            if opening['level'] != wall['level']:
                continue
            orientation, fixed = opening_plane(data, opening)
            if orientation == wall['orientation'] and abs(fixed - at) < 1e-6:
                if opening['offset'] < end and opening['offset'] + opening['width'] > start:
                    related.append(opening)
        cuts = [(o['offset'], o['offset'] + o['width'], o['sill'], o['sill'] + o['height'])
                for o in related]
        base = data['levels'][f"fl{wall['level']}"]
        for index, (a, b, low, high) in enumerate(wall_segments(
                start, end, base, data['defaults']['ceilingHeight'], cuts)):
            panels.append(dict(wall=wall, openings=related, index=index,
                               at=at, start=a, end=b, bottom=low, top=high))
    return panels
