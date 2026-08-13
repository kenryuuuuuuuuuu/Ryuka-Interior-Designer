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
- Transition sync tool: `scripts/sync-house-from-html.mjs`
- HTML/Blender operations: `docs/WORKFLOW.md`

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

The generator creates named collections for slabs, exterior walls, interior
walls, openings, interior-door markers, special walls, and roofs. Exterior and
interior walls are split around openings, so windows and doors are actual
voids rather than decals.

**Update (Phase 1b):** interior room partitions are no longer deferred. Room
polygons were normalized into deduplicated wall centerlines (`data/house.json`
`walls`, sourced from `rooms`) via a one-time conversion script external to
this repository. Interior-door voids are cut into these walls using a
placeholder door height (2.0 m) until real 建具表 (door schedule) heights are
available. This conversion does not yet run automatically from
`sync-house-from-html.mjs`; see the "rooms / walls" section in `README.md` for
the staleness-detection mechanism and manual regeneration steps.

## Run

From the repository root:

```text
blender --background --python blender/build_house.py -- --input data/house.json --output build/ryuka-white-model.blend
```

For an interactive Blender session, open the Scripting workspace and run the
same script. With no arguments it resolves `../data/house.json` relative to the
script and leaves the generated scene open.

## Verification

1. Run `node scripts/sync-house-from-html.mjs --check` to detect legacy drift.
2. Run `python tests/validate_house.py`; optionally validate the full contract
   with any Draft 2020-12 JSON Schema validator.
3. Run the Blender command and confirm it exits successfully.
4. Compare Blender top orthographic view against the Three.js plan view at the
   910 mm grid.
5. Check the four 1F footprint zones, 2F footprint, floor levels, 19 exterior
   openings, 19 interior-door markers, 24 rooms, 23 interior walls, sound
   wall, and two low-roof panels.
6. Record discrepancies as data issues; do not hand-edit generated Blender
   geometry.

## Next migration steps

1. Normalize room boundaries into explicit wall segments.
2. Add a small web loader and switch one non-critical layer to `house.json`.
3. Add automated drift checks between legacy constants and JSON.
4. Confirm ceiling/section/roof dimensions with construction drawings.
5. Start the high-detail minpaku LDK proof of concept only after geometric QA.
