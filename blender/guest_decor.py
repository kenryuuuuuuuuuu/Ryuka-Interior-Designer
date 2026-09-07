"""Regenerable visual dressing, anchored to canonical furniture/openings.

This first wall-mounted implementation deliberately supports south windows and
north-facing room boundaries only; unsupported anchors fail instead of drifting.
"""
import math


def number(item, key, low, high):
    value = item.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{item.get('id')}: invalid {key}")
    return value


def resolve(document, data, furniture, openings):
    if document.get('schemaVersion') != '0.1.0':
        raise ValueError('Unsupported decoration schema')
    room = next((r for r in data['rooms'] if r['id'] == document['roomId']), None)
    if room is None:
        raise ValueError('Decoration room missing')
    floor = data['levels'][f"fl{room['level']}"]
    by_furniture = {i['id']: i for i in furniture}
    by_opening = {i['id']: i for i in openings}
    result, seen = [], set()
    for item in document['items']:
        ident = item.get('id')
        if not isinstance(ident, str) or not ident or ident in seen or item.get('status') != 'estimated' or not item.get('note'):
            raise ValueError('Decoration requires unique id and estimated provenance')
        seen.add(ident)
        kind = item.get('kind')
        resolved = dict(item, floor=floor)
        if kind in ('rug', 'slat'):
            parent = by_furniture.get(item.get('furnitureId'))
            if parent is None or parent['level'] != room['level']:
                raise ValueError(f'{ident}: furniture anchor missing from study room')
            resolved.update(x=parent['x'], z=parent['z'], rotation=parent.get('rotation', 0))
            number(item, 'width', .3, 3)
        if kind == 'rug':
            number(item, 'depth', .3, 3)
        elif kind == 'blind':
            op = by_opening.get(item.get('openingId'))
            if op is None or op.get('face') != 'S' or op['level'] != room['level'] or not op.get('exterior') or not op['type'].startswith('window'):
                raise ValueError(f'{ident}: requires a south exterior window on the study level')
            number(item, 'dropFraction', .01, 1)
            resolved.update(x=(op['start']+op['end'])/2, z=op['at']-data['defaults']['wallThickness']/2-.045,
                            width=op['end']-op['start']+.06, top=op['top'], drop=(op['top']-op['bottom'])*item['dropFraction'])
        elif kind == 'slat':
            number(item, 'height', .3, 2)
            number(item, 'bottom', .8, 2)
            polygon = room['polygon']
            candidates = [a[1] for a, b in zip(polygon, polygon[1:]+polygon[:1])
                          if abs(a[1]-b[1]) < 1e-6 and a[1] < parent['z']
                          and min(a[0], b[0]) <= parent['x']-item['width']/2-.08
                          and max(a[0], b[0]) >= parent['x']+item['width']/2+.08]
            if not candidates:
                raise ValueError(f'{ident}: no north wall spanning ornament behind furniture')
            resolved['z'] = max(candidates)+data['defaults']['interiorWallThickness']/2+.015
        else:
            raise ValueError(f'{ident}: unknown decoration kind {kind}')
        result.append(resolved)
    return result


def build(document, data, furniture, openings, mats, block, mesh):
    resolved = resolve(document, data, furniture, openings)
    for item in resolved:
        prefix = 'decoration.'+item['id']+'.'
        x, z, floor = item['x'], item['z'], item['floor']
        w = item['width']
        def box(name, bounds, role, bevel=0):
            return block(prefix+name, *bounds, mats[role], bevel, item)
        if item['kind'] == 'rug':
            d = item['depth']
            obj = box('woven', (-w/2,w/2,-d/2,d/2,.002,.012), 'fabric', .003)
            # Same source-to-Blender convention as furniture.
            angle = math.radians(item['rotation']); c, s = math.cos(angle), math.sin(angle)
            for v in obj.data.vertices:
                vx, vy, vz = v.co
                v.co = (c*vx-s*vy+x, s*vx+c*vy-z, vz+floor)
        elif item['kind'] == 'blind':
            top, drop = item['top'], item['drop']
            box('roller-case', (x-w/2,x+w/2,z-.04,z+.015,top,top+.07), 'fabric', .02)
            box('cloth', (x-w/2,x+w/2,z-.012,z-.008,top-drop,top+.005), 'fabric')
            box('bottom-rail', (x-w/2,x+w/2,z-.02,z,top-drop-.012,top-drop+.012), 'fabric', .006)
        else:
            h = item['height']; cy = floor+item['bottom']+h/2
            # Elliptical annulus extruded through depth. Four loops, all closed.
            count = 96; vertices = []
            for depth, inset in ((0,0),(0,.025),(.025,0),(.025,.025)):
                vertices += [(x+(w/2-inset)*math.cos(j*2*math.pi/count), -(z+depth),
                              cy+(h/2-inset)*math.sin(j*2*math.pi/count)) for j in range(count)]
            faces = []
            for a,b in ((0,1),(2,0),(1,3),(3,2)):
                for j in range(count):
                    k=(j+1)%count
                    faces.append((a*count+j,a*count+k,b*count+k,b*count+j))
            mesh(prefix+'oval-frame', vertices, faces, mats['wood'], item)
            rx, ry = w/2-.026, h/2-.026
            for j in range(-8,9):
                dx=j*.05; half=.009
                if abs(dx)+half >= rx: continue
                extent=ry*math.sqrt(1-((abs(dx)+half)/rx)**2)
                box(f'slat-{j+8}', (x+dx-half,x+dx+half,z+.006,z+.022,cy-extent,cy+extent), 'wood', .002)
            y=cy-h*.2
            box('shelf', (x-w/2-.08,x+w/2+.08,z,z+.15,y,y+.025), 'wood', .004)
    return resolved
