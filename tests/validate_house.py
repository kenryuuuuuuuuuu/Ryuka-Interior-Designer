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
    assert len(data["openings"]) == 19
    assert len(data["interiorDoors"]) == 19
    ids = []
    for key in ("footprints", "openings", "interiorDoors", "specialWalls", "roofs"):
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
    print("house.json: Phase 1 checks passed")


if __name__ == "__main__":
    main()

