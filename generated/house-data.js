// ============================================================================
// 自動生成ファイル。手で編集しないこと。
// 生成元: data/house.json / data/furniture-catalog.json / data/furniture.json /
//        data/door-catalog.json / data/window-catalog.json / data/openings.json / data/interior-doors.json
//        （このリポジトリの正本）
// 生成コマンド: node scripts/build-web-data.mjs
// これらのJSONを編集したら、このファイルを再生成してからブラウザで確認すること。
// ============================================================================
const LEVELS = { gl:0, fl1:0.707, fl2:3.439, eaveLow:3.4, eaveHigh:4.567, eave2:6.3, ridge:7.423 };
const CEIL_H = 2.4; // 推測値（要確認）
const WALL_T = 0.12;
const INTERIOR_WALL_T = 0.06;

const FLOOR1 = [
  { id:'1f-a1', x0:0, x1:9.1, z0:0.91, z1:6.37, use:'民泊棟（玄関・洋室・LDK・水回り）' },
  { id:'1f-a2', x0:9.1, x1:12.74, z0:0.455, z1:6.37, use:'ヌック・自宅玄関・北土間' },
  { id:'1f-a3', x0:12.74, x1:16.38, z0:0, z1:6.37, use:'自宅LDK・階段' },
  { id:'1f-a4', x0:16.38, x1:19.11, z0:0, z1:7.735, use:'水回り・南土間' }
];
const FLOOR2 = { x0:12.74, x1:19.11, z0:0, z1:6.37 };

const DOOR_WINDOW_CATALOG = {
  'door-entrance': { label:'玄関ドア', category:'door', operation:'swing', width:0.95, height:2.33, sill:0 },
  'door-hinged': { label:'室内開き戸', category:'door', operation:'swing', width:0.8, height:2, sill:0 },
  'door-hinged-wide': { label:'室内開き戸（広幅）', category:'door', operation:'swing', width:0.91, height:2, sill:0 },
  'door-louver': { label:'ルーバー戸', category:'door', operation:'swing', width:0.85, height:2.33, sill:0 },
  'door-double-swing': { label:'両開き戸', category:'door', operation:'double-swing', width:0.91, height:2, sill:0 },
  'door-fold': { label:'片開き折れ戸', category:'door', operation:'fold', width:0.91, height:2, sill:0 },
  'door-double-fold': { label:'両開き折れ戸', category:'door', operation:'double-fold', width:1.82, height:2, sill:0 },
  'door-slide': { label:'引き戸', category:'door', operation:'slide', width:0.8, height:2, sill:0 },
  'door-open': { label:'開口', category:'door', operation:'open', width:0.91, height:2, sill:0 },
  'door-open-arch': { label:'開口（アーチ）', category:'door', operation:'open-arch', width:0.91, height:2.1, sill:0, archRise:0.3 },
  'window-waist': { label:'腰窓', category:'window', operation:'openable', width:1.7, height:1, sill:1.25 },
  'window-full': { label:'掃き出し窓', category:'window', operation:'openable', width:1.73, height:2.26, sill:0.19 },
  'window-small': { label:'小窓', category:'window', operation:'openable', width:0.7, height:0.9, sill:1.3 },
  'window-fixed-small': { label:'小窓（FIX）', category:'window', operation:'fixed', width:0.7, height:0.5, sill:1.9 },
  'window-fixed-high': { label:'高窓（FIX）', category:'window', operation:'fixed', width:0.8, height:0.4, sill:2 }
};

const OPENINGS = [
  { id:'op-001', type:'door-entrance', category:'door', operation:'swing', face:'N', lx:0.91, w:0.95, h:2.33, sill:0, level:1, hingeSide:'L', swingDir:'out', label:'民泊 玄関ドア', status:'verified' },
  { id:'op-002', type:'window-waist', category:'window', operation:'openable', face:'N', lx:3.5, w:1.76, h:1.03, sill:1.33, level:1, label:'民泊 北窓', status:'verified' },
  { id:'op-003', type:'door-entrance', category:'door', operation:'swing', face:'N', lx:9.54, w:0.95, h:2.33, sill:0, level:1, hingeSide:'L', swingDir:'out', label:'自宅 玄関ドア', status:'verified' },
  { id:'op-004', type:'window-fixed-small', category:'window', operation:'fixed', face:'N', lx:11.05, w:0.71, h:1, sill:1, level:1, label:'土間 フィックス窓', status:'estimated' },
  { id:'op-005', type:'window-fixed-high', category:'window', operation:'fixed', face:'N', lx:13.7, w:1.72, h:0.45, sill:1.97, level:2, label:'2階 階段北窓', status:'verified' },
  { id:'op-006', type:'window-waist', category:'window', operation:'openable', face:'S', lx:2.79, w:1.77, h:1.03, sill:1.22, level:1, label:'民泊 腰窓', status:'verified' },
  { id:'op-007', type:'window-fixed-small', category:'window', operation:'fixed', face:'S', lx:5.66, w:0.7, h:0.56, sill:1.69, level:1, label:'民泊 小窓', status:'verified' },
  { id:'op-008', type:'window-waist', category:'window', operation:'openable', face:'S', lx:8.22, w:1.8, h:1.03, sill:1.25, level:1, label:'自宅 腰窓', status:'verified' },
  { id:'op-009', type:'window-small', category:'window', operation:'openable', face:'S', lx:10.01, w:0.7, h:0.96, sill:1.29, level:1, label:'自宅 小窓（西）', status:'verified' },
  { id:'op-010', type:'window-full', category:'window', operation:'openable', face:'S', lx:11.01, w:1.73, h:2.26, sill:0.19, level:1, label:'自宅LDK 掃き出し窓', status:'verified' },
  { id:'op-011', type:'window-small', category:'window', operation:'openable', face:'S', lx:14.04, w:0.7, h:0.96, sill:1.29, level:1, label:'自宅 小窓（東）', status:'verified' },
  { id:'op-012', type:'window-waist', category:'window', operation:'openable', face:'S', lx:13.68, w:1.57, h:0.96, sill:1.32, level:2, label:'2階 南窓①(子供部屋1)', status:'verified' },
  { id:'op-013', type:'window-waist', category:'window', operation:'openable', face:'S', lx:16.38, w:1.77, h:0.96, sill:1.32, level:2, label:'2階 南窓②(夫婦寝室)', status:'verified' },
  { id:'op-014', type:'window-waist', category:'window', operation:'openable', face:'E', lz:0.92, w:1.62, h:0.97, sill:1.28, level:2, label:'2階 東窓①(子供部屋2)', status:'verified' },
  { id:'op-015', type:'window-waist', category:'window', operation:'openable', face:'E', lz:3.75, w:1.46, h:0.97, sill:1.28, level:2, label:'2階 東窓②(夫婦寝室)', status:'verified' },
  { id:'op-016', type:'window-fixed-high', category:'window', operation:'fixed', face:'E', lz:2.79, w:0.81, h:0.36, sill:2.23, level:1, label:'1階 東の細長窓', status:'verified' },
  { id:'op-017', type:'door-louver', category:'door', operation:'swing', face:'E', lz:6.41, w:0.85, h:2.33, sill:0, level:1, hingeSide:'L', swingDir:'out', label:'南土間 東のルーバー戸', status:'verified' },
  { id:'op-018', type:'window-fixed-small', category:'window', operation:'fixed', face:'W', lz:1.95, x:12.74, w:0.65, h:0.6, sill:1.86, level:2, label:'2階 廊下西窓', status:'verified' },
  { id:'op-019', type:'window-fixed-high', category:'window', operation:'fixed', face:'W', lz:3.2, w:0.85, h:0.35, sill:2, level:1, label:'洗面脱衣室 天井近くフィックス窓', status:'verified' },
];

const SOUND_WALL = { x:7.28, z0:0.91, z1:6.37, level:1, topY:LEVELS.eaveLow }; // 西端から7,280mm(910mm×8マス)。施主指摘により修正（2026-08-13）

const INTERIOR_DOORS = [
  { id:'door-001', type:'door-slide', category:'door', operation:'slide', label:'トイレ⟷玄関', orientation:'V', wallAt:0.91, center:2.33, width:0.8, height:2, floor:1, slideDir:'L', status:'verified' },
  { id:'door-002', type:'door-hinged', category:'door', operation:'swing', label:'玄関⟷洗面脱衣室', orientation:'H', wallAt:2.73, center:2.26, width:0.8, height:2, floor:1, hingeSide:'L', swingDir:'out', status:'verified' },
  { id:'door-003', type:'door-hinged', category:'door', operation:'swing', label:'洗面脱衣室⟷UB', orientation:'H', wallAt:4.55, center:1.37, width:0.8, height:2, floor:1, hingeSide:'R', swingDir:'out', status:'verified' },
  { id:'door-004', type:'door-hinged', category:'door', operation:'swing', label:'玄関⟷LDK張り出し', orientation:'H', wallAt:2.73, center:1.38, width:0.8, height:2, floor:1, hingeSide:'R', swingDir:'out', status:'verified' },
  { id:'door-005', type:'door-slide', category:'door', operation:'slide', label:'玄関⟷洋室', orientation:'V', wallAt:2.73, center:2.27, width:0.8, height:2, floor:1, slideDir:'R', status:'verified' },
  { id:'door-006', type:'door-open-arch', category:'door', operation:'open-arch', label:'ヌック⟷LDK', orientation:'H', wallAt:2.73, center:8.22, width:0.91, height:2.1, floor:1, status:'verified' },
  { id:'door-007', type:'door-hinged', category:'door', operation:'swing', label:'自宅玄関・ホール⟷LDK', orientation:'H', wallAt:2.73, center:9.56, width:0.8, height:2, floor:1, hingeSide:'L', swingDir:'in', status:'verified' },
  { id:'door-008', type:'door-hinged-wide', category:'door', operation:'swing', label:'自宅玄関⟷土間', orientation:'V', wallAt:10.92, center:0.94, width:0.91, height:2, floor:1, hingeSide:'L', swingDir:'out', status:'verified' },
  { id:'door-009', type:'door-slide', category:'door', operation:'slide', label:'SC⟷LDK', orientation:'H', wallAt:2.275, center:13.2, width:0.8, height:2, floor:1, slideDir:'L', status:'verified' },
  { id:'door-010', type:'door-slide', category:'door', operation:'slide', label:'LDK(キッチン部)⟷廊下', orientation:'V', wallAt:15.471, center:2.28, width:0.8, height:2, floor:1, slideDir:'R', status:'verified' },
  { id:'door-011', type:'door-slide', category:'door', operation:'slide', label:'ファミリークローク⟷廊下', orientation:'H', wallAt:1.82, center:16, width:0.8, height:2, floor:1, slideDir:'R', status:'verified' },
  { id:'door-012', type:'door-hinged-wide', category:'door', operation:'swing', label:'トイレ(東)⟷洗面(東)', orientation:'H', wallAt:2.73, center:17.75, width:0.91, height:2, floor:1, hingeSide:'L', swingDir:'in', status:'verified' },
  { id:'door-013', type:'door-slide', category:'door', operation:'slide', label:'廊下⟷脱衣室', orientation:'H', wallAt:3.64, center:16.84, width:0.8, height:2, floor:1, slideDir:'L', status:'verified' },
  { id:'door-014', type:'door-hinged-wide', category:'door', operation:'swing', label:'脱衣室⟷UB(東)', orientation:'V', wallAt:17.291, center:4.58, width:0.91, height:2, floor:1, hingeSide:'L', swingDir:'out', status:'verified' },
  { id:'door-015', type:'door-hinged-wide', category:'door', operation:'swing', label:'脱衣室⟷南土間', orientation:'H', wallAt:6.37, center:16.83, width:0.91, height:2, floor:1, hingeSide:'L', swingDir:'out', status:'verified' },
  { id:'door-016', type:'door-hinged-wide', category:'door', operation:'swing', label:'トイレ(2F)⟷廊下(2F)', orientation:'H', wallAt:1.82, center:13.27, width:0.7, height:2, floor:2, hingeSide:'L', swingDir:'out', status:'verified' },
  { id:'door-017', type:'door-hinged-wide', category:'door', operation:'swing', label:'廊下(2F)⟷子供部屋1', orientation:'H', wallAt:2.73, center:15.02, width:0.91, height:2, floor:2, hingeSide:'R', swingDir:'out', status:'verified' },
  { id:'door-018', type:'door-hinged-wide', category:'door', operation:'swing', label:'廊下(2F)⟷子供部屋2', orientation:'V', wallAt:16.38, center:2.28, width:0.91, height:2, floor:2, hingeSide:'R', swingDir:'out', status:'verified' },
  { id:'door-019', type:'door-hinged-wide', category:'door', operation:'swing', label:'廊下(2F)⟷夫婦寝室', orientation:'H', wallAt:2.73, center:15.93, width:0.91, height:2, floor:2, hingeSide:'L', swingDir:'out', status:'verified' },
  { id:'door-020', type:'door-open', category:'door', operation:'open', label:'自宅玄関⟷自宅ホール（斜め框）', orientation:'D', x0:9.1, z0:1.365, x1:10.92, z1:1.82, width:0.91, height:2, floor:1, status:'estimated' }, // 新規(2026-08-15)：施主指摘により斜め框（目分量の角度）に、壁のないドアなしの開口として配置。room-1f-08/room-1f-19の境界と一致させること。施主指摘により角度を緩やかに変更後、同じ角度のまま0.455下へ平行移動
  { id:'door-021', type:'door-open', category:'door', operation:'open', label:'土間⟷SC', orientation:'V', wallAt:12.451, center:1.37, width:1.82, height:2, floor:1, status:'estimated' },
  { id:'door-022', type:'door-open', category:'door', operation:'open', label:'階段⟷パントリー', orientation:'H', wallAt:1.82, center:15.02, width:0.91, height:2, floor:1, status:'estimated' },
  { id:'door-023', type:'door-fold', category:'door', operation:'fold', label:'廊下⟷収納', orientation:'H', wallAt:2.73, center:16.84, width:0.91, height:2, floor:1, hingeSide:'L', swingDir:'out', status:'estimated' },
  { id:'door-024', type:'door-double-swing', category:'door', operation:'double-swing', label:'洋室⟷収納', orientation:'V', wallAt:6.37, center:3.01, width:1.25, height:2, floor:1, swingDir:'in', status:'estimated' },
  { id:'door-025', type:'door-open', category:'door', operation:'open', label:'玄関(民泊)⟷ホール(民泊)', orientation:'H', wallAt:1.82, center:1.82, width:1.82, height:2, floor:1, status:'estimated' },
  { id:'door-026', type:'door-double-fold', category:'door', operation:'double-fold', label:'子供部屋1⟷クローゼット', orientation:'H', wallAt:3.64, center:13.65, width:1.82, height:2, floor:2, swingDir:'out', status:'estimated' },
  { id:'door-027', type:'door-double-fold', category:'door', operation:'double-fold', label:'子供部屋2⟷クローゼット', orientation:'V', wallAt:16.38, center:0.91, width:1.82, height:2, floor:2, swingDir:'out', status:'estimated' },
  { id:'door-028', type:'door-open', category:'door', operation:'open', label:'夫婦寝室⟷書斎', orientation:'H', wallAt:3.64, center:17.75, width:2.73, height:2, floor:2, status:'estimated' },
  { id:'door-029', type:'door-open', category:'door', operation:'open', label:'LDK⟷階段', orientation:'H', wallAt:1.82, center:14.106, width:0.91, height:2, floor:1, status:'estimated' }, // 新規(2026-08-15)：階段の実体表現にあたり新設。階段の直進部分（西側柱状部分）はLDKに向けて壁のない開口で開放されているリビング階段として配置。room-1f-10/room-1f-11の境界と一致させること
  { id:'door-030', type:'door-open', category:'door', operation:'open', label:'階段(2F)⟷廊下(2F)', orientation:'H', wallAt:1.82, center:14.5605, width:1.819, height:2, floor:2, status:'estimated' }, // 新規(2026-08-15)：階段の実体表現にあたり新設。2F階段室の全幅を廊下(2F)に向けて壁のない開口で開放。room-2f-02/room-2f-03の境界と一致させること
  { id:'door-031', type:'door-open', category:'door', operation:'open', label:'廊下⟷洗面(東)', orientation:'V', wallAt:17.291, center:3.185, width:0.91, height:2, floor:1, status:'estimated' }, // 新規(2026-08-16)：施主指摘により追加（前回配置し忘れていた）。room-1f-13/room-1f-15の共有区間(z:2.73-3.64、幅0.91)全体を壁のない開口で開放
];

const WALLS = [
  { id:'wall-1f-auto-001', level:1, x0:0.91, x1:0.91, z0:0.91, z1:2.73, orientation:'V' },
  { id:'wall-1f-auto-002', level:1, x0:0, x1:2.73, z0:2.73, z1:2.73, orientation:'H' },
  { id:'wall-1f-auto-003', level:1, x0:7.28, x1:10.92, z0:2.73, z1:2.73, orientation:'H' },
  { id:'wall-1f-auto-004', level:1, x0:16.381, x1:19.11, z0:2.73, z1:2.73, orientation:'H' },
  { id:'wall-1f-auto-005', level:1, x0:0.91, x1:2.73, z0:1.82, z1:1.82, orientation:'H' },
  { id:'wall-1f-auto-006', level:1, x0:13.651, x1:19.11, z0:1.82, z1:1.82, orientation:'H' },
  { id:'wall-1f-auto-007', level:1, x0:2.73, x1:2.73, z0:0.91, z1:3.691, orientation:'V' },
  { id:'wall-1f-auto-008', level:1, x0:0, x1:1.82, z0:4.55, z1:4.55, orientation:'H' },
  { id:'wall-1f-auto-009', level:1, x0:1.82, x1:1.82, z0:2.73, z1:6.37, orientation:'V' },
  { id:'wall-1f-auto-010', level:1, x0:6.37, x1:7.28, z0:2.326, z1:2.326, orientation:'H' },
  { id:'wall-1f-auto-011', level:1, x0:6.37, x1:6.37, z0:2.326, z1:3.691, orientation:'V' },
  { id:'wall-1f-auto-012', level:1, x0:2.73, x1:7.28, z0:3.691, z1:3.691, orientation:'H' },
  { id:'wall-1f-auto-013', level:1, x0:7.28, x1:7.28, z0:0.91, z1:6.37, orientation:'V' },
  { id:'wall-1f-auto-014', level:1, x0:9.1, x1:9.1, z0:0.91, z1:2.73, orientation:'V' },
  { id:'wall-1f-auto-015', level:1, x0:10.92, x1:10.92, z0:0.455, z1:2.73, orientation:'V' },
  { id:'wall-1f-auto-016', level:1, x0:12.451, x1:12.451, z0:0.455, z1:2.275, orientation:'V' },
  { id:'wall-1f-auto-017', level:1, x0:10.92, x1:13.651, z0:2.275, z1:2.275, orientation:'H' },
  { id:'wall-1f-auto-018', level:1, x0:13.651, x1:13.651, z0:0, z1:2.275, orientation:'V' },
  { id:'wall-1f-auto-019', level:1, x0:14.561, x1:15.471, z0:0.91, z1:0.91, orientation:'H' },
  { id:'wall-1f-auto-020', level:1, x0:14.561, x1:14.561, z0:0.91, z1:1.82, orientation:'V' },
  { id:'wall-1f-auto-021', level:1, x0:15.471, x1:15.471, z0:0, z1:6.37, orientation:'V' },
  { id:'wall-1f-auto-022', level:1, x0:16.381, x1:16.381, z0:1.82, z1:2.73, orientation:'V' },
  { id:'wall-1f-auto-023', level:1, x0:17.291, x1:17.291, z0:1.82, z1:6.37, orientation:'V' },
  { id:'wall-1f-auto-024', level:1, x0:15.471, x1:17.291, z0:3.64, z1:3.64, orientation:'H' },
  { id:'wall-1f-auto-025', level:1, x0:17.291, x1:19.11, z0:4.095, z1:4.095, orientation:'H' },
  { id:'wall-1f-auto-026', level:1, x0:16.38, x1:19.11, z0:6.37, z1:6.37, orientation:'H' },
  { id:'wall-2f-auto-001', level:2, x0:13.651, x1:13.651, z0:0, z1:1.82, orientation:'V' },
  { id:'wall-2f-auto-002', level:2, x0:12.74, x1:16.38, z0:1.82, z1:1.82, orientation:'H' },
  { id:'wall-2f-auto-003', level:2, x0:15.47, x1:15.47, z0:0, z1:1.82, orientation:'V' },
  { id:'wall-2f-auto-004', level:2, x0:15.47, x1:15.47, z0:2.73, z1:6.37, orientation:'V' },
  { id:'wall-2f-auto-005', level:2, x0:12.74, x1:19.11, z0:2.73, z1:2.73, orientation:'H' },
  { id:'wall-2f-auto-006', level:2, x0:16.38, x1:16.38, z0:0, z1:3.64, orientation:'V' },
  { id:'wall-2f-auto-007', level:2, x0:12.74, x1:14.56, z0:3.64, z1:3.64, orientation:'H' },
  { id:'wall-2f-auto-008', level:2, x0:16.38, x1:19.11, z0:3.64, z1:3.64, orientation:'H' },
  { id:'wall-2f-auto-009', level:2, x0:14.56, x1:14.56, z0:2.73, z1:3.64, orientation:'V' }
];

const ROOMS_APPROX = {
  1: [
    { name:'トイレ(民泊)', x0:0, x1:0.91, z0:0.91, z1:2.73, conf:'高', note:'面積1.66㎡相当・マイホームクラウド値と一致確認' },
    { name:'玄関(民泊)', x0:0.91, x1:2.73, z0:0.91, z1:1.82, conf:'低', note:'訂正(2026-08-13)：西端(x=0)と東端(x=7.280)を基準とした再キャリブレーションで、玄関の東壁はx=2.730が正しいと判明（前回のx=1.820は近接点同士のキャリブレーション誤差による誤り）。追記(2026-08-15)：施主指摘により南側1マス(2×1マス)を「ホール(民泊)」（room-1f-24）として分離' },
    { name:'ホール(民泊)', x0:0.91, x1:2.73, z0:1.82, z1:2.73, conf:'低', note:'新規(2026-08-15)：施主指摘により「玄関(民泊)」（2×2マス）の南側1マス(2×1マス)を分離。北側1辺を壁のない開口（door-025）として配置。room-1f-02の境界と一致させること' },
    { name:'洗面脱衣室', x0:0, x1:1.82, z0:2.73, z1:4.55, conf:'高', note:'面積3.31㎡相当。この行はx=1.820に壁あり(ピクセル解析で確認)' },
    { name:'UB(民泊)', x0:0, x1:1.82, z0:4.55, z1:6.37, conf:'中', note:'面積3.31㎡相当。洗面脱衣室と同幅と仮定' },
    { name:'洋室', x0:2.73, x1:7.28, z0:0.91, z1:3.691, poly:[[2.73,0.91],[7.28,0.91],[7.28,2.326],[6.37,2.326],[6.37,3.691],[2.73,3.691]], conf:'低', note:'訂正(2026-08-13)：西端をx=2.730に戻し、洋室|LDK境界z=3.691で再検算。箱面積12.60㎡は実際11.18㎡に近い（+13%）。x=1.820-2.730×z=2.730-6.370の範囲(洗面所/浴室の東側)は未モデル化の欠き（LDK側に含まれる可能性）。ラベルから面積表記は削除(2026-08-13)。追記(2026-08-15)：施主指摘により南東の横1マス×縦1.5マス(x:6.37-7.28,z:2.326-3.691)を「収納」（room-1f-23）として分離、L字形状に変更' },
    { name:'収納', x0:6.37, x1:7.28, z0:2.326, z1:3.691, conf:'低', note:'新規(2026-08-15)：施主指摘により「洋室」の南東1マス(0.91×1.365)を分離。西側1辺を両開き戸（door-024）として配置。room-1f-05の境界と一致させること' },
    { name:'LDK(民泊)', x0:1.82, x1:7.28, z0:2.73, z1:6.37, poly:[[1.82,2.73],[2.73,2.73],[2.73,3.691],[7.28,3.691],[7.28,6.37],[1.82,6.37]], conf:'高', note:'施主指摘(2026-08-13)によりLDK本体＋張り出し部をL字ポリゴンとして統合。内部の継ぎ目線は表示されない。ラベルから面積表記は削除(2026-08-13)。自宅側のLDKと区別するため「(民泊)」を付記' },
    { name:'ヌック', x0:7.28, x1:9.1, z0:0.91, z1:2.73, conf:'高', note:'床面はFL+200mm（施工会社図面表記の一段上がった小上がり）。訂正(2026-08-13)：マイホームクラウド画像で西端が防音壁位置(x=7.280)から始まると判明（前回のx=9.100は誤り）。幅1.820m確定・奥行は面積3.31㎡から逆算(1.819m)しz1=2.730とほぼ一致。ラベルから面積表記は削除(2026-08-13)' },
    { name:'自宅玄関', x0:9.1, x1:10.92, z0:0.455, z1:1.82, poly:[[9.1,0.455],[10.92,0.455],[10.92,1.82],[9.1,1.365]], conf:'低', note:'施主指摘(2026-08-13)により赤枠の座標をピクセル解析。旧「自宅玄関・土間・ホール」から西半分を分離。2026-08-15：施主指摘により斜め框（目分量の角度）で「自宅玄関・ホール」を分割。角度は概算のため`estimated`。施主指摘により当初の(9.100,0.910)-(10.920,1.820)から(9.100,0.910)-(10.920,1.365)へ緩やかに変更後、同じ角度のまま0.455下（南）へ平行移動し(9.100,1.365)-(10.920,1.820)に' },
    { name:'自宅ホール', x0:9.1, x1:10.92, z0:1.365, z1:2.73, poly:[[9.1,1.365],[10.92,1.82],[10.92,2.73],[9.1,2.73]], conf:'低', note:'新規(2026-08-15)：施主指摘により斜め框で「自宅玄関・ホール」（旧room-1f-08）を分割して新設。境界は斜め框（door-020、開口のみで壁なし）。施主指摘により角度を緩やかに変更後、同じ角度のまま0.455下へ平行移動（(9.100,1.365)-(10.920,1.820)）' },
    { name:'土間', x0:10.92, x1:12.451, z0:0.455, z1:2.275, conf:'低', note:'訂正(2026-08-13)：施主指摘により南端をz=2.730→2.275に縮小(0.5マス分をLD側へ移管)。2026-08-15：施主指摘により「土間・シューズクローク」を右の壁(x=13.651)から1200mmの位置(x=12.451)で分割し「土間」に改称。境界に壁はなく開口のみ（door-021）' },
    { name:'SC', x0:12.451, x1:13.651, z0:0, z1:2.275, poly:[[12.451,0.455],[12.74,0.455],[12.74,0],[13.651,0],[13.651,2.275],[12.451,2.275]], conf:'低', note:'新規(2026-08-15)：施主指摘により「土間・シューズクローク」（旧room-1f-09）を右の壁(x=13.651)から1200mmの位置(x=12.451)で分割して新設。境界は開口のみ（door-021、壁なし）。ラベルは施主指摘により「SC」と表記' },
    { name:'階段（曲がり階段）', x0:13.651, x1:15.471, z0:0, z1:1.82, poly:[[13.651,0],[15.471,0],[15.471,0.91],[14.561,0.91],[14.561,1.82],[13.651,1.82]], conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×2マス(1.820m角)に確定。2026-08-15：施主指摘により南東の1マス(0.91×0.91)を「パントリー」（room-1f-21）として分離' },
    { name:'パントリー（階段下）', x0:14.561, x1:15.471, z0:0.91, z1:1.82, conf:'低', note:'新規(2026-08-15)：施主指摘により「階段（曲がり階段）＋パントリー」（旧room-1f-10）の南東1マス(0.91×0.91)を分離して新設。南側1辺は壁のない開口（door-022）。追記(2026-08-15)：階段の廻り部分（stair-1f-01）の真上を通ることが判明したため、ラベルに「（階段下）」を付記。1F平面図では階段の踏み面線がこの区画の上を破線（hiddenBelow）で通過する' },
    { name:'LDK', x0:7.28, x1:15.471, z0:1.82, z1:6.37, poly:[[7.28,2.73],[10.92,2.73],[10.92,2.275],[13.651,2.275],[13.651,1.82],[15.471,1.82],[15.471,6.37],[7.28,6.37]], conf:'高', note:'確定(2026-08-13)：施主指摘によりLD＋キッチンを統合しLDKに変更。北端が3段階（z=2.730→2.275→1.820）の階段状になっているのが実際の間取り' },
    { name:'ファミリークローク', x0:15.471, x1:19.11, z0:0, z1:1.82, conf:'高', note:'確定(2026-08-13)：施主指摘により4マス×2マス(3.640m×1.820m)、東側全幅で確定' },
    { name:'廊下', x0:15.471, x1:17.291, z0:1.82, z1:3.64, poly:[[15.471,1.82],[16.381,1.82],[16.381,2.73],[17.291,2.73],[17.291,3.64],[15.471,3.64]], conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×2マス(1.820m角)で確定。西列。2026-08-15：施主指摘により北東の1マス(0.91×0.91)を「収納」（room-1f-22）として分離' },
    { name:'収納', x0:16.381, x1:17.291, z0:1.82, z1:2.73, conf:'低', note:'新規(2026-08-15)：施主指摘により「廊下＋収納」（旧room-1f-13）の北東1マス(0.91×0.91)を分離して新設。南側1辺は両開き戸（door-023）' },
    { name:'トイレ(東)', x0:17.291, x1:19.11, z0:1.82, z1:2.73, conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×1マス(1.820m×0.910m)で確定。東列' },
    { name:'洗面(東)', x0:17.291, x1:19.11, z0:2.73, z1:4.095, conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×1.5マス(1.820m×1.365m)で確定。東列' },
    { name:'脱衣室', x0:15.471, x1:17.291, z0:3.64, z1:6.37, conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×3マス(1.820m×2.730m)で確定。西列' },
    { name:'UB(東)', x0:17.291, x1:19.11, z0:4.095, z1:6.37, conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×2.5マス(1.820m×2.275m)で確定。東列' },
    { name:'南土間', x0:16.38, x1:19.11, z0:6.37, z1:7.735, conf:'高', note:'確定(2026-08-13)：施主指摘により3マス×1.5マス(2.730m×1.365m)で確定。z=6.370起点に修正（旧z0=5.460は誤り）' }
  ],
  2: [
    { name:'トイレ(2F)', x0:12.74, x1:13.651, z0:0, z1:1.82, conf:'高', note:'確定(2026-08-13)：施主指摘により1マス×2マス(0.910m×1.820m)で確定' },
    { name:'階段(2F)', x0:13.651, x1:15.47, z0:0, z1:1.82, conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×2マス(1.820m角)で確定。1Fの曲がり階段と同じ位置' },
    { name:'廊下(2F)', x0:12.74, x1:16.38, z0:1.82, z1:2.73, conf:'高', note:'確定(2026-08-13)：施主指摘により4マス×1マス(3.640m×0.910m)で確定。東端はA3/A4境界(16.380)と一致' },
    { name:'子供部屋1', x0:12.74, x1:15.47, z0:2.73, z1:6.37, poly:[[14.56,2.73],[15.47,2.73],[15.47,6.37],[12.74,6.37],[12.74,3.64],[14.56,3.64]], conf:'低', note:'確定(2026-08-13)：施主指摘により3マス×4マス(2.730m×3.640m)で確定。追記(2026-08-15)：施主指摘により北西2マス×1マスを「クローゼット」（room-2f-07）として分離、L字形状に変更' },
    { name:'クローゼット', x0:12.74, x1:14.56, z0:2.73, z1:3.64, conf:'低', note:'新規(2026-08-15)：施主指摘により「子供部屋1」の北西2マス×1マス(1.82×0.91)を分離。南側1辺を両開き折れ戸（door-026）として配置。room-2f-04の境界と一致させること' },
    { name:'子供部屋2', x0:16.38, x1:19.11, z0:0, z1:2.73, conf:'低', note:'確定(2026-08-13)：施主指摘により矩形＋廊下の張り出し分を除いたL字で確定。追記(2026-08-15)：施主指摘により西端1マス×2マスを「クローゼット」（room-2f-08）として分離、廊下の張り出し分とあわせて西端の1マス列が丸ごと外れたため矩形に戻った' },
    { name:'クローゼット', x0:15.47, x1:16.38, z0:0, z1:1.82, conf:'低', note:'新規(2026-08-15)：施主指摘により「子供部屋2」の西端1マス×2マス(0.91×1.82)を分離。東側1辺を両開き折れ戸（door-027）として配置。room-2f-05の境界と一致させること' },
    { name:'夫婦寝室', x0:15.47, x1:19.11, z0:2.73, z1:6.37, poly:[[15.47,2.73],[16.38,2.73],[16.38,3.64],[19.11,3.64],[19.11,6.37],[15.47,6.37]], conf:'低', note:'確定(2026-08-13)：施主指摘により4マス×4マス(3.640m角)で確定。追記(2026-08-15)：施主指摘により北東3マス×1マスを「書斎」（room-2f-09）として分離、L字形状に変更' },
    { name:'書斎', x0:16.38, x1:19.11, z0:2.73, z1:3.64, conf:'低', note:'新規(2026-08-15)：施主指摘により「夫婦寝室」の北東3マス×1マス(2.73×0.91)を分離。南側1辺を壁のない開口（door-028）として配置。room-2f-06の境界と一致させること' }
  ]
};

const ROOFS = [
  { id:'roof-a1', kind:'lean_to', x0:0, x1:9.1, zNorth:0.41, zSouth:7.28, pitch:0.15, thickness:0.15, base:3.4 },
  { id:'roof-a2', kind:'lean_to', x0:9.1, x1:12.74, zNorth:-0.045, zSouth:7.28, pitch:0.15, thickness:0.15, base:3.4 },
  { id:'roof-2f-gable', kind:'gable', x0:12.52, x1:19.33, zNorth:-0.558, zRidge:3.185, zSouth:6.928, yEave:6.3, yRidge:7.423, thickness:0.18 }
];

const STAIRS = [
  { id:'stair-1f-01', label:'階段（曲がり階段）', levelFrom:1, levelTo:2, width:0.91, totalSteps:13, opening:{ x0:13.651, x1:15.47, z0:0, z1:1.82 }, hiddenBelow:{ x0:14.561, x1:15.471, z0:0.91, z1:1.82 }, segments:[
    { type:'straight', x0:14.106, z0:1.82, x1:14.106, z1:0.91 },
    { type:'arc', pivotX:14.561, pivotZ:0.91, radius:0.455, startAngleDeg:180, endAngleDeg:360 },
    { type:'straight', x0:15.016, z0:0.91, x1:15.016, z1:1.82 }
  ] }, // 新規(2026-08-15)：施主指摘により、平面図・俯瞰・内覧すべてで階段の実体（段差ジオメトリ・2F床の吹き抜け・平面図記号・内覧での歩行）を表現するために新設。room-1f-10（西側柱状部分＋北東の曲がり部分）に沿う直進1.82マス分＋室-1f-10の凹角(x14.561,z0.91)を中心とした180度の廻り階段＋南への短い直進で2F(room-2f-02、パントリーの真上を含む)へ着地する。修正(2026-08-15)：施主指摘により、廻りは90度ではなく180度（パントリーの真上を回り込む）が正しいと判明し訂正。最後の直進部分はroom-1f-21パントリーの直上（1Fからは見えない、階段下収納の表現）を通るため、hiddenBelowで1F平面図では破線表示にする。再訂正(2026-08-16)：施主指摘により、最後の直進部分がパントリーの南端(z=1.82、room-1f-21の南側境界かつ2F開口の南端)まで届いていなかったのを、z=1.82まで延長。段数13・蹴上約210mmは施工図未確認のため推測値。totalStepsぶんの均等な蹴上でlevelFromのFLからlevelToのFLまで積み上げる
];

const FURNITURE_CATALOG = {
  'kitchen-counter': { label:'システムキッチン', category:'fixture', shape:'kitchenCounter', width:2.55, depth:0.65, height:0.85, clearance:0.9 },
  'refrigerator': { label:'冷蔵庫', category:'furniture', shape:'boxAppliance', width:0.69, depth:0.7, height:1.83, clearance:0.7 },
  'washing-machine': { label:'洗濯機', category:'furniture', shape:'boxAppliance', width:0.64, depth:0.72, height:1.05, clearance:0.6 },
  'vanity': { label:'洗面化粧台', category:'fixture', shape:'vanity', width:0.75, depth:0.53, height:1.9, clearance:0.75 },
  'toilet': { label:'便器（タンク付き）', category:'fixture', shape:'toilet', width:0.45, depth:0.75, height:1, clearance:0.5 },
  'toilet-tankless': { label:'便器（タンクレス）', category:'fixture', shape:'toiletTankless', width:0.4, depth:0.65, height:0.75, clearance:0.5 },
  'bathtub': { label:'浴槽（ユニットバス）', category:'fixture', shape:'bathtub', width:1.6, depth:0.8, height:0.6, clearance:0.6 },
  'bed-single': { label:'シングルベッド', category:'furniture', shape:'bed', width:0.97, depth:1.95, height:0.5, clearance:0.5 },
  'bed-semi-double': { label:'セミダブルベッド', category:'furniture', shape:'bed', width:1.2, depth:1.95, height:0.5, clearance:0.5 },
  'bed-double': { label:'ダブルベッド', category:'furniture', shape:'bed', width:1.4, depth:1.95, height:0.5, clearance:0.5 },
  'coffee-table': { label:'ローテーブル', category:'furniture', shape:'table', width:1, depth:0.5, height:0.4, clearance:0.3 },
  'counter-table': { label:'カウンターテーブル', category:'furniture', shape:'table', width:0.65, depth:0.35, height:1, clearance:0.4 },
  'sofa-2seat': { label:'2人掛けソファ', category:'furniture', shape:'sofa', width:1.5, depth:0.85, height:0.8, clearance:0.4 },
  'sofa-3seat': { label:'3人掛けソファ', category:'furniture', shape:'sofa', width:1.9, depth:0.85, height:0.8, clearance:0.4 },
  'dining-table-4': { label:'ダイニングテーブル（4人）', category:'furniture', shape:'table', width:1.35, depth:0.8, height:0.72, clearance:0.75 },
  'dining-table-6': { label:'ダイニングテーブル（6人）', category:'furniture', shape:'table', width:1.8, depth:0.85, height:0.72, clearance:0.75 },
  'chair': { label:'椅子', category:'furniture', shape:'chair', width:0.45, depth:0.5, height:0.85, clearance:0.3 },
  'cupboard': { label:'カップボード', category:'furniture', shape:'cupboard', width:1.2, depth:0.45, height:1.9, clearance:0.45 },
  'tv-board': { label:'テレビボード', category:'furniture', shape:'lowCabinet', width:1.5, depth:0.4, height:0.45, clearance:0.3 },
  'desk': { label:'デスク', category:'furniture', shape:'table', width:1.1, depth:0.6, height:0.72, clearance:0.75 },
  'shelf': { label:'収納棚・本棚', category:'furniture', shape:'shelf', width:0.9, depth:0.3, height:1.8, clearance:0.6 },
  'wardrobe': { label:'ワードローブ・洋服ダンス', category:'furniture', shape:'shelf', width:1.2, depth:0.6, height:1.8, clearance:0.7 }
};

const FURNITURE_ITEMS = [
  { id:'fur-035', type:'toilet', level:1, x:0.44, z:1.27, rotation:0, width:0.45, depth:0.75, height:1, label:'便器（タンク付き）', status:'estimated', room:'room-1f-01' },
  { id:'fur-001', type:'vanity', level:1, x:0.29, z:3.26, rotation:270, width:0.75, depth:0.53, height:1.9, label:'洗面化粧台', status:'estimated', room:'room-1f-03' },
  { id:'fur-002', type:'washing-machine', level:1, x:0.34, z:4.19, rotation:0, width:0.64, depth:0.72, height:1.05, label:'洗濯機', status:'estimated', room:'room-1f-03' },
  { id:'fur-003', type:'bathtub', level:1, x:0.92, z:5.96, rotation:0, width:1.82, depth:0.8, height:0.6, label:'浴槽', status:'estimated', room:'room-1f-04' },
  { id:'fur-036', type:'bed-single', level:1, x:3.9, z:2.67, rotation:180, width:0.97, depth:1.95, height:0.5, label:'ベッド1', status:'estimated', room:'room-1f-05' },
  { id:'fur-037', type:'bed-single', level:1, x:5.07, z:2.69, rotation:180, width:0.97, depth:1.95, height:0.5, label:'ベッド2', status:'estimated', room:'room-1f-05' },
  { id:'fur-041', type:'desk', level:1, x:6.9, z:1.47, rotation:90, width:1.1, depth:0.6, height:0.72, label:'デスク', status:'estimated', room:'room-1f-05' },
  { id:'fur-042', type:'chair', level:1, x:6.46, z:1.49, rotation:90, width:0.45, depth:0.5, height:0.85, label:'椅子', status:'estimated', room:'room-1f-05' },
  { id:'fur-006', type:'kitchen-counter', level:1, x:6.87, z:5.43, rotation:90, width:1.8, depth:0.65, height:0.85, label:'キッチン', status:'estimated', room:'room-1f-06' },
  { id:'fur-007', type:'refrigerator', level:1, x:6.86, z:4.06, rotation:90, width:0.69, depth:0.7, height:1.83, label:'冷蔵庫', status:'estimated', room:'room-1f-06' },
  { id:'fur-008', type:'dining-table-4', level:1, x:5.24, z:5.22, rotation:0, width:1.2, depth:0.8, height:0.72, label:'ダイニングテーブル', status:'estimated', room:'room-1f-06' },
  { id:'fur-009', type:'chair', level:1, x:5.26, z:4.82, rotation:0, width:0.45, depth:0.5, height:0.85, label:'椅子1', status:'estimated', room:'room-1f-06' },
  { id:'fur-010', type:'chair', level:1, x:5.26, z:5.66, rotation:180, width:0.45, depth:0.5, height:0.85, label:'椅子2', status:'estimated', room:'room-1f-06' },
  { id:'fur-011', type:'sofa-2seat', level:1, x:3.54, z:4.14, rotation:0, width:1.5, depth:0.85, height:0.8, label:'ソファ', status:'estimated', room:'room-1f-06' },
  { id:'fur-012', type:'tv-board', level:1, x:2.05, z:5.22, rotation:90, width:1.5, depth:0.4, height:0.45, label:'テレビボード', status:'estimated', room:'room-1f-06' },
  { id:'fur-038', type:'coffee-table', level:1, x:3.53, z:5.07, rotation:0, width:0.8, depth:0.4, height:0.4, label:'ローテーブル', status:'estimated', room:'room-1f-06' },
  { id:'fur-043', type:'counter-table', level:1, x:3.67, z:6.11, rotation:180, width:1.7, depth:0.35, height:1, label:'カウンターテーブル', status:'estimated', room:'room-1f-06' },
  { id:'fur-044', type:'chair', level:1, x:3.7, z:6.01, rotation:180, width:0.45, depth:0.7, height:0.85, label:'椅子（カウンター）', status:'estimated', room:'room-1f-06' },
  { id:'fur-013', type:'kitchen-counter', level:1, x:13.63, z:5.08, rotation:270, width:2.55, depth:0.65, height:0.85, label:'キッチン', status:'estimated', room:'room-1f-11' },
  { id:'fur-014', type:'refrigerator', level:1, x:15.11, z:5.99, rotation:180, width:0.69, depth:0.7, height:1.83, label:'冷蔵庫', status:'estimated', room:'room-1f-11' },
  { id:'fur-015', type:'dining-table-6', level:1, x:12.08, z:4.69, rotation:0, width:1.4, depth:0.85, height:0.72, label:'ダイニングテーブル', status:'estimated', room:'room-1f-11' },
  { id:'fur-016', type:'chair', level:1, x:11.79, z:4.07, rotation:0, width:0.45, depth:0.5, height:0.85, label:'椅子1', status:'estimated', room:'room-1f-11' },
  { id:'fur-017', type:'chair', level:1, x:12.47, z:4.12, rotation:0, width:0.45, depth:0.5, height:0.85, label:'椅子2', status:'estimated', room:'room-1f-11' },
  { id:'fur-018', type:'chair', level:1, x:11.81, z:5.24, rotation:180, width:0.45, depth:0.5, height:0.85, label:'椅子3', status:'estimated', room:'room-1f-11' },
  { id:'fur-019', type:'chair', level:1, x:12.43, z:5.28, rotation:180, width:0.45, depth:0.5, height:0.85, label:'椅子4', status:'estimated', room:'room-1f-11' },
  { id:'fur-020', type:'sofa-3seat', level:1, x:9.38, z:4.87, rotation:90, width:2, depth:0.85, height:0.8, label:'ソファ', status:'estimated', room:'room-1f-11' },
  { id:'fur-021', type:'tv-board', level:1, x:7.56, z:4.82, rotation:90, width:1.5, depth:0.4, height:0.45, label:'テレビボード', status:'estimated', room:'room-1f-11' },
  { id:'fur-039', type:'coffee-table', level:1, x:8.36, z:4.87, rotation:90, width:1, depth:0.5, height:0.4, label:'ローテーブル', status:'estimated', room:'room-1f-11' },
  { id:'fur-034', type:'cupboard', level:1, x:15.23, z:4.34, rotation:90, width:2.55, depth:0.45, height:1.9, label:'カップボード', status:'estimated', room:'room-1f-11' },
  { id:'fur-022', type:'toilet-tankless', level:1, x:18.79, z:2.27, rotation:90, width:0.4, depth:0.65, height:0.75, label:'便器（タンクレス）', status:'estimated', room:'room-1f-14' },
  { id:'fur-023', type:'vanity', level:1, x:18.19, z:3.86, rotation:180, width:1.82, depth:0.45, height:1.9, label:'洗面化粧台', status:'estimated', room:'room-1f-15' },
  { id:'fur-024', type:'washing-machine', level:1, x:15.8, z:5.99, rotation:0, width:0.64, depth:0.72, height:1.05, label:'洗濯機', status:'estimated', room:'room-1f-16' },
  { id:'fur-025', type:'bathtub', level:1, x:18.2, z:5.86, rotation:180, width:1.8, depth:1, height:0.6, label:'浴槽', status:'estimated', room:'room-1f-17' },
  { id:'fur-026', type:'toilet', level:2, x:13.19, z:0.35, rotation:0, width:0.45, depth:0.75, height:1, label:'便器（タンク付き）', status:'estimated', room:'room-2f-01' },
  { id:'fur-027', type:'bed-single', level:2, x:14.47, z:5.86, rotation:90, width:0.97, depth:1.95, height:0.5, label:'ベッド', status:'estimated', room:'room-2f-04' },
  { id:'fur-028', type:'desk', level:2, x:13.06, z:4.79, rotation:270, width:1.1, depth:0.6, height:0.72, label:'デスク', status:'estimated', room:'room-2f-04' },
  { id:'fur-030', type:'bed-single', level:2, x:18.57, z:1.71, rotation:180, width:0.97, depth:1.95, height:0.5, label:'ベッド', status:'estimated', room:'room-2f-05' },
  { id:'fur-031', type:'desk', level:2, x:17.44, z:0.3, rotation:0, width:1.1, depth:0.6, height:0.72, label:'デスク', status:'estimated', room:'room-2f-05' },
  { id:'fur-032', type:'bed-double', level:2, x:18.07, z:5.07, rotation:90, width:2, depth:2, height:0.5, label:'ベッド', status:'estimated', room:'room-2f-06' },
  { id:'fur-040', type:'tv-board', level:2, x:15.72, z:5, rotation:90, width:1.5, depth:0.4, height:0.45, label:'テレビボード', status:'estimated', room:'room-2f-06' },
];
