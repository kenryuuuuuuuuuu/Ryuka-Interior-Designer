"""Laundry-room joinery modules. Local +z is front (the wall is behind, at -z).

The 脱衣室 (room-1f-16) is a 1.82 x 2.73 m interior room with no window and
three openings that all swing/slide AWAY from it, so every wall face is usable.
These three modules are the built-in fittings that a Japanese laundry room of
this size is normally finished with (作業カウンター・壁付けオープン棚・室内物干し),
mirrored one-for-one by FURNITURE_SHAPES in interior-white-model.html so the
browser study and the Blender/UE model agree.

Estimated joinery/appearance studies, not load-rated construction drawings:
board thickness, pipe diameter and fixing method are all assumptions to confirm
with the builder. Outer dimensions come from data/furniture.json as usual.
"""
import math

SHAPES = ('laundryCounter', 'laundryShelf', 'laundryRack', 'laundryBasket')

LIMITS = {
    # 作業カウンター: たたむ・アイロンの作業面。実例は幅1.59-1.80m/奥行0.45-0.55m/高さ0.85-0.90m。
    'laundryCounter': ((.9, 2.4), (.4, .65), (.8, .95)),
    # 壁付けオープン棚: カウンター・洗濯機の上。実例は幅0.91m/奥行0.30m/4段。
    'laundryShelf': ((.5, 2.2), (.2, .45), (.3, .9)),
    # 室内物干し: 壁付けコの字バー。実例は壁からの出350-455mm。
    'laundryRack': ((.6, 2.0), (.25, .5), (.03, .12)),
    # ランドリーバスケット: 蓋なしの開放型（洗う前の衣類を放り込む用途で、
    # storage-box=蓋付き収納箱の流用は「段ボール箱」に見えてしまうため専用形状にした）。
    'laundryBasket': ((.3, .55), (.3, .55), (.25, .45)),
}

BOARD = .025   # 側板・棚板の板厚
TOP = .04      # カウンター天板の厚み
PIPE = .03     # 物干しパイプの見付け
BASKET_WALL = .015  # バスケットの側面厚み
BASKET_RIM = .02    # バスケット上端の縁の高さ（幅は本体と同一、外形寸法からはみ出さない）


def check(shape, w, d, h):
    if shape not in LIMITS:
        raise ValueError('Unknown laundry shape: '+shape)
    for value, (lo, hi) in zip((w, d, h), LIMITS[shape]):
        if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError('ランドリー造作の寸法が対応範囲外です: '+shape)


def solid(name, bounds, material='wood', bevel=.006):
    return dict(name=name, bounds=bounds, material=material, kind='box', bevel=bevel)


def counter_parts(w, d, h):
    """壁付けの造作カウンター。天板＋左右の側板＋奥の幕板で、下部はオープン。

    下をオープンにするのは、ランドリーバスケットやワゴンを置くための実例どおりの
    使い方（3畳の実例2件とも、カウンター下はかご3個かワゴン）。"""
    check('laundryCounter', w, d, h)
    top = h - TOP
    return [
        solid('top', [-w/2, w/2, -d/2, d/2, top, h], 'wood', bevel=.004),
        solid('side-left', [-w/2, -w/2+BOARD, -d/2, d/2, 0, top], 'cabinet'),
        solid('side-right', [w/2-BOARD, w/2, -d/2, d/2, 0, top], 'cabinet'),
        # 奥の幕板は天板の下だけ（背面いっぱいの板にすると下部の使い勝手を殺す）
        solid('rail-back', [-w/2+BOARD, w/2-BOARD, -d/2, -d/2+BOARD, top-.09, top], 'cabinet'),
    ]


def shelf_parts(w, d, h):
    """壁付けのオープン棚。背板を持たず、左右の側板＋棚板3枚（下・中・天）。

    背板を省くのは壁付け造作の一般的な納まりで、奥行0.3m級の棚では
    壁面がそのまま見えるほうが軽く見える。"""
    check('laundryShelf', w, d, h)
    parts = [
        solid('side-left', [-w/2, -w/2+BOARD, -d/2, d/2, 0, h], 'cabinet'),
        solid('side-right', [w/2-BOARD, w/2, -d/2, d/2, 0, h], 'cabinet'),
    ]
    inner = (-w/2+BOARD, w/2-BOARD)
    for name, y0 in (('shelf-low', 0.), ('shelf-mid', (h-BOARD)/2), ('shelf-top', h-BOARD)):
        parts.append(solid(name, [inner[0], inner[1], -d/2, d/2, y0, y0+BOARD], 'wood', bevel=.004))
    return parts


def rack_parts(w, d, h):
    """室内物干しのコの字バー。壁から2本の腕が出て、先端を1本のバーで繋ぐ。

    乾燥機で乾かせない衣類用の補助で、実例でも『物干しは2本も要らない』という
    実感が語られているため1本構成。高さ(h)はパイプの見付けそのもの。"""
    check('laundryRack', w, d, h)
    pipe = min(PIPE, h)
    return [
        solid('arm-left', [-w/2, -w/2+pipe, -d/2, d/2, 0, h], 'metal', bevel=.004),
        solid('arm-right', [w/2-pipe, w/2, -d/2, d/2, 0, h], 'metal', bevel=.004),
        solid('bar', [-w/2, w/2, d/2-pipe, d/2, 0, h], 'metal', bevel=.004),
    ]


def basket_parts(w, d, h):
    """蓋のない開放型ランドリーバスケット。底板＋4面の薄い側壁（上端2cmだけ色を変えて
    縁のトリムを表す）。壁は常に薄板のままで、天面を塞ぐ板は一切置かない＝開口部は
    最後まで開いたまま（W07-G3レビューで踏襲：視認性確保のための補助形状でも本体の
    開口を塞いではいけない）。

    素材はfabric（クロークの布地色と同じ、キャンバス地に近いトーン）を本体に、
    wood（クロークの木質色）を縁のトリムに使い、段ボール箱ではなく布製の
    洗濯かごに見えるようにする（蓋・ラベルは持たない＝storageBoxとの差）。"""
    check('laundryBasket', w, d, h)
    t = BASKET_WALL
    rim0 = h - BASKET_RIM
    parts = [solid('bottom', [-w/2, w/2, -d/2, d/2, 0, t], 'fabric', bevel=.004)]
    walls = [('front', [-w/2, w/2, d/2-t, d/2]), ('back', [-w/2, w/2, -d/2, -d/2+t]),
             ('left', [-w/2, -w/2+t, -d/2, d/2]), ('right', [w/2-t, w/2, -d/2, d/2])]
    for name, (x0, x1, z0, z1) in walls:
        parts.append(solid('wall-'+name, [x0, x1, z0, z1, 0, rim0], 'fabric', bevel=.004))
        parts.append(solid('rim-'+name, [x0, x1, z0, z1, rim0, h], 'wood', bevel=.004))
    return parts


FACTORIES = {
    'laundryCounter': counter_parts,
    'laundryShelf': shelf_parts,
    'laundryRack': rack_parts,
    'laundryBasket': basket_parts,
}


def laundry_parts(shape, w, d, h):
    if shape not in FACTORIES:
        raise ValueError('Unknown laundry shape: '+shape)
    return FACTORIES[shape](w, d, h)
