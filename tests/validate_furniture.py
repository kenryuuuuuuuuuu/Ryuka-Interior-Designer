"""Dependency-free checks for data/furniture-catalog.json and data/furniture.json.

house.json 側の rooms/levels と整合しているかも確認する（部屋の取り違え・階の
取り違えを機械的に検出するため）。詳細は docs/ARCHITECTURE.md を参照。
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "furniture-catalog.json"
FURNITURE = ROOT / "data" / "furniture.json"
HOUSE = ROOT / "data" / "house.json"

VALID_STATUS = {"verified", "derived", "estimated"}
VALID_ROTATION = {0, 90, 180, 270}
BBOX_TOLERANCE = 0.6  # m。部屋の外形からこの範囲内なら許容（家具の半径分の余裕）


def room_bbox(polygon):
    xs = [p[0] for p in polygon]
    zs = [p[1] for p in polygon]
    return min(xs), max(xs), min(zs), max(zs)


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    furniture = json.loads(FURNITURE.read_text(encoding="utf-8"))
    house = json.loads(HOUSE.read_text(encoding="utf-8"))

    assert catalog["schemaVersion"] == "1.0.0"
    assert catalog["units"] == "m"
    types = catalog["types"]
    assert len(types) > 0, "furniture-catalog.json: types が空"

    type_ids = [t["type"] for t in types]
    assert len(type_ids) == len(set(type_ids)), "furniture-catalog.json: type が重複している"
    for t in types:
        for field in ("type", "label", "category", "shape", "width", "depth", "height", "clearance"):
            assert field in t, f"furniture-catalog.json: {t.get('type', '?')} に{field}がない"
        assert t["category"] in ("fixture", "furniture"), f"{t['type']}: 不正なcategory"
        assert t["width"] > 0 and t["depth"] > 0 and t["height"] > 0, f"{t['type']}: 寸法は正の数であること"
    by_type = {t["type"]: t for t in types}

    assert furniture["schemaVersion"] == "1.0.0"
    assert furniture["units"] == "m"
    items = furniture["items"]

    rooms_by_id = {r["id"]: r for r in house["rooms"]}
    valid_levels = {fp["level"] for fp in house["footprints"]}

    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)), "furniture.json: id が重複している"

    for item in items:
        assert item["type"] in by_type, f"{item['id']}: 未知のtype「{item['type']}」（furniture-catalog.jsonに存在しない）"
        assert item["rotation"] in VALID_ROTATION, f"{item['id']}: rotationは0/90/180/270のいずれか"
        assert item["status"] in VALID_STATUS, f"{item['id']}: 不正なstatus"
        assert item["level"] in valid_levels, f"{item['id']}: 存在しないlevel {item['level']}"
        for override in ("widthOverride", "depthOverride", "heightOverride"):
            if override in item:
                assert item[override] > 0, f"{item['id']}: {override}は正の数であること"

        room_id = item.get("room")
        if room_id is not None:
            assert room_id in rooms_by_id, f"{item['id']}: 存在しないroom「{room_id}」"
            room = rooms_by_id[room_id]
            assert room["level"] == item["level"], f"{item['id']}: levelが参照roomの階と食い違っている"
            x0, x1, z0, z1 = room_bbox(room["polygon"])
            assert x0 - BBOX_TOLERANCE <= item["x"] <= x1 + BBOX_TOLERANCE, f"{item['id']}: xが部屋「{room_id}」の外形から大きく外れている"
            assert z0 - BBOX_TOLERANCE <= item["z"] <= z1 + BBOX_TOLERANCE, f"{item['id']}: zが部屋「{room_id}」の外形から大きく外れている"

    print(f"furniture: {len(types)} types in catalog, {len(items)} placed items - checks passed")


if __name__ == "__main__":
    main()
