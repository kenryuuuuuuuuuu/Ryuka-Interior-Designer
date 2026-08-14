/**
 * data/house.json（正本）から、Three.js白模型（interior-white-model.html）が読み込む
 * 描画用データファイル generated/house-data.js を生成する。
 *
 * house.json を編集したら、このスクリプトを実行してHTML側のデータを更新すること。
 * 詳細な運用手順は docs/ARCHITECTURE.md を参照。
 *
 * 使い方:
 *   node scripts/build-web-data.mjs           # generated/house-data.js を書き出す
 *   node scripts/build-web-data.mjs --check   # 生成結果が最新かだけ確認する（CI向け）
 */
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const housePath = path.join(root, "data", "house.json");
const outPath = path.join(root, "generated", "house-data.js");
const mode = process.argv[2] ?? "--write";

if (!["--check", "--write"].includes(mode)) {
  console.error("Usage: node scripts/build-web-data.mjs [--check|--write]");
  process.exit(2);
}

const house = JSON.parse(fs.readFileSync(housePath, "utf8"));

const CONF_FROM_STATUS = { verified: "高", derived: "中", estimated: "低" };

function num(n) {
  // 3.2320000000004 のような浮動小数の誤差表示を避けつつ、末尾ゼロは切り詰める。
  return Number(n.toFixed(6)).toString();
}
function str(s) {
  return `'${String(s).replace(/\\/g, "\\\\").replace(/'/g, "\\'")}'`;
}
function withNote(line, note) {
  return note ? `${line} // ${note}` : line;
}

function buildLevels() {
  const l = house.levels;
  return `const LEVELS = { gl:${num(l.gl)}, fl1:${num(l.fl1)}, fl2:${num(l.fl2)}, eaveLow:${num(l.eaveLow)}, eaveHigh:${num(l.eaveHigh)}, eave2:${num(l.eave2)}, ridge:${num(l.ridge)} };`;
}

function buildFloor1() {
  const rows = house.footprints
    .filter((f) => f.level === 1)
    .map((f) => `  { id:${str(f.id)}, x0:${num(f.x0)}, x1:${num(f.x1)}, z0:${num(f.z0)}, z1:${num(f.z1)}, use:${str(f.use)} }`)
    .join(",\n");
  return `const FLOOR1 = [\n${rows}\n];`;
}

function buildFloor2() {
  const fp = house.footprints.find((f) => f.level === 2);
  return `const FLOOR2 = { x0:${num(fp.x0)}, x1:${num(fp.x1)}, z0:${num(fp.z0)}, z1:${num(fp.z1)} };`;
}

function buildOpenings() {
  const rows = house.openings.map((o) => {
    const parts = [`face:${str(o.face)}`];
    if (o.face === "N" || o.face === "S") parts.push(`lx:${num(o.offset)}`);
    else parts.push(`lz:${num(o.offset)}`);
    if (o.wallX !== undefined) parts.push(`x:${num(o.wallX)}`);
    parts.push(`w:${num(o.width)}`, `h:${num(o.height)}`, `sill:${num(o.sill)}`, `level:${o.level}`, `kind:${str(o.kind)}`, `label:${str(o.label)}`);
    return withNote(`  { ${parts.join(", ")} },`, o.note);
  });
  return `const OPENINGS = [\n${rows.join("\n")}\n];`;
}

function buildSoundWall() {
  const sw = house.specialWalls[0];
  const topY = sw.topY === house.levels.eaveLow ? "LEVELS.eaveLow" : num(sw.topY);
  const line = `const SOUND_WALL = { x:${num(sw.x)}, z0:${num(sw.z0)}, z1:${num(sw.z1)}, level:${sw.level}, topY:${topY} };`;
  return withNote(line, sw.note);
}

function buildInteriorDoors() {
  const rows = house.interiorDoors
    .map((d) => `  { label:${str(d.label)}, wallAt:${num(d.wallAt)}, orientation:${str(d.orientation)}, center:${num(d.center)}, width:${num(d.width)}, floor:${d.floor} }`)
    .join(",\n");
  return `const INTERIOR_DOORS = [\n${rows}\n];`;
}

function bbox(polygon) {
  const xs = polygon.map((p) => p[0]);
  const zs = polygon.map((p) => p[1]);
  return { x0: Math.min(...xs), x1: Math.max(...xs), z0: Math.min(...zs), z1: Math.max(...zs) };
}

function buildRoomsApprox() {
  const byLevel = (lvl) => {
    const rows = house.rooms
      .filter((r) => r.level === lvl)
      .map((r) => {
        const b = bbox(r.polygon);
        const fields = [`name:${str(r.label)}`, `x0:${num(b.x0)}`, `x1:${num(b.x1)}`, `z0:${num(b.z0)}`, `z1:${num(b.z1)}`];
        if (r.polygon.length > 4) {
          const pts = r.polygon.map(([x, z]) => `[${num(x)},${num(z)}]`).join(",");
          fields.push(`poly:[${pts}]`);
        }
        fields.push(`conf:${str(CONF_FROM_STATUS[r.status])}`);
        if (r.note) fields.push(`note:${str(r.note)}`);
        return `    { ${fields.join(", ")} }`;
      })
      .join(",\n");
    return `  ${lvl}: [\n${rows}\n  ]`;
  };
  return `const ROOMS_APPROX = {\n${byLevel(1)},\n${byLevel(2)}\n};`;
}

function buildRoofs() {
  const fpById = Object.fromEntries(house.footprints.map((f) => [f.id, f]));
  const rows = house.roofs
    .map((r) => {
      const fp = fpById[r.footprintId];
      return `  { id:${str(r.id)}, x0:${num(fp.x0)}, x1:${num(fp.x1)}, zNorth:${num(r.zNorth)}, zSouth:${num(r.zSouth)}, pitch:${num(r.pitch)}, thickness:${num(r.thickness)}, base:${num(r.baseAtZMinus0_5)} }`;
    })
    .join(",\n");
  return `const ROOFS = [\n${rows}\n];`;
}

const banner = `// ============================================================================
// 自動生成ファイル。手で編集しないこと。
// 生成元: data/house.json （このリポジトリの正本）
// 生成コマンド: node scripts/build-web-data.mjs
// house.json を編集したら、このファイルを再生成してからブラウザで確認すること。
// ============================================================================`;

const CEIL_H = `const CEIL_H = ${num(house.defaults.ceilingHeight)}; // ${house.defaults.ceilingHeightStatus === "estimated" ? "推測値（要確認）" : house.defaults.ceilingHeightStatus}`;
const WALL_T = `const WALL_T = ${num(house.defaults.wallThickness)};`;

const output = [
  banner,
  buildLevels(),
  CEIL_H,
  WALL_T,
  "",
  buildFloor1(),
  buildFloor2(),
  "",
  buildOpenings(),
  "",
  buildSoundWall(),
  "",
  buildInteriorDoors(),
  "",
  buildRoomsApprox(),
  "",
  buildRoofs(),
  "",
].join("\n");

if (mode === "--check") {
  const current = fs.existsSync(outPath) ? fs.readFileSync(outPath, "utf8") : null;
  if (current === output) {
    console.log("generated/house-data.js is up to date with data/house.json.");
    process.exit(0);
  }
  console.error("generated/house-data.js is STALE. Run: node scripts/build-web-data.mjs");
  process.exit(1);
}

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, output, "utf8");
console.log(`Wrote ${path.relative(root, outPath)} from data/house.json.`);
