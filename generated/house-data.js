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
  { id:'op-001', type:'door-entrance', category:'door', operation:'swing', face:'N', lx:0.91, w:0.95, h:2.33, sill:0, level:1, hingeSide:'R', swingDir:'out', label:'民泊 玄関ドア', status:'verified' }, // 訂正(2026-08-13)：施主指摘の青線(中心1.35m)に合わせ、トイレ|玄関の壁(x=0.910)起点に修正
  { id:'op-002', type:'window-waist', category:'window', operation:'openable', face:'N', lx:3.5, w:1.76, h:1.03, sill:1.33, level:1, label:'民泊 北窓', status:'verified' }, // 訂正(2026-08-13)：施主指摘の青線位置(中心4.381)に合わせ左へ移動
  { id:'op-003', type:'door-entrance', category:'door', operation:'swing', face:'N', lx:9.535, w:0.95, h:2.33, sill:0, level:1, hingeSide:'R', swingDir:'out', label:'自宅 玄関ドア', status:'verified' }, // 訂正(2026-08-13)：施主指摘により自宅玄関・ホール(x:9.100-10.920)の中心(10.010)に配置
  { id:'op-004', type:'window-fixed-small', category:'window', operation:'fixed', face:'N', lx:11.048, w:0.71, h:1, sill:1, level:1, label:'土間・シューズクローク フィックス窓', status:'estimated' }, // 新規(2026-08-13)：施主指摘の青線位置。A2区画(北壁z=0.455)に該当。高さ・シル高は仮値のため要確認
  { id:'op-005', type:'window-fixed-high', category:'window', operation:'fixed', face:'N', lx:13.699, w:1.716, h:0.45, sill:1.97, level:2, label:'2階 階段北窓', status:'verified' }, // 訂正(2026-08-13)：施主指摘の青線位置に合わせ左へ移動。階段(2F)モジュール(13.651-15.470)内に収まる
  { id:'op-006', type:'window-waist', category:'window', operation:'openable', face:'S', lx:3.585, w:1.77, h:1.03, sill:1.22, level:1, label:'民泊 腰窓', status:'verified' },
  { id:'op-007', type:'window-fixed-small', category:'window', operation:'fixed', face:'S', lx:5.88, w:0.7, h:0.56, sill:1.69, level:1, label:'民泊 小窓', status:'verified' },
  { id:'op-008', type:'window-waist', category:'window', operation:'openable', face:'S', lx:9.2, w:1.8, h:1.03, sill:1.25, level:1, label:'自宅 腰窓', status:'verified' },
  { id:'op-009', type:'window-small', category:'window', operation:'openable', face:'S', lx:10.15, w:0.7, h:0.96, sill:1.29, level:1, label:'自宅 小窓（西）', status:'verified' },
  { id:'op-010', type:'window-full', category:'window', operation:'openable', face:'S', lx:11.665, w:1.73, h:2.26, sill:0.19, level:1, label:'自宅LDK 掃き出し窓', status:'verified' },
  { id:'op-011', type:'window-small', category:'window', operation:'openable', face:'S', lx:14.62, w:0.7, h:0.96, sill:1.29, level:1, label:'自宅 小窓（東）', status:'verified' },
  { id:'op-012', type:'window-waist', category:'window', operation:'openable', face:'S', lx:13.681, w:1.568, h:0.96, sill:1.32, level:2, label:'2階 南窓①(子供部屋1)', status:'verified' }, // 訂正(2026-08-13)：施主指摘の青線位置に合わせ左へ移動。子供部屋1の右下に位置
  { id:'op-013', type:'window-waist', category:'window', operation:'openable', face:'S', lx:16.375, w:1.771, h:0.96, sill:1.32, level:2, label:'2階 南窓②(夫婦寝室)', status:'verified' }, // 訂正(2026-08-13)：施主指摘の青線位置に合わせ左へ移動。夫婦寝室南側の中央
  { id:'op-014', type:'window-waist', category:'window', operation:'openable', face:'E', lz:0.923, w:1.623, h:0.97, sill:1.28, level:2, label:'2階 東窓①(子供部屋2)', status:'verified' }, // 訂正(2026-08-13)：施主指摘の青線位置に合わせ上へ移動。子供部屋2東側の中央付近
  { id:'op-015', type:'window-waist', category:'window', operation:'openable', face:'E', lz:3.745, w:1.457, h:0.97, sill:1.28, level:2, label:'2階 東窓②(夫婦寝室)', status:'verified' }, // 訂正(2026-08-13)：施主指摘の青線位置に合わせ上へ移動。夫婦寝室東側の中央付近
  { id:'op-016', type:'window-fixed-high', category:'window', operation:'fixed', face:'E', lz:3.065, w:0.81, h:0.36, sill:2.23, level:1, label:'1階 東の細長窓', status:'verified' },
  { id:'op-017', type:'door-louver', category:'door', operation:'swing', face:'E', lz:7, w:0.85, h:2.33, sill:0, level:1, hingeSide:'R', swingDir:'out', label:'南土間 東のルーバー戸', status:'verified' },
  { id:'op-018', type:'window-fixed-small', category:'window', operation:'fixed', face:'W', lz:1.95, x:12.74, w:0.65, h:0.6, sill:1.86, level:2, label:'2階 廊下西窓', status:'verified' }, // 訂正(2026-08-13)：はみ出し指摘により廊下(2F)の中心(z=2.275)を基準に、両側0.38m前後の余裕を持たせて再配置
  { id:'op-019', type:'window-fixed-high', category:'window', operation:'fixed', face:'W', lz:3.2, w:0.85, h:0.35, sill:2, level:1, label:'洗面脱衣室 天井近くフィックス窓', status:'verified' }, // 訂正(2026-08-13)：施主指摘により旧「平屋 西の細長窓」(lz:3.895)を削除し、新規に天井近くの位置(sill=2.0)へ細長いフィックス窓を配置
];

const SOUND_WALL = { x:7.28, z0:0.91, z1:6.37, level:1, topY:LEVELS.eaveLow }; // 西端から7,280mm(910mm×8マス)。施主指摘により修正（2026-08-13）

const INTERIOR_DOORS = [
  { id:'door-001', type:'door-hinged', operation:'swing', label:'トイレ⟷玄関', wallAt:0.91, orientation:'V', center:2.33, width:0.8, height:2, floor:1, hingeSide:'R', swingDir:'out', status:'verified' },
  { id:'door-002', type:'door-hinged', operation:'swing', label:'玄関⟷洗面脱衣室', wallAt:2.73, orientation:'H', center:1.355, width:0.8, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-003', type:'door-hinged', operation:'swing', label:'洗面脱衣室⟷UB', wallAt:4.55, orientation:'H', center:1.371, width:0.8, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-004', type:'door-hinged', operation:'swing', label:'玄関⟷LDK張り出し', wallAt:2.73, orientation:'H', center:2.274, width:0.8, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-005', type:'door-hinged', operation:'swing', label:'玄関⟷洋室', wallAt:2.73, orientation:'V', center:2.329, width:0.8, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-006', type:'door-hinged-wide', operation:'swing', label:'ヌック⟷LDK', wallAt:2.73, orientation:'H', center:8.218, width:0.91, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-007', type:'door-hinged-wide', operation:'swing', label:'自宅玄関・ホール⟷LDK', wallAt:2.73, orientation:'H', center:9.555, width:0.91, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-008', type:'door-hinged-wide', operation:'swing', label:'自宅玄関・ホール⟷土間・シューズクローク', wallAt:10.92, orientation:'V', center:0.91, width:0.91, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-009', type:'door-hinged-wide', operation:'swing', label:'土間・シューズクローク⟷LDK', wallAt:2.275, orientation:'H', center:13.195, width:0.91, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-010', type:'door-hinged-wide', operation:'swing', label:'LDK(キッチン部)⟷廊下+収納', wallAt:15.471, orientation:'V', center:2.275, width:0.91, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-011', type:'door-hinged-wide', operation:'swing', label:'ファミリークローク⟷廊下+収納', wallAt:1.82, orientation:'H', center:16, width:0.91, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-012', type:'door-hinged-wide', operation:'swing', label:'トイレ(東)⟷洗面(東)', wallAt:2.73, orientation:'H', center:17.746, width:0.91, height:2, floor:1, hingeSide:'R', swingDir:'out', status:'verified' },
  { id:'door-013', type:'door-hinged-wide', operation:'swing', label:'廊下+収納⟷脱衣室', wallAt:3.64, orientation:'H', center:16.836, width:0.91, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-014', type:'door-hinged-wide', operation:'swing', label:'脱衣室⟷UB(東)', wallAt:17.291, orientation:'V', center:4.584, width:0.91, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-015', type:'door-hinged-wide', operation:'swing', label:'脱衣室⟷南土間', wallAt:6.37, orientation:'H', center:16.836, width:0.91, height:2, floor:1, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-016', type:'door-hinged-wide', operation:'swing', label:'トイレ(2F)⟷廊下(2F)', wallAt:1.82, orientation:'H', center:13.195, width:0.91, height:2, floor:2, hingeSide:'R', swingDir:'out', status:'verified' },
  { id:'door-017', type:'door-hinged-wide', operation:'swing', label:'廊下(2F)⟷子供部屋1', wallAt:2.73, orientation:'H', center:15.015, width:0.91, height:2, floor:2, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-018', type:'door-hinged-wide', operation:'swing', label:'廊下(2F)⟷子供部屋2', wallAt:16.38, orientation:'V', center:2.275, width:0.91, height:2, floor:2, hingeSide:'R', swingDir:'in', status:'verified' },
  { id:'door-019', type:'door-hinged-wide', operation:'swing', label:'廊下(2F)⟷夫婦寝室', wallAt:2.73, orientation:'H', center:15.925, width:0.91, height:2, floor:2, hingeSide:'R', swingDir:'in', status:'verified' },
];

const WALLS = [
  { id:'wall-1f-001', level:1, x0:13.651, x1:19.11, z0:1.82, z1:1.82, orientation:'H' },
  { id:'wall-1f-002', level:1, x0:10.92, x1:13.651, z0:2.275, z1:2.275, orientation:'H' },
  { id:'wall-1f-003', level:1, x0:0, x1:2.73, z0:2.73, z1:2.73, orientation:'H' },
  { id:'wall-1f-004', level:1, x0:7.28, x1:10.92, z0:2.73, z1:2.73, orientation:'H' },
  { id:'wall-1f-005', level:1, x0:17.291, x1:19.11, z0:2.73, z1:2.73, orientation:'H' },
  { id:'wall-1f-006', level:1, x0:15.471, x1:17.291, z0:3.64, z1:3.64, orientation:'H' },
  { id:'wall-1f-007', level:1, x0:2.73, x1:7.28, z0:3.691, z1:3.691, orientation:'H' },
  { id:'wall-1f-008', level:1, x0:17.291, x1:19.11, z0:4.095, z1:4.095, orientation:'H' },
  { id:'wall-1f-009', level:1, x0:0, x1:1.82, z0:4.55, z1:4.55, orientation:'H' },
  { id:'wall-1f-010', level:1, x0:16.38, x1:19.11, z0:6.37, z1:6.37, orientation:'H' },
  { id:'wall-1f-011', level:1, x0:0.91, x1:0.91, z0:0.91, z1:2.73, orientation:'V' },
  { id:'wall-1f-012', level:1, x0:1.82, x1:1.82, z0:2.73, z1:6.37, orientation:'V' },
  { id:'wall-1f-013', level:1, x0:2.73, x1:2.73, z0:0.91, z1:3.691, orientation:'V' },
  { id:'wall-1f-014', level:1, x0:10.92, x1:10.92, z0:0.455, z1:2.73, orientation:'V' },
  { id:'wall-1f-015', level:1, x0:13.651, x1:13.651, z0:0, z1:2.275, orientation:'V' },
  { id:'wall-1f-016', level:1, x0:15.471, x1:15.471, z0:0, z1:6.37, orientation:'V' },
  { id:'wall-1f-017', level:1, x0:17.291, x1:17.291, z0:1.82, z1:6.37, orientation:'V' },
  { id:'wall-2f-001', level:2, x0:12.74, x1:16.38, z0:1.82, z1:1.82, orientation:'H' },
  { id:'wall-2f-002', level:2, x0:12.74, x1:19.11, z0:2.73, z1:2.73, orientation:'H' },
  { id:'wall-2f-003', level:2, x0:13.651, x1:13.651, z0:0, z1:1.82, orientation:'V' },
  { id:'wall-2f-004', level:2, x0:15.47, x1:15.47, z0:0, z1:1.82, orientation:'V' },
  { id:'wall-2f-005', level:2, x0:15.47, x1:15.47, z0:2.73, z1:6.37, orientation:'V' },
  { id:'wall-2f-006', level:2, x0:16.38, x1:16.38, z0:1.82, z1:2.73, orientation:'V' }
];

const ROOMS_APPROX = {
  1: [
    { name:'トイレ(民泊)', x0:0, x1:0.91, z0:0.91, z1:2.73, conf:'高', note:'面積1.66㎡相当・マイホームクラウド値と一致確認' },
    { name:'玄関(民泊)', x0:0.91, x1:2.73, z0:0.91, z1:2.73, conf:'高', note:'訂正(2026-08-13)：西端(x=0)と東端(x=7.280)を基準とした再キャリブレーションで、玄関の東壁はx=2.730が正しいと判明（前回のx=1.820は近接点同士のキャリブレーション誤差による誤り）' },
    { name:'洗面脱衣室', x0:0, x1:1.82, z0:2.73, z1:4.55, conf:'高', note:'面積3.31㎡相当。この行はx=1.820に壁あり(ピクセル解析で確認)' },
    { name:'UB(民泊)', x0:0, x1:1.82, z0:4.55, z1:6.37, conf:'中', note:'面積3.31㎡相当。洗面脱衣室と同幅と仮定' },
    { name:'洋室', x0:2.73, x1:7.28, z0:0.91, z1:3.691, conf:'高', note:'訂正(2026-08-13)：西端をx=2.730に戻し、洋室|LDK境界z=3.691で再検算。箱面積12.60㎡は実際11.18㎡に近い（+13%）。x=1.820-2.730×z=2.730-6.370の範囲(洗面所/浴室の東側)は未モデル化の欠き（LDK側に含まれる可能性）。ラベルから面積表記は削除(2026-08-13)' },
    { name:'LDK(民泊)', x0:1.82, x1:7.28, z0:2.73, z1:6.37, poly:[[1.82,2.73],[2.73,2.73],[2.73,3.691],[7.28,3.691],[7.28,6.37],[1.82,6.37]], conf:'高', note:'施主指摘(2026-08-13)によりLDK本体＋張り出し部をL字ポリゴンとして統合。内部の継ぎ目線は表示されない。ラベルから面積表記は削除(2026-08-13)。自宅側のLDKと区別するため「(民泊)」を付記' },
    { name:'ヌック', x0:7.28, x1:9.1, z0:0.91, z1:2.73, conf:'高', note:'床面はFL+200mm（施工会社図面表記の一段上がった小上がり）。訂正(2026-08-13)：マイホームクラウド画像で西端が防音壁位置(x=7.280)から始まると判明（前回のx=9.100は誤り）。幅1.820m確定・奥行は面積3.31㎡から逆算(1.819m)しz1=2.730とほぼ一致。ラベルから面積表記は削除(2026-08-13)' },
    { name:'自宅玄関・ホール', x0:9.1, x1:10.92, z0:0.455, z1:2.73, conf:'高', note:'施主指摘(2026-08-13)により赤枠の座標をピクセル解析。旧「自宅玄関・土間・ホール」から西半分を分離' },
    { name:'土間・シューズクローク', x0:10.92, x1:13.651, z0:0, z1:2.275, poly:[[10.92,0.455],[12.74,0.455],[12.74,0],[13.651,0],[13.651,2.275],[10.92,2.275]], conf:'高', note:'訂正(2026-08-13)：施主指摘により南端をz=2.730→2.275に縮小(0.5マス分をLD側へ移管)' },
    { name:'階段（曲がり階段）＋パントリー', x0:13.651, x1:15.471, z0:0, z1:1.82, conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×2マス(1.820m角)に確定' },
    { name:'LDK', x0:7.28, x1:15.471, z0:1.82, z1:6.37, poly:[[7.28,2.73],[10.92,2.73],[10.92,2.275],[13.651,2.275],[13.651,1.82],[15.471,1.82],[15.471,6.37],[7.28,6.37]], conf:'高', note:'確定(2026-08-13)：施主指摘によりLD＋キッチンを統合しLDKに変更。北端が3段階（z=2.730→2.275→1.820）の階段状になっているのが実際の間取り' },
    { name:'ファミリークローク', x0:15.471, x1:19.11, z0:0, z1:1.82, conf:'高', note:'確定(2026-08-13)：施主指摘により4マス×2マス(3.640m×1.820m)、東側全幅で確定' },
    { name:'廊下＋収納', x0:15.471, x1:17.291, z0:1.82, z1:3.64, conf:'高', note:'確定(2026-08-13)：施主指摘により2マス×2マス(1.820m角)で確定。西列' },
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
    { name:'子供部屋1', x0:12.74, x1:15.47, z0:2.73, z1:6.37, conf:'高', note:'確定(2026-08-13)：施主指摘により3マス×4マス(2.730m×3.640m)で確定' },
    { name:'子供部屋2', x0:15.47, x1:19.11, z0:0, z1:2.73, poly:[[15.47,0],[19.11,0],[19.11,2.73],[16.38,2.73],[16.38,1.82],[15.47,1.82]], conf:'高', note:'確定(2026-08-13)：施主指摘により矩形＋廊下の張り出し分を除いたL字で確定' },
    { name:'夫婦寝室', x0:15.47, x1:19.11, z0:2.73, z1:6.37, conf:'高', note:'確定(2026-08-13)：施主指摘により4マス×4マス(3.640m角)で確定' }
  ]
};

const ROOFS = [
  { id:'roof-a1', kind:'lean_to', x0:0, x1:9.1, zNorth:0.41, zSouth:7.28, pitch:0.15, thickness:0.15, base:3.4 },
  { id:'roof-a2', kind:'lean_to', x0:9.1, x1:12.74, zNorth:-0.045, zSouth:7.28, pitch:0.15, thickness:0.15, base:3.4 },
  { id:'roof-2f-gable', kind:'gable', x0:12.52, x1:19.33, zNorth:-0.558, zRidge:3.185, zSouth:6.928, yEave:6.3, yRidge:7.423, thickness:0.18 }
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
  { id:'fur-036', type:'bed-single', level:1, x:4.23, z:2.64, rotation:180, width:0.97, depth:1.95, height:0.5, label:'ベッド1', status:'estimated', room:'room-1f-05' }, // 施主指摘(2026-08-15)により、セミダブル1台からシングル2台へ変更
  { id:'fur-037', type:'bed-single', level:1, x:5.42, z:2.67, rotation:180, width:0.97, depth:1.95, height:0.5, label:'ベッド2', status:'estimated', room:'room-1f-05' }, // 施主指摘(2026-08-15)により、セミダブル1台からシングル2台へ変更
  { id:'fur-041', type:'desk', level:1, x:6.9, z:1.47, rotation:90, width:1.1, depth:0.6, height:0.72, label:'デスク', status:'estimated', room:'room-1f-05' }, // 施主指摘(2026-08-15)によりワークデスクを新規配置
  { id:'fur-042', type:'chair', level:1, x:6.46, z:1.49, rotation:90, width:0.45, depth:0.5, height:0.85, label:'椅子', status:'estimated', room:'room-1f-05' }, // 施主指摘(2026-08-15)によりデスク用の椅子を新規配置
  { id:'fur-005', type:'wardrobe', level:1, x:6.89, z:3.04, rotation:90, width:1.2, depth:0.6, height:1.8, label:'ワードローブ', status:'estimated', room:'room-1f-05' },
  { id:'fur-006', type:'kitchen-counter', level:1, x:6.87, z:5.43, rotation:270, width:1.8, depth:0.65, height:0.85, label:'キッチン', status:'estimated', room:'room-1f-06' },
  { id:'fur-007', type:'refrigerator', level:1, x:6.86, z:4.06, rotation:90, width:0.69, depth:0.7, height:1.83, label:'冷蔵庫', status:'estimated', room:'room-1f-06' },
  { id:'fur-008', type:'dining-table-4', level:1, x:5.01, z:5.25, rotation:0, width:1.2, depth:0.8, height:0.72, label:'ダイニングテーブル', status:'estimated', room:'room-1f-06' },
  { id:'fur-009', type:'chair', level:1, x:5.01, z:4.8, rotation:180, width:0.45, depth:0.5, height:0.85, label:'椅子1', status:'estimated', room:'room-1f-06' },
  { id:'fur-010', type:'chair', level:1, x:5.01, z:5.65, rotation:0, width:0.45, depth:0.5, height:0.85, label:'椅子2', status:'estimated', room:'room-1f-06' },
  { id:'fur-011', type:'sofa-2seat', level:1, x:3.54, z:4.14, rotation:0, width:1.5, depth:0.85, height:0.8, label:'ソファ', status:'estimated', room:'room-1f-06' },
  { id:'fur-012', type:'tv-board', level:1, x:2.05, z:5.22, rotation:90, width:1.5, depth:0.4, height:0.45, label:'テレビボード', status:'estimated', room:'room-1f-06' },
  { id:'fur-038', type:'coffee-table', level:1, x:3.54, z:4.87, rotation:0, width:1, depth:0.5, height:0.4, label:'ローテーブル', status:'estimated', room:'room-1f-06' }, // 施主指摘(2026-08-15)によりソファ前に新規配置
  { id:'fur-043', type:'counter-table', level:1, x:3.6, z:6.14, rotation:180, width:1.7, depth:0.35, height:1, label:'カウンターテーブル', status:'estimated', room:'room-1f-06' }, // 施主指摘(2026-08-15)により南窓際にカフェ風のカウンターテーブルを新規配置
  { id:'fur-044', type:'chair', level:1, x:3.46, z:5.97, rotation:180, width:0.45, depth:0.7, height:0.85, label:'椅子（カウンター）', status:'estimated', room:'room-1f-06' }, // 施主指摘(2026-08-15)により、カウンターテーブル用の椅子を新規配置
  { id:'fur-013', type:'kitchen-counter', level:1, x:13.63, z:5.08, rotation:90, width:2.55, depth:0.65, height:0.85, label:'キッチン', status:'estimated', room:'room-1f-11' },
  { id:'fur-014', type:'refrigerator', level:1, x:15.11, z:5.99, rotation:180, width:0.69, depth:0.7, height:1.83, label:'冷蔵庫', status:'estimated', room:'room-1f-11' },
  { id:'fur-015', type:'dining-table-6', level:1, x:12.08, z:4.69, rotation:0, width:1.4, depth:0.85, height:0.72, label:'ダイニングテーブル', status:'estimated', room:'room-1f-11' },
  { id:'fur-016', type:'chair', level:1, x:11.79, z:4.07, rotation:180, width:0.45, depth:0.5, height:0.85, label:'椅子1', status:'estimated', room:'room-1f-11' },
  { id:'fur-017', type:'chair', level:1, x:12.47, z:4.12, rotation:180, width:0.45, depth:0.5, height:0.85, label:'椅子2', status:'estimated', room:'room-1f-11' },
  { id:'fur-018', type:'chair', level:1, x:11.81, z:5.24, rotation:0, width:0.45, depth:0.5, height:0.85, label:'椅子3', status:'estimated', room:'room-1f-11' },
  { id:'fur-019', type:'chair', level:1, x:12.43, z:5.28, rotation:0, width:0.45, depth:0.5, height:0.85, label:'椅子4', status:'estimated', room:'room-1f-11' },
  { id:'fur-020', type:'sofa-3seat', level:1, x:9.38, z:4.87, rotation:90, width:2, depth:0.85, height:0.8, label:'ソファ', status:'estimated', room:'room-1f-11' },
  { id:'fur-021', type:'tv-board', level:1, x:7.56, z:4.82, rotation:90, width:1.5, depth:0.4, height:0.45, label:'テレビボード', status:'estimated', room:'room-1f-11' },
  { id:'fur-039', type:'coffee-table', level:1, x:8.36, z:4.87, rotation:90, width:1, depth:0.5, height:0.4, label:'ローテーブル', status:'estimated', room:'room-1f-11' }, // 施主指摘(2026-08-15)によりソファ前に新規配置
  { id:'fur-034', type:'cupboard', level:1, x:15.23, z:4.34, rotation:90, width:2.55, depth:0.45, height:1.9, label:'カップボード', status:'estimated', room:'room-1f-11' },
  { id:'fur-022', type:'toilet-tankless', level:1, x:18.79, z:2.27, rotation:90, width:0.4, depth:0.65, height:0.75, label:'便器（タンクレス）', status:'estimated', room:'room-1f-14' },
  { id:'fur-023', type:'vanity', level:1, x:18.19, z:3.86, rotation:180, width:1.82, depth:0.45, height:1.9, label:'洗面化粧台', status:'estimated', room:'room-1f-15' },
  { id:'fur-024', type:'washing-machine', level:1, x:15.8, z:5.99, rotation:0, width:0.64, depth:0.72, height:1.05, label:'洗濯機', status:'estimated', room:'room-1f-16' },
  { id:'fur-025', type:'bathtub', level:1, x:18.2, z:5.86, rotation:180, width:1.8, depth:1, height:0.6, label:'浴槽', status:'estimated', room:'room-1f-17' },
  { id:'fur-026', type:'toilet', level:2, x:13.19, z:0.35, rotation:0, width:0.45, depth:0.75, height:1, label:'便器（タンク付き）', status:'estimated', room:'room-2f-01' },
  { id:'fur-027', type:'bed-single', level:2, x:14.47, z:5.86, rotation:90, width:0.97, depth:1.95, height:0.5, label:'ベッド', status:'estimated', room:'room-2f-04' },
  { id:'fur-028', type:'desk', level:2, x:13.06, z:4.79, rotation:270, width:1.1, depth:0.6, height:0.72, label:'デスク', status:'estimated', room:'room-2f-04' },
  { id:'fur-029', type:'shelf', level:2, x:13.19, z:2.9, rotation:0, width:0.9, depth:0.3, height:1.8, label:'本棚', status:'estimated', room:'room-2f-04' },
  { id:'fur-030', type:'bed-single', level:2, x:18.57, z:1.71, rotation:180, width:0.97, depth:1.95, height:0.5, label:'ベッド', status:'estimated', room:'room-2f-05' },
  { id:'fur-031', type:'desk', level:2, x:17.44, z:0.3, rotation:0, width:1.1, depth:0.6, height:0.72, label:'デスク', status:'estimated', room:'room-2f-05' },
  { id:'fur-032', type:'bed-double', level:2, x:18.07, z:5.07, rotation:90, width:2, depth:2, height:0.5, label:'ベッド', status:'estimated', room:'room-2f-06' },
  { id:'fur-033', type:'wardrobe', level:2, x:17.73, z:3.2, rotation:180, width:2.73, depth:0.91, height:1.8, label:'ワードローブ', status:'estimated', room:'room-2f-06' },
  { id:'fur-040', type:'tv-board', level:2, x:15.72, z:5, rotation:90, width:1.5, depth:0.4, height:0.45, label:'テレビボード', status:'estimated', room:'room-2f-06' }, // 施主指摘(2026-08-15)により西壁側に新規配置
];
