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
                    'chair-timber-v1': ('timberChair', chair_parts),
                    'toilet-v1': ('toilet', toilet_parts),
                    'toilet-tankless-v1': ('toiletTankless', tankless_parts),
                    'vanity-v1': ('vanity', vanity_parts),
                    'washer-v1': ('boxAppliance', washer_parts),
                    'bathtub-v1': ('bathtub', bathtub_parts),
                    'bed-v1': ('bed', bed_parts), 'desk-v1': ('table', desk_parts)}
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
            'faucet-v1':faucet_parts,'air-conditioner-v1':air_conditioner_parts,
            'toilet-v1':toilet_parts,'toilet-tankless-v1':tankless_parts,'vanity-v1':vanity_parts,
            'washer-v1':washer_parts,'bathtub-v1':bathtub_parts,'bed-v1':bed_parts,'desk-v1':desk_parts}[asset_id](w,d,h)


# W07-G3: water-room fixtures -- simple parametric parts that read as their
# TYPE (a tank+bowl+seat toilet, a basin+mirror vanity, a front-load washer,
# a hollow tub with a rim), not a product reproduction. Ceramic/metal stay
# fixed materials; a room variant must not turn them into wood. Basins and
# the tub are built as rims + a lowered inner bottom -- never a solid box
# filling the vessel. Outer dimensions from furniture-catalog.json/overrides.

def toilet_parts(w, d, h):
    check_dimensions((w, d, h), ((.34, .55), (.6, .85), (.7, 1.15)))
    seat = min(.42, h * .43)
    return [
        solid('cistern', [-w / 2, w / 2, -d / 2, -d / 2 + .21, seat + .02, min(h, seat + .40)], 'stone', bevel=.012),
        solid('pedestal', [-w * .26, w * .26, -d / 2 + .16, d * .16, 0, seat - .02], 'stone', kind='ellipse', bevel=.02),
        solid('bowl', [-w * .44, w * .44, -d * .08, d / 2 - .01, seat - .12, seat], 'stone', kind='ellipse', bevel=.03),
        solid('seat', [-w * .47, w * .47, -d * .12, d / 2, seat, seat + .03], 'black', kind='ellipse', bevel=.01),
        solid('lid', [-w * .47, w * .47, -d / 2 + .04, -d / 2 + .07, seat + .02, min(h, seat + .40)], 'black', bevel=.008),
    ]


def vanity_parts(w, d, h):
    check_dimensions((w, d, h), ((.5, 2.0), (.4, .65), (.7, 2.1)))
    counter = min(.86, h * .5)
    bx0, bx1, bz0, bz1 = -min(w * .30,.39), min(w * .30,.39), -d * .18, d * .30
    inner = counter - .13
    # W07-G3 review R3: the cabinet must leave a real cavity under the basin
    # -- a full-height solid box buried the bowl and its walls, so the
    # counter cut-out only ever revealed the box's top. Build the carcass as
    # a low base plus panels flanking the basin footprint; the basin空間
    # (bx0..bx1 x bz0..bz1, from just under the bowl up to the counter) stays
    # open (spec section 3: "水槽内部を裏の固体箱で埋めない").
    cab_top = counter - .03
    parts = [
        solid('cabinet-base', [-w / 2, w / 2, -d / 2 + .02, d / 2, .04, inner - .02], 'cabinet', bevel=.004),
        solid('plinth', [-w * .46, w * .46, -d * .42, d * .42, 0, .04], 'frame', bevel=.002),
    ]
    for name, x0, x1, z0, z1 in [('left', -w / 2, bx0, -d / 2 + .02, d / 2), ('right', bx1, w / 2, -d / 2 + .02, d / 2),
                                 ('rear', bx0, bx1, -d / 2 + .02, bz0), ('front', bx0, bx1, bz1, d / 2)]:
        parts.append(solid('cabinet-' + name, [x0, x1, z0, z1, inner - .02, cab_top], 'cabinet', bevel=.004))
    # counter as a frame around the basin cut-out (no slab across the basin)
    for name, x0, x1, z0, z1 in [('left', -w / 2, bx0, -d / 2, d / 2), ('right', bx1, w / 2, -d / 2, d / 2),
                                 ('rear', bx0, bx1, -d / 2, bz0), ('front', bx0, bx1, bz1, d / 2)]:
        parts.append(solid('counter-' + name, [x0, x1, z0, z1, counter - .03, counter], 'stone', bevel=.003))
    parts.append(solid('basin-bottom', [bx0, bx1, bz0, bz1, inner, inner + .01], 'stone', kind='ellipse', bevel=.006))
    for name, x0, x1, z0, z1 in [('left', bx0, bx0 + .012, bz0, bz1), ('right', bx1 - .012, bx1, bz0, bz1),
                                 ('rear', bx0, bx1, bz0, bz0 + .012), ('front', bx0, bx1, bz1 - .012, bz1)]:
        parts.append(solid('basin-' + name, [x0, x1, z0, z1, inner, counter - .02], 'stone', bevel=.004))
    parts.append(solid('faucet', [-w * .07, w * .07, -d * .06, d * .06, counter, counter + .18], 'metal', kind='ellipse', bevel=.006))
    parts.append(solid('mirror', [-w * .46, w * .46, -d / 2 + .01, -d / 2 + .04, counter + .18, h], 'black', bevel=.004))
    return parts


def washer_parts(w, d, h):
    check_dimensions((w, d, h), ((.45, .75), (.5, .85), (.8, 1.15)))
    front = d / 2
    parts = [
        solid('body', [-w / 2, w / 2, -d / 2, front - .015, .02, h], 'metal', bevel=.012),
        solid('feet', [-w * .44, w * .44, -d * .42, d * .42, 0, .02], 'frame', bevel=.002),
        solid('panel', [-w * .46, w * .46, front - .015, front, h - .12, h - .02], 'black', bevel=.004),
    ]
    r = min(w * .32, (h - .30) / 2)
    cy = .12 + r + .06
    # W07-G3 review R3: the door opening is a circle in the VERTICAL plane
    # facing front (kind='disc'), not a plan-plane ellipse extruded upward.
    # The glass sits proud of the rim so the round porthole reads from the
    # front and the rim shows as a frame ring around it.
    parts.append(solid('door-rim', [-r, r, front - .02, front + .015, cy - r, cy + r], 'frame', kind='disc', bevel=.01))
    parts.append(solid('door-glass', [-(r - .035), r - .035, front + .010, front + .035, cy - (r - .035), cy + (r - .035)],
                       'black', kind='disc', bevel=.006))
    return parts


def bathtub_parts(w, d, h):
    check_dimensions((w, d, h), ((1.2, 2.0), (.65, 1.0), (.45, .75)))
    wall_t = .07
    inner = min(.14, h * .28)
    parts = [
        solid('inner-bottom', [-w / 2 + wall_t, w / 2 - wall_t, -d / 2 + wall_t, d / 2 - wall_t, inner, inner + .012], 'stone', bevel=.03),
        solid('skirt', [-w / 2, w / 2, d / 2 - .04, d / 2, 0, h - .02], 'stone', bevel=.006),
        solid('plinth', [-w / 2, w / 2, -d / 2, d / 2, 0, .05], 'frame', bevel=.003),
    ]
    for name, x0, x1, z0, z1 in [('left', -w / 2, -w / 2 + wall_t, -d / 2, d / 2),
                                 ('right', w / 2 - wall_t, w / 2, -d / 2, d / 2),
                                 ('head', -w / 2, w / 2, -d / 2, -d / 2 + wall_t)]:
        parts.append(solid('rim-' + name, [x0, x1, z0, z1, .05, h], 'stone', bevel=.02))
    parts.append(solid('rim-front', [-w / 2, w / 2, d / 2 - wall_t - .02, d / 2 - .04, h - .05, h], 'stone', bevel=.02))
    parts.append(solid('tap', [w / 2 - wall_t - .10, w / 2 - wall_t - .02, -d * .05, d * .05, h, h + .16], 'metal', kind='ellipse', bevel=.006))
    return parts


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


def tankless_parts(w,d,h):
    check_dimensions((w,d,h),((.34,.65),(.5,.85),(.4,.8)))
    seat=h-.04
    return [solid('pedestal',[-w*.32,w*.32,-d*.42,d*.3,0,seat-.1],'stone',kind='ellipse'),
            solid('bowl',[-w*.48,w*.48,-d/2,d/2,seat-.1,seat],'stone',kind='ellipse'),
            solid('lid',[-w/2,w/2,-d/2,d/2,seat,h],'stone',kind='ellipse')]


def bed_parts(w,d,h):
    """Source height is mattress top; all detail stays inside that envelope."""
    check_dimensions((w,d,h),((.8,2.2),(1.7,2.3),(.3,.8)))
    parts=[solid('frame',[-w/2,w/2,-d/2,d/2,h*.2,h*.58],'wood',bevel=.015),
           solid('mattress',[-w*.49,w*.49,-d*.49,d*.49,h*.58,h],'fabric',bevel=.035)]
    for i,x in enumerate((-w*.4,w*.4)):
        for j,z in enumerate((-d*.4,d*.4)):
            parts.append(solid(f'foot-{i}-{j}',[x-.025,x+.025,z-.025,z+.025,0,h*.2],'frame'))
    return parts


def desk_parts(w,d,h):
    check_dimensions((w,d,h),((.7,2.0),(.4,1.0),(.55,.9)))
    parts=[solid('top',[-w/2,w/2,-d/2,d/2,h-.04,h],'wood',bevel=.012)]
    for i,x in enumerate((-w/2+.05,w/2-.05)):
        for j,z in enumerate((-d/2+.05,d/2-.05)):
            parts.append(solid(f'leg-{i}-{j}',[x-.025,x+.025,z-.025,z+.025,0,h-.04],'frame'))
    return parts
