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
        if binding.get('assetId') != ASSET_ID or binding.get('sizing') != 'parametric':
            raise ValueError(f'Unsupported asset or sizing policy: {target}')
        if binding.get('status') != 'estimated' or not binding.get('note'):
            raise ValueError(f'Asset needs estimated status and provenance note: {target}')
        item = by_id[target]
        profile = by_type[item['type']]
        if profile['shape'] != 'sofa': raise ValueError(f'Sofa asset assigned to another shape: {target}')
        dimensions = [item.get(k+'Override', profile[k]) for k in DIMENSIONS]
        sofa_parts(*dimensions)  # fail before rendering, never silently stretch a product
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
