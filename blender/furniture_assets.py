"""Versioned, dimension-aware furniture assets; no Blender dependency.

Plans use source local x/z/y metres. Placement belongs exclusively to furniture.json.
"""
import math

ASSET_ID = 'sofa-timber-v1'
DIMENSIONS = {'width': (1.2, 2.4), 'depth': (.7, 1.05), 'height': (.65, 1.0)}


def validate_bindings(document, items, catalog):
    if document.get('schemaVersion') != '1.0.0' or not isinstance(document.get('bindings'), list):
        raise ValueError('Invalid furniture asset bindings')
    by_id = {i['id']: i for i in items}
    by_type = {t['type']: t for t in catalog['types']}
    result = {}
    for binding in document['bindings']:
        target = binding.get('furnitureId')
        if target in result: raise ValueError(f'Duplicate furniture binding: {target}')
        if target not in by_id: raise ValueError(f'Remove or reassign orphan furniture binding: {target}')
        registry = {'sofa-timber-v1': ('sofa', sofa_parts),
                    'round-table-v1': ('roundTable', round_table_parts),
                    'chair-timber-v1': ('timberChair', chair_parts)}
        if binding.get('assetId') not in registry or binding.get('sizing') != 'parametric':
            raise ValueError(f'Unsupported asset or sizing policy: {target}')
        if binding.get('status') != 'estimated' or not binding.get('note'):
            raise ValueError(f'Asset needs estimated status and provenance note: {target}')
        item = by_id[target]
        profile = by_type[item['type']]
        shape, factory = registry[binding['assetId']]
        if profile['shape'] != shape: raise ValueError(f'Asset assigned to another shape: {target}')
        dimensions = [item.get(k+'Override', profile[k]) for k in DIMENSIONS]
        factory(*dimensions)  # fail before rendering, never silently stretch a product
        result[target] = binding
    return result


def sofa_parts(width, depth, height):
    """Closed rounded boxes: timber frame, separate seat/back cushions and feet.

    Timber thickness stays constant as the outer dimensions change.
    Curved joinery, seams and textile weave are later appearance work.
    """
    for (key, (lo, hi)), value in zip(DIMENSIONS.items(), (width, depth, height)):
        if type(value) not in (float, int) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError(f'{ASSET_ID}: {key} must be within {lo}–{hi}m')
    w,d,h = width,depth,height
    parts=[]
    def box(name,x0,x1,z0,z1,y0,y1,material,bevel):
        parts.append(dict(name=name,bounds=[x0,x1,z0,z1,y0,y1],material=material,
                          bevel=min(bevel,(x1-x0)/3,(z1-z0)/3,(y1-y0)/3)))
    seat_top=min(.44,h*.58)
    # Posts define the outer width/depth, independently of cushion fullness.
    for side,x in [('left',-w/2),('right',w/2-.045)]:
        for end,z in [('rear',-d/2),('front',d/2-.05)]:
            box(f'{side}-{end}-post',x,x+.045,z,z+.05,0,h*.70,'wood',.009)
        box(side+'-arm',x-.0,x+.045,-d/2,d/2,h*.70,h*.70+.04,'wood',.012)
    for name,z in [('front',d/2-.06),('rear',-d/2+.01)]:
        box(name+'-rail',-w/2+.045,w/2-.045,z,z+.045,.23,.30,'wood',.008)
    box('seat-support',-w/2+.045,w/2-.045,-d/2+.05,d/2-.05,.27,.30,'wood',.008)
    box('back-rail',-w/2+.045,w/2-.045,-d/2,-d/2+.045,h-.09,h-.035,'wood',.01)
    for j in range(5):
        x=-w/2+.10+(w-.20)*j/4
        box(f'back-slat-{j}',x-.018,x+.018,-d/2,-d/2+.035,.30,h-.07,'wood',.008)
    inner=w-.13; half=inner/2
    for j in range(2):
        x=-inner/2+j*half
        box(f'seat-cushion-{j}',x+.008,x+half-.008,-d/2+.12,d/2-.025,.30,seat_top,'fabric',.055)
        box(f'back-cushion-{j}',x+.008,x+half-.008,-d/2+.035,-d/2+.20,seat_top-.035,h,'fabric',.065)
    return parts


def check_dimensions(values, limits):
    for value,(lo,hi) in zip(values,limits):
        if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:
            raise ValueError(f'Furniture dimensions outside supported range: {values}')


def solid(name,bounds,material='wood',kind='box',bevel=.008):
    return dict(name=name,bounds=bounds,material=material,kind=kind,bevel=bevel)


def round_table_parts(w,d,h):
    check_dimensions((w,d,h),((.7,1.4),(.7,1.4),(.65,.8)))
    parts=[solid('top',[-w/2,w/2,-d/2,d/2,h-.035,h],kind='ellipse',bevel=.006)]
    for j,(sx,sz) in enumerate([(-1,-1),(-1,1),(1,-1),(1,1)]):
        x,z=sx*w*.25,sz*d*.25
        parts.append(solid(f'leg-{j}',[x-.026,x+.026,z-.026,z+.026,0,h-.035],kind='ellipse'))
    return parts


def chair_parts(w,d,h):
    check_dimensions((w,d,h),((.4,.65),(.42,.65),(.75,1)))
    seat=h*.53
    parts=[solid('seat',[-w/2,w/2,-d/2,d/2,seat-.045,seat],'fabric',bevel=.02)]
    for j,(sx,sz) in enumerate([(-1,-1),(-1,1),(1,-1),(1,1)]):
        x,z=sx*(w/2-.035),sz*(d/2-.035)
        parts.append(solid(f'leg-{j}',[x-.018,x+.018,z-.018,z+.018,0,seat-.045],kind='ellipse'))
    for j,x in enumerate([-w*.35,0,w*.35]):
        parts.append(solid(f'back-support-{j}',[x-.012,x+.012,-d*.44,-d*.39,seat-.03,h-.055],bevel=.01))
    # Closed U-shaped rail, sampled at fixed angles; +z is the open front.
    poly=[]
    for i in range(33):
        angle=i*math.pi/32
        poly.append([w*.48*math.cos(angle),-d*.46*math.sin(angle)])
    for i in range(32,-1,-1):
        angle=i*math.pi/32
        poly.append([(w*.48-.028)*math.cos(angle),-(d*.46-.028)*math.sin(angle)])
    rail=solid('curved-back',[-w/2,w/2,-d/2,0,h-.055,h],kind='polygon',bevel=.005)
    rail['polygon']=poly
    parts.append(rail)
    return parts


def asset_parts(asset_id,w,d,h):
    return {'sofa-timber-v1':sofa_parts,'round-table-v1':round_table_parts,
            'chair-timber-v1':chair_parts,'range-hood-v1':hood_parts,
            'faucet-v1':faucet_parts,'air-conditioner-v1':air_conditioner_parts}[asset_id](w,d,h)


def hood_parts(w,d,h):
    check_dimensions((w,d,h),((.4,1.2),(.3,.8),(.3,1.2)))
    return [solid('canopy',[-w/2,w/2,-d/2,d/2,.012,.09],'metal',bevel=.009),
            solid('filter',[-w*.38,w*.38,-d*.35,d*.35,0,.012],'black',bevel=.002),
            solid('chimney',[-w*.24,w*.24,-d/2,-d*.02,.09,h],'metal',bevel=.008)]


def faucet_parts(w,d,h):
    check_dimensions((w,d,h),((.06,.18),(.12,.35),(.15,.5)))
    return [solid('base',[-w/2,w/2,-d/2,0,0,h*.12],'metal',kind='ellipse',bevel=.003),
            solid('stem',[-w*.16,w*.16,-d*.4,-d*.2,h*.1,h*.94],'metal',kind='ellipse',bevel=.006),
            solid('spout',[-w*.16,w*.16,-d*.3,d/2,h*.82,h],'metal',bevel=.008),
            solid('lever',[-w*.45,-w*.1,-d*.3,-d*.2,h*.3,h*.55],'metal',bevel=.004)]


def air_conditioner_parts(w,d,h):
    check_dimensions((w,d,h),((.6,1.2),(.15,.4),(.2,.5)))
    return [solid('case',[-w/2,w/2,-d/2,d*.46,0,h],'stone',bevel=.025),
            solid('front',[-w*.48,w*.48,d*.46,d/2,h*.18,h*.94],'stone',bevel=.016),
            solid('outlet',[-w*.43,w*.43,d*.46,d/2,h*.03,h*.15],'black',bevel=.003)]
