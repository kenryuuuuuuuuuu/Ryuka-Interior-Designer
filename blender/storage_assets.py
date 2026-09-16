"""Family cloak modules. Local +z is front; heights are metres above the base.

Preview contents belong to their module, so moving/deleting it never leaves orphan clothes.
These are estimated joinery/appearance studies, not load-rated construction drawings.
"""
import math

SHAPES = ('closetSingle', 'closetDouble', 'closetShelves', 'closetDrawers', 'closetMirror', 'storageBox')


def settings(shape, w, d, h, options=None):
    limits = {
        'closetSingle': ((.6, 1.5), (.5, .7), (1.8, 2.35)),
        'closetDouble': ((.6, 1.5), (.5, .7), (1.8, 2.35)),
        'closetShelves': ((.4, 1.3), (.25, .6), (1.5, 2.35)),
        'closetDrawers': ((.4, 1.3), (.25, .6), (.6, 1.1)),
        'closetMirror': ((.25, .6), (.02, .06), (1, 1.9)),
        'storageBox': ((.2, .5), (.2, .5), (.15, .4)),
    }
    if shape not in limits:
        raise ValueError('Unknown storage shape: '+shape)
    for value, (lo, hi) in zip((w, d, h), limits[shape]):
        if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError('収納家具の寸法が対応範囲外です: '+shape)
    options = {} if options is None else options
    if not isinstance(options, dict) or set(options)-{'railHeights', 'shelfHeights', 'contents'}:
        raise ValueError('収納設定の項目が不正です')
    rails = [round(h-.35, 3)] if shape == 'closetSingle' else [round(h*.45, 3), round(h-.25, 3)] if shape == 'closetDouble' else []
    count=min(6,math.floor((h-.15)/.28)+1)
    shelves = [round(.10+j*(h-.15)/(count-1), 3) for j in range(count)] if shape == 'closetShelves' else []
    rails = options.get('railHeights', rails)
    shelves = options.get('shelfHeights', shelves)
    contents = options.get('contents', True)
    if type(contents) is not bool:
        raise ValueError('収納物表示は真偽値で指定してください')
    expected = 1 if shape == 'closetSingle' else 2 if shape == 'closetDouble' else 0
    for values, low, high, gap in ((rails, .45, h-.12, .65), (shelves, .04, h-.025, .28)):
        if not isinstance(values, list) or any(type(v) not in (int, float) or not math.isfinite(v) or not low <= v <= high for v in values):
            raise ValueError('パイプ・棚板の高さが範囲外です')
        if any(b-a < gap-1e-6 for a,b in zip(values, values[1:])):
            raise ValueError('高さは低い順に、パイプ65cm・棚板28cm以上の間隔で指定してください')
    if len(rails) != expected or (shape == 'closetShelves' and not 2 <= len(shelves) <= 8) or (shape != 'closetShelves' and shelves):
        raise ValueError('収納種類に合わないパイプ・棚板の数です')
    return dict(railHeights=rails, shelfHeights=shelves, contents=contents)


def storage_parts(shape, w, d, h, options=None):
    cfg = settings(shape, w, d, h, options)
    parts = []
    def box(name, x0,x1,z0,z1,y0,y1, material='cabinet', kind='box'):
        parts.append(dict(name=name, bounds=[x0,x1,z0,z1,y0,y1], material=material, kind=kind,
                          bevel=min(.003,(x1-x0)/4,(z1-z0)/4,(y1-y0)/4)))
    def container(prefix, x, z, bottom, bw, bd, bh):
        box(prefix+'-body',x-bw/2,x+bw/2,z-bd/2,z+bd/2,bottom,bottom+bh-.012,'fabric')
        box(prefix+'-lid',x-bw/2,x+bw/2,z-bd/2,z+bd/2,bottom+bh-.012,bottom+bh,'cabinet')
        box(prefix+'-label',x-bw*.18,x+bw*.18,z+bd/2,z+bd/2+.001,bottom+bh*.5,bottom+bh*.7,'metal')
    if shape == 'storageBox':
        container('box',0,-.001,0,w,d-.002,h)
        return parts
    if shape == 'closetMirror':
        box('back',-w/2,w/2,-d/2,d/2-.008,0,h,'wood')
        box('mirror',-w/2+.016,w/2-.016,d/2-.008,d/2,.016,h-.016,'mirror')
        return parts
    t=.024
    for name,x0,x1 in [('left',-w/2,-w/2+t),('right',w/2-t,w/2)]:
        box(name,x0,x1,-d/2,d/2,0,h)
    if shape not in ('closetSingle','closetDouble'):
        box('top',-w/2+t,w/2-t,-d/2,d/2,h-t,h,'wood')
    box('back',-w/2+t,w/2-t,-d/2,-d/2+.012,0,h-t)
    if shape in ('closetSingle','closetDouble'):
        box('upper-shelf',-w/2+t,w/2-t,-d/2,d/2,h-.1,h-.076,'wood')
        for j,y in enumerate(cfg['railHeights']):
            box(f'pipe-{j}',-w/2+t,w/2-t,-.014,.014,y-.014,y+.014,'metal','cylinderX')
            if cfg['contents']:
                length = min(1.3 if shape=='closetSingle' else .72, y-.12)
                for k in range(5):
                    x=-w*.32+k*w*.16
                    box(f'hanger-{j}-{k}',x-.006,x+.006,-d*.38,d*.38,y-.06,y-.052,'metal')
                    box(f'garment-{j}-{k}',x-.018,x+.018,-d*.28,d*.28,y-.06-length,y-.09,'fabric')
                    box(f'shoulder-{j}-{k}',x-.018,x+.018,-d*.38,d*.38,y-.22,y-.09,'fabric')
    elif shape == 'closetShelves':
        box('divider',-.012,.012,-d/2,d/2,0,h-t)
        for j,y in enumerate(cfg['shelfHeights']):
            box(f'shelf-{j}',-w/2+t,w/2-t,-d/2,d/2,y,y+t,'wood')
            # Four accessible rows, two lidded boxes per row. Upper shelf remains spare.
            if cfg['contents'] and j < min(4,len(cfg['shelfHeights'])-1):
                bw=min(.35,(w-3*t)/2-.025); bd=min(.4,d-.04); bh=min(.25,cfg['shelfHeights'][j+1]-y-t-.015)
                for k,x in enumerate([-w/4,w/4]): container(f'box-{j}-{k}',x,.002,y+t,bw,bd,bh)
    elif shape == 'closetDrawers':
        box('plinth',-w/2+t,w/2-t,-d/2+.025,d/2-.025,0,.06,'wood')
        for j in range(3):
            bottom=.07+j*(h-.10)/3; top=.07+(j+1)*(h-.10)/3-.008
            box(f'drawer-{j}',-w/2+t+.003,w/2-t-.003,-d/2+.02,d/2-.008,bottom,top)
            box(f'pull-{j}',-w*.18,w*.18,d/2-.008,d/2,top-.024,top-.014,'metal')
    return parts
