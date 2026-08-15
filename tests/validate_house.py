"""Dependency-free Phase 1 data checks."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOUSE = ROOT / "data" / "house.json"


def main():
    data = json.loads(HOUSE.read_text(encoding="utf-8"))
    assert data["schemaVersion"] == "1.0.0"
    assert data["units"] == "m"
    assert len(data["footprints"]) == 5
    assert len(data["rooms"]) == 28, f"expected 28 rooms, got {len(data['rooms'])}"
    assert len(data["walls"]) >= 20, f"expected at least 20 interior walls, got {len(data['walls'])}"

    ids = []
    for key in ("footprints", "specialWalls", "roofs", "rooms", "walls"):
        ids.extend(item["id"] for item in data[key])
    assert len(ids) == len(set(ids)), "IDs must be globally unique"

    for fp in data["footprints"]:
        assert fp["x0"] < fp["x1"] and fp["z0"] < fp["z1"]
        assert fp["status"] in {"verified", "derived", "estimated"}
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

    print(f"house.json: Phase 1 checks passed ({len(data['rooms'])} rooms, {len(data['walls'])} walls)")


if __name__ == "__main__":
    main()

