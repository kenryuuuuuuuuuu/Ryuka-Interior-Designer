"""Dependency-free Phase 1 data checks."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOUSE = ROOT / "data" / "house.json"
INTERIOR_WALLS = ROOT / "generated" / "interior-walls.json"


def main():
    data = json.loads(HOUSE.read_text(encoding="utf-8"))
    assert data["schemaVersion"] == "1.0.0"
    assert data["units"] == "m"
    assert len(data["footprints"]) == 5
    assert len(data["rooms"]) == 33, f"expected 33 rooms, got {len(data['rooms'])}"
    assert "walls" not in data, "walls は data/house.json から廃止済み（roomsから自動導出する方式に統一。generated/interior-walls.json を参照）"

    ids = []
    for key in ("footprints", "specialWalls", "roofs", "rooms"):
        ids.extend(item["id"] for item in data[key])
    assert len(ids) == len(set(ids)), "IDs must be globally unique"

    for fp in data["footprints"]:
        assert fp["x0"] < fp["x1"] and fp["z0"] < fp["z1"]
        assert fp["status"] in {"verified", "derived", "estimated"}
    for room in data["rooms"]:
        assert len(room["polygon"]) >= 3, f"{room['id']}: polygon needs >=3 points"
        assert room["status"] in {"verified", "derived", "estimated"}

    # 内壁は data/house.json の rooms から自動導出したもの
    # （scripts/build-web-data.mjs、generated/interior-walls.json）。生成物として
    # 最低限の形状の妥当性（H/Vの座標整合、ID重複なし）だけをここで検証する。
    # 「roomsを直したのに再生成し忘れて古いまま」を検知するのは
    # `node scripts/build-web-data.mjs --check` の役目（CIで別途実行される）。
    walls_payload = json.loads(INTERIOR_WALLS.read_text(encoding="utf-8"))
    walls = walls_payload["walls"]
    assert len(walls) > 0, "generated/interior-walls.json: walls が空（node scripts/build-web-data.mjs を実行したか確認）"
    wall_ids = [w["id"] for w in walls]
    assert len(wall_ids) == len(set(wall_ids)), "generated/interior-walls.json: id が重複している"
    for wall in walls:
        if wall["orientation"] == "H":
            assert wall["z0"] == wall["z1"], f"{wall['id']}: horizontal wall must have z0==z1"
            assert wall["x0"] < wall["x1"], f"{wall['id']}: x0 must be < x1"
        else:
            assert wall["x0"] == wall["x1"], f"{wall['id']}: vertical wall must have x0==x1"
            assert wall["z0"] < wall["z1"], f"{wall['id']}: z0 must be < z1"

    for stair in data.get("stairs", []):
        assert stair["levelTo"] == stair["levelFrom"] + 1, f"{stair['id']}: levelTo must be levelFrom+1"
        assert stair["totalSteps"] > 0, f"{stair['id']}: totalSteps must be positive"
        assert stair["status"] in {"verified", "derived", "estimated"}
        for seg in stair["segments"]:
            if seg["type"] == "straight":
                assert (seg["x0"], seg["z0"]) != (seg["x1"], seg["z1"]), f"{stair['id']}: straight segment has zero length"
            elif seg["type"] == "arc":
                assert seg["radius"] > 0, f"{stair['id']}: arc radius must be positive"
                assert seg["startAngleDeg"] != seg["endAngleDeg"], f"{stair['id']}: arc has zero sweep"
            else:
                raise AssertionError(f"{stair['id']}: unknown segment type {seg['type']}")

    print(f"house.json: Phase 1 checks passed ({len(data['rooms'])} rooms, {len(walls)} derived interior walls)")


if __name__ == "__main__":
    main()

