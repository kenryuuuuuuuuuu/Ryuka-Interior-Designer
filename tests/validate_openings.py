"""Dependency-free checks for data/door-catalog.json, data/window-catalog.json,
data/openings.json, data/interior-doors.json.

house.json 側の footprints、および rooms から自動導出された内壁
（generated/interior-walls.json、node scripts/build-web-data.mjs で生成）と
整合しているかも確認する（壁を「越えて」宙に浮いた窓・ドアがないことの機械的な保証）。
実行前に必ず node scripts/build-web-data.mjs を実行しておくこと。詳細は docs/ARCHITECTURE.md を参照。
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOOR_CATALOG = ROOT / "data" / "door-catalog.json"
WINDOW_CATALOG = ROOT / "data" / "window-catalog.json"
OPENINGS = ROOT / "data" / "openings.json"
INTERIOR_DOORS = ROOT / "data" / "interior-doors.json"
HOUSE = ROOT / "data" / "house.json"
INTERIOR_WALLS = ROOT / "generated" / "interior-walls.json"

VALID_STATUS = {"verified", "derived", "estimated"}
VALID_FACE = {"N", "S", "E", "W"}
VALID_ORIENTATION = {"H", "V", "D"}  # D=斜め壁（x0/z0/x1/z1で始点・終点を指定）
TOL = 0.01  # m。浮動小数の誤差許容
EW_TOL = 0.2  # m。E/W面のfootprint照合はゾーン区分の近似値との比較なのでゆるめに取る


def effective(item, field, override_field, profile):
    return item.get(override_field, profile[field])


def seg_at_x(x, footprints, level):
    """interior-white-model.html の segAtX() と同じロジック（Nface/Sfaceの位置解決に使う）。"""
    candidates = [fp for fp in footprints if fp["level"] == level]
    for fp in candidates:
        if fp["x0"] - 1e-6 <= x <= fp["x1"] + 1e-6:
            return fp
    return candidates[0] if candidates else None


def check_opening_within_footprint(o, effective_width, footprints):
    """openings.json の1件が実在する壁の上に収まっているかを確認する。
    offsetは面に沿った開始端（西端/北端）で、中心ではない（interior-white-model.htmlの
    描画ロジック x0=o.lx, x1=o.lx+o.w と同じ規約）。
    footprintsは求積図のゾーン区分であり、隣接ゾーンの共有辺（同じz0/z1）は実在する
    1本の壁のことが多いため、単一footprintへの完全包含ではなく、開口の両端が同じ
    壁座標(z0/z1)を持つfootprint上にあるかで判定する（segAtXと同じ考え方）。"""
    lo, hi = o["offset"], o["offset"] + effective_width
    if o["face"] in ("N", "S"):
        seg_lo = seg_at_x(lo, footprints, o["level"])
        seg_hi = seg_at_x(hi, footprints, o["level"])
        if not seg_lo or not seg_hi:
            return False
        edge = "z0" if o["face"] == "N" else "z1"
        return abs(seg_lo[edge] - seg_hi[edge]) < TOL
    # E/W: 壁のx座標はwallX（未指定なら建物端の0/19.11）で固定。z範囲は該当階の
    # footprint全体のz最小〜最大に収まっているかだけを確認する（既存の描画ロジック
    # 自体がE/W面をfootprintから動的に解決していないため、それに合わせた粒度）。
    # footprintは求積図のゾーン区分の近似値で実測の壁面ではないため、E/Wはゆるめの
    # 許容差(EW_TOL)で「大きく外れていないか」だけを見る。
    same_level = [fp for fp in footprints if fp["level"] == o["level"]]
    if not same_level:
        return False
    z0 = min(fp["z0"] for fp in same_level)
    z1 = max(fp["z1"] for fp in same_level)
    return z0 - EW_TOL <= lo and hi <= z1 + EW_TOL


def check_door_within_wall(d, effective_width, walls):
    """interior-doors.json の1件が、実在する壁エンティティの範囲内に収まっているかを確認する。"""
    lo, hi = d["center"] - effective_width / 2, d["center"] + effective_width / 2
    for w in walls:
        if w["level"] != d["floor"]:
            continue
        if d["orientation"] == "H" and w["orientation"] == "H" and abs(w["z0"] - d["wallAt"]) < TOL:
            if w["x0"] - TOL <= lo and hi <= w["x1"] + TOL:
                return True
        if d["orientation"] == "V" and w["orientation"] == "V" and abs(w["x0"] - d["wallAt"]) < TOL:
            if w["z0"] - TOL <= lo and hi <= w["z1"] + TOL:
                return True
    return False


def main():
    door_catalog = json.loads(DOOR_CATALOG.read_text(encoding="utf-8"))
    window_catalog = json.loads(WINDOW_CATALOG.read_text(encoding="utf-8"))
    openings = json.loads(OPENINGS.read_text(encoding="utf-8"))
    interior_doors = json.loads(INTERIOR_DOORS.read_text(encoding="utf-8"))
    house = json.loads(HOUSE.read_text(encoding="utf-8"))

    assert door_catalog["schemaVersion"] == "1.0.0" and window_catalog["schemaVersion"] == "1.0.0"
    assert door_catalog["units"] == "m" and window_catalog["units"] == "m"
    types = door_catalog["types"] + window_catalog["types"]
    assert len(types) > 0, "door-catalog.json/window-catalog.json: types が空"
    type_ids = [t["type"] for t in types]
    assert len(type_ids) == len(set(type_ids)), "door-catalog.json/window-catalog.json: type が重複している"
    for t in door_catalog["types"]:
        assert t["category"] == "door", f"{t['type']}: door-catalog.jsonのtypeはcategory:doorであること"
    for t in window_catalog["types"]:
        assert t["category"] == "window", f"{t['type']}: window-catalog.jsonのtypeはcategory:windowであること"
    for t in types:
        for field in ("type", "label", "category", "operation", "width", "height", "sill"):
            assert field in t, f"{t.get('type', '?')} に{field}がない"
        assert t["category"] in ("door", "window"), f"{t['type']}: 不正なcategory"
        assert t["operation"] in ("swing", "double-swing", "fold", "double-fold", "slide", "fixed", "openable", "open", "open-arch"), f"{t['type']}: 不正なoperation"
        assert t["width"] > 0 and t["height"] > 0 and t["sill"] >= 0, f"{t['type']}: 寸法が不正"
        if t["operation"] == "open-arch":
            assert t.get("archRise", 0) > 0, f"{t['type']}: open-archはarchRiseが正の数であること"
            assert t["archRise"] < t["height"], f"{t['type']}: archRiseはheight未満であること（springline=height-archRiseが正になる必要がある）"
    by_type = {t["type"]: t for t in types}

    footprints = house["footprints"]
    # 内壁は data/house.json の rooms から自動導出したもの（node scripts/build-web-data.mjs で
    # generated/interior-walls.json に書き出される）。このスクリプトの実行前に必ず再生成しておくこと。
    walls = json.loads(INTERIOR_WALLS.read_text(encoding="utf-8"))["walls"]

    assert openings["schemaVersion"] == "1.0.0"
    o_items = openings["items"]
    o_ids = [o["id"] for o in o_items]
    assert len(o_ids) == len(set(o_ids)), "openings.json: id が重複している"

    for o in o_items:
        assert o["type"] in by_type, f"{o['id']}: 未知のtype「{o['type']}」（door-catalog.json/window-catalog.jsonに存在しない）"
        profile = by_type[o["type"]]
        assert o["face"] in VALID_FACE, f"{o['id']}: 不正なface"
        assert o["status"] in VALID_STATUS, f"{o['id']}: 不正なstatus"
        for override in ("widthOverride", "heightOverride"):
            if override in o:
                assert o[override] > 0, f"{o['id']}: {override}は正の数であること"
        if "sillOverride" in o:
            assert o["sillOverride"] >= 0, f"{o['id']}: sillOverrideは0以上であること"
        if profile["category"] == "door" and profile["operation"] not in ("open", "open-arch"):
            has_swing = "hingeSide" in o and "swingDir" in o
            has_double_swing = profile["operation"] in ("double-swing", "double-fold") and "swingDir" in o
            has_slide = "slideDir" in o
            assert has_swing or has_double_swing or has_slide, f"{o['id']}: ドアはhingeSide+swingDir、swingDir(両開き)、またはslideDirのいずれかが必要"
        w = effective(o, "width", "widthOverride", profile)
        assert check_opening_within_footprint(o, w, footprints), f"{o['id']}: 対応するfootprintの面からはみ出している"

    assert interior_doors["schemaVersion"] == "1.0.0"
    d_items = interior_doors["items"]
    d_ids = [d["id"] for d in d_items]
    assert len(d_ids) == len(set(d_ids)), "interior-doors.json: id が重複している"

    for d in d_items:
        assert d["type"] in by_type, f"{d['id']}: 未知のtype「{d['type']}」（door-catalog.json/window-catalog.jsonに存在しない）"
        profile = by_type[d["type"]]
        assert profile["category"] == "door", f"{d['id']}: interior-doors.jsonのtypeはcategory:doorであること"
        assert d["orientation"] in VALID_ORIENTATION, f"{d['id']}: 不正なorientation"
        assert d["status"] in VALID_STATUS, f"{d['id']}: 不正なstatus"
        for override in ("widthOverride", "heightOverride"):
            if override in d:
                assert d[override] > 0, f"{d['id']}: {override}は正の数であること"
        if d["orientation"] == "D":
            # 斜め壁：wallAt/centerではなくx0/z0/x1/z1で始点・終点を指定する。壁のない
            # 開口(open/open-arch)のみ想定しているため、開き勝手は不要でWALLSとの
            # 突合せも行わない（rooms→wallsの自動変換は軸に沿った壁しか扱えないため）
            for key in ("x0", "z0", "x1", "z1"):
                assert key in d, f"{d['id']}: orientation:Dは{key}が必要"
            length = ((d["x1"] - d["x0"]) ** 2 + (d["z1"] - d["z0"]) ** 2) ** 0.5
            assert length > 0.1, f"{d['id']}: 始点・終点の距離が短すぎる"
        else:
            if profile["operation"] not in ("open", "open-arch"):
                has_swing = "hingeSide" in d and "swingDir" in d
                has_double_swing = profile["operation"] in ("double-swing", "double-fold") and "swingDir" in d
                has_slide = "slideDir" in d
                assert has_swing or has_double_swing or has_slide, f"{d['id']}: hingeSide+swingDir、swingDir(両開き)、またはslideDirのいずれかが必要"
            w = effective(d, "width", "widthOverride", profile)
            assert check_door_within_wall(d, w, walls), f"{d['id']}: 対応する壁エンティティの範囲からはみ出している"

    print(f"openings/interior-doors: {len(types)} types in catalog, {len(o_items)} exterior + {len(d_items)} interior door/window instances - checks passed")


if __name__ == "__main__":
    main()
