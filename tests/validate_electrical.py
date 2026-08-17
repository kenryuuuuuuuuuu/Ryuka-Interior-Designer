"""Dependency-free checks for data/electrical-catalog.json and data/electrical.json.

house.json 側の rooms/footprints、および rooms から自動導出された内壁
（generated/interior-walls.json、node scripts/build-web-data.mjs で生成）と
整合しているかも確認する。実行前に必ず node scripts/build-web-data.mjs を
実行しておくこと。詳細は docs/ARCHITECTURE.md を参照。
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "electrical-catalog.json"
ELECTRICAL = ROOT / "data" / "electrical.json"
HOUSE = ROOT / "data" / "house.json"
INTERIOR_WALLS = ROOT / "generated" / "interior-walls.json"

VALID_STATUS = {"verified", "derived", "estimated"}
VALID_CATEGORY = {"outlet", "switch", "lighting", "data", "equipment"}
VALID_MOUNT = {"wall", "ceiling", "floor"}
VALID_HEIGHT_REF = {"floor", "ceiling"}
VALID_ORIENTATION = {"H", "V"}
VALID_SIDE = {1, -1}
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
    壁付け設備の1件が、実在する壁エンティティの範囲内に収まっているかを確認する。"""
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


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    electrical = json.loads(ELECTRICAL.read_text(encoding="utf-8"))
    house = json.loads(HOUSE.read_text(encoding="utf-8"))
    # 内壁はdata/house.jsonのroomsから自動導出したもの（node scripts/build-web-data.mjsで
    # generated/interior-walls.jsonに書き出される）。このスクリプトの実行前に必ず再生成しておくこと。
    walls = json.loads(INTERIOR_WALLS.read_text(encoding="utf-8"))["walls"]

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
            assert check_within_wall(item, w, walls), f"{item['id']}: 対応する壁エンティティの範囲からはみ出している"
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
