# Phase 1: reproducible geometry foundation

## Goal

Create a version-controlled, reviewable path from architectural data to a
Blender white model without changing the existing Three.js viewer.

```text
data/house.json
  ├─ Blender: blender/build_house.py
  └─ Three.js: existing HTML (migration target; unchanged in Phase 1)
```

## Deliverables

- Shared architectural model: `data/house.json`
- Validation contract: `data/house.schema.json`
- Reserved domain files: `data/electrical.json`, `data/furniture.json`
- Blender generator: `blender/build_house.py`
- Repository working rules: `AGENTS.md`

## Data contract

- Unit: metre
- Source axes: right-handed architectural local coordinates; `x` west to east,
  `z` north to south, `y` upward from GL.
- Blender mapping: `(x, z, y)` becomes `(X, -Y, Z)`. North therefore points to
  positive Blender Y while elevations use Blender Z.
- Every durable object has a stable ID.
- `status` distinguishes verified, derived, and estimated values.
- `source` records where a value came from; `note` records unresolved detail.

## Initial generation scope

The generator creates named collections for slabs, exterior walls, openings,
interior-door markers, special walls, and roofs. Exterior walls are split around
openings, so windows and doors are actual voids rather than decals. Interior
room partitions are intentionally deferred until their polygons are normalized
as wall centerlines; generating walls from room boxes would duplicate shared
walls and encode known approximations as construction geometry.

## Run

From the repository root:

```text
blender --background --python blender/build_house.py -- --input data/house.json --output build/ryuka-white-model.blend
```

For an interactive Blender session, open the Scripting workspace and run the
same script. With no arguments it resolves `../data/house.json` relative to the
script and leaves the generated scene open.

## Verification

1. Run `python tests/validate_house.py`; optionally validate the full contract
   with any Draft 2020-12 JSON Schema validator.
2. Run the Blender command and confirm it exits successfully.
3. Compare Blender top orthographic view against the Three.js plan view at the
   910 mm grid.
4. Check the four 1F footprint zones, 2F footprint, floor levels, 19 exterior
   openings, 19 interior-door markers, sound wall, and two low-roof panels.
5. Record discrepancies as data issues; do not hand-edit generated Blender
   geometry.

## Next migration steps

1. Normalize room boundaries into explicit wall segments.
2. Add a small web loader and switch one non-critical layer to `house.json`.
3. Add automated drift checks between legacy constants and JSON.
4. Confirm ceiling/section/roof dimensions with construction drawings.
5. Start the high-detail minpaku LDK proof of concept only after geometric QA.
