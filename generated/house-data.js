// ============================================================================
// 自動生成ファイル。手で編集しないこと。
// 生成元: data/house.json / data/furniture-catalog.json / data/furniture.json /
//        data/door-catalog.json / data/window-catalog.json / data/openings.json / data/interior-doors.json /
//        data/electrical-catalog.json / data/electrical.json / data/electrical-estimate.json
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

const GUARD_WALLS = [
  { id:'guard-2f-01', label:'階段吹き抜け 腰壁', level:2, orientation:'H', at:1.82, from:13.651, to:14.561, height:1.5, status:'estimated' }, // 新規(2026-08-16)：施主指摘（俯瞰スクリーンショットに赤線で図示）により新設。room-2f-02（階段(2F)、stair.openingと同一形状の吹き抜け）の南辺(z=1.82)のうち、door-030（階段(2F)⟷廊下(2F)、全幅1.819m開放）で壁のない開口になっている区間の西側半分（x:13.651-14.561）に、床から1.5mの腰壁を追加。この区間は階段経路の廻り部分の真上にあたり、2F床面より大きく低い位置しかない（＝実際にはまだ2Fの床がない吹き抜け）ため、施主指摘の通りガードなしでは廊下から誤って落下しうる。東側半分（x:14.561-15.471、階段経路の最後の直進＝上端の着地部分の真上）は、実際に階段へ出入りする通路として腰壁を設けず開放したまま残した。壁の高さ・区間の境界は目分量の推測値（要施工確認）
];

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
    { id:'room-1f-01', name:'トイレ(民泊)', x0:0, x1:0.91, z0:0.91, z1:2.73, conf:'高', note:'面積1.66㎡相当・マイホームクラウド値と一致確認' },
    { id:'room-1f-02', name:'玄関(民泊)', x0:0.91, x1:2.73, z0:0.91, z1:1.82, conf:'低', note:'訂正(2026-08-13)：西端(x=0)と東端(x=7.280)を基準とした再キャリブレーションで、玄関の東壁はx=2.730が正しいと判明（前回のx=1.820は近接点同士のキャリブレーション誤差による誤り）。追記(2026-08-15)：施主指摘により南側1マス(2×1マス)を「ホール(民泊)」（room-1f-24）として分離' },
    { id:'room-1f-24', name:'ホール(民泊)', x0:0.91, x1:2.73, z0:1.82, z1:2.73, conf:'低', note:'新規(2026-08-15)：施主指摘により「玄関(民泊)」（2×2マス）の南側1マス(2×1マス)を分離。北側1辺を壁のない開口（door-025）として配置。room-1f-02の境界と一致させること' },
    { id:'room-1f-03', name:'洗面脱衣室', x0:0, x1:1.82, z0:2.73, z1:4.55, conf:'高', note:'面積3.31㎡相当。この行はx=1.820に壁あり(ピクセル解析で確認)' },
    { id:'room-1f-04', name:'UB(民泊)', x0:0, x1:1.82, z0:4.55, z1:6.37, conf:'中', note:'面積3.31㎡相当。洗面脱衣室と同幅と仮定' },
    { id:'room-1f-05', name:'洋室', x0:2.73, x1:7.28, z0:0.91, z1:3.691, poly:[[2.73,0.91],[7.28,0.91],[7.28,2.326],[6.37,2.326],[6.37,3.691],[2.73,3.691]], conf:'低', note:'訂正(2026-08-13)：西端をx=2.730に戻し、洋室|LDK境界z=3.691で再検算。箱面積12.60㎡は実際11.18㎡に近い（+13%）。x=1.820-2.730×z=2.730-6.370の範囲(洗面所/浴室の東側)は未モデル化の欠き（LDK側に含まれる可能性）。ラベルから面積表記は削除(2026-08-13)。追記(2026-08-15)：施主指摘により南東の横1マス×縦1.5マス(x:6.37-7.28,z:2.326-3.691)を「収納」（room-1f-23）として分離、L字形状に変更' },
    { id:'room-1f-23', name:'収納', x0:6.37, x1:7.28, z0:2.326, z1:3.691, conf:'低', note:'新規(2026-08-15)：施主指摘により「洋室」の南東1マス(0.91×1.365)を分離。西側1辺を両開き戸（door-024）として配置。room-1f-05の境界と一致させること' },
    { id:'room-1f-06', name:'LDK(民泊)', x0:1.82, x1:7.28, z0:2.73, z1:6.37, poly:[[1.82,2.73],[2.73,2.73],[2.73,3.691],[7.28,3.691],[7.28,6.37],[1.82,6.37]], conf:'高', note:'施主指摘(2026-08-13)によりLDK本体＋張り出し部をL字ポリゴンとして統合。内部の継ぎ目線は表示されない。ラベルから面積表記は削除(2026-08-13)。自宅側のLDKと区別するため「(民泊)」を付記。追記(2026-08-16)：施主指摘により、片流れ屋根（roof-a1）がかかる範囲は天井高を屋根なりの勾配天井にすることになった（`ceiling:"sloped"`）。詳細はdocs/ARCHITECTURE.md「勾配天井（ceiling:sloped）」を参照' },
    { id:'room-1f-07', name:'ヌック', x0:7.28, x1:9.1, z0:0.91, z1:2.73, conf:'高', note:'床面はFL+200mm（施工会社図面表記の一段上がった小上がり）。訂正(2026-08-13)：マイホームクラウド画像で西端が防音壁位置(x=7.280)から始まると判明（前回のx=9.100は誤り）。幅1.820m確定・奥行は面積3.31㎡から逆算(1.819m)しz1=2.730とほぼ一致。ラベルから面積表記は削除(2026-08-13)' },
    { id:'room-1f-08', name:'自宅玄関', x0:9.1, x1:10.92, z0:0.455, z1:1.82, poly:[[9.1,0.455],[10.92,0.455],[10.92,1.82],[9.1,1.365]], conf:'低', note:'施主指摘(2026-08-13)により赤枠の座標をピクセル解析。旧「自宅玄関・土間・ホール」から西半分を分離。2026-08-15：施主指摘により斜め框（目分量の角度）で「自宅玄関・ホール」を分割。角度は概算のため`estimated`。施主指摘により当初の(9.100,0.910)-(10.920,1.820)から(9.100,0.910)-(10.920,1.365)へ緩やかに変更後、同じ角度のまま0.455下（南）へ平行移動し(9.100,1.365)-(10.920,1.820)に' },
    { id:'room-1f-19', name:'自宅ホール', x0:9.1, x1:10.92, z0:1.365, z1:2.73, poly:[[9.1,1.365],[10.92,1.82],[10.92,2.73],[9.1,2.73]], conf:'低', note:'新規(2026-08-15)：施主指摘により斜め框で「自宅玄関・ホール」（旧room-1f-08）を分割して新設。境界は斜め框（door-020、開口のみで壁なし）。施主指摘により角度を緩やかに変更後、同じ角度のまま0.455下へ平行移動（(9.100,1.365)-(10.920,1.820)）' },
    { id:'room-1f-09', name:'土間', x0:10.92, x1:12.451, z0:0.455, z1:2.275, conf:'低', note:'訂正(2026-08-13)：施主指摘により南端をz=2.730→2.275に縮小(0.5マス分をLD側へ移管)。2026-08-15：施主指摘により「土間・シューズクローク」を右の壁(x=13.651)から1200mmの位置(x=12.451)で分割し「土間」に改称。境界に壁はなく開口のみ（door-021）' },
    { id:'room-1f-20', name:'SC', x0:12.451, x1:13.651, z0:0, z1:2.275, poly:[[12.451,0.455],[12.74,0.455],[12.74,0],[13.651,0],[13.651,2.275],[12.451,2.275]], conf:'低', note:'新規(2026-08-15)：施主指摘により「土間・シューズクローク」（旧room-1f-09）を右の壁(x=13.651)から1200mmの位置(x=12.451)で分割して新設。境界は開口のみ（door-021、壁なし）。ラベルは施主指摘により「SC」と表記' },
    { id:'room-1f-10', name:'階段（曲がり階段）', x0:13.651, x1:15.471, z0:0, z1:1.82, poly:[[13.651,0],[15.471,0],[15.471,0.91],[14.561,0.91],[14.561,1.82],[13.651,1.82]], conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×2マス(1.820m角)に確定。2026-08-15：施主指摘により南東の1マス(0.91×0.91)を「パントリー」（room-1f-21）として分離' },
    { id:'room-1f-21', name:'パントリー（階段下）', x0:14.561, x1:15.471, z0:0.91, z1:1.82, conf:'低', note:'新規(2026-08-15)：施主指摘により「階段（曲がり階段）＋パントリー」（旧room-1f-10）の南東1マス(0.91×0.91)を分離して新設。南側1辺は壁のない開口（door-022）。追記(2026-08-15)：階段の廻り部分（stair-1f-01）の真上を通ることが判明したため、ラベルに「（階段下）」を付記。1F平面図では階段の踏み面線がこの区画の上を破線（hiddenBelow）で通過する' },
    { id:'room-1f-11', name:'LDK', x0:7.28, x1:15.471, z0:1.82, z1:6.37, poly:[[7.28,2.73],[10.92,2.73],[10.92,2.275],[13.651,2.275],[13.651,1.82],[15.471,1.82],[15.471,6.37],[7.28,6.37]], conf:'高', note:'確定(2026-08-13)：施主指摘によりLD＋キッチンを統合しLDKに変更。北端が3段階（z=2.730→2.275→1.820）の階段状になっているのが実際の間取り。追記(2026-08-16)：施主指摘により、片流れ屋根（roof-a1/roof-a2）がかかる範囲（x:7.28-12.74）は天井高を屋根なりの勾配天井にすることになった（`ceiling:"sloped"`）。2階の直下にあたる東側（x:12.74-15.471）は屋根がかからないためフラットな天井のまま。詳細はdocs/ARCHITECTURE.md「勾配天井（ceiling:sloped）」を参照' },
    { id:'room-1f-12', name:'ファミリークローク', x0:15.471, x1:19.11, z0:0, z1:1.82, conf:'高', note:'確定(2026-08-13)：施主指摘により4マス×2マス(3.640m×1.820m)、東側全幅で確定' },
    { id:'room-1f-13', name:'廊下', x0:15.471, x1:17.291, z0:1.82, z1:3.64, poly:[[15.471,1.82],[16.381,1.82],[16.381,2.73],[17.291,2.73],[17.291,3.64],[15.471,3.64]], conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×2マス(1.820m角)で確定。西列。2026-08-15：施主指摘により北東の1マス(0.91×0.91)を「収納」（room-1f-22）として分離' },
    { id:'room-1f-22', name:'収納', x0:16.381, x1:17.291, z0:1.82, z1:2.73, conf:'低', note:'新規(2026-08-15)：施主指摘により「廊下＋収納」（旧room-1f-13）の北東1マス(0.91×0.91)を分離して新設。南側1辺は両開き戸（door-023）' },
    { id:'room-1f-14', name:'トイレ(東)', x0:17.291, x1:19.11, z0:1.82, z1:2.73, conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×1マス(1.820m×0.910m)で確定。東列' },
    { id:'room-1f-15', name:'洗面(東)', x0:17.291, x1:19.11, z0:2.73, z1:4.095, conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×1.5マス(1.820m×1.365m)で確定。東列' },
    { id:'room-1f-16', name:'脱衣室', x0:15.471, x1:17.291, z0:3.64, z1:6.37, conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×3マス(1.820m×2.730m)で確定。西列' },
    { id:'room-1f-17', name:'UB(東)', x0:17.291, x1:19.11, z0:4.095, z1:6.37, conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×2.5マス(1.820m×2.275m)で確定。東列' },
    { id:'room-1f-18', name:'南土間', x0:16.38, x1:19.11, z0:6.37, z1:7.735, conf:'高', note:'確定(2026-08-13)：施主指摘により3マス×1.5マス(2.730m×1.365m)で確定。z=6.370起点に修正（旧z0=5.460は誤り）' }
  ],
  2: [
    { id:'room-2f-01', name:'トイレ(2F)', x0:12.74, x1:13.651, z0:0, z1:1.82, conf:'高', note:'確定(2026-08-13)：施主指摘により1マス×2マス(0.910m×1.820m)で確定' },
    { id:'room-2f-02', name:'階段(2F)', x0:13.651, x1:15.47, z0:0, z1:1.82, conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×2マス(1.820m角)で確定。1Fの曲がり階段と同じ位置' },
    { id:'room-2f-03', name:'廊下(2F)', x0:12.74, x1:16.38, z0:1.82, z1:2.73, conf:'高', note:'確定(2026-08-13)：施主指摘により4マス×1マス(3.640m×0.910m)で確定。東端はA3/A4境界(16.380)と一致' },
    { id:'room-2f-04', name:'子供部屋1', x0:12.74, x1:15.47, z0:2.73, z1:6.37, poly:[[14.56,2.73],[15.47,2.73],[15.47,6.37],[12.74,6.37],[12.74,3.64],[14.56,3.64]], conf:'低', note:'確定(2026-08-13)：施主指摘により3マス×4マス(2.730m×3.640m)で確定。追記(2026-08-15)：施主指摘により北西2マス×1マスを「クローゼット」（room-2f-07）として分離、L字形状に変更' },
    { id:'room-2f-07', name:'クローゼット', x0:12.74, x1:14.56, z0:2.73, z1:3.64, conf:'低', note:'新規(2026-08-15)：施主指摘により「子供部屋1」の北西2マス×1マス(1.82×0.91)を分離。南側1辺を両開き折れ戸（door-026）として配置。room-2f-04の境界と一致させること' },
    { id:'room-2f-05', name:'子供部屋2', x0:16.38, x1:19.11, z0:0, z1:2.73, conf:'低', note:'確定(2026-08-13)：施主指摘により矩形＋廊下の張り出し分を除いたL字で確定。追記(2026-08-15)：施主指摘により西端1マス×2マスを「クローゼット」（room-2f-08）として分離、廊下の張り出し分とあわせて西端の1マス列が丸ごと外れたため矩形に戻った' },
    { id:'room-2f-08', name:'クローゼット', x0:15.47, x1:16.38, z0:0, z1:1.82, conf:'低', note:'新規(2026-08-15)：施主指摘により「子供部屋2」の西端1マス×2マス(0.91×1.82)を分離。東側1辺を両開き折れ戸（door-027）として配置。room-2f-05の境界と一致させること' },
    { id:'room-2f-06', name:'夫婦寝室', x0:15.47, x1:19.11, z0:2.73, z1:6.37, poly:[[15.47,2.73],[16.38,2.73],[16.38,3.64],[19.11,3.64],[19.11,6.37],[15.47,6.37]], conf:'低', note:'確定(2026-08-13)：施主指摘により4マス×4マス(3.640m角)で確定。追記(2026-08-15)：施主指摘により北東3マス×1マスを「書斎」（room-2f-09）として分離、L字形状に変更' },
    { id:'room-2f-09', name:'書斎', x0:16.38, x1:19.11, z0:2.73, z1:3.64, conf:'低', note:'新規(2026-08-15)：施主指摘により「夫婦寝室」の北東3マス×1マス(2.73×0.91)を分離。南側1辺を壁のない開口（door-028）として配置。room-2f-06の境界と一致させること' }
  ]
};

const ROOFS = [
  { id:'roof-a1', kind:'lean_to', x0:0, x1:9.1, zNorth:0.41, zSouth:7.28, pitch:0.15, thickness:0.15, base:3.4 },
  { id:'roof-a2', kind:'lean_to', x0:9.1, x1:12.74, zNorth:-0.045, zSouth:7.28, pitch:0.15, thickness:0.15, base:3.4 },
  { id:'roof-2f-gable', kind:'gable', x0:12.52, x1:19.33, zNorth:-0.558, zRidge:3.185, zSouth:6.928, yEave:6.3, yRidge:7.423, thickness:0.18 }
];

const CEILING_ALLOWANCE = 0.15; // 垂木・断熱・仕上げの見込み(m)。屋根裏面からこの分だけ勾配天井を下げる
const SLOPED_CEILING_PIECES = [
  { roomId:'room-1f-06', x0:1.82, x1:2.73, z0:2.73, z1:3.691, sloped:true, base:3.4, pitch:0.15, roofThickness:0.15 },
  { roomId:'room-1f-06', x0:1.82, x1:7.28, z0:3.691, z1:6.37, sloped:true, base:3.4, pitch:0.15, roofThickness:0.15 },
  { roomId:'room-1f-11', x0:13.651, x1:15.471, z0:1.82, z1:2.275, sloped:false },
  { roomId:'room-1f-11', x0:10.92, x1:12.74, z0:2.275, z1:2.73, sloped:true, base:3.4, pitch:0.15, roofThickness:0.15 },
  { roomId:'room-1f-11', x0:12.74, x1:15.471, z0:2.275, z1:2.73, sloped:false },
  { roomId:'room-1f-11', x0:7.28, x1:9.1, z0:2.73, z1:6.37, sloped:true, base:3.4, pitch:0.15, roofThickness:0.15 },
  { roomId:'room-1f-11', x0:9.1, x1:12.74, z0:2.73, z1:6.37, sloped:true, base:3.4, pitch:0.15, roofThickness:0.15 },
  { roomId:'room-1f-11', x0:12.74, x1:15.471, z0:2.73, z1:6.37, sloped:false }
];

const STAIRS = [
  { id:'stair-1f-01', label:'階段（曲がり階段）', levelFrom:1, levelTo:2, width:0.91, totalSteps:13, opening:{ x0:13.651, x1:15.47, z0:0, z1:1.82 }, hiddenBelow:{ x0:14.561, x1:15.471, z0:0.91, z1:1.82 }, segments:[
    { type:'straight', x0:14.106, z0:1.82, x1:14.106, z1:0.91 },
    { type:'arc', pivotX:14.561, pivotZ:0.91, radius:0.455, startAngleDeg:180, endAngleDeg:360 },
    { type:'straight', x0:15.016, z0:0.91, x1:15.016, z1:1.82 }
  ] }, // 新規(2026-08-15)：施主指摘により、平面図・俯瞰・内覧すべてで階段の実体（段差ジオメトリ・2F床の吹き抜け・平面図記号・内覧での歩行）を表現するために新設。room-1f-10（西側柱状部分＋北東の曲がり部分）に沿う直進1.82マス分＋室-1f-10の凹角(x14.561,z0.91)を中心とした180度の廻り階段＋南への短い直進で2F(room-2f-02、パントリーの真上を含む)へ着地する。修正(2026-08-15)：施主指摘により、廻りは90度ではなく180度（パントリーの真上を回り込む）が正しいと判明し訂正。最後の直進部分はroom-1f-21パントリーの直上（1Fからは見えない、階段下収納の表現）を通るため、hiddenBelowで1F平面図では破線表示にする。再訂正(2026-08-16)：施主指摘により、最後の直進部分がパントリーの南端(z=1.82、room-1f-21の南側境界かつ2F開口の南端)まで届いていなかったのを、z=1.82まで延長。段数13・蹴上約210mmは施工図未確認のため推測値。totalStepsぶんの均等な蹴上でlevelFromのFLからlevelToのFLまで積み上げる
];

const FURNITURE_CATALOG = {
  'dining-table-round': { label:'円形ダイニングテーブル', category:'furniture', shape:'roundTable', width:0.9, depth:0.9, height:0.72, clearance:0.75, rotationConvention:'source' },
  'chair-timber': { label:'木製チェア', category:'furniture', shape:'timberChair', width:0.45, depth:0.48, height:0.85, clearance:0.3, rotationConvention:'source' },
  'television': { label:'テレビ', category:'furniture', shape:'television', width:1.12, depth:0.06, height:0.65, clearance:0, rotationConvention:'source' },
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
  'sofa-2seat': { label:'2人掛けソファ', category:'furniture', shape:'sofa', width:1.5, depth:0.85, height:0.8, clearance:0.4, rotationConvention:'source' },
  'sofa-3seat': { label:'3人掛けソファ', category:'furniture', shape:'sofa', width:1.9, depth:0.85, height:0.8, clearance:0.4 },
  'dining-table-4': { label:'ダイニングテーブル（4人）', category:'furniture', shape:'table', width:1.35, depth:0.8, height:0.72, clearance:0.75 },
  'dining-table-6': { label:'ダイニングテーブル（6人）', category:'furniture', shape:'table', width:1.8, depth:0.85, height:0.72, clearance:0.75 },
  'chair': { label:'椅子', category:'furniture', shape:'chair', width:0.45, depth:0.5, height:0.85, clearance:0.3 },
  'cupboard': { label:'カップボード', category:'furniture', shape:'cupboard', width:1.2, depth:0.45, height:1.9, clearance:0.45 },
  'tv-board': { label:'テレビボード', category:'furniture', shape:'lowCabinet', width:1.5, depth:0.4, height:0.45, clearance:0.3 },
  'desk': { label:'デスク', category:'furniture', shape:'table', width:1.1, depth:0.6, height:0.72, clearance:0.75 },
  'shelf': { label:'収納棚・本棚', category:'furniture', shape:'shelf', width:0.9, depth:0.3, height:1.8, clearance:0.6 },
  'wardrobe': { label:'ワードローブ・洋服ダンス', category:'furniture', shape:'shelf', width:1.2, depth:0.6, height:1.8, clearance:0.7 },
  'kitchen-guest': { label:'システムキッチン', category:'fixture', shape:'kitchenCounter', width:2.55, depth:0.65, height:0.85, clearance:0.9, rotationConvention:'source' },
  'refrigerator-guest': { label:'冷蔵庫', category:'furniture', shape:'refrigeratorFront', width:0.69, depth:0.7, height:1.83, clearance:0.7, rotationConvention:'source' },
  'range-hood': { label:'レンジフード', category:'fixture', shape:'rangeHood', width:0.6, depth:0.5, height:0.6, clearance:0, rotationConvention:'source' },
  'kitchen-faucet': { label:'水栓', category:'fixture', shape:'faucet', width:0.1, depth:0.18, height:0.3, clearance:0, rotationConvention:'source' },
  'air-conditioner': { label:'エアコン', category:'fixture', shape:'airConditioner', width:0.8, depth:0.25, height:0.3, clearance:0, rotationConvention:'source' }
};

const FURNITURE_ITEMS = [
  { id:'fur-045', type:'television', level:1, x:1.95, z:5.22, rotation:90, width:1.12, depth:0.06, height:0.65, label:'テレビ', status:'estimated', elevation:1, note:'参考画像の壁掛け案として追加。既存テレビボードfur-012の上方、西壁の室内側で東向き。底面は1階床上1.00m、外形は仮寸法で施工・購入仕様ではない。既存ボードは維持。金具・配線・視聴高さは今後確認。', room:'room-1f-06' }, // 参考画像の壁掛け案として追加。既存テレビボードfur-012の上方、西壁の室内側で東向き。底面は1階床上1.00m、外形は仮寸法で施工・購入仕様ではない。既存ボードは維持。金具・配線・視聴高さは今後確認。
  { id:'fur-035', type:'toilet', level:1, x:0.44, z:1.27, rotation:0, width:0.45, depth:0.75, height:1, label:'便器（タンク付き）', status:'estimated', room:'room-1f-01' },
  { id:'fur-001', type:'vanity', level:1, x:0.29, z:3.26, rotation:270, width:0.75, depth:0.53, height:1.9, label:'洗面化粧台', status:'estimated', room:'room-1f-03' },
  { id:'fur-002', type:'washing-machine', level:1, x:0.34, z:4.19, rotation:0, width:0.64, depth:0.72, height:1.05, label:'洗濯機', status:'estimated', room:'room-1f-03' },
  { id:'fur-003', type:'bathtub', level:1, x:0.92, z:5.96, rotation:0, width:1.82, depth:0.8, height:0.6, label:'浴槽', status:'estimated', room:'room-1f-04' },
  { id:'fur-036', type:'bed-single', level:1, x:3.84, z:2.69, rotation:180, width:0.9, depth:1.9, height:0.5, label:'ベッド1', status:'estimated', room:'room-1f-05' },
  { id:'fur-037', type:'bed-single', level:1, x:5.05, z:2.68, rotation:180, width:0.9, depth:1.9, height:0.5, label:'ベッド2', status:'estimated', room:'room-1f-05' },
  { id:'fur-041', type:'desk', level:1, x:6.9, z:1.47, rotation:90, width:1.1, depth:0.6, height:0.72, label:'デスク', status:'estimated', room:'room-1f-05' },
  { id:'fur-042', type:'chair', level:1, x:6.46, z:1.49, rotation:270, width:0.45, depth:0.5, height:0.85, label:'椅子', status:'estimated', room:'room-1f-05' },
  { id:'fur-006', type:'kitchen-guest', level:1, x:6.87, z:5.43, rotation:270, width:1.8, depth:0.65, height:0.85, label:'キッチン', status:'estimated', note:' ゲストLDK東壁の設備正面を西（室内側）へ統一。旧回転90度から正本規約の270度へ変更。中心・寸法は維持。', room:'room-1f-06' }, //  ゲストLDK東壁の設備正面を西（室内側）へ統一。旧回転90度から正本規約の270度へ変更。中心・寸法は維持。
  { id:'fur-007', type:'refrigerator-guest', level:1, x:6.86, z:4.06, rotation:270, width:0.69, depth:0.7, height:1.4, label:'冷蔵庫', status:'estimated', note:' ゲストLDK東壁の設備正面を西（室内側）へ統一。旧回転90度から正本規約の270度へ変更。中心・寸法は維持。', room:'room-1f-06' }, //  ゲストLDK東壁の設備正面を西（室内側）へ統一。旧回転90度から正本規約の270度へ変更。中心・寸法は維持。
  { id:'fur-008', type:'dining-table-round', level:1, x:5.45, z:5.02, rotation:0, width:0.9, depth:0.9, height:0.72, label:'ダイニングテーブル', status:'estimated', note:' 参考画像に沿った配置検討として施主の許可に基づき変更。旧値:{"type":"dining-table-4","x":5.36,"z":5.06,"widthOverride":0.8}。仮寸法・仮配置、製品未選定。', room:'room-1f-06' }, //  参考画像に沿った配置検討として施主の許可に基づき変更。旧値:{"type":"dining-table-4","x":5.36,"z":5.06,"widthOverride":0.8}。仮寸法・仮配置、製品未選定。
  { id:'fur-009', type:'chair-timber', level:1, x:5.45, z:4.31, rotation:0, width:0.45, depth:0.48, height:0.85, label:'椅子1', status:'estimated', note:' 参考画像に沿った配置検討として施主の許可に基づき変更。旧値:{"type":"chair","x":5.39,"z":4.61}。仮寸法・仮配置、製品未選定。', room:'room-1f-06' }, //  参考画像に沿った配置検討として施主の許可に基づき変更。旧値:{"type":"chair","x":5.39,"z":4.61}。仮寸法・仮配置、製品未選定。
  { id:'fur-010', type:'chair-timber', level:1, x:5.45, z:5.73, rotation:180, width:0.45, depth:0.48, height:0.85, label:'椅子2', status:'estimated', note:' 参考画像に沿った配置検討として施主の許可に基づき変更。旧値:{"type":"chair","x":5.36,"z":5.56}。仮寸法・仮配置、製品未選定。', room:'room-1f-06' }, //  参考画像に沿った配置検討として施主の許可に基づき変更。旧値:{"type":"chair","x":5.36,"z":5.56}。仮寸法・仮配置、製品未選定。
  { id:'fur-011', type:'sofa-2seat', level:1, x:3.76, z:4.13, rotation:0, width:1.7, depth:0.78, height:0.78, label:'ソファ', status:'estimated', note:'参考画像の木枠ソファに合わせた検討案。施主より既存家具の寸法・配置変更可の指示。旧案は中心(3.74,4.05)、1.40×0.70×0.70m。新案は北壁室内側に収まるよう中心(3.76,4.13)、1.70×0.78×0.78mへ変更。製品未選定。', room:'room-1f-06' }, // 参考画像の木枠ソファに合わせた検討案。施主より既存家具の寸法・配置変更可の指示。旧案は中心(3.74,4.05)、1.40×0.70×0.70m。新案は北壁室内側に収まるよう中心(3.76,4.13)、1.70×0.78×0.78mへ変更。製品未選定。
  { id:'fur-012', type:'tv-board', level:1, x:2.05, z:5.22, rotation:90, width:1.5, depth:0.4, height:0.45, label:'テレビボード', status:'estimated', room:'room-1f-06' },
  { id:'fur-038', type:'coffee-table', level:1, x:3.65, z:5, rotation:0, width:0.85, depth:0.4, height:0.4, label:'ローテーブル', status:'estimated', note:' 参考画像に沿った配置検討として施主の許可に基づき変更。旧値:{"x":3.66,"z":4.9,"widthOverride":0.5,"depthOverride":0.4}。仮寸法・仮配置、製品未選定。', room:'room-1f-06' }, //  参考画像に沿った配置検討として施主の許可に基づき変更。旧値:{"x":3.66,"z":4.9,"widthOverride":0.5,"depthOverride":0.4}。仮寸法・仮配置、製品未選定。
  { id:'fur-043', type:'counter-table', level:1, x:3.7, z:6.1, rotation:180, width:1.9, depth:0.42, height:0.74, label:'カウンターテーブル', status:'estimated', note:' 参考画像に沿った配置検討として施主の許可に基づき変更。旧値:{"x":3.67,"z":6.11,"widthOverride":1.7,"depthOverride":null,"heightOverride":null}。仮寸法・仮配置、製品未選定。', room:'room-1f-06' }, //  参考画像に沿った配置検討として施主の許可に基づき変更。旧値:{"x":3.67,"z":6.11,"widthOverride":1.7,"depthOverride":null,"heightOverride":null}。仮寸法・仮配置、製品未選定。
  { id:'fur-044', type:'chair-timber', level:1, x:3.15, z:5.67, rotation:0, width:0.45, depth:0.48, height:0.85, label:'椅子（カウンター1）', status:'estimated', note:' 参考画像に沿った配置検討として施主の許可に基づき変更。旧値:{"type":"chair","x":3.7,"z":6.01,"depthOverride":0.7,"label":"椅子（カウンター）"}。仮寸法・仮配置、製品未選定。', room:'room-1f-06' }, //  参考画像に沿った配置検討として施主の許可に基づき変更。旧値:{"type":"chair","x":3.7,"z":6.01,"depthOverride":0.7,"label":"椅子（カウンター）"}。仮寸法・仮配置、製品未選定。
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
  { id:'fur-046', type:'chair-timber', level:1, x:4.05, z:5.67, rotation:0, width:0.45, depth:0.48, height:0.85, label:'椅子（カウンター2）', status:'estimated', note:'窓際カウンターを2席とする参考案。高さ740mmの天板と座面約450mmを組み合わせる。仮配置・製品未選定。', room:'room-1f-06' }, // 窓際カウンターを2席とする参考案。高さ740mmの天板と座面約450mmを組み合わせる。仮配置・製品未選定。
  { id:'fur-047', type:'range-hood', level:1, x:6.94, z:5.98, rotation:270, width:0.6, depth:0.5, height:0.6, label:'レンジフード', status:'estimated', elevation:1.65, note:'キッチンfur-006のIH上方の仮配置。IH天面から底面まで約0.80mは検討用の仮値で、製品の設置条件ではない。キッチンを動かす際は水栓と共に位置を再確認。', room:'room-1f-06' }, // キッチンfur-006のIH上方の仮配置。IH天面から底面まで約0.80mは検討用の仮値で、製品の設置条件ではない。キッチンを動かす際は水栓と共に位置を再確認。
  { id:'fur-048', type:'kitchen-faucet', level:1, x:7.1, z:5.23, rotation:270, width:0.1, depth:0.18, height:0.3, label:'水栓', status:'estimated', elevation:0.85, note:'キッチンfur-006のシンク背面に仮配置。底面を床上0.85mの天板に合わせた。キッチンの移動・寸法変更には自動追従せず、共通配置側で再調整する。', room:'room-1f-06' }, // キッチンfur-006のシンク背面に仮配置。底面を床上0.85mの天板に合わせた。キッチンの移動・寸法変更には自動追従せず、共通配置側で再調整する。
  { id:'fur-049', type:'air-conditioner', level:1, x:2.07, z:5.22, rotation:90, width:0.8, depth:0.25, height:0.3, label:'エアコン', status:'estimated', elevation:2.1, note:'ゲストLDK西壁のテレビ上方に置く参考案。底面床上2.10m。コンセント・配管・保守空間は別途照合。', room:'room-1f-06' }, // ゲストLDK西壁のテレビ上方に置く参考案。底面床上2.10m。コンセント・配管・保守空間は別途照合。
];

const ELECTRICAL_CATALOG = {
  'outlet-double': { label:'コンセント（2口）', category:'outlet', mount:'wall', heightRef:'floor', shape:'outletPlate', width:0.09, depth:0.02, height:0.09, mountHeight:0.25 },
  'outlet-triple': { label:'コンセント（3口）', category:'outlet', mount:'wall', heightRef:'floor', shape:'outletPlate', width:0.12, depth:0.02, height:0.09, mountHeight:0.25 },
  'outlet-grounded': { label:'コンセント（アース付）', category:'outlet', mount:'wall', heightRef:'floor', shape:'outletPlate', width:0.09, depth:0.02, height:0.09, mountHeight:0.25 },
  'outlet-waterproof': { label:'コンセント（防水）', category:'outlet', mount:'exterior', heightRef:'floor', shape:'outletPlate', width:0.1, depth:0.03, height:0.11, mountHeight:0.25 },
  'outlet-ac': { label:'コンセント（AC専用）', category:'outlet', mount:'wall', heightRef:'floor', shape:'outletPlate', width:0.09, depth:0.02, height:0.09, mountHeight:2 },
  'outlet-ih': { label:'コンセント（IH専用）', category:'outlet', mount:'wall', heightRef:'floor', shape:'outletPlate', width:0.09, depth:0.02, height:0.09, mountHeight:0.2 },
  'outlet-floor': { label:'コンセント（床）', category:'outlet', mount:'floor', heightRef:'floor', shape:'outletFloorPlate', width:0.1, depth:0.1, height:0.01, mountHeight:0 },
  'switch-1p': { label:'スイッチ（片切）', category:'switch', mount:'wall', heightRef:'floor', shape:'switchPlate', width:0.09, depth:0.02, height:0.09, mountHeight:1.2 },
  'switch-3way': { label:'スイッチ（3路）', category:'switch', mount:'wall', heightRef:'floor', shape:'switchPlate', width:0.09, depth:0.02, height:0.09, mountHeight:1.2 },
  'switch-dimmer': { label:'スイッチ（調光）', category:'switch', mount:'wall', heightRef:'floor', shape:'switchPlate', width:0.12, depth:0.02, height:0.09, mountHeight:1.2 },
  'switch-sensor': { label:'スイッチ（人感）', category:'switch', mount:'wall', heightRef:'floor', shape:'switchPlate', width:0.09, depth:0.03, height:0.09, mountHeight:1.2 },
  'light-downlight': { label:'ダウンライト', category:'lighting', mount:'ceiling', heightRef:'ceiling', shape:'downlight', width:0.1, depth:0.1, height:0.02, mountHeight:0 },
  'light-ceiling': { label:'シーリングライト', category:'lighting', mount:'ceiling', heightRef:'ceiling', shape:'ceilingLight', width:0.35, depth:0.35, height:0.12, mountHeight:0 },
  'light-bracket': { label:'ブラケットライト', category:'lighting', mount:'wall', heightRef:'floor', shape:'bracketLight', width:0.12, depth:0.1, height:0.15, mountHeight:1.8 },
  'light-pendant': { label:'ペンダントライト', category:'lighting', mount:'ceiling', heightRef:'ceiling', shape:'pendantLight', width:0.25, depth:0.25, height:0.2, mountHeight:0.6 },
  'light-indirect': { label:'間接照明', category:'lighting', mount:'ceiling', heightRef:'ceiling', shape:'indirectLight', width:0.6, depth:0.05, height:0.03, mountHeight:0 },
  'light-exterior': { label:'外灯（壁付けブラケット）', category:'lighting', mount:'exterior', heightRef:'floor', shape:'bracketLight', width:0.12, depth:0.1, height:0.15, mountHeight:1.8 },
  'data-lan': { label:'LANコンセント', category:'data', mount:'wall', heightRef:'floor', shape:'dataJack', width:0.09, depth:0.02, height:0.09, mountHeight:0.25 },
  'data-tv': { label:'TV端子', category:'data', mount:'wall', heightRef:'floor', shape:'dataJack', width:0.09, depth:0.02, height:0.09, mountHeight:0.3 },
  'data-intercom': { label:'インターホン', category:'data', mount:'wall', heightRef:'floor', shape:'intercomPanel', width:0.09, depth:0.03, height:0.15, mountHeight:1.4 },
  'equip-ac-sleeve': { label:'エアコンスリーブ', category:'equipment', mount:'wall', heightRef:'floor', shape:'acSleeve', width:0.08, depth:0.03, height:0.08, mountHeight:2 },
  'equip-vent-fan': { label:'換気扇', category:'equipment', mount:'ceiling', heightRef:'ceiling', shape:'ventFan', width:0.25, depth:0.25, height:0.15, mountHeight:0 },
  'equip-distribution-board': { label:'分電盤', category:'equipment', mount:'wall', heightRef:'floor', shape:'distributionBoard', width:0.4, depth:0.12, height:0.35, mountHeight:1.8 }
};

const ELECTRICAL_ITEMS = [
  { id:'elec-001', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:0.46, z:1.82, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-01' },
  { id:'elec-002', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:1.82, z:1.37, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-02' },
  { id:'elec-003', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:1.82, z:2.28, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-24' },
  { id:'elec-004', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:0.91, z:3.64, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-03' },
  { id:'elec-005', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:0.91, z:5.46, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-04' },
  { id:'elec-006', type:'light-ceiling', category:'lighting', mount:'ceiling', level:1, x:5.01, z:2.3, width:0.35, depth:0.35, height:0.12, mountHeight:0, heightRef:'ceiling', shape:'ceilingLight', label:'シーリングライト', status:'estimated', room:'room-1f-05' },
  { id:'elec-007', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:6.83, z:3.01, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-23' },
  { id:'elec-008', type:'light-ceiling', category:'lighting', mount:'ceiling', level:1, x:4.65, z:4.55, width:0.35, depth:0.35, height:0.12, mountHeight:0, heightRef:'ceiling', shape:'ceilingLight', label:'シーリングライト', status:'estimated', room:'room-1f-06' },
  { id:'elec-200', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:3.3, z:4.6, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト（ソファ上）', status:'estimated', room:'room-1f-06' }, // W06追加：夜間比較検証用の仮配置。ソファ上の読書灯を想定。
  { id:'elec-201', type:'light-pendant', category:'lighting', mount:'ceiling', level:1, x:5.45, z:5.02, width:0.25, depth:0.25, height:0.2, mountHeight:1.9, heightRef:'ceiling', shape:'pendantLight', label:'ペンダントライト（ダイニング）', status:'estimated', room:'room-1f-06' }, // W06追加：夜間比較検証用の仮配置。丸テーブル(fur-008)上を想定し、天井高が高い(勾配天井)ためmountHeightOverrideでテーブル上らしい下がり寸法へ調整。
  { id:'elec-010', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:8.19, z:1.82, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-07' },
  { id:'elec-011', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:10.01, z:1.14, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-08' },
  { id:'elec-012', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:10.01, z:2.05, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-19' },
  { id:'elec-013', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:11.69, z:1.37, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-09' },
  { id:'elec-014', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:13.05, z:1.14, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-20' },
  { id:'elec-015', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:14.11, z:0.91, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト 1', status:'estimated', room:'room-1f-10' },
  { id:'elec-016', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:14.56, z:0.91, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト 2', status:'estimated', room:'room-1f-10' },
  { id:'elec-017', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:15.02, z:1.37, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-21' },
  { id:'elec-018', type:'light-ceiling', category:'lighting', mount:'ceiling', level:1, x:9.33, z:4.1, width:0.35, depth:0.35, height:0.12, mountHeight:0, heightRef:'ceiling', shape:'ceilingLight', label:'シーリングライト', status:'estimated', room:'room-1f-11' },
  { id:'elec-019', type:'light-pendant', category:'lighting', mount:'ceiling', level:1, x:11.38, z:4.1, width:0.25, depth:0.25, height:0.2, mountHeight:0.6, heightRef:'ceiling', shape:'pendantLight', label:'ペンダントライト', status:'estimated', room:'room-1f-11' },
  { id:'elec-020', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:13.42, z:4.1, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-11' },
  { id:'elec-021', type:'light-ceiling', category:'lighting', mount:'ceiling', level:1, x:16.38, z:0.91, width:0.35, depth:0.35, height:0.12, mountHeight:0, heightRef:'ceiling', shape:'ceilingLight', label:'シーリングライト', status:'estimated', room:'room-1f-12' },
  { id:'elec-022', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:18.2, z:0.91, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-12' },
  { id:'elec-023', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:16.38, z:2.73, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-13' },
  { id:'elec-024', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:16.84, z:2.28, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-22' },
  { id:'elec-025', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:18.2, z:2.28, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-14' },
  { id:'elec-026', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:18.2, z:3.41, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-15' },
  { id:'elec-027', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:16.38, z:5.01, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-16' },
  { id:'elec-028', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:18.2, z:5.23, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-17' },
  { id:'elec-029', type:'light-downlight', category:'lighting', mount:'ceiling', level:1, x:17.74, z:7.05, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-1f-18' },
  { id:'elec-030', type:'light-downlight', category:'lighting', mount:'ceiling', level:2, x:13.2, z:0.91, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-2f-01' },
  { id:'elec-031', type:'light-downlight', category:'lighting', mount:'ceiling', level:2, x:14.56, z:0.91, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-2f-02' },
  { id:'elec-032', type:'light-downlight', category:'lighting', mount:'ceiling', level:2, x:13.65, z:2.28, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト 1', status:'estimated', room:'room-2f-03' },
  { id:'elec-033', type:'light-downlight', category:'lighting', mount:'ceiling', level:2, x:15.47, z:2.28, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト 2', status:'estimated', room:'room-2f-03' },
  { id:'elec-034', type:'light-ceiling', category:'lighting', mount:'ceiling', level:2, x:14.11, z:4.55, width:0.35, depth:0.35, height:0.12, mountHeight:0, heightRef:'ceiling', shape:'ceilingLight', label:'シーリングライト', status:'estimated', room:'room-2f-04' },
  { id:'elec-035', type:'light-downlight', category:'lighting', mount:'ceiling', level:2, x:13.65, z:3.19, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-2f-07' },
  { id:'elec-036', type:'light-ceiling', category:'lighting', mount:'ceiling', level:2, x:17.74, z:1.37, width:0.35, depth:0.35, height:0.12, mountHeight:0, heightRef:'ceiling', shape:'ceilingLight', label:'シーリングライト', status:'estimated', room:'room-2f-05' },
  { id:'elec-037', type:'light-downlight', category:'lighting', mount:'ceiling', level:2, x:15.93, z:0.91, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-2f-08' },
  { id:'elec-038', type:'light-ceiling', category:'lighting', mount:'ceiling', level:2, x:17.29, z:4.55, width:0.35, depth:0.35, height:0.12, mountHeight:0, heightRef:'ceiling', shape:'ceilingLight', label:'シーリングライト', status:'estimated', room:'room-2f-06' },
  { id:'elec-039', type:'light-downlight', category:'lighting', mount:'ceiling', level:2, x:17.74, z:3.19, width:0.1, depth:0.1, height:0.02, mountHeight:0, heightRef:'ceiling', shape:'downlight', label:'ダウンライト', status:'estimated', room:'room-2f-09' },
  { id:'elec-041', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:2.33, orientation:'H', center:6.47, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 2', status:'estimated' },
  { id:'elec-043', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:1.82, orientation:'V', center:6.13, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.34, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 1', status:'estimated' },
  { id:'elec-044', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:6.37, orientation:'H', center:3.21, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.62, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 2', status:'estimated' },
  { id:'elec-045', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:1.82, orientation:'V', center:4.32, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.33, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 3', status:'estimated' },
  { id:'elec-046', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:2.73, orientation:'H', center:7.38, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口）', status:'estimated' },
  { id:'elec-047', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:9.1, orientation:'V', center:1.01, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口）', status:'estimated' },
  { id:'elec-048', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:2.73, orientation:'H', center:7.38, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 1', status:'estimated' },
  { id:'elec-049', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:1.82, orientation:'H', center:13.75, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 2', status:'estimated' },
  { id:'elec-050', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:7.28, orientation:'V', center:2.83, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 3', status:'estimated' },
  { id:'elec-051', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:10.92, orientation:'V', center:2.37, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 4', status:'estimated' },
  { id:'elec-052', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:2.28, orientation:'H', center:11.02, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 5', status:'estimated' },
  { id:'elec-053', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:1.82, orientation:'H', center:15.57, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口）', status:'estimated' },
  { id:'elec-054', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:2.73, orientation:'H', center:16.48, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口）', status:'estimated' },
  { id:'elec-055', type:'outlet-double', category:'outlet', mount:'wall', level:2, wallAt:1.82, orientation:'H', center:12.84, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口）', status:'estimated' },
  { id:'elec-056', type:'outlet-double', category:'outlet', mount:'wall', level:2, wallAt:15.47, orientation:'V', center:2.83, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 1', status:'estimated' },
  { id:'elec-057', type:'outlet-double', category:'outlet', mount:'wall', level:2, wallAt:2.73, orientation:'H', center:14.66, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 2', status:'estimated' },
  { id:'elec-058', type:'outlet-double', category:'outlet', mount:'wall', level:2, wallAt:2.73, orientation:'H', center:16.47, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 1', status:'estimated' },
  { id:'elec-059', type:'outlet-double', category:'outlet', mount:'wall', level:2, wallAt:16.38, orientation:'V', center:0.1, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 2', status:'estimated' },
  { id:'elec-060', type:'outlet-double', category:'outlet', mount:'wall', level:2, wallAt:15.47, orientation:'V', center:2.83, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 1', status:'estimated' },
  { id:'elec-061', type:'outlet-double', category:'outlet', mount:'wall', level:2, wallAt:2.73, orientation:'H', center:15.57, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 2', status:'estimated' },
  { id:'elec-062', type:'outlet-double', category:'outlet', mount:'wall', level:2, wallAt:16.38, orientation:'V', center:2.83, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 3', status:'estimated' },
  { id:'elec-063', type:'outlet-double', category:'outlet', mount:'wall', level:2, wallAt:2.73, orientation:'H', center:16.47, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 1', status:'estimated' },
  { id:'elec-064', type:'outlet-double', category:'outlet', mount:'wall', level:2, wallAt:16.38, orientation:'V', center:2.83, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 2', status:'estimated' },
  { id:'elec-074', type:'outlet-grounded', category:'outlet', mount:'wall', level:1, wallAt:13.65, orientation:'V', center:1.92, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付） 1', status:'estimated' },
  { id:'elec-075', type:'outlet-grounded', category:'outlet', mount:'wall', level:1, wallAt:15.47, orientation:'V', center:1.92, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付） 2', status:'estimated' },
  { id:'elec-076', type:'outlet-grounded', category:'outlet', mount:'wall', level:1, wallAt:6.37, orientation:'H', center:7.38, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付） 3', status:'estimated' },
  { id:'elec-077', type:'outlet-grounded', category:'outlet', mount:'wall', level:1, wallAt:6.37, orientation:'H', center:9.2, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付） 4', status:'estimated' },
  { id:'elec-078', type:'outlet-grounded', category:'outlet', mount:'wall', level:1, wallAt:6.37, orientation:'H', center:12.84, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付） 5', status:'estimated' },
  { id:'elec-079', type:'outlet-grounded', category:'outlet', mount:'wall', level:1, wallAt:15.47, orientation:'V', center:0.1, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付）', status:'estimated' },
  { id:'elec-080', type:'outlet-grounded', category:'outlet', mount:'wall', level:1, wallAt:2.73, orientation:'H', center:17.39, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付）', status:'estimated' },
  { id:'elec-081', type:'outlet-grounded', category:'outlet', mount:'wall', level:1, wallAt:15.47, orientation:'V', center:3.74, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付）', status:'estimated' },
  { id:'elec-082', type:'outlet-grounded', category:'outlet', mount:'wall', level:1, wallAt:17.29, orientation:'V', center:4.19, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付）', status:'estimated' },
  { id:'elec-083', type:'outlet-grounded', category:'outlet', mount:'wall', level:1, wallAt:12.45, orientation:'V', center:0.55, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付）', status:'estimated' },
  { id:'elec-084', type:'outlet-grounded', category:'outlet', mount:'wall', level:1, wallAt:1.82, orientation:'H', center:14.66, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付）', status:'estimated' },
  { id:'elec-085', type:'outlet-grounded', category:'outlet', mount:'wall', level:2, wallAt:13.65, orientation:'V', center:0.1, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付）', status:'estimated' },
  { id:'elec-086', type:'outlet-grounded', category:'outlet', mount:'wall', level:2, wallAt:3.64, orientation:'H', center:12.84, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付）', status:'estimated' },
  { id:'elec-087', type:'outlet-grounded', category:'outlet', mount:'wall', level:2, wallAt:0, orientation:'H', center:16.47, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付）', status:'estimated' },
  { id:'elec-088', type:'outlet-grounded', category:'outlet', mount:'wall', level:2, wallAt:3.64, orientation:'H', center:16.47, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付）', status:'estimated' },
  { id:'elec-089', type:'outlet-grounded', category:'outlet', mount:'wall', level:2, wallAt:3.64, orientation:'H', center:16.47, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（アース付）', status:'estimated' },
  { id:'elec-092', type:'outlet-ac', category:'outlet', mount:'wall', level:1, wallAt:2.73, orientation:'H', center:7.87, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:2, heightRef:'floor', shape:'outletPlate', label:'コンセント（AC専用）', status:'estimated' },
  { id:'elec-093', type:'outlet-ac', category:'outlet', mount:'wall', level:2, wallAt:14.56, orientation:'V', center:2.83, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:2, heightRef:'floor', shape:'outletPlate', label:'コンセント（AC専用）', status:'estimated' },
  { id:'elec-094', type:'outlet-ac', category:'outlet', mount:'wall', level:2, wallAt:19.11, orientation:'V', center:0.1, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:2, heightRef:'floor', shape:'outletPlate', label:'コンセント（AC専用）', status:'estimated' },
  { id:'elec-095', type:'outlet-ac', category:'outlet', mount:'wall', level:2, wallAt:6.37, orientation:'H', center:15.57, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:2, heightRef:'floor', shape:'outletPlate', label:'コンセント（AC専用）', status:'estimated' },
  { id:'elec-097', type:'outlet-ih', category:'outlet', mount:'wall', level:1, wallAt:1.82, orientation:'H', center:14.24, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.2, heightRef:'floor', shape:'outletPlate', label:'コンセント（IH専用）', status:'estimated' },
  { id:'elec-098', type:'switch-3way', category:'switch', mount:'wall', level:1, wallAt:1.82, orientation:'H', center:13.75, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路）', status:'estimated' },
  { id:'elec-099', type:'switch-3way', category:'switch', mount:'wall', level:2, wallAt:13.65, orientation:'V', center:0.1, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路）', status:'estimated' },
  { id:'elec-100', type:'switch-3way', category:'switch', mount:'wall', level:1, wallAt:1.82, orientation:'H', center:15.57, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路） 1', status:'estimated' },
  { id:'elec-101', type:'switch-3way', category:'switch', mount:'wall', level:1, wallAt:15.47, orientation:'V', center:1.92, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路） 2', status:'estimated' },
  { id:'elec-102', type:'switch-3way', category:'switch', mount:'wall', level:2, wallAt:2.73, orientation:'H', center:12.84, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路） 1', status:'estimated' },
  { id:'elec-103', type:'switch-3way', category:'switch', mount:'wall', level:2, wallAt:16.38, orientation:'V', center:1.92, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路） 2', status:'estimated' },
  { id:'elec-104', type:'switch-3way', category:'switch', mount:'wall', level:2, wallAt:19.11, orientation:'V', center:3.74, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路） 1', status:'estimated' },
  { id:'elec-105', type:'switch-3way', category:'switch', mount:'wall', level:2, wallAt:15.47, orientation:'V', center:3.32, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路） 2', status:'estimated' },
  { id:'elec-106', type:'switch-3way', category:'switch', mount:'wall', level:1, wallAt:7.28, orientation:'V', center:3.32, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路） 1', status:'estimated' },
  { id:'elec-107', type:'switch-3way', category:'switch', mount:'wall', level:1, wallAt:10.92, orientation:'V', center:2.5, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路） 2', status:'estimated' },
  { id:'elec-110', type:'switch-3way', category:'switch', mount:'wall', level:1, wallAt:3.691, orientation:'H', center:4.44, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.9, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路） 1', status:'estimated' },
  { id:'elec-111', type:'switch-3way', category:'switch', mount:'wall', level:1, wallAt:2.73, orientation:'V', center:1.72, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路） 2', status:'estimated' },
  { id:'elec-112', type:'switch-3way', category:'switch', mount:'wall', level:1, wallAt:2.73, orientation:'H', center:9.2, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路）', status:'estimated' },
  { id:'elec-113', type:'switch-3way', category:'switch', mount:'wall', level:1, wallAt:10.92, orientation:'V', center:0.55, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（3路）', status:'estimated' },
  { id:'elec-114', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:2.73, orientation:'H', center:0.82, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-115', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:0.91, orientation:'V', center:1.01, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-116', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:0.91, orientation:'V', center:1.92, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-120', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:2.33, orientation:'H', center:6.47, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-121', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:2.73, orientation:'V', center:3.32, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-122', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:7.28, orientation:'V', center:1.01, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-123', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:10.92, orientation:'V', center:0.55, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-124', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:2.28, orientation:'H', center:12.55, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-125', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:13.65, orientation:'V', center:0.1, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-126', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:0.91, orientation:'H', center:14.66, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-127', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:2.28, orientation:'H', center:11.51, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-128', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:0, orientation:'H', center:15.57, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切） 1', status:'estimated' },
  { id:'elec-129', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:0, orientation:'H', center:16.47, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切） 2', status:'estimated' },
  { id:'elec-130', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:2.73, orientation:'H', center:16.48, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-131', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:1.82, orientation:'H', center:17.39, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-132', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:2.73, orientation:'H', center:17.39, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-133', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:17.29, orientation:'V', center:3.74, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切） 1', status:'estimated' },
  { id:'elec-134', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:3.64, orientation:'H', center:15.57, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切） 2', status:'estimated' },
  { id:'elec-135', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:4.1, orientation:'H', center:17.39, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-136', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:6.37, orientation:'H', center:16.47, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-137', type:'switch-1p', category:'switch', mount:'wall', level:2, wallAt:1.82, orientation:'H', center:12.84, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-138', type:'switch-1p', category:'switch', mount:'wall', level:2, wallAt:6.37, orientation:'H', center:12.84, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-139', type:'switch-1p', category:'switch', mount:'wall', level:2, wallAt:2.73, orientation:'H', center:12.84, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-140', type:'switch-1p', category:'switch', mount:'wall', level:2, wallAt:2.73, orientation:'H', center:16.96, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-141', type:'switch-1p', category:'switch', mount:'wall', level:2, wallAt:1.82, orientation:'H', center:15.57, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-142', type:'switch-1p', category:'switch', mount:'wall', level:2, wallAt:19.11, orientation:'V', center:2.83, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated' },
  { id:'elec-143', type:'data-tv', category:'data', mount:'wall', level:1, wallAt:1.82, orientation:'V', center:5.23, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.59, heightRef:'floor', shape:'dataJack', label:'TV端子', status:'estimated' },
  { id:'elec-144', type:'data-tv', category:'data', mount:'wall', level:1, wallAt:13.65, orientation:'V', center:2.05, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.3, heightRef:'floor', shape:'dataJack', label:'TV端子', status:'estimated' },
  { id:'elec-145', type:'data-tv', category:'data', mount:'wall', level:2, wallAt:2.73, orientation:'H', center:16.06, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.3, heightRef:'floor', shape:'dataJack', label:'TV端子', status:'estimated' },
  { id:'elec-146', type:'data-tv', category:'data', mount:'wall', level:2, wallAt:12.74, orientation:'V', center:3.74, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.3, heightRef:'floor', shape:'dataJack', label:'TV端子', status:'estimated' },
  { id:'elec-148', type:'data-intercom', category:'data', mount:'wall', level:1, wallAt:0.46, orientation:'H', center:9.2, side:1, width:0.09, depth:0.03, height:0.15, mountHeight:1.4, heightRef:'floor', shape:'intercomPanel', label:'インターホン', status:'estimated' },
  { id:'elec-149', type:'equip-distribution-board', category:'equipment', mount:'wall', level:1, wallAt:13.65, orientation:'V', center:0.25, side:-1, width:0.4, depth:0.12, height:0.35, mountHeight:1.8, heightRef:'floor', shape:'distributionBoard', label:'分電盤', status:'estimated' },
  { id:'elec-150', type:'light-exterior', category:'lighting', mount:'exterior', level:1, face:'N', offset:2, width:0.12, depth:0.1, height:0.15, mountHeight:1.8, heightRef:'floor', shape:'bracketLight', label:'外灯（壁付けブラケット） 1', status:'estimated' },
  { id:'elec-151', type:'light-exterior', category:'lighting', mount:'exterior', level:1, face:'N', offset:11.5, width:0.12, depth:0.1, height:0.15, mountHeight:1.8, heightRef:'floor', shape:'bracketLight', label:'外灯（壁付けブラケット） 2', status:'estimated' },
  { id:'elec-152', type:'outlet-waterproof', category:'outlet', mount:'exterior', level:1, face:'S', offset:3, width:0.1, depth:0.03, height:0.11, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（防水） 1', status:'estimated' },
  { id:'elec-153', type:'outlet-waterproof', category:'outlet', mount:'exterior', level:1, face:'S', offset:10, width:0.1, depth:0.03, height:0.11, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（防水） 2', status:'estimated' },
  { id:'elec-154', type:'outlet-waterproof', category:'outlet', mount:'exterior', level:1, face:'S', offset:17.5, width:0.1, depth:0.03, height:0.11, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（防水） 3', status:'estimated' },
  { id:'elec-m01', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:0, orientation:'V', center:1.13, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口）', status:'estimated', room:'room-1f-01' },
  { id:'elec-m02', type:'data-intercom', category:'data', mount:'wall', level:1, wallAt:0.91, orientation:'H', center:1.98, side:-1, width:0.09, depth:0.03, height:0.15, mountHeight:1.4, heightRef:'floor', shape:'intercomPanel', label:'インターホン', status:'estimated', room:'room-1f-02' },
  { id:'elec-m03', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:4.55, orientation:'H', center:0.59, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切）', status:'estimated', room:'room-1f-03' },
  { id:'elec-m04', type:'switch-1p', category:'switch', mount:'wall', level:1, wallAt:2.73, orientation:'H', center:0.87, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.2, heightRef:'floor', shape:'switchPlate', label:'スイッチ（片切） 2', status:'estimated', room:'room-1f-03' },
  { id:'elec-m05', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:0, orientation:'V', center:3.92, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:1.15, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口）', status:'estimated', room:'room-1f-03' },
  { id:'elec-m06', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:0, orientation:'V', center:2.83, side:1, width:0.09, depth:0.02, height:0.09, mountHeight:0.87, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 2', status:'estimated', room:'room-1f-03' },
  { id:'elec-m08', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:7.28, orientation:'V', center:1.51, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.33, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 2', status:'estimated', room:'room-1f-05' },
  { id:'elec-m10', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:3.691, orientation:'H', center:4.45, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 3', status:'estimated', room:'room-1f-05' },
  { id:'elec-m07', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:3.691, orientation:'H', center:6.83, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:0.25, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口）', status:'estimated', room:'room-1f-23' },
  { id:'elec-m09', type:'outlet-double', category:'outlet', mount:'wall', level:1, wallAt:7.28, orientation:'V', center:4.1, side:-1, width:0.09, depth:0.02, height:0.09, mountHeight:1.64, heightRef:'floor', shape:'outletPlate', label:'コンセント（2口） 4', status:'estimated', room:'room-1f-06' },
];

const ELECTRICAL_ESTIMATE = [
  { id:'est-lighting', label:'電灯配線', quantity:41, types:['light-downlight', 'light-ceiling', 'light-pendant', 'light-bracket', 'light-indirect', 'light-exterior'] },
  { id:'est-outlet-general', label:'コンセント', quantity:25, types:['outlet-double', 'outlet-triple', 'outlet-floor'] },
  { id:'est-outlet-dedicated', label:'専用コンセント', quantity:25, types:['outlet-grounded'] },
  { id:'est-outlet-ac', label:'コンセント（AC専用）', quantity:6, types:['outlet-ac'] },
  { id:'est-outlet-ih', label:'コンセント（IH用）', quantity:2, types:['outlet-ih'] },
  { id:'est-outlet-waterproof', label:'防水コンセント', quantity:3, types:['outlet-waterproof'] },
  { id:'est-switch-1p', label:'スイッチ（片切）', quantity:29, types:['switch-1p', 'switch-dimmer', 'switch-sensor'] },
  { id:'est-switch-3way', label:'スイッチ（3路）', quantity:16, types:['switch-3way'] },
  { id:'est-tv', label:'TV配線', quantity:4, types:['data-tv'] },
  { id:'est-intercom', label:'インターホン', quantity:2, types:['data-intercom'] },
  { id:'est-distribution-board', label:'分電盤', quantity:1, types:['equip-distribution-board'] },
];
