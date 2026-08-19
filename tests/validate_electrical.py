"""Dependency-free checks for data/electrical-catalog.json and data/electrical.json.

house.json 側の rooms/footprints、および house.json から自動導出された内壁・外壁
（generated/interior-walls.json・generated/exterior-walls.json、
node scripts/build-web-data.mjs で生成）と整合しているかも確認する。
実行前に必ず node scripts/build-web-data.mjs を実行しておくこと。詳細は docs/ARCHITECTURE.md を参照。
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "electrical-catalog.json"
ELECTRICAL = ROOT / "data" / "electrical.json"
ESTIMATE = ROOT / "data" / "electrical-estimate.json"
HOUSE = ROOT / "data" / "house.json"
INTERIOR_WALLS = ROOT / "generated" / "interior-walls.json"
EXTERIOR_WALLS = ROOT / "generated" / "exterior-walls.json"

VALID_STATUS = {"verified", "derived", "estimated"}
VALID_CATEGORY = {"outlet", "switch", "lighting", "data", "equipment"}
VALID_MOUNT = {"wall", "ceiling", "floor", "exterior"}
VALID_HEIGHT_REF = {"floor", "ceiling"}
VALID_ORIENTATION = {"H", "V"}
VALID_SIDE = {1, -1}
VALID_FACE = {"N", "S", "E", "W"}
TOL = 0.01  # m。浮動小数の誤差許容（壁突合せ）
BBOX_TOLERANCE = 0.6  # m。部屋の外形からこの範囲内なら許容（validate_furniture.pyと同じ値）


def room_bbox(polygon):
    xs = [p[0] for p in polygon]
    zs = [p[1] for p in polygon]
    return min(xs), max(xs), min(zs), max(zs)


def effective(item, field, override_field, profile):
    return item.get(override_field, profile[field])


def check_within_wall(item, effective_width, walls):
    """interior-doors.jsonのcheck_door_within_wall()と同じロジック。
    壁付け設備の1件が、実在する壁エンティティの範囲内に収まっているかを確認する。
    wallsは内壁(generated/interior-walls.json)＋外壁(generated/exterior-walls.json)の
    結合リストを渡す（外壁の室内側に付く設備も表現できるようにするため。この関数自体は
    壁の由来を区別しない）。"""
    lo, hi = item["center"] - effective_width / 2, item["center"] + effective_width / 2
    for w in walls:
        if w["level"] != item["level"]:
            continue
        if item["orientation"] == "H" and w["orientation"] == "H" and abs(w["z0"] - item["wallAt"]) < TOL:
            if w["x0"] - TOL <= lo and hi <= w["x1"] + TOL:
                return True
        if item["orientation"] == "V" and w["orientation"] == "V" and abs(w["x0"] - item["wallAt"]) < TOL:
            if w["z0"] - TOL <= lo and hi <= w["z1"] + TOL:
                return True
    return False


def seg_at_x(x, footprints, level):
    """interior-white-model.html の segAtX()・tests/validate_openings.py の同名関数と同じ
    ロジック（N/S面のface+offsetから、対応するfootprintを解決する）。"""
    candidates = [fp for fp in footprints if fp["level"] == level]
    for fp in candidates:
        if fp["x0"] - 1e-6 <= x <= fp["x1"] + 1e-6:
            return fp
    return candidates[0] if candidates else None


def footprint_for_exterior_face(item, footprints):
    """mount:'exterior'の1件について、face+offset(+wallX)からその面が乗るfootprintを解決する。
    blender/build_house.py の footprint_for_opening() と同じ考え方。"""
    level = item["level"]
    candidates = [fp for fp in footprints if fp["level"] == level]
    if not candidates:
        return None
    if item["face"] in ("N", "S"):
        return seg_at_x(item["offset"], footprints, level)
    if "wallX" in item:
        return seg_at_x(item["wallX"], footprints, level)
    if item["face"] == "E":
        return max(candidates, key=lambda f: f["x1"])
    return min(candidates, key=lambda f: f["x0"])  # face == 'W'


def check_exterior_within_wall(item, effective_width, footprints, exterior_walls):
    """mount:'exterior'の1件が、真の外壁セグメント(generated/exterior-walls.json)の上に
    収まっているかを確認する。footprint_for_exterior_face()で対応するfootprintを求め、
    そのfootprintのN/S/E/W辺の座標を「壁のat座標」として、同じorientation・at(許容差TOL)を
    持つexterior_walls上のセグメントに offset〜offset+width の区間が収まっているかを判定する。"""
    fp = footprint_for_exterior_face(item, footprints)
    if not fp:
        return False
    if item["face"] in ("N", "S"):
        orientation, at = "H", (fp["z0"] if item["face"] == "N" else fp["z1"])
    else:
        orientation = "V"
        at = item.get("wallX", fp["x1"] if item["face"] == "E" else fp["x0"])
    lo, hi = item["offset"], item["offset"] + effective_width
    for w in exterior_walls:
        if w["level"] != item["level"] or w["orientation"] != orientation:
            continue
        w_at = w["z0"] if orientation == "H" else w["x0"]
        if abs(w_at - at) > TOL:
            continue
        w_lo, w_hi = (w["x0"], w["x1"]) if orientation == "H" else (w["z0"], w["z1"])
        if w_lo - TOL <= lo and hi <= w_hi + TOL:
            return True
    return False


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    electrical = json.loads(ELECTRICAL.read_text(encoding="utf-8"))
    estimate = json.loads(ESTIMATE.read_text(encoding="utf-8"))
    house = json.loads(HOUSE.read_text(encoding="utf-8"))
    # 内壁・外壁はいずれもdata/house.jsonから自動導出したもの（node scripts/build-web-data.mjsで
    # generated/interior-walls.json・generated/exterior-walls.jsonに書き出される）。
    # このスクリプトの実行前に必ず再生成しておくこと。
    interior_walls = json.loads(INTERIOR_WALLS.read_text(encoding="utf-8"))["walls"]
    exterior_walls = json.loads(EXTERIOR_WALLS.read_text(encoding="utf-8"))["walls"]
    # mount:'wall'は間仕切り壁・外壁の室内側のどちらにも付けられるため、突合せ先は結合リストにする
    walls = interior_walls + exterior_walls
    footprints = house["footprints"]

    assert catalog["schemaVersion"] == "1.0.0"
    assert catalog["units"] == "m"
    types = catalog["types"]
    assert len(types) > 0, "electrical-catalog.json: types が空"

    type_ids = [t["type"] for t in types]
    assert len(type_ids) == len(set(type_ids)), "electrical-catalog.json: type が重複している"
    for t in types:
        for field in ("type", "label", "category", "mount", "heightRef", "shape", "width", "depth", "height", "mountHeight"):
            assert field in t, f"electrical-catalog.json: {t.get('type', '?')} に{field}がない"
        assert t["category"] in VALID_CATEGORY, f"{t['type']}: 不正なcategory"
        assert t["mount"] in VALID_MOUNT, f"{t['type']}: 不正なmount"
        assert t["heightRef"] in VALID_HEIGHT_REF, f"{t['type']}: 不正なheightRef"
        assert t["width"] > 0 and t["depth"] > 0 and t["height"] > 0, f"{t['type']}: 寸法は正の数であること"
        assert t["mountHeight"] >= 0, f"{t['type']}: mountHeightは0以上であること"
    by_type = {t["type"]: t for t in types}

    # 見積書の明細（施主が削除・追加を始めても、見積数量との差分を明細単位で追えるようにする
    # ための正本）。型を複数の明細で重複計上すると差分がずれるため、1型=最大1明細であることを確認する
    assert estimate["schemaVersion"] == "1.0.0"
    lines = estimate["lines"]
    assert len(lines) > 0, "electrical-estimate.json: lines が空"
    line_ids = [l["id"] for l in lines]
    assert len(line_ids) == len(set(line_ids)), "electrical-estimate.json: id が重複している"
    seen_types = {}
    for line in lines:
        for field in ("id", "label", "quantity", "types"):
            assert field in line, f"electrical-estimate.json: {line.get('id', '?')} に{field}がない"
        assert line["quantity"] > 0, f"electrical-estimate.json: {line['id']}のquantityは正の数であること"
        assert len(line["types"]) > 0, f"electrical-estimate.json: {line['id']}のtypesが空"
        for t in line["types"]:
            assert t in by_type, f"electrical-estimate.json: {line['id']}が未知のtype「{t}」を参照している"
            assert t not in seen_types, f"electrical-estimate.json: type「{t}」が複数の明細（{seen_types.get(t)}, {line['id']}）に重複して属している"
            seen_types[t] = line["id"]

    assert electrical["schemaVersion"] == "1.0.0"
    assert electrical["units"] == "m"
    items = electrical["items"]

    rooms_by_id = {r["id"]: r for r in house["rooms"]}
    valid_levels = {fp["level"] for fp in house["footprints"]}

    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)), "electrical.json: id が重複している"

    for item in items:
        assert item["type"] in by_type, f"{item['id']}: 未知のtype「{item['type']}」（electrical-catalog.jsonに存在しない）"
        profile = by_type[item["type"]]
        assert item["status"] in VALID_STATUS, f"{item['id']}: 不正なstatus"
        assert item["level"] in valid_levels, f"{item['id']}: 存在しないlevel {item['level']}"
        for override in ("widthOverride", "depthOverride", "heightOverride"):
            if override in item:
                assert item[override] > 0, f"{item['id']}: {override}は正の数であること"
        if "mountHeightOverride" in item:
            assert item["mountHeightOverride"] >= 0, f"{item['id']}: mountHeightOverrideは0以上であること"

        if profile["mount"] == "wall":
            for field in ("wallAt", "orientation", "center", "side"):
                assert field in item, f"{item['id']}: mount:wallの型はwallAt/orientation/center/sideが必要"
            assert item["orientation"] in VALID_ORIENTATION, f"{item['id']}: 不正なorientation"
            assert item["side"] in VALID_SIDE, f"{item['id']}: sideは1または-1であること"
            w = effective(item, "width", "widthOverride", profile)
            assert check_within_wall(item, w, walls), f"{item['id']}: 対応する壁エンティティ（内壁・外壁とも）の範囲からはみ出している"
        elif profile["mount"] == "exterior":
            for field in ("face", "offset"):
                assert field in item, f"{item['id']}: mount:exteriorの型はface/offsetが必要"
            assert item["face"] in VALID_FACE, f"{item['id']}: 不正なface"
            w = effective(item, "width", "widthOverride", profile)
            assert check_exterior_within_wall(item, w, footprints, exterior_walls), f"{item['id']}: 対応する外壁セグメント(generated/exterior-walls.json)の範囲からはみ出している"
        else:
            for field in ("x", "z"):
                assert field in item, f"{item['id']}: mount:{profile['mount']}の型はx/zが必要"
            room_id = item.get("room")
            if room_id is not None:
                assert room_id in rooms_by_id, f"{item['id']}: 存在しないroom「{room_id}」"
                room = rooms_by_id[room_id]
                assert room["level"] == item["level"], f"{item['id']}: levelが参照roomの階と食い違っている"
                x0, x1, z0, z1 = room_bbox(room["polygon"])
                assert x0 - BBOX_TOLERANCE <= item["x"] <= x1 + BBOX_TOLERANCE, f"{item['id']}: xが部屋「{room_id}」の外形から大きく外れている"
                assert z0 - BBOX_TOLERANCE <= item["z"] <= z1 + BBOX_TOLERANCE, f"{item['id']}: zが部屋「{room_id}」の外形から大きく外れている"

    print(f"electrical: {len(types)} types in catalog, {len(items)} placed items - checks passed")


if __name__ == "__main__":
    main()
