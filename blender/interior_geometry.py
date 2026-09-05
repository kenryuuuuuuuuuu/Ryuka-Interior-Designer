"""Render-envelope geometry from shared topology, using absolute GL heights."""
import math


def point_in_room(x, z, polygon):
    """Use placement geometry, since the Web editor's room label may be stale."""
    inside = False
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        dx,dz=b[0]-a[0],b[1]-a[1]
        if abs((x-a[0])*dz-(z-a[1])*dx)<1e-8 and min(a[0],b[0])-1e-8<=x<=max(a[0],b[0])+1e-8 and min(a[1],b[1])-1e-8<=z<=max(a[1],b[1])+1e-8:
            return True
        if (a[1]>z)!=(b[1]>z) and x<a[0]+(z-a[1])*dx/dz:
            inside=not inside
    return inside


def ceiling_y(data, piece, z):
    if piece and piece.get('sloped'):
        return (piece['base'] + (z + .5) * piece['pitch'] - piece['roofThickness']/2
                - data['defaults'].get('ceilingAllowance', .15))
    return data['levels']['fl1'] + data['defaults']['ceilingHeight']


def height_runs(data, wall):
    horizontal = wall['orientation'] == 'H'
    at = wall['z0'] if horizontal else wall['x0']
    start, end = (wall['x0'], wall['x1']) if horizontal else (wall['z0'], wall['z1'])
    base = data['levels'][f"fl{wall['level']}"]
    default_top = base + data['defaults']['ceilingHeight']
    if 'guardHeight' in wall:
        return [(start, end, base+wall['guardHeight'], base+wall['guardHeight'])]
    pieces = data['envelope']['slopedCeilingPieces'] if wall['level'] == 1 else []
    breaks = {start, end}
    for p in pieces:
        for v in (p['x0'], p['x1']) if horizontal else (p['z0'], p['z1']):
            if start < v < end:
                breaks.add(v)
    result = []
    xs = sorted(breaks)
    for a, b in zip(xs, xs[1:]):
        mid = (a+b)/2
        selected = []
        for offset in (-.03, .03):
            x, z = (mid, at+offset) if horizontal else (at+offset, mid)
            selected.append(next((p for p in pieces if p['x0'] <= x <= p['x1'] and
                                  p['z0'] <= z <= p['z1']), None))
        # Select the region with interior samples, then evaluate its equation at
        # exact endpoints. No FL double subtraction or shortened sloped wall top.
        top = lambda u: max([default_top] + [ceiling_y(data, p, at if horizontal else u)
                                             for p in selected if p])
        result.append((a, b, top(a), top(b)))
    return result


def clip(poly, value):
    """Clip a polygon to the positive half-plane of an affine function."""
    out = []
    for a, b in zip(poly, poly[1:]+poly[:1]):
        va, vb = value(a), value(b)
        if va >= -1e-9:
            out.append(a)
        if (va > 0 and vb < 0) or (va < 0 and vb > 0):
            t = va / (va-vb)
            out.append((a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])))
    clean = []
    for p in out:
        if not clean or math.dist(p, clean[-1]) > 1e-8:
            clean.append(p)
    if len(clean) > 1 and math.dist(clean[0], clean[-1]) < 1e-8:
        clean.pop()
    area = abs(sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(clean, clean[1:]+clean[:1])))/2
    return clean if len(clean) >= 3 and area > 1e-10 else []


def arch_top(opening, u):
    if opening.get('operation') != 'open-arch':
        return opening['top']
    width, rise = opening['end']-opening['start'], opening['archRise']
    radius = width*width/(8*rise) + rise/2
    x = u - (opening['start']+opening['end'])/2
    return opening['top']-radius + math.sqrt(max(0, radius*radius-x*x))


def wall_polygons(data, wall, openings):
    """Solid polygons around rectangular/arched holes under piecewise sloped tops."""
    base = data['levels'][f"fl{wall['level']}"]
    result = []
    for start, end, top_a, top_b in height_runs(data, wall):
        breaks = {start, end}
        active = [o for o in openings if o['start'] < end and o['end'] > start]
        for o in active:
            segments = 48 if o.get('operation') == 'open-arch' else 1
            for i in range(segments+1):
                v = o['start'] + (o['end']-o['start'])*i/segments
                if start < v < end:
                    breaks.add(v)
        xs = sorted(breaks)
        top_at = lambda x: top_a + (top_b-top_a)*(x-start)/(end-start)
        for a, b in zip(xs, xs[1:]):
            if b-a < 1e-6:
                continue
            solids = [[(a, base), (b, base), (b, top_at(b)), (a, top_at(a))]]
            for o in active:
                if not o['start'] < (a+b)/2 < o['end']:
                    continue
                ha, hb = arch_top(o, a), arch_top(o, b)
                upper = lambda p: p[1] - (ha+(hb-ha)*(p[0]-a)/(b-a))
                lower = lambda p: o['bottom']-p[1]
                solids = [part for poly in solids for part in (clip(poly, lower), clip(poly, upper)) if part]
            result.extend(solids)
    return result
