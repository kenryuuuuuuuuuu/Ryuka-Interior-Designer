/**
 * 電気工事の見積書（天領住宅、電灯配線41／コンセント25／専用コンセント25／
 * AC専用6／IH用2／防水コンセント3／スイッチ片切29／3路16(8組)／TV4／
 * インターホン2／分電盤1＝合計154箇所）に基づき、施主指示の部屋別配分を
 * 実際の壁・部屋データへ機械的に割り付け、data/electrical.json を丸ごと
 * 書き換える一回限りの生成スクリプト（たたき台）。
 *
 * 再実行すると data/electrical.json の内容（Web UI編集を書き出したものも含む）を
 * 完全に上書きするので注意。実行後は必ず次を実行すること：
 *   node scripts/build-web-data.mjs
 *   python tests/validate_electrical.py
 *
 * 使い方: node scripts/seed-electrical.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const house = JSON.parse(fs.readFileSync(path.join(root, "data", "house.json"), "utf8"));
const catalog = JSON.parse(fs.readFileSync(path.join(root, "data", "electrical-catalog.json"), "utf8"));
const interiorWalls = JSON.parse(fs.readFileSync(path.join(root, "generated", "interior-walls.json"), "utf8")).walls;
const exteriorWalls = JSON.parse(fs.readFileSync(path.join(root, "generated", "exterior-walls.json"), "utf8")).walls;

const CATALOG = Object.fromEntries(catalog.types.map((t) => [t.type, t]));
const roomsById = Object.fromEntries(house.rooms.map((r) => [r.id, r]));

function round2(n) {
  return Math.round(n * 100) / 100;
}
function bbox(polygon) {
  const xs = polygon.map((p) => p[0]);
  const zs = polygon.map((p) => p[1]);
  return { x0: Math.min(...xs), x1: Math.max(...xs), z0: Math.min(...zs), z1: Math.max(...zs) };
}
function roomArea(polygon) {
  let a = 0;
  for (let i = 0; i < polygon.length; i++) {
    const [x1, z1] = polygon[i];
    const [x2, z2] = polygon[(i + 1) % polygon.length];
    a += x1 * z2 - x2 * z1;
  }
  return Math.abs(a) / 2;
}
function pointInPolygon(x, z, pts) {
  let inside = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, zi] = pts[i], [xj, zj] = pts[j];
    const intersect = zi > z !== zj > z && x < ((xj - xi) * (z - zi)) / (zj - zi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}
function centroid(polygon) {
  let x = 0, z = 0;
  polygon.forEach(([px, pz]) => { x += px; z += pz; });
  return { x: x / polygon.length, z: z / polygon.length };
}
// N点をbbox内に分散配置する。1点なら中心、複数なら長辺方向に等間隔で並べる
// （短辺は中心のまま）。L字部屋のはみ出しはplaceCeilingItem側でpointInPolygon
// チェック＋centroidフォールバックにより補正する
function distributePoints(n, b) {
  const cx = (b.x0 + b.x1) / 2, cz = (b.z0 + b.z1) / 2;
  const w = b.x1 - b.x0, d = b.z1 - b.z0;
  if (n <= 1) return [{ x: cx, z: cz }];
  const alongX = w >= d;
  const span = (alongX ? w : d) * 0.5; // 全長の50%の範囲に等間隔で分散（端に寄りすぎないよう余白を持たせる）
  const pts = [];
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const off = (t - 0.5) * span;
    pts.push(alongX ? { x: cx + off, z: cz } : { x: cx, z: cz + off });
  }
  return pts;
}

// ============================================================================
// 154箇所の部屋別配分。見積書の各項目・合計と一致するよう検算済み
// （C:\Users\Kenryu\AppData\Local\Temp\claude\...\scratchpad\allocate_electrical.py
// で生成したものをそのまま埋め込んでいる）
// ============================================================================
const ALLOC = {
  light: {
    "room-1f-01": 1, "room-1f-02": 1, "room-1f-24": 1, "room-1f-03": 1, "room-1f-04": 1,
    "room-1f-05": 1, "room-1f-23": 1, "room-1f-06": 2, "room-1f-07": 1, "room-1f-08": 1,
    "room-1f-19": 1, "room-1f-09": 1, "room-1f-20": 1, "room-1f-10": 2, "room-1f-21": 1,
    "room-1f-11": 3, "room-1f-12": 2, "room-1f-13": 1, "room-1f-22": 1, "room-1f-14": 1,
    "room-1f-15": 1, "room-1f-16": 1, "room-1f-17": 1, "room-1f-18": 1,
    "room-2f-01": 1, "room-2f-02": 1, "room-2f-03": 2, "room-2f-04": 1, "room-2f-07": 1,
    "room-2f-05": 1, "room-2f-08": 1, "room-2f-06": 1, "room-2f-09": 1,
  },
  light_exterior: 2,
  outlet_general: {
    "room-1f-05": 3, "room-1f-06": 3, "room-1f-07": 1, "room-1f-08": 1, "room-1f-11": 5,
    "room-1f-12": 1, "room-1f-13": 1,
    "room-2f-03": 1, "room-2f-04": 2, "room-2f-05": 2, "room-2f-06": 3, "room-2f-09": 2,
  },
  outlet_dedicated: {
    "room-1f-01": 1, "room-1f-03": 1, "room-1f-04": 1, "room-1f-05": 1, "room-1f-06": 5,
    "room-1f-11": 5, "room-1f-12": 1, "room-1f-14": 1, "room-1f-16": 1, "room-1f-17": 1,
    "room-1f-20": 1, "room-1f-21": 1,
    "room-2f-01": 1, "room-2f-04": 1, "room-2f-05": 1, "room-2f-06": 1, "room-2f-09": 1,
  },
  outlet_ac: {
    "room-1f-05": 1, "room-1f-06": 1, "room-1f-11": 1,
    "room-2f-04": 1, "room-2f-05": 1, "room-2f-06": 1,
  },
  outlet_ih: { "room-1f-06": 1, "room-1f-11": 1 },
  outlet_waterproof_exterior: 3,
  switch_3way_pairs: [
    ["room-1f-10", "room-2f-02"],
    ["room-1f-13", "room-1f-13"],
    ["room-2f-03", "room-2f-03"],
    ["room-2f-06", "room-2f-06"],
    ["room-1f-11", "room-1f-11"],
    ["room-1f-06", "room-1f-06"],
    ["room-1f-05", "room-1f-05"],
    ["room-1f-19", "room-1f-08"],
  ],
  switch_1p: {
    "room-1f-01": 1, "room-1f-02": 1, "room-1f-24": 1, "room-1f-03": 2, "room-1f-04": 1,
    "room-1f-23": 1, "room-1f-06": 1, "room-1f-07": 1, "room-1f-09": 1, "room-1f-20": 1,
    "room-1f-10": 1, "room-1f-21": 1, "room-1f-11": 1, "room-1f-12": 2, "room-1f-22": 1,
    "room-1f-14": 1, "room-1f-15": 1, "room-1f-16": 2, "room-1f-17": 1, "room-1f-18": 1,
    "room-2f-01": 1, "room-2f-04": 1, "room-2f-07": 1, "room-2f-05": 1, "room-2f-08": 1,
    "room-2f-09": 1,
  },
  tv: { "room-1f-06": 1, "room-1f-11": 1, "room-2f-06": 1, "room-2f-04": 1 },
  intercom: { "room-1f-02": 1, "room-1f-08": 1 },
  distribution_board: { "room-1f-20": 1 },
};

// ============================================================================
// 壁付けアイテムの配置：部屋ごとに使える壁セグメントを集める。内壁・外壁のいずれも、
// 壁データ（generated/interior-walls.json・exterior-walls.json）1件が複数の部屋に
// またがっていることがあるため（内壁は3部屋以上が同じ直線に並ぶ通し壁をmergeCollinearWalls()で
// 1本にまとめる仕様、外壁はそもそも建物外周の連続した1本）、壁データのfrom/toをそのまま
// 使わず、必ず部屋自身のポリゴンの辺のうちその壁の直線上にある区間だけへ切り詰める。
// 2026-08-20、施主報告により発覚：切り詰めていなかったため154件中53件が意図した部屋の
// 外（隣室・別室）に配置されてしまっていた
// ============================================================================
function wallSegmentsForRoom(room) {
  const segs = [];
  const poly = room.polygon;
  const addClipped = (walls) => {
    walls.forEach((w) => {
      const wAt = w.orientation === "H" ? w.z0 : w.x0;
      const wFrom = w.orientation === "H" ? w.x0 : w.z0;
      const wTo = w.orientation === "H" ? w.x1 : w.z1;
      for (let i = 0; i < poly.length; i++) {
        const [x1, z1] = poly[i];
        const [x2, z2] = poly[(i + 1) % poly.length];
        if (w.orientation === "H" && Math.abs(z1 - z2) < 0.001 && Math.abs(z1 - wAt) < 0.01) {
          const lo = Math.max(Math.min(x1, x2), wFrom), hi = Math.min(Math.max(x1, x2), wTo);
          if (hi - lo > 0.01) segs.push({ orientation: "H", at: wAt, from: lo, to: hi });
        }
        if (w.orientation === "V" && Math.abs(x1 - x2) < 0.001 && Math.abs(x1 - wAt) < 0.01) {
          const lo = Math.max(Math.min(z1, z2), wFrom), hi = Math.min(Math.max(z1, z2), wTo);
          if (hi - lo > 0.01) segs.push({ orientation: "V", at: wAt, from: lo, to: hi });
        }
      }
    });
  };
  addClipped(interiorWalls.filter((w) => w.level === room.level && w.sourceRooms.includes(room.label)));
  addClipped(exteriorWalls.filter((w) => w.level === room.level));
  return segs;
}

const items = [];
let seq = 0;
function nextId() {
  seq += 1;
  return `elec-${String(seq).padStart(3, "0")}`;
}
// 部屋+型ごとに生成したアイテムを覚えておき、後から「同室・同型が複数あれば連番を振る」
// （docs/ARCHITECTURE.mdの家具ラベル命名規則と同じ考え方）
const roomLabelGroups = new Map(); // roomId -> Map(type -> item[])
function trackForLabeling(roomId, item) {
  if (!roomId) return;
  if (!roomLabelGroups.has(roomId)) roomLabelGroups.set(roomId, new Map());
  const byType = roomLabelGroups.get(roomId);
  if (!byType.has(item.type)) byType.set(item.type, []);
  byType.get(item.type).push(item);
}

const roomWallState = new Map(); // roomId -> { segs, cursors, nextSegIdx }（同室内の全カテゴリで共有し重なりを防ぐ）
function getRoomWallState(room) {
  if (!roomWallState.has(room.id)) {
    const segs = wallSegmentsForRoom(room);
    roomWallState.set(room.id, { segs, cursors: segs.map(() => null), nextSegIdx: 0 });
  }
  return roomWallState.get(room.id);
}

// 壁のどちら側が部屋の内側かを判定する。以前は部屋全体のbbox中心と壁の座標を比較する
// 単純な方法だったが、L字・凹型の部屋では、bbox中心から見た方向と、細い張り出し部分の
// 壁から見た実際の室内方向が逆になることがあり、隣室側を向いて配置されてしまっていた
// （2026-08-20、施主報告により発覚）。壁の両側をポリゴンの内外判定で直接調べる方式にする
function sideForSegment(room, seg, along) {
  const probeOffset = 0.1;
  const p1 = seg.orientation === "H" ? [along, seg.at + probeOffset] : [seg.at + probeOffset, along];
  if (pointInPolygon(p1[0], p1[1], room.polygon)) return 1;
  const p2 = seg.orientation === "H" ? [along, seg.at - probeOffset] : [seg.at - probeOffset, along];
  if (pointInPolygon(p2[0], p2[1], room.polygon)) return -1;
  // ポリゴン境界ぎりぎりで丸め誤差により両方falseになった場合のフォールバック
  const b = bbox(room.polygon);
  const roomCenterX = (b.x0 + b.x1) / 2, roomCenterZ = (b.z0 + b.z1) / 2;
  return (seg.orientation === "H" ? roomCenterZ : roomCenterX) > seg.at ? 1 : -1;
}

function placeWallItems(room, catalogType, count) {
  if (count <= 0) return;
  const profile = CATALOG[catalogType];
  const state = getRoomWallState(room);
  const { segs, cursors } = state;
  if (segs.length === 0) {
    console.error(`WARN: ${room.id}(${room.label}) に壁セグメントが見つからない。type=${catalogType} count=${count}件をスキップ`);
    return;
  }
  for (let i = 0; i < count; i++) {
    const segIdx = state.nextSegIdx % segs.length;
    state.nextSegIdx += 1;
    const seg = segs[segIdx];
    const margin = profile.width / 2 + 0.05;
    let center = cursors[segIdx] === null ? seg.from + margin : cursors[segIdx];
    if (center + margin > seg.to) center = Math.max(seg.from + margin, Math.min(seg.to - margin, (seg.from + seg.to) / 2));
    cursors[segIdx] = center + profile.width + 0.4;
    const side = sideForSegment(room, seg, center);
    const item = {
      id: nextId(), type: catalogType, level: room.level,
      wallAt: round2(seg.at), orientation: seg.orientation, center: round2(center), side,
      label: profile.label, status: "estimated",
    };
    items.push(item);
    trackForLabeling(room.id, item);
  }
}

function placeCeilingItem(room, catalogType, x, z) {
  const profile = CATALOG[catalogType];
  let px = x, pz = z;
  if (room.polygon.length > 4 && !pointInPolygon(px, pz, room.polygon)) {
    const c = centroid(room.polygon);
    px = c.x; pz = c.z;
  }
  const item = {
    id: nextId(), type: catalogType, level: room.level,
    x: round2(px), z: round2(pz), room: room.id, label: profile.label, status: "estimated",
  };
  items.push(item);
  trackForLabeling(room.id, item);
}

// ---- 照明（41箇所） ----
// 民泊LDK・自宅LDKは「主照明＋ダイニング上のペンダント（＋自宅LDKはキッチン上に
// もう1灯）」という具体的な構成にする。他の複数灯の部屋は「1灯目は主照明
// （面積5m2以上ならシーリング、未満ならダウンライト）、2灯目以降はダウンライト」
// という単純なルールで割り付ける
const LIGHT_TYPE_OVERRIDES = {
  "room-1f-06": ["light-ceiling", "light-pendant"],
  "room-1f-11": ["light-ceiling", "light-pendant", "light-downlight"],
};
Object.entries(ALLOC.light).forEach(([roomId, count]) => {
  if (count <= 0) return;
  const room = roomsById[roomId];
  const b = bbox(room.polygon);
  const area = roomArea(room.polygon);
  const pts = distributePoints(count, b);
  const overrideTypes = LIGHT_TYPE_OVERRIDES[roomId];
  pts.forEach((p, i) => {
    const type = overrideTypes ? overrideTypes[i] : (i === 0 && area >= 5 ? "light-ceiling" : "light-downlight");
    placeCeilingItem(room, type, p.x, p.z);
  });
});

// ---- コンセント一般（25箇所、outlet-double） ----
Object.entries(ALLOC.outlet_general).forEach(([roomId, count]) => placeWallItems(roomsById[roomId], "outlet-double", count));

// ---- 専用コンセント（25箇所、outlet-grounded＝アース付。冷蔵庫・洗濯機・レンジ等の
// 専用回路をまとめて表現する） ----
Object.entries(ALLOC.outlet_dedicated).forEach(([roomId, count]) => placeWallItems(roomsById[roomId], "outlet-grounded", count));

// ---- AC専用コンセント（6箇所） ----
Object.entries(ALLOC.outlet_ac).forEach(([roomId, count]) => placeWallItems(roomsById[roomId], "outlet-ac", count));

// ---- IH用コンセント（2箇所） ----
Object.entries(ALLOC.outlet_ih).forEach(([roomId, count]) => placeWallItems(roomsById[roomId], "outlet-ih", count));

// ---- スイッチ：3路（16箇所＝8組、両端をそれぞれ配置） ----
ALLOC.switch_3way_pairs.forEach(([roomIdA, roomIdB]) => {
  placeWallItems(roomsById[roomIdA], "switch-3way", 1);
  placeWallItems(roomsById[roomIdB], "switch-3way", 1);
});

// ---- スイッチ：片切（29箇所） ----
Object.entries(ALLOC.switch_1p).forEach(([roomId, count]) => placeWallItems(roomsById[roomId], "switch-1p", count));

// ---- TV配線（4箇所） ----
Object.entries(ALLOC.tv).forEach(([roomId, count]) => placeWallItems(roomsById[roomId], "data-tv", count));

// ---- インターホン（2箇所） ----
Object.entries(ALLOC.intercom).forEach(([roomId, count]) => placeWallItems(roomsById[roomId], "data-intercom", count));

// ---- 分電盤（1箇所） ----
Object.entries(ALLOC.distribution_board).forEach(([roomId, count]) => placeWallItems(roomsById[roomId], "equip-distribution-board", count));

// ---- 屋外：外灯2箇所（民泊棟・自宅それぞれの玄関脇、N面）＋防水コンセント3箇所（南面） ----
// 玄関ドアの位置（民泊: face N offset 0.91、自宅: face N offset 9.54、いずれも
// data/openings.jsonより）から少し離した位置に配置する
items.push({ id: nextId(), type: "light-exterior", level: 1, face: "N", offset: 2.0, label: CATALOG["light-exterior"].label + " 1", status: "estimated", note: "民泊棟 玄関脇" });
items.push({ id: nextId(), type: "light-exterior", level: 1, face: "N", offset: 11.5, label: CATALOG["light-exterior"].label + " 2", status: "estimated", note: "自宅 玄関脇" });
items.push({ id: nextId(), type: "outlet-waterproof", level: 1, face: "S", offset: 3.0, label: CATALOG["outlet-waterproof"].label + " 1", status: "estimated", note: "民泊LDK南面" });
items.push({ id: nextId(), type: "outlet-waterproof", level: 1, face: "S", offset: 10.0, label: CATALOG["outlet-waterproof"].label + " 2", status: "estimated", note: "自宅LDK南面（西寄り）" });
items.push({ id: nextId(), type: "outlet-waterproof", level: 1, face: "S", offset: 17.5, label: CATALOG["outlet-waterproof"].label + " 3", status: "estimated", note: "南土間付近" });

// ---- 同室・同型が複数ある場合は連番を振る（家具ラベルの命名規則と同じ考え方） ----
roomLabelGroups.forEach((byType) => {
  byType.forEach((arr) => {
    if (arr.length > 1) arr.forEach((it, i) => { it.label = `${it.label} ${i + 1}`; });
  });
});

const payload = {
  schemaVersion: "1.0.0",
  units: "m",
  note: "電気設備の配置インスタンス。typeはdata/electrical-catalog.jsonのtypeを参照する。mount:wallの型はwallAt+orientation+center+side（wallAt=壁の固定座標、centerは壁沿いの位置、side=+1/-1で壁のどちら側を向くか）、mount:ceiling/floorの型はx+z（footprint内の自由座標、furniture.jsonと同じ）、mount:exteriorの型はface+offset+level（data/openings.jsonと同じ規約）で位置を表す。施工会社の見積書（電気工事）の項目・数量に基づき、scripts/seed-electrical.mjsで機械的に配置したたたき台（status:estimated）。実際の生活動線に基づく判断は入っていないため、俯瞰モードの部屋フォーカス機能で確認しながら位置を調整すること。ブラウザの配置編集機能（俯瞰モード限定）で編集した内容は「electrical.jsonを書き出す」ボタンでダウンロードし、このファイルへ上書きしてコミットする運用。",
  items,
};

const outPath = path.join(root, "data", "electrical.json");
fs.writeFileSync(outPath, JSON.stringify(payload, null, 2) + "\n", "utf8");
console.log(`Wrote ${path.relative(root, outPath)}: ${items.length} items (target: 154).`);
console.log("Next: node scripts/build-web-data.mjs && python tests/validate_electrical.py");
