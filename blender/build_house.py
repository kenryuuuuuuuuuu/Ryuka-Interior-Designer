"""Build the Ryuka architectural white model from data/house.json.

Run with Blender, not CPython:
  blender --background --python blender/build_house.py -- \
    --input data/house.json --output build/ryuka-white-model.blend
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

try:
    import bpy
except ImportError as exc:  # Helpful failure when accidentally run with CPython.
    raise SystemExit("This script must be run by Blender (bpy is unavailable).") from exc


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR.parent / "data" / "house.json"


def cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def collection(name: str, parent=None):
    coll = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def material(name: str, color: tuple[float, float, float, float]):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def box(name, x0, x1, z0, z1, y0, y1, coll, mat=None):
    """Create an architectural box, mapping source z to negative Blender Y."""
    bpy.ops.mesh.primitive_cube_add(
        location=((x0 + x1) / 2, -(z0 + z1) / 2, (y0 + y1) / 2),
        scale=((x1 - x0) / 2, (z1 - z0) / 2, (y1 - y0) / 2),
    )
    obj = bpy.context.object
    obj.name = name
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    coll.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


def level_y(data, level):
    return data["levels"][f"fl{level}"]


def footprint_for_opening(data, opening):
    level = opening["level"]
    offset = opening["offset"]
    candidates = [f for f in data["footprints"] if f["level"] == level]
    if opening["face"] in ("N", "S"):
        matches = [f for f in candidates if f["x0"] <= offset <= f["x1"]]
    elif "wallX" in opening:
        matches = [f for f in candidates if f["x0"] <= opening["wallX"] <= f["x1"]]
    elif opening["face"] == "E":
        matches = [max(candidates, key=lambda f: f["x1"])]
    else:
        matches = [min(candidates, key=lambda f: f["x0"])]
    return matches[0] if matches else candidates[0]


def wall_segments(length0, length1, y0, height, cuts):
    """Split a wall plane into rectangles around horizontal/vertical openings."""
    xs = sorted({length0, length1, *[max(length0, c[0]) for c in cuts], *[min(length1, c[1]) for c in cuts]})
    result = []
    for a, b in zip(xs, xs[1:]):
        if b - a <= 1e-6:
            continue
        active = [c for c in cuts if c[0] < b - 1e-6 and c[1] > a + 1e-6]
        ys = sorted({y0, y0 + height, *[y0 + c[2] for c in active], *[y0 + c[3] for c in active]})
        for low, high in zip(ys, ys[1:]):
            mid_x, mid_y = (a + b) / 2, (low + high) / 2
            inside = any(c[0] < mid_x < c[1] and y0 + c[2] < mid_y < y0 + c[3] for c in active)
            if not inside and high - low > 1e-6:
                result.append((a, b, low, high))
    return result


def build_exterior_walls(data, coll, mat):
    thickness = data["defaults"]["wallThickness"]
    height = data["defaults"]["ceilingHeight"]
    for fp in data["footprints"]:
        base = level_y(data, fp["level"])
        related = [o for o in data["openings"] if o["level"] == fp["level"] and footprint_for_opening(data, o)["id"] == fp["id"]]
        for face in ("N", "S", "E", "W"):
            wall_openings = [o for o in related if o["face"] == face]
            if face in ("N", "S"):
                fixed = fp["z0"] if face == "N" else fp["z1"]
                cuts = [(o["offset"], o["offset"] + o["width"], o["sill"], o["sill"] + o["height"]) for o in wall_openings]
                for i, (a, b, low, high) in enumerate(wall_segments(fp["x0"], fp["x1"], base, height, cuts)):
                    box(f"wall-{fp['id']}-{face}-{i:02d}", a, b, fixed-thickness/2, fixed+thickness/2, low, high, coll, mat)
            else:
                fixed = next((o["wallX"] for o in wall_openings if "wallX" in o), fp["x1"] if face == "E" else fp["x0"])
                cuts = [(o["offset"], o["offset"] + o["width"], o["sill"], o["sill"] + o["height"]) for o in wall_openings]
                for i, (a, b, low, high) in enumerate(wall_segments(fp["z0"], fp["z1"], base, height, cuts)):
                    box(f"wall-{fp['id']}-{face}-{i:02d}", fixed-thickness/2, fixed+thickness/2, a, b, low, high, coll, mat)


def build_interior_walls(data, coll, mat):
    """data['walls'](部屋ポリゴンから重複統合した壁芯データ)から室内壁を生成する。
    同じ壁の上にある室内ドア(interiorDoors)を自動検出し、開口として切り欠く。
    ドア高さは建具表が未入手のため暫定値(2.0m)。実データが揃い次第、
    interiorDoorsにheightフィールドを足して置き換えること。
    """
    thickness = data["defaults"].get("interiorWallThickness", 0.06)
    placeholder_door_height = 2.0
    for wall in data["walls"]:
        base = level_y(data, wall["level"])
        height = data["defaults"]["ceilingHeight"]
        doors_on_wall = []
        for d in data["interiorDoors"]:
            if d["floor"] != wall["level"] or d["orientation"] != wall["orientation"]:
                continue
            lo, hi = d["center"] - d["width"] / 2, d["center"] + d["width"] / 2
            if wall["orientation"] == "H":
                if abs(d["wallAt"] - wall["z0"]) < 0.01 and wall["x0"] - 0.01 <= lo and hi <= wall["x1"] + 0.01:
                    doors_on_wall.append(d)
            else:
                if abs(d["wallAt"] - wall["x0"]) < 0.01 and wall["z0"] - 0.01 <= lo and hi <= wall["z1"] + 0.01:
                    doors_on_wall.append(d)
        cuts = [(d["center"] - d["width"] / 2, d["center"] + d["width"] / 2, 0, placeholder_door_height) for d in doors_on_wall]
        if wall["orientation"] == "H":
            for i, (a, b, low, high) in enumerate(wall_segments(wall["x0"], wall["x1"], base, height, cuts)):
                box(f"{wall['id']}-{i:02d}", a, b, wall["z0"]-thickness/2, wall["z0"]+thickness/2, low, high, coll, mat)
        else:
            for i, (a, b, low, high) in enumerate(wall_segments(wall["z0"], wall["z1"], base, height, cuts)):
                box(f"{wall['id']}-{i:02d}", wall["x0"]-thickness/2, wall["x0"]+thickness/2, a, b, low, high, coll, mat)


def build_roof(data, roof, fp, coll, mat):
    z0, z1 = roof["zNorth"], roof["zSouth"]
    y0 = roof["baseAtZMinus0_5"] + (z0 + 0.5) * roof["pitch"]
    y1 = roof["baseAtZMinus0_5"] + (z1 + 0.5) * roof["pitch"]
    run = math.hypot(z1 - z0, y1 - y0)
    bpy.ops.mesh.primitive_cube_add(
        location=((fp["x0"] + fp["x1"]) / 2, -(z0 + z1) / 2, (y0 + y1) / 2),
        scale=((fp["x1"] - fp["x0"]) / 2, run / 2, roof["thickness"] / 2),
        rotation=(-math.atan2(y1 - y0, z1 - z0), 0, 0),
    )
    obj = bpy.context.object
    obj.name = roof["id"]
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    coll.objects.link(obj)
    obj.data.materials.append(mat)


def build(data):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    root = collection("RYUKA_DIGITAL_TWIN")
    slabs, walls = collection("Slabs", root), collection("ExteriorWalls", root)
    interior_walls = collection("InteriorWalls", root)
    markers, specials, roofs = collection("DoorMarkers", root), collection("SpecialWalls", root), collection("Roofs", root)
    white = material("MAT_WhiteModel", (0.78, 0.82, 0.86, 1))
    interior_white = material("MAT_InteriorWall", (0.92, 0.88, 0.78, 1))
    marker = material("MAT_DoorMarker", (0.2, 0.55, 0.9, 0.35))
    roof_mat = material("MAT_Roof", (0.45, 0.4, 0.34, 1))
    for fp in data["footprints"]:
        y = level_y(data, fp["level"])
        box(f"slab-{fp['id']}", fp["x0"], fp["x1"], fp["z0"], fp["z1"], y-0.12, y, slabs, white)
    build_exterior_walls(data, walls, white)
    build_interior_walls(data, interior_walls, interior_white)
    for door in data["interiorDoors"]:
        base, thick, height = level_y(data, door["floor"]), 0.03, 1.9
        if door["orientation"] == "H":
            box(door["id"], door["center"]-door["width"]/2, door["center"]+door["width"]/2, door["wallAt"]-thick, door["wallAt"]+thick, base, base+height, markers, marker)
        else:
            box(door["id"], door["wallAt"]-thick, door["wallAt"]+thick, door["center"]-door["width"]/2, door["center"]+door["width"]/2, base, base+height, markers, marker)
    for wall in data["specialWalls"]:
        t = data["defaults"]["wallThickness"]
        box(wall["id"], wall["x"]-t/2, wall["x"]+t/2, wall["z0"], wall["z1"], level_y(data, wall["level"]), wall["topY"], specials, white)
    fps = {fp["id"]: fp for fp in data["footprints"]}
    for roof in data["roofs"]:
        build_roof(data, roof, fps[roof["footprintId"]], roofs, roof_mat)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.length_unit = "METERS"
    bpy.context.scene["ryuka_schema_version"] = data["schemaVersion"]


def main():
    args = cli_args()
    with args.input.resolve().open(encoding="utf-8") as stream:
        data = json.load(stream)
    build(data)
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output))
        print(f"Saved {output}")


if __name__ == "__main__":
    main()
