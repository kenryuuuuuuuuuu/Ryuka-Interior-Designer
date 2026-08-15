/**
 * data/house.json・data/furniture-catalog.json・data/furniture.json・
 * data/door-catalog.json・data/window-catalog.json・data/openings.json・data/interior-doors.json
 * （いずれも正本）から、Three.js白模型（interior-white-model.html）が読み込む
 * 描画用データファイル generated/house-data.js を生成する。
 *
 * これらのJSONを編集したら、このスクリプトを実行してHTML側のデータを更新すること。
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
const furnitureCatalogPath = path.join(root, "data", "furniture-catalog.json");
const furniturePath = path.join(root, "data", "furniture.json");
const furnitureCatalog = JSON.parse(fs.readFileSync(furnitureCatalogPath, "utf8"));
const furniture = JSON.parse(fs.readFileSync(furniturePath, "utf8"));
const doorCatalogPath = path.join(root, "data", "door-catalog.json");
const windowCatalogPath = path.join(root, "data", "window-catalog.json");
const openingsPath = path.join(root, "data", "openings.json");
const interiorDoorsPath = path.join(root, "data", "interior-doors.json");
const doorCatalog = JSON.parse(fs.readFileSync(doorCatalogPath, "utf8"));
const windowCatalog = JSON.parse(fs.readFileSync(windowCatalogPath, "utf8"));
const openings = JSON.parse(fs.readFileSync(openingsPath, "utf8"));
const interiorDoors = JSON.parse(fs.readFileSync(interiorDoorsPath, "utf8"));
const doorWindowTypes = [...doorCatalog.types, ...windowCatalog.types];
const doorWindowByType = Object.fromEntries(doorWindowTypes.map((t) => [t.type, t]));

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

function buildDoorWindowCatalog() {
  const rows = doorWindowTypes
    .map((t) => {
      const fields = [`label:${str(t.label)}`, `category:${str(t.category)}`, `operation:${str(t.operation)}`, `width:${num(t.width)}`, `height:${num(t.height)}`, `sill:${num(t.sill)}`];
      if (t.archRise !== undefined) fields.push(`archRise:${num(t.archRise)}`);
      return `  ${str(t.type)}: { ${fields.join(", ")} }`;
    })
    .join(",\n");
  return `const DOOR_WINDOW_CATALOG = {\n${rows}\n};`;
}

function buildOpenings() {
  const rows = openings.items.map((o) => {
    const profile = doorWindowByType[o.type];
    if (!profile) throw new Error(`openings.json: ${o.id} が未知のtype「${o.type}」を参照している`);
    const parts = [`id:${str(o.id)}`, `type:${str(o.type)}`, `category:${str(profile.category)}`, `operation:${str(profile.operation)}`, `face:${str(o.face)}`];
    if (o.face === "N" || o.face === "S") parts.push(`lx:${num(o.offset)}`);
    else parts.push(`lz:${num(o.offset)}`);
    if (o.wallX !== undefined) parts.push(`x:${num(o.wallX)}`);
    parts.push(
      `w:${num(o.widthOverride ?? profile.width)}`,
      `h:${num(o.heightOverride ?? profile.height)}`,
      `sill:${num(o.sillOverride ?? profile.sill)}`,
      `level:${o.level}`,
    );
    if (o.hingeSide) parts.push(`hingeSide:${str(o.hingeSide)}`);
    if (o.swingDir) parts.push(`swingDir:${str(o.swingDir)}`);
    if (o.slideDir) parts.push(`slideDir:${str(o.slideDir)}`);
    parts.push(`label:${str(o.label)}`);
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
  const rows = interiorDoors.items.map((d) => {
    const profile = doorWindowByType[d.type];
    if (!profile) throw new Error(`interior-doors.json: ${d.id} が未知のtype「${d.type}」を参照している`);
    const parts = [
      `id:${str(d.id)}`, `type:${str(d.type)}`, `operation:${str(profile.operation)}`, `label:${str(d.label)}`, `wallAt:${num(d.wallAt)}`,
      `orientation:${str(d.orientation)}`, `center:${num(d.center)}`,
      `width:${num(d.widthOverride ?? profile.width)}`,
      `height:${num(d.heightOverride ?? profile.height)}`,
      `floor:${d.floor}`,
    ];
    if (d.hingeSide) parts.push(`hingeSide:${str(d.hingeSide)}`);
    if (d.swingDir) parts.push(`swingDir:${str(d.swingDir)}`);
    if (d.slideDir) parts.push(`slideDir:${str(d.slideDir)}`);
    return withNote(`  { ${parts.join(", ")} },`, d.note);
  });
  return `const INTERIOR_DOORS = [\n${rows.join("\n")}\n];`;
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
      if (r.kind === "gable") {
        const zRidge = (fp.z0 + fp.z1) / 2;
        const fields = [
          `id:${str(r.id)}`, `kind:${str(r.kind)}`,
          `x0:${num(fp.x0 - r.eaveGableEnd)}`, `x1:${num(fp.x1 + r.eaveGableEnd)}`,
          `zNorth:${num(fp.z0 - r.eaveLongSide)}`, `zRidge:${num(zRidge)}`, `zSouth:${num(fp.z1 + r.eaveLongSide)}`,
          `yEave:${num(house.levels.eave2)}`, `yRidge:${num(house.levels.ridge)}`,
          `thickness:${num(r.thickness)}`,
        ];
        return `  { ${fields.join(", ")} }`;
      }
      const fields = [
        `id:${str(r.id)}`, `kind:${str(r.kind ?? "lean_to")}`,
        `x0:${num(fp.x0)}`, `x1:${num(fp.x1)}`,
        `zNorth:${num(r.zNorth)}`, `zSouth:${num(r.zSouth)}`,
        `pitch:${num(r.pitch)}`, `thickness:${num(r.thickness)}`, `base:${num(r.baseAtZMinus0_5)}`,
      ];
      return `  { ${fields.join(", ")} }`;
    })
    .join(",\n");
  return `const ROOFS = [\n${rows}\n];`;
}

function buildWalls() {
  const rows = house.walls
    .map((w) => `  { id:${str(w.id)}, level:${w.level}, x0:${num(w.x0)}, x1:${num(w.x1)}, z0:${num(w.z0)}, z1:${num(w.z1)}, orientation:${str(w.orientation)} }`)
    .join(",\n");
  return `const WALLS = [\n${rows}\n];`;
}

function buildFurnitureCatalog() {
  const rows = furnitureCatalog.types
    .map((t) => `  ${str(t.type)}: { label:${str(t.label)}, category:${str(t.category)}, shape:${str(t.shape)}, width:${num(t.width)}, depth:${num(t.depth)}, height:${num(t.height)}, clearance:${num(t.clearance)} }`)
    .join(",\n");
  return `const FURNITURE_CATALOG = {\n${rows}\n};`;
}

function buildFurnitureItems() {
  const byType = Object.fromEntries(furnitureCatalog.types.map((t) => [t.type, t]));
  const rows = furniture.items.map((item) => {
    const profile = byType[item.type];
    if (!profile) throw new Error(`furniture.json: ${item.id} が未知のtype「${item.type}」を参照している`);
    const fields = [
      `id:${str(item.id)}`, `type:${str(item.type)}`, `level:${item.level}`,
      `x:${num(item.x)}`, `z:${num(item.z)}`, `rotation:${item.rotation}`,
      `width:${num(item.widthOverride ?? profile.width)}`,
      `depth:${num(item.depthOverride ?? profile.depth)}`,
      `height:${num(item.heightOverride ?? profile.height)}`,
      `label:${str(item.label ?? profile.label)}`,
      `status:${str(item.status)}`,
    ];
    if (item.room) fields.push(`room:${str(item.room)}`);
    return withNote(`  { ${fields.join(", ")} },`, item.note);
  });
  return `const FURNITURE_ITEMS = [\n${rows.join("\n")}\n];`;
}

const banner = `// ============================================================================
// 自動生成ファイル。手で編集しないこと。
// 生成元: data/house.json / data/furniture-catalog.json / data/furniture.json /
//        data/door-catalog.json / data/window-catalog.json / data/openings.json / data/interior-doors.json
//        （このリポジトリの正本）
// 生成コマンド: node scripts/build-web-data.mjs
// これらのJSONを編集したら、このファイルを再生成してからブラウザで確認すること。
// ============================================================================`;

const CEIL_H = `const CEIL_H = ${num(house.defaults.ceilingHeight)}; // ${house.defaults.ceilingHeightStatus === "estimated" ? "推測値（要確認）" : house.defaults.ceilingHeightStatus}`;
const WALL_T = `const WALL_T = ${num(house.defaults.wallThickness)};`;
const INTERIOR_WALL_T = `const INTERIOR_WALL_T = ${num(house.defaults.interiorWallThickness ?? 0.06)};`;

const output = [
  banner,
  buildLevels(),
  CEIL_H,
  WALL_T,
  INTERIOR_WALL_T,
  "",
  buildFloor1(),
  buildFloor2(),
  "",
  buildDoorWindowCatalog(),
  "",
  buildOpenings(),
  "",
  buildSoundWall(),
  "",
  buildInteriorDoors(),
  "",
  buildWalls(),
  "",
  buildRoomsApprox(),
  "",
  buildRoofs(),
  "",
  buildFurnitureCatalog(),
  "",
  buildFurnitureItems(),
  "",
].join("\n");

if (mode === "--check") {
  // Windowsのgit checkoutはCRLFに変換することがあるため、改行コードの違いだけで
  // 誤ってSTALE判定しないよう正規化してから比較する。
  const normalize = (s) => (s == null ? s : s.replace(/\r\n/g, "\n"));
  const current = fs.existsSync(outPath) ? fs.readFileSync(outPath, "utf8") : null;
  if (normalize(current) === normalize(output)) {
    console.log("generated/house-data.js is up to date with data/house.json / furniture-catalog.json / furniture.json / door-catalog.json / window-catalog.json / openings.json / interior-doors.json.");
    process.exit(0);
  }
  console.error("generated/house-data.js is STALE. Run: node scripts/build-web-data.mjs");
  process.exit(1);
}

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, output, "utf8");
console.log(`Wrote ${path.relative(root, outPath)} from data/house.json / furniture-catalog.json / furniture.json / door-catalog.json / window-catalog.json / openings.json / interior-doors.json.`);
