"""Dependency-free Phase 1 data checks."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOUSE = ROOT / "data" / "house.json"


def check_door_has_matching_wall(door, walls):
    lo, hi = door["center"] - door["width"] / 2, door["center"] + door["width"] / 2
    for w in walls:
        if w["level"] != door["floor"]:
            continue
        if door["orientation"] == "H" and w["orientation"] == "H" and abs(w["z0"] - door["wallAt"]) < 0.01:
            if w["x0"] - 0.01 <= lo and hi <= w["x1"] + 0.01:
                return True
        if door["orientation"] == "V" and w["orientation"] == "V" and abs(w["x0"] - door["wallAt"]) < 0.01:
            if w["z0"] - 0.01 <= lo and hi <= w["z1"] + 0.01:
                return True
    return False


def main():
    data = json.loads(HOUSE.read_text(encoding="utf-8"))
    assert data["schemaVersion"] == "1.0.0"
    assert data["units"] == "m"
    assert len(data["footprints"]) == 5
    assert len(data["openings"]) == 19
    assert len(data["interiorDoors"]) == 19
    assert len(data["rooms"]) == 24, f"expected 24 rooms, got {len(data['rooms'])}"
    assert len(data["walls"]) >= 20, f"expected at least 20 interior walls, got {len(data['walls'])}"

    ids = []
    for key in ("footprints", "openings", "interiorDoors", "specialWalls", "roofs", "rooms", "walls"):
        ids.extend(item["id"] for item in data[key])
    assert len(ids) == len(set(ids)), "IDs must be globally unique"

    for fp in data["footprints"]:
        assert fp["x0"] < fp["x1"] and fp["z0"] < fp["z1"]
        assert fp["status"] in {"verified", "derived", "estimated"}
    for opening in data["openings"]:
        assert opening["width"] > 0 and opening["height"] > 0 and opening["sill"] >= 0
        assert opening["face"] in {"N", "S", "E", "W"}
    for door in data["interiorDoors"]:
        assert door["orientation"] in {"H", "V"} and door["width"] > 0
    for room in data["rooms"]:
        assert len(room["polygon"]) >= 3, f"{room['id']}: polygon needs >=3 points"
        assert room["status"] in {"verified", "derived", "estimated"}
    for wall in data["walls"]:
        if wall["orientation"] == "H":
            assert wall["z0"] == wall["z1"], f"{wall['id']}: horizontal wall must have z0==z1"
            assert wall["x0"] < wall["x1"], f"{wall['id']}: x0 must be < x1"
        else:
            assert wall["x0"] == wall["x1"], f"{wall['id']}: vertical wall must have x0==x1"
            assert wall["z0"] < wall["z1"], f"{wall['id']}: z0 must be < z1"

    # 各室内ドアが、実在する壁エンティティの範囲内に収まっているかを確認する。
    # (壁を「越えて」宙に浮いたドアがないことの機械的な保証)
    missing = [d["label"] for d in data["interiorDoors"] if not check_door_has_matching_wall(d, data["walls"])]
    assert not missing, f"doors without a matching wall segment: {missing}"

    print(f"house.json: Phase 1 checks passed ({len(data['rooms'])} rooms, {len(data['walls'])} walls)")


if __name__ == "__main__":
    main()

