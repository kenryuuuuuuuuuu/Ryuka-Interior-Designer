"""Entry/mudroom joinery modules. Local +z is front (the wall is behind, at -z).

Two fittings:
- wallHookRail: the "shaker peg rail" style wall-mounted hook board the owner
  referenced (a horizontal board with a row of evenly spaced hooks, for
  bags/coats -- distinct from closetSingle/closetDouble's hanging PIPE for
  coats on hangers).
- wallPlankShelf: a general-purpose wall-mounted floating shelf (a photo of
  wooden planks on wall brackets/rails, no sides/back/base -- distinct from
  the boxed closetShelves unit used elsewhere for a general purpose movable
  shelf). Started as a shoe shelf design (SC/room-1f-09's 靴棚); renamed
  generic (2026-09-18) once the owner also wanted it for a shallow pantry
  shelf -- same shape, just a shallower depth.

Estimated joinery/appearance study, not a load-rated fixing drawing: board
thickness, hook/plank spacing and fixing method are all assumptions to
confirm with the builder. Outer dimensions come from data/furniture.json.
"""
import math

SHAPES = ('wallHookRail', 'wallPlankShelf')

LIMITS = {
    # 壁付けフックレール（シェーカーレール/なげしフック）。widthはレールの長さ、
    # depthは板厚+フック突き出し、heightは板の見付け高さ。
    'wallHookRail': ((.3, 1.5), (.05, .15), (.08, .18)),
    # 壁付け板棚（汎用。靴棚・パントリーの浅い棚など用途を問わない）。左右の縦レール
    # (金物)に棚板を渡すだけの構成で、側板・背板・地板を持たない。widthは棚板の長さ、
    # depthは板の奥行、heightは最上段棚板の上面までの高さ。depthの下限は0.05m
    # （パントリーの缶詰・調味料棚のような浅い用途にも対応するため、靴棚前提の
    # 0.22mから訂正(2026-09-18)）。
    'wallPlankShelf': ((.6, 2.0), (.05, .4), (.3, 2.0)),
}

BOARD = .02   # 背板の厚み
PEG_LEN = .07  # フックの腕の突き出し長さ
PEG_W = .022   # フックの腕の太さ（幅・高さ）
TIP_RISE = .045  # フック先端の立ち上がり（掛けた鞄・コートの紐が抜けない返し）
SPACING_TARGET = .17  # フックの目安間隔

RAIL_W = .04       # 板棚：縦レールの見付け幅（x方向）
RAIL_D = .025      # 板棚：縦レールの壁からの厚み（z方向、壁に密着）
PLANK_T = .02      # 板棚：棚板の厚み
PLANK_PITCH = .28  # 板棚：段ピッチ
PLANK_FIRST = .28  # 板棚：最下段棚板の下面高さ


def check(shape, w, d, h):
    if shape not in LIMITS:
        raise ValueError('Unknown entry shape: '+shape)
    for value, (lo, hi) in zip((w, d, h), LIMITS[shape]):
        if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError('エントリー造作の寸法が対応範囲外です: '+shape)


def solid(name, bounds, material='wood', bevel=.006):
    return dict(name=name, bounds=bounds, material=material, kind='box', bevel=bevel)


def peg_count(width):
    # 端から半ピッチ空けて等間隔に並べる。最低3本、最大8本。
    return max(3, min(8, round(width / SPACING_TARGET) + 1))


def hook_rail_parts(w, d, h):
    """背板1枚＋等間隔のフック（腕＋上向きの先端）。boardは壁面(-z側)に密着、
    フックは板の正面(+z側)から突き出す。フックは板の下寄りに取り付け、
    先端は腕の上に立ち上がる（掛けた鞄・コートの持ち手が奥へ滑り抜けない
    返しになる、実物のシェーカーペグ／コートフックと同じ向き）。フック自体は
    板と同じ木質色（wood）で統一し、金物色は使わない（実物は木製ペグ・金属
    フックいずれもあるが、詳細未確定のため単純な木の突起として表現）。

    arm_y0・tip_riseはhの下限(.08)でも上限(.18)でも板からはみ出さないよう、
    hに対して相対的にスケールさせる（固定値だとLIMITSの下限側で先端が
    板の上端を突き抜けてしまうため）。"""
    check('wallHookRail', w, d, h)
    board_d = min(BOARD, d * .4)
    parts = [solid('board', [-w/2, w/2, -d/2, -d/2+board_d, 0, h], 'wood', bevel=.004)]
    n = peg_count(w)
    peg_h = min(PEG_W, h * .5)
    arm_y0 = min(.02, h * .15)  # 下寄りに取り付け（先端が上に立ち上がる分の余白を確保）
    available_top = h - arm_y0 - peg_h
    tip_rise = max(peg_h, min(TIP_RISE, available_top - .008))
    for j in range(n):
        cx = -w/2 + (j + .5) * w / n
        parts.append(solid(f'peg-{j}-arm', [cx-PEG_W/2, cx+PEG_W/2, -d/2+board_d, -d/2+board_d+PEG_LEN,
                                              arm_y0, arm_y0+peg_h], 'wood', bevel=.003))
        parts.append(solid(f'peg-{j}-tip', [cx-PEG_W/2, cx+PEG_W/2, -d/2+board_d+PEG_LEN-PEG_W, -d/2+board_d+PEG_LEN,
                                              arm_y0+peg_h, arm_y0+peg_h+tip_rise], 'wood', bevel=.003))
    return parts


def plank_positions(h):
    """最下段PLANK_FIRSTから等ピッチで、板厚PLANK_Tがhに収まる限り積む（最大6段）。
    1段も収まらない極端な低いhでも、最低1段はhの直下に配置する。"""
    ys = []
    y0 = PLANK_FIRST
    while y0 + PLANK_T <= h + 1e-9 and len(ys) < 6:
        ys.append(y0)
        y0 += PLANK_PITCH
    if not ys:
        ys = [max(0., h - PLANK_T)]
    return ys


def plank_shelf_parts(w, d, h):
    """側板・背板・地板を持たない壁付け板棚。左右の縦レール(金物、壁に密着)に、
    棚板(木質)を渡しただけの構成にして、参考画像の「木の板が壁から水平に
    出ている」見え方にする（closetShelvesの箱型ユニットとの違い）。"""
    check('wallPlankShelf', w, d, h)
    rail_d = min(RAIL_D, d * .3)
    parts = [
        solid('rail-left', [-w/2, -w/2+RAIL_W, -d/2, -d/2+rail_d, 0, h], 'metal', bevel=.003),
        solid('rail-right', [w/2-RAIL_W, w/2, -d/2, -d/2+rail_d, 0, h], 'metal', bevel=.003),
    ]
    for j, y0 in enumerate(plank_positions(h)):
        parts.append(solid(f'plank-{j}', [-w/2, w/2, -d/2, d/2, y0, y0+PLANK_T], 'wood', bevel=.004))
    return parts


FACTORIES = {
    'wallHookRail': hook_rail_parts,
    'wallPlankShelf': plank_shelf_parts,
}


def entry_parts(shape, w, d, h):
    if shape not in FACTORIES:
        raise ValueError('Unknown entry shape: '+shape)
    return FACTORIES[shape](w, d, h)
