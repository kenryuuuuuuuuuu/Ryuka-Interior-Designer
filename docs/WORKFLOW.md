# HTML / Blender update workflow

## Why there are two workflows

The current Three.js model is a standalone HTML file whose geometry and viewer
code live together. It is still actively edited, so Phase 1 treats it as the
legacy geometry input. The destination architecture separates geometry from
presentation so the web viewer and Blender cannot silently diverge.

## Transition workflow: HTML changes drive Blender

Use this while architectural constants are still edited inside
`interior-white-model.html`.

```text
edit interior-white-model.html
        ↓
preview and verify in browser
        ↓
node scripts/sync-house-from-html.mjs --check
        ↓ if expected differences are reported
node scripts/sync-house-from-html.mjs --write
        ↓
python tests/validate_house.py
        ↓
Blender rebuild from data/house.json
```

The sync command covers levels, ceiling/wall defaults, footprints, exterior
openings, interior doors, and the sound wall. It deliberately refuses changes
that add or remove array items because stable IDs and verification status need a
human decision. Roof formulas and room approximations must currently be reviewed
manually and are reported as migration work.

HTML-only changes such as camera controls, colors, labels, and menus do not need
a Blender rebuild.

## Destination workflow: shared data drives both outputs

After the web data loader is complete:

```text
edit data/house.json
        ├─ generate standalone web data → web viewer
        └─ blender/build_house.py       → Blender model
```

At that point:

- Architectural dimensions are edited only in `data/house.json`.
- Web appearance and interaction are edited under `web/`.
- Blender materials and generation logic are edited under `blender/`.
- The standalone HTML remains a generated/distributable artifact, not a second
  geometry database.

## Planned repository layout

```text
Ryuka-Interior-Designer/
├─ README.md
├─ AGENTS.md
├─ interior-white-model.html      # current compatible entry during migration
├─ web/
│  ├─ index.html                  # future viewer source
│  ├─ js/
│  └─ generated/house-data.js     # generated; keeps file:// preview possible
├─ data/
│  ├─ house.json                  # shared architectural model
│  ├─ electrical.json
│  ├─ furniture.json
│  └─ house.schema.json
├─ blender/
│  └─ build_house.py
├─ scripts/
│  ├─ sync-house-from-html.mjs    # transition-only import
│  └─ build-web-data.mjs          # future JSON → standalone web data
├─ tests/
├─ assets/
│  ├─ textures/
│  ├─ furniture/
│  └─ fixtures/
└─ docs/
```

The current root HTML should move only when `web/index.html` has parity. When it
moves, retain a root compatibility entry so existing bookmarks and GitHub Pages
links do not break.

## Change classification

| Change | Edit here now | Blender rebuild |
|---|---|---|
| Wall, floor, opening, door position | HTML, then sync to `house.json` | Required |
| Ceiling/level dimension | HTML, then sync to `house.json` | Required |
| Roof or room approximation | HTML and reviewed JSON update | Required |
| Three.js controls, menu, colors | HTML only | Not required |
| Blender material/render settings | `blender/` only | Required |
| Furniture/electrical data | matching file under `data/` | Required when generator supports it |

