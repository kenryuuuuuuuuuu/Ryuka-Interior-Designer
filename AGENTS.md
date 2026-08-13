# Repository guidance

This repository contains a browser-based architectural white model and the
first phase of a reproducible Blender digital-twin pipeline.

## Source of truth

- `data/house.json` is the target shared geometry source of truth.
- `interior-white-model.html` is the current production viewer and must keep
  working during the migration.
- Until the web viewer reads `house.json`, geometry changes must be applied to
  both files and checked for drift.
- All geometry is expressed in metres. Source coordinates are `x = west to
  east`, `z = north to south`, and `y = height above GL`.

## Change rules

- Do not restructure or rewrite the existing HTML as part of Phase 1.
- Preserve provenance, confidence, and verification notes when moving data.
- Never replace an observed value with an assumption without marking it as
  `estimated` and documenting the reason.
- Generated `.blend` files and renders are outputs; do not commit them unless a
  task explicitly asks for an approved reference artifact.
- Validate JSON before committing and run Blender generation when Blender is
  available.

## Phase 1 acceptance criteria

1. Existing `interior-white-model.html` remains byte-for-byte unchanged.
2. `data/house.json` validates against `data/house.schema.json`.
3. `blender/build_house.py` can rebuild the initial white model from JSON.
4. IDs are stable and units/coordinate transforms are documented.

