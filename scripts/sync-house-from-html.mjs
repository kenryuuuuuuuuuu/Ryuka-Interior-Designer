/** Transition-only synchronization from legacy HTML constants to house.json. */

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const htmlPath = path.join(root, "interior-white-model.html");
const housePath = path.join(root, "data", "house.json");
const mode = process.argv[2] ?? "--check";

if (!["--check", "--write"].includes(mode)) {
  console.error("Usage: node scripts/sync-house-from-html.mjs [--check|--write]");
  process.exit(2);
}

const html = fs.readFileSync(htmlPath, "utf8");
const house = JSON.parse(fs.readFileSync(housePath, "utf8"));

function declaration(name) {
  const start = html.indexOf(`const ${name} =`);
  if (start < 0) throw new Error(`Missing HTML constant: ${name}`);
  let quote = null;
  let escaped = false;
  let square = 0;
  let curly = 0;
  for (let i = start; i < html.length; i += 1) {
    const char = html[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (char === "\\") escaped = true;
      else if (char === quote) quote = null;
      continue;
    }
    if (char === "'" || char === '"' || char === "`") quote = char;
    else if (char === "[") square += 1;
    else if (char === "]") square -= 1;
    else if (char === "{") curly += 1;
    else if (char === "}") curly -= 1;
    else if (char === ";" && square === 0 && curly === 0) return html.slice(start, i + 1);
  }
  throw new Error(`Unterminated HTML constant: ${name}`);
}

const names = ["LEVELS", "CEIL_H", "WALL_T", "FLOOR1", "FLOOR2", "OPENINGS", "SOUND_WALL", "INTERIOR_DOORS"];
const source = `${names.map(declaration).join("\n")}\nreturn {${names.join(",")}};`;
// The repository HTML is trusted project source. Do not run this against downloaded HTML.
const legacy = Function(source)();

function retain(existing, incoming, fields) {
  if (existing.length !== incoming.length) {
    throw new Error(`Item count changed (${existing.length} → ${incoming.length}). Assign stable IDs/status manually.`);
  }
  return incoming.map((item, index) => ({
    id: existing[index].id,
    ...Object.fromEntries(fields.map(([target, sourceKey]) => [target, item[sourceKey]])),
    status: existing[index].status,
  }));
}

const next = structuredClone(house);
next.levels = legacy.LEVELS;
next.defaults.ceilingHeight = legacy.CEIL_H;
next.defaults.wallThickness = legacy.WALL_T;
const footprints = [
  ...legacy.FLOOR1.map((item) => ({ ...item, level: 1 })),
  { id: "2f-main", ...legacy.FLOOR2, level: 2, use: "2階" },
];
next.footprints = footprints.map((item, index) => ({
  id: house.footprints[index].id,
  level: item.level,
  x0: item.x0, x1: item.x1, z0: item.z0, z1: item.z1,
  use: house.footprints[index].use,
  status: house.footprints[index].status,
}));
if (house.openings.length !== legacy.OPENINGS.length) {
  throw new Error(`Opening count changed (${house.openings.length} → ${legacy.OPENINGS.length}). Assign stable IDs/status manually.`);
}
next.openings = legacy.OPENINGS.map((item, index) => {
  const opening = {
    id: house.openings[index].id,
    face: item.face,
    offset: item.lx ?? item.lz,
    width: item.w, height: item.h, sill: item.sill, level: item.level,
    kind: item.kind, label: item.label,
    status: house.openings[index].status,
  };
  if (item.x !== undefined) opening.wallX = item.x;
  return opening;
});
next.interiorDoors = retain(house.interiorDoors, legacy.INTERIOR_DOORS, [
  ["label", "label"], ["wallAt", "wallAt"], ["orientation", "orientation"],
  ["center", "center"], ["width", "width"], ["floor", "floor"],
]);
next.specialWalls = [{
  id: house.specialWalls[0].id,
  label: house.specialWalls[0].label,
  x: legacy.SOUND_WALL.x, z0: legacy.SOUND_WALL.z0, z1: legacy.SOUND_WALL.z1,
  level: legacy.SOUND_WALL.level, topY: legacy.SOUND_WALL.topY,
  status: house.specialWalls[0].status,
}];

const normalize = (value) => JSON.stringify(value, null, 2);
const canonical = (value) => {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  }
  return value;
};
if (JSON.stringify(canonical(next)) === JSON.stringify(canonical(house))) {
  console.log("HTML geometry and house.json are synchronized.");
  process.exit(0);
}

if (mode === "--check") {
  console.error("HTML geometry differs from house.json. Review, then run with --write.");
  process.exit(1);
}

next.provenance.migratedFrom = "interior-white-model.html";
next.provenance.snapshotDate = new Date().toISOString().slice(0, 10);
fs.writeFileSync(housePath, `${normalize(next)}\n`, "utf8");
console.log("Updated data/house.json. Review the diff and run python tests/validate_house.py.");
