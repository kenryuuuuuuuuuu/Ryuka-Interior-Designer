# アーキテクチャ・データ契約

2026-09-08補足：以下にはThree.js/白模型のみだった時点の記述が残っています。現在は家具を含むBlender→UEのvisual生成系があります。追加契約は [VISUAL_TWIN_PLAN.md](VISUAL_TWIN_PLAN.md)、状態更新は [REFRESH_WORKFLOW.md](REFRESH_WORKFLOW.md)、内覧は [UNREAL_WALKTHROUGH.md](UNREAL_WALKTHROUGH.md) を参照してください。家具・電気・開口の正本はそれぞれのJSONであり、house.jsonへ戻して統合しません。

このリポジトリの「正本はどこか」「どう変更するか」を定義する。技術的な仕組みの解説。プロジェクトの背景・経緯は [BACKGROUND.md](BACKGROUND.md)、現在の進捗・未解決事項は [STATUS.md](STATUS.md) を参照。

## 正本と生成パイプライン

**`data/house.json` がこのリポジトリの唯一の正本（Single Source of Truth）。** 建物の寸法・部屋・壁・屋根はすべてここで管理し、Three.js表示用データとBlenderモデルの両方をここから生成する。**家具・設備の配置は`data/furniture.json`（型のライブラリは`data/furniture-catalog.json`）が正本で、こちらはHTML側（Three.js）でのみ扱い、Blenderへは今のところ生成しない**（施主の判断：配置の試行錯誤はインタラクティブ性が命なのでHTML側で詰める。詳細は[BACKGROUND.md](BACKGROUND.md)の変更履歴ログ参照）。**電気設備（コンセント・スイッチ・照明等）の配置は`data/electrical.json`（型のライブラリは`data/electrical-catalog.json`）が正本で、家具と同じ理由でHTML側のみ**（2026-08-18、第1段階）。**窓・ドアの配置は`data/openings.json`（外部）・`data/interior-doors.json`（室内、型のライブラリはドアが`data/door-catalog.json`・窓が`data/window-catalog.json`）が正本で、こちらはThree.js・Blenderの両方が読み込む**（外壁・室内壁の開口の切り欠きに使うため）。窓・ドアは2026-08-15に`house.json`から分離した（元は`openings`/`interiorDoors`という配列としてhouse.json内にあった）。`blender/build_house.py`は`data/house.json`と同じディレクトリにある`door-catalog.json`/`window-catalog.json`/`openings.json`/`interior-doors.json`を自動的に読み込む

```
data/house.json（建物データの正本）
data/furniture-catalog.json（家具・設備の型ライブラリ）
data/furniture.json（家具・設備の配置インスタンス）
data/door-catalog.json（ドアの型ライブラリ）
data/window-catalog.json（窓の型ライブラリ）
data/openings.json（外部の窓・ドアの配置インスタンス）
data/interior-doors.json（室内ドアの配置インスタンス）
data/electrical-catalog.json（電気設備の型ライブラリ）
data/electrical.json（電気設備の配置インスタンス）
data/electrical-estimate.json（電気工事見積書の明細）
    │
    ├─ node scripts/build-web-data.mjs
    │      ↓
    │  generated/house-data.js（生成物。手で編集しない）
    │      ↓ <script src>で読み込み
    │  interior-white-model.html（Three.js白模型。表示・操作ロジックのみ）
    │
    └─ blender --background --python blender/build_house.py -- --input data/house.json --output build/ryuka-white-model.blend
           ↓
       Blenderモデル（house.json + door-catalog.json/window-catalog.json/openings.json/interior-doors.jsonが対象。家具は未対応）
```

2026-08-14以前は逆方向（`interior-white-model.html` → `sync-house-from-html.mjs` → `house.json`）だった。HTMLに建物データを手で埋め込み、それをスクリプトが逆解析してJSONへ同期する構造で、rooms/wallsだけは同期対象外という無理のある例外を抱えていた。今は house.json 側を直接編集する一方向パイプラインに変更済み（詳細は [BACKGROUND.md 5章](BACKGROUND.md#5-変更履歴ログ)）。

## データ契約

### 内装描画用の追加出力（2026-09-06）

`scripts/build-web-data.mjs`は既存のWeb・内壁・外壁出力に加えて`generated/visual-envelope.json`を生成します。内容は`slopedCeilingPieces`（Webと同じ勾配天井分割）、`slabs`（階段の到着階の床開口を除外）、`flatCeilings`（階段出発階の天井開口・勾配天井領域を除外）です。単位m、水平座標x/z、GL高さの参照元は引き続きhouse.jsonです。生成ファイルを手修正しません。`--check`で鮮度を検証します。

従来の`blender/build_house.py`に加えて、`blender/build_interior.py`がゲストLDKの家具・内装を生成します。上記の「家具はHTML側のみ」は従来の白模型の範囲であり、内装版は家具の正本・カタログも読み込みます。配置の編集は引き続きThree.js／JSONで行います。電気設備は入力スナップショットに保持しますが、内装版の発光器具としてはまだ描画しません。

仕上げ・比較条件は`data/visual/guest-ldk-study.json`、転送はBlender標準GLBとUE Interchangeです。再生成・検証・未対応範囲は [VISUAL_TWIN_PLAN.md](VISUAL_TWIN_PLAN.md) を参照してください。

UEの表面模様・粗さは`data/visual/unreal-finishes.json`で管理します。生成プロジェクトでは`study-bindings.json`がそのビルド内のActor／材質スロットと役割を対応付けます。この対応表自体は次回生成へ流用しません。比較条件の保存はローカルの`study-state.json`で、部屋ID・案名・光源・露出・カメラだけを新しい生成物へ再適用します。建物・家具データの逆輸入ではありません。

- 単位: メートル
- 座標系: 建物ローカル座標。`x` = 西→東、`z` = 北→南、`y` = GLからの高さ（上向き）
- Blenderへのマッピング: `(x, z, y)` → Blenderの `(X, -Y, Z)`。北がBlenderの+Y方向になる
- すべての永続的なオブジェクトは安定したIDを持つ（`id`フィールド）
- `status` は `verified`（確定）/ `derived`（間接的な根拠あり）/ `estimated`（推測）の3段階
- `note` は個々のエンティティの根拠・修正履歴を記録する任意フィールド（施主指摘の内容、キャリブレーションの経緯など）。データを移動・変換する際は必ず引き継ぐこと
- `provenance`（ファイル全体）は出典一覧・修正履歴を記録する

## ファイル構成

| ファイル | 役割 |
|---|---|
| `data/house.json` | 建物データの正本。寸法・部屋・壁・屋根 |
| `data/house.schema.json` | `house.json` のデータ契約（JSON Schema、Draft 2020-12） |
| `data/furniture-catalog.json` | 家具・設備の「型」のライブラリ（種類ごとの標準寸法・形状指定） |
| `data/furniture.json` | 家具・設備の配置インスタンス（どこに何を置くか）。正本 |
| `data/furniture.schema.json` | `furniture.json` のデータ契約（JSON Schema） |
| `data/door-catalog.json` / `data/window-catalog.json` | 窓・ドアの「型」のライブラリ（種類ごとの標準寸法・開閉方式） |
| `data/openings.json` | 外部の窓・ドアの配置インスタンス。正本 |
| `data/openings.schema.json` | `openings.json` のデータ契約（JSON Schema） |
| `data/interior-doors.json` | 室内ドアの配置インスタンス。正本 |
| `data/interior-doors.schema.json` | `interior-doors.json` のデータ契約（JSON Schema） |
| `data/electrical-catalog.json` | 電気設備（コンセント・スイッチ・照明・情報系配線・屋外設備）の「型」のライブラリ |
| `data/electrical.json` | 電気設備の配置インスタンス。正本。見積書に基づく154箇所の完全配置（たたき台）＋Web UIでの削除・追加編集 |
| `data/electrical.schema.json` | `electrical.json` のデータ契約（JSON Schema） |
| `data/electrical-estimate.json` | 電気工事の見積書の明細（数量）。正本。Web UI編集後の現在数と明細単位で比較するために使う |
| `scripts/build-web-data.mjs` | 上記の正本ファイル群 → `generated/house-data.js` を生成する |
| `scripts/seed-electrical.mjs` | 電気設備154箇所を部屋別配分から機械的に配置し`data/electrical.json`を再生成する一回限りのツール（常設パイプラインには含めない） |
| `generated/house-data.js` | 生成物。`interior-white-model.html` が `<script src>` で読み込む |
| `generated/interior-walls.json` | 生成物。`house.json`のroomsから自動導出した内壁データ |
| `generated/exterior-walls.json` | 生成物。`house.json`のfootprintsから自動導出した外壁（建物の真の外周）データ。屋外電気設備・外壁沿いの壁付け設備の検証に使う |
| `interior-white-model.html` | Three.js製の内装白模型。表示・操作ロジックのみを持つ。単体でブラウザに開ける |
| `blender/build_house.py` | `house.json`・`door-catalog.json`・`window-catalog.json`・`openings.json`・`interior-doors.json`からBlender白模型を再生成するスクリプト（家具・電気設備は対象外） |
| `tests/validate_house.py` | `house.json` の整合性チェック（依存ライブラリなしで動作） |
| `tests/validate_furniture.py` | `furniture-catalog.json` / `furniture.json` の整合性チェック（house.jsonのroomsとの照合含む） |
| `tests/validate_openings.py` | `door-catalog.json` / `window-catalog.json` / `openings.json` / `interior-doors.json` の整合性チェック（house.jsonのfootprints、および`generated/interior-walls.json`との照合含む。実行前に`node scripts/build-web-data.mjs`が必要） |
| `tests/validate_electrical.py` | `electrical-catalog.json` / `electrical.json` の整合性チェック（house.jsonのrooms/footprints、および`generated/interior-walls.json`・`generated/exterior-walls.json`との照合含む。実行前に`node scripts/build-web-data.mjs`が必要） |
| `index.html` | GitHub PagesのルートURL用リダイレクト。`interior-white-model.html`へ転送するだけ |
| `manifest.webmanifest` / `sw.js` / `icon.svg` | PWA化（ホーム画面追加・オフライン起動）の設定一式。詳細は下記「公開（GitHub Pages / PWA）」 |
| `vendor/three.min.js` | Three.js本体のローカル同梱コピー（CDN非依存。オフライン起動のため） |

## rooms / walls について

`rooms`（部屋の輪郭ポリゴン）が間取りの唯一の正本。**`walls`（壁芯データ）は`data/house.json`には存在しない**（2026-08-16に廃止）。かつては`rooms`とは別に`walls`を人手で保守していたが、部屋を分割するたびに更新を忘れる事故が繰り返し起きたため（内覧モードで「壁があったりなかったり」という不具合の主因になった。詳細は[BACKGROUND.md](BACKGROUND.md)）、`rooms`だけを唯一の情報源とし、壁は毎回機械的に導出する方式に統一した。

- **導出ロジックは`scripts/build-web-data.mjs`の`deriveInteriorWalls()`に一箇所だけ実装されている。** 同じレベル（1F/2F）の全部屋ポリゴンを総当たりし、2部屋が軸に沿った辺（H/V）を共有している区間を「内壁」として抽出する。同一直線上で隙間なく連続する区間は1本にまとめる（`mergeCollinearWalls()`。3部屋以上が同じ直線に並ぶ通し壁が、部屋ペアごとに細切れになって、その上のドア幅がどの区間にも収まらないと誤判定される問題への対策）。斜めの辺（x0/x1もz0/z1も一致しない辺）は対象外で、`orientation:'D'`（斜め框など）はこれまで通り`data/interior-doors.json`側で個別に表現する
- 建物の外周壁は対象外（Three.js側の`exteriorSegmentsForLevel()`、Blender側の`build_exterior_walls()`が別途`footprints`+`openings`から導出する。こちらは元々`rooms`とは独立した仕組み）
- ドアによる開口の切り欠きも、この導出処理では行わない（消費側＝Three.jsの`doorGapsForLevel()`/`cutGaps()`、Blenderの`build_interior_walls()`が、それぞれ`data/interior-doors.json`を見て壁生成時に切り欠く。これは元の設計を踏襲している）
- 導出結果は`generated/interior-walls.json`として書き出される（`node scripts/build-web-data.mjs`で再生成、`generated/house-data.js`と同様に**手で編集しないコミット対象の生成物**）。Three.js側は`generated/house-data.js`内の`WALLS`定数として、Blender側（`blender/build_house.py`の`load_data()`）はこのJSONを直接読み込む形でそれぞれ利用する。**壁の導出ロジックをPythonで再実装することはしない**（HTML側とBlender側の壁がズレるリスクを避けるため、単一の実装をJSON経由で共有する）
- `rooms`を分割・追加・移動したら、`node scripts/build-web-data.mjs`を再実行するだけで、Three.js・Blender双方の壁が自動的に追従する（手動更新の手順が不要になった）

`rooms`の`polygon`は矩形・L字（軸に沿った頂点のみ）が基本だが、斜め框のような斜めの境界線を持つ部屋も表現できる（`polyWire()`はThree.js側で任意の多角形を描画できるため）。斜めの辺は壁の自動導出の対象外なので、そのような境界には必ず`data/interior-doors.json`側で`orientation:'D'`の開口を用意すること。

**間取りの精細化（部屋の分割）の進め方**：家具・窓ドアのような「既存の枠内で位置を調整する」編集とは異なり、部屋を分割する作業（例：1つの部屋を2部屋に割る、部屋の中に収納区画を切り出す）はトポロジーそのものを変える。編集モードは作らず、施主からスクリーンショット＋書き込み線などで指示を受け、`rooms`を直接編集する方式にしている（検討の経緯は[BACKGROUND.md](BACKGROUND.md)参照）。部屋を分割したら、境界上にドアを置くのか（`data/interior-doors.json`に登録）、ただの壁のままにするのか（何もしない。壁は自動的にできる）を決めるだけでよく、以前のように`walls`エントリを別途追加する必要はない。

## 家具・設備（furniture）

2026-09-06追記：任意の `elevation`（床から家具底面までのm、省略時0）を追加しました。Three.jsの高さ編集・書き出しとBlender/Unreal生成で共有します。テレビの前面規約と歩行判定の範囲は[家具の設置高さ](FURNITURE_ELEVATION.md)を参照してください。

- `data/furniture-catalog.json`：家具・設備の「型」。`type`（キー）ごとに`label`・`category`（`fixture`=施工会社が設置する造作／`furniture`=後から置く家具）・`shape`（下記）・標準寸法（`width`/`depth`/`height`）・`clearance`（前面等に必要な最小空き）を持つ
- `data/furniture.json`：配置インスタンス。`type`でカタログを参照し、`x`/`z`（footprint中心、建物ローカル座標）・`level`・`rotation`・任意で`widthOverride`等（このインスタンスだけ標準寸法から変える場合）を持つ
- **`label`の命名規則（配置インスタンスの`label`のみ。カタログ側の`label`＝型の一般名はこの限りではない）**：部屋が増えるほど平面図上でラベルが密集するため、部屋名・棟名（民泊／自宅／1F／2F／部屋の呼称など）はラベルに含めない。部屋自体のラベルで既に表示されているため冗長になる
  - 同じ部屋の中に同じ`type`が複数あり、用途が同じグループに属する場合（例：ダイニングチェア4脚）：「椅子1」「椅子2」…と連番を付ける
  - 同じ部屋の中に同じ`type`が複数あるが、用途のグループが異なる場合（例：ダイニングの椅子とは別に、カウンターテーブル用の椅子がある）：連番ではなく「椅子（カウンター）」のように短い用途名を括弧で付ける
  - 見た目・仕様が変わる型の違い（便器の「タンク付き」「タンクレス」など）はラベルに残す。これは立地情報ではなく機能情報のため
  - 例：「テレビボード（民泊LDK）」→「テレビボード」、「便器（1F民泊・タンク付き）」→「便器（タンク付き）」
- **見た目は既製3Dモデル（GLB等）を使わず、箱・円柱の組み合わせで作る。** サイズを自由に変えられること、PWAのオフライン保存が軽いことを優先した判断（詳細は[BACKGROUND.md](BACKGROUND.md)）。組み方は`interior-white-model.html`の`FURNITURE_SHAPES`（`shape`名 → 描画関数のマップ）で定義する。新しい家具の種類を追加する場合は、カタログに`type`を追加し、対応する`shape`が`FURNITURE_SHAPES`になければ関数も追加する
- **`rotation`は0/90/180/270度のみ。** 斜め配置は当たり判定の実装コストに見合わないため対象外とした（将来必要になれば再検討）
- **Web UI上での配置編集（第2段階、`interior-white-model.html`内に実装）**：平面図モードで「✎ 家具編集」ボタンをONにすると、家具のクリック/タップ選択→ドラッグ移動、パネルからの90度回転・幅/奥行/高さ変更ができる
  - 編集内容は`FURNITURE_ITEMS`（生成データ、正本ではない）を直接書き換えず、`furnitureEdits`という差分オブジェクトとして持ち、`effectiveFurniture()`で重ねて描画する
  - `furnitureEdits`はブラウザの`localStorage`（キー`ryuka-furniture-edits-v1`）に自動保存される。**これは正本ではなく、あくまで作業中の下書き。** ページを閉じても残るが、別端末・別ブラウザには残らない（`Ryuka-Landscape-Designer`の弱点と同じ制約を踏まえた設計）
  - 「furniture.jsonを書き出す」ボタンで、編集を反映した完全なJSONをダウンロードできる。**これを`data/furniture.json`に上書きしてコミットするのが、正本を更新する唯一の手段。** ダウンロードするだけではリポジトリには反映されない
  - 「編集をすべて取り消す」でlocalStorageの下書きを破棄し、`data/furniture.json`の内容に戻せる

## 窓・ドア（door-window）

- `data/door-catalog.json`・`data/window-catalog.json`：窓・ドアの「型」。`type`（キー）ごとに`label`・`category`（`door`／`window`）・`operation`・標準寸法（`width`/`height`/`sill`）を持つ。furniture-catalog.jsonと同じ考え方
  - ドアの`operation`：`swing`=開き戸／`double-swing`=両開き戸／`fold`=片開き折れ戸／`double-fold`=両開き折れ戸／`slide`=引き戸／`open`=ドアなしの開口／`open-arch`=ドアなしの開口（天端アーチ）。窓は`openable`=開閉可／`fixed`=FIX
  - `open-arch`のみ`archRise`（円弧が占める高さ）を追加で持つ。`height`はアーチ頂部までの全高で、springline（円弧が始まる高さ）は`height-archRise`
- `data/openings.json`：外部（外壁）の窓・ドアの配置インスタンス。`type`でカタログを参照し、`face`（N/S/E/W）＋`offset`（その面に沿った建物ローカル座標の絶対値。**中心ではなく開始端（西端/北端）**）で位置を表す。E/W面は`wallX`を省略すると建物端（x=0またはx=19.11）とみなす
- `data/interior-doors.json`：室内ドアの配置インスタンス。`type`でカタログを参照し、`wallAt`（壁の固定座標）＋`orientation`（H/V）＋`center`（壁沿いの位置、こちらは中心）で位置を表す
  - **`orientation:'D'`（斜め壁）**：`wallAt`/`center`の代わりに`x0`/`z0`/`x1`/`z1`（始点・終点、建物ローカル座標）で位置を表す。壁のない開口（`operation:open`/`open-arch`）専用の想定で、開き戸・引き戸（`hingeSide`/`swingDir`/`slideDir`）や壁線スライド編集（Stage 2 UI）の対象外。`interior-white-model.html`の`placeDiagonalInteriorDoor()`が、始点・終点を結ぶ厚みのない平板で描画する
- どちらも任意で`widthOverride`/`heightOverride`/`sillOverride`（このインスタンスだけ標準寸法から変える場合）を持つ
- **ドアの開き勝手**：`operation:swing`の型を使うインスタンスは`hingeSide`（`L`/`R`、蝶番側）＋`swingDir`（`in`/`out`）、`operation:double-swing`（両開き戸）は`swingDir`のみ（両端をそれぞれ蝶番にした2枚の扉が左右対称に開くため`hingeSide`は不要）、`operation:slide`なら`slideDir`（`L`/`R`、引き込み方向）を持つ。`operation:fold`（片開き折れ戸）は`swing`と同じく`hingeSide`+`swingDir`、`operation:double-fold`（両開き折れ戸）は`double-swing`と同じく`swingDir`のみ。`operation:open`/`open-arch`（ドアなしの開口）はどちらも不要（扉本体を描かない）。外部の窓・ドア（`openings.json`）は`face`（N/S/E/W）から「外側」の方向が一意に決まるため、`swingDir:'out'`は文字通り建物の外側へ開く向きになる。室内ドア（`interior-doors.json`）には「外」の概念がないため、`swingDir`は「壁を挟んでどちら向きに開くか」を軸ベースで簡易表現したものにとどまる。隣接する部屋同士の内外関係までは今のデータモデルにはない（見た目を見ながら調整する運用）
- **折れ戸（`fold`/`double-fold`）の描画**：`interior-white-model.html`の`drawFoldLeaf()`が、建具表の図記号（開口の片側または両側を蝶番にした折れ線）を模して描く。蝶番側の固定点A・開口幅の中点にあたる自由端C（ともに壁面上）・折れ点Bの3点を、A-B=B-C=A-C（=開口幅/2）の正三角形になるよう配置し（Bは壁から`(開口幅/2)*sin60°`張り出す）、A→B→Cの2本の折れ線として描画する。`double-fold`は両端をそれぞれ蝶番にした2組の`drawFoldLeaf()`呼び出しで表現する（`double-swing`を`drawSwingLeaf()`2回で表現するのと同じパターン）
- **開口（アーチ）の描画**：`interior-white-model.html`の`archOpeningMesh()`が、天端が円弧になった板の輪郭を黒線のみ（`open`と同じくピンクの塗りつぶしなし）で描く。この板は完全に鉛直な厚みゼロの形状のため、平面図モード（真上からの正投影）では単体だとほぼ視認できない（塗りつぶしの有無に関係なく、真上から見ると輪郭線がほぼ一直線に潰れて見えてしまう）。そのため`placeInteriorDoor()`/`placeOpening()`側で、`open`と同じ矩形の枠線（`EdgesGeometry(BoxGeometry(...))`）を必ず重ねて描き、平面図でも最低限の視認性（他の開口と同じ矩形の黒枠）を確保している（2026-08-16、施主指摘により追加。詳細は3章の教訓の表）。アーチの円弧そのものを確認したい場合は俯瞰・内覧モードで見ること
  - 現在の室内ドア19件はすべて開き戸として移行しており、`hingeSide`/`swingDir`は施工会社の建具表が未確認のため暫定値（[STATUS.md](STATUS.md)の未解決事項を参照）
- `house.json`から2026-08-15に分離した（元は`openings`/`interiorDoors`という配列としてhouse.json内にあった）。理由は、家具編集の「書き出しボタンでファイルを上書き」という運用を安全に行うため。house.jsonに残したままだと、書き出しは`rooms`/`walls`/`roofs`等を含むファイル全体が対象になり、ブラウザ側が保持していない付帯情報を巻き込んで構造データを壊すリスクがある
- **Web UI上での配置編集（第2段階、`interior-white-model.html`内に実装）**：平面図モードで「✎ 窓・ドア編集」ボタンをONにすると、窓・ドアのクリック/タップ選択→壁に沿ったドラッグでスライドができる。家具編集とは仕組みが異なる点が2つある
  - **自由な2D移動ではなく、壁線上の1次元スライドに制約される。** 室内ドアは`WALLS`（重複統合済みの壁芯データ）、外部の窓・ドアは`footprints`（求積図のゾーン区分）から対応する壁の区間を求め、その範囲内にクランプする（`wallRangeForInteriorDoor()`/`wallRangeForOpening()`。ロジックは`tests/validate_openings.py`の壁突合せチェックと同じ考え方）。「別の壁・別の面へ移動」はドラッグでは扱わない
  - **家具編集と同時にはONにできない（排他）。** `setDoorEditMode(true)`は`setEditMode(false)`を呼び、逆も同様
  - パネルからは種類（`type`）の切替、幅/高さ/シル高の変更、開き勝手（開き戸は蝶番側+開く向き、引き戸は引き込み方向）の変更ができる。種類を切り替えると寸法は新しい型の標準値にリセットされ、`operation`が変われば開き勝手の項目も対応するものに切り替わる（例：開き戸→引き戸で`hingeSide`/`swingDir`は無視され`slideDir`が使われる）
  - 編集内容は`OPENINGS`/`INTERIOR_DOORS`（生成データ、正本ではない）を直接書き換えず、`doorWindowEdits`という差分オブジェクトとして持ち、`effectiveOpening()`/`effectiveInteriorDoor()`で重ねて描画する。ブラウザの`localStorage`（キー`ryuka-door-window-edits-v1`）に自動保存される、あくまで作業中の下書きという位置づけは家具編集と同じ
  - 「openings.json」「interior-doors.json」の2つの書き出しボタンで、それぞれ編集を反映した完全なJSONをダウンロードできる。データが2ファイルに分かれているため、家具のような単一の書き出しボタンにはしていない。**これらを`data/openings.json`・`data/interior-doors.json`に上書きしてコミットするのが、正本を更新する唯一の手段**
  - **注意（既知の制約）**：この書き出し処理は`orientation:'D'`（斜め壁）の`x0`/`z0`/`x1`/`z1`を素通しする専用分岐を持つが、`note`フィールドは（door-window問わず）書き出さない。`generated/house-data.js`側がそもそも`note`を実データとして持たず、ソースコメントとしてしか埋め込んでいないため（`scripts/build-web-data.mjs`の`withNote()`参照）。Web UI編集を書き出して`data/*.json`に上書きすると、既存の`note`（変更履歴の説明文）が消えるので、書き出し後は元のJSONと差分を見比べて必要な`note`を書き戻すこと

## 電気設備（electrical）

家具・窓ドアに続く3本目の柱。着工後は変更コストが跳ね上がるため優先度が高い（[STATUS.md](STATUS.md)参照）。2026-08-18に**第1段階（データ構造＋読み取り専用の3D/平面図表示）**→**第2段階（Web UI編集）**→施主から天領住宅の電気工事見積書（電灯配線41／コンセント25／専用コンセント25／AC専用6／IH用2／防水コンセント3／スイッチ片切29／3路16(8組)／TV4／インターホン2／分電盤1＝合計154箇所）に基づく**完全配置（154箇所、屋外含む）＋俯瞰モードの部屋フォーカス＋電気設備編集の俯瞰専用化**、と3段階で実装した。当たり判定は対象外（電気設備は壁・天井付けで歩行の障害物にならないため）。

### データモデル：`mount`による3系統＋屋外の位置表現

- `data/electrical-catalog.json`：コンセント・スイッチ・照明・情報系配線（LAN/TV/インターホン）・関連設備（エアコンスリーブ・換気扇・分電盤）の「型」。furniture-catalog.jsonと同じ考え方で、種類ごとの標準寸法（`width`/`depth`/`height`）に加え、電気設備特有の3フィールドを持つ
  - `mount`（`wall`=壁付け／`ceiling`=天井付け／`floor`=床付け／`exterior`=屋外設置）：`data/electrical.json`側でどの位置表現（下記）を使うかを型ごとに決める
  - `heightRef`（`floor`=床から／`ceiling`=天井から。`exterior`は常に`floor`）＋`mountHeight`：取付け高さの基準面と距離。`heightRef:floor`はFLからのセンターハイト（コンセント0.25m・スイッチ1.2m等、日本の住宅の慣習値）、`heightRef:ceiling`は天井面から器具の取付け原点までの下がり寸法（0=天井面フラッシュ、ペンダント照明は吊り下げ長ぶん正の値）
  - `shape`：`interior-white-model.html`の`ELECTRICAL_SHAPES`に対応（`light-exterior`は`bracketLight`関数を流用し、専用のshape関数は追加していない）
- `data/electrical.json`：配置インスタンス。正本。位置表現が型の`mount`によって3系統に分かれる
  - `mount:wall`（コンセント・スイッチ・情報系・分電盤・エアコンスリーブ・ブラケット照明）：`data/interior-doors.json`と同じ`wallAt`＋`orientation`（H/V）＋`center`に加え、`side`（`1`/`-1`、壁のどちら側を向くか）。壁付け設備は家具のような自由回転を持たず、`orientation`+`side`から`rotation.y`を自動導出する
  - `mount:ceiling`/`floor`（照明・換気扇・床コンセント）：`data/furniture.json`と同じ`x`/`z`（自由座標）＋`room`（任意）
  - `mount:exterior`（防水コンセント・外灯）：`data/openings.json`の外部窓・ドアと同じ`face`(N/S/E/W)+`offset`+`level`(+任意`wallX`)。`side`は持たず、回転は`face`から一意に決まる（外部開口の`swingDir:'out'`と同じ考え方）
  - いずれも任意で`widthOverride`/`depthOverride`/`heightOverride`/`mountHeightOverride`（このインスタンスだけ標準値から変える場合）を持つ。`circuit`（回路名・ブレーカー番号）は将来の配線図用に予約したフィールドで、現状は表示に使わない
- `data/electrical.schema.json`：`mount`によって必須フィールドが変わるため、スキーマ自体はどの位置系フィールドも任意にし、`mount`別の必須チェックは`tests/validate_electrical.py`側で行う（`interior-doors.schema.json`と`validate_openings.py`のoperation別チェックと同じ考え方）

### 外壁データ（`generated/exterior-walls.json`）

屋外電気設備の配置検証と、壁付け設備が「外壁の室内側」に付く場合の壁突合せ検証のために新設した、`generated/interior-walls.json`（内壁の自動導出）と対になる生成物。`interior-white-model.html`の`exteriorSegmentsForLevel()`/`subtractRanges()`（footprints群の共有辺を「区間の引き算」方式で取り除き、建物の真の外周だけを抽出するロジック。内覧モードの当たり判定で従来から使用）を`scripts/build-web-data.mjs`側に複製し（HTML側は変更なし、内覧モード用に引き続き実行時計算する）、`node scripts/build-web-data.mjs`で書き出す。

- **壁付け設備の探索先を内壁+外壁の結合に拡張**：`generated/interior-walls.json`（間仕切り壁）だけでは「外壁の室内側に付くコンセント」（実際の住宅で最も多いケース）を表現できないため、`mount:wall`の壁突合せは常にこの2つを結合したリストに対して行う（`interior-white-model.html`の`wallRangeForElectrical()`は`wallSegmentsByLevel`＝内壁+外壁+ドア開口の切り欠き済みデータを検索、`tests/validate_electrical.py`の`check_within_wall()`は`generated/interior-walls.json`+`generated/exterior-walls.json`の単純結合を検索。関数自体は壁の由来を区別しない）
- **屋外(`mount:exterior`)専用の検証**：`check_exterior_within_wall()`が`face`/`offset`から対応するfootprint・外壁セグメントを解決し（`footprint_for_exterior_face()`、`blender/build_house.py`の`footprint_for_opening()`と同じ考え方）、範囲内に収まっているか確認する

### 表示・編集の実装（`interior-white-model.html`）

- `ELECTRICAL_SHAPES`（型ごとの組み立て関数、`fPart()`ベース）→`placeElectricalItem()`（型→shape関数→`groups.electrical1/2`へ追加→`makeLabel()`）という流れは家具（`FURNITURE_SHAPES`/`placeFurnitureItem()`）と同一パターン。**ドアのような「平面図記号＋内覧用の別実装」の二重実装はしない**（電気設備には開閉のような動的状態がなく、俯瞰・平面図・内覧の全モードで同一メッシュを使い回せば足りるため）。壁付け設備用の共有ジオメトリ`ePlate()`、天井/床付け設備用の`eDisc()`の2つのヘルパーに形状を集約し、各shape関数はその上に小さな装飾（差込口・トグルドット等）を足すだけの薄いラッパーにしている
  - `exteriorElectricalGeom(item)`：`mount:exterior`の`face`+`offset`から実座標・外向き回転を計算する（`openingWallGeom()`と対称的な設計）
  - 平面図の記号表現：JIS Z 8017準拠の専用2D記号エンジンは作らず、3D形状そのものを真上から見てJIS記号に近いシルエットになるよう設計する折衷案（コンセント＝円盤＋差込口ドット2つ、スイッチ＝角プレート＋中央ドット等）。配色はカテゴリごとに彩度の高い色（電源=紫、情報系=ティール、照明=琥珀、関連設備=濃紺）にし、既存の凡例色（窓の水色・ドアのマゼンタ等）と衝突しないようにしている（2026-08-18、施主指摘：淡色だと平面図の他要素に埋もれて見えない）
  - 当たり判定は持たない。電気設備は壁・天井付けで歩行の障害物にならないため
- **配置編集（第2段階、俯瞰モード専用）**：「✎ 電気設備編集」ボタンは俯瞰(orbit)モードでのみ表示される（平面図では小さすぎて視認・選択ができないため、2026-08-18に平面図モードのサポートを取りやめた）。`groundPointAt(clientX,clientY,planeY,cam=orthoCam)`のようにカメラを引数化し、電気設備の呼び出し側だけ透視投影の`camera`を渡す（家具・窓ドアの編集は`orthoCam`のまま平面図限定を維持）
  - **壁付け設備**：窓ドア編集と同じ「壁に沿った1次元ドラッグ＋範囲クランプ」。`wallRangeForElectrical()`は`wallSegmentsByLevel`（内壁+外壁+ドア切り欠き済み）を検索し、ドアでセグメントが複数に分かれる場合は`center`を含む区間を優先、無ければ最も近い区間にフォールバックする
  - **天井/床付け設備**：家具編集と同じ「自由な2Dドラッグ（クランプなし）」
  - **屋外(`mount:exterior`)設備**：選択・種類/寸法編集は可能だが、ドラッグでの位置移動は対象外（`data/electrical.json`を直接編集する運用）
  - **家具編集・窓ドア編集との三者択一**：`setEditMode`/`setDoorEditMode`/`setElectricalEditMode`が、ONになる際に他の2つを両方OFFにする
  - **ドラッグ中はメッシュを再構築しない**：`holder.position`/`holder.rotation.y`の直接更新のみ（軽量）。type変更・寸法変更は`rebuildElectricalItem()`で再構築、位置（X/Y/Z）変更だけは`repositionElectricalItem()`という軽量パス（座標のみ更新、形状は変えない）
  - **種類（type）切替の候補は`mount`が同じもの同士に制限**：`category`ではなく`mount`が位置表現を決めるフィールドのため（`light-bracket`はwall、他の照明はceilingのように同じcategoryでもmountが異なる型が実在する）
  - **XYZ数値入力パネル（微調整用、2026-08-19追加）**：パネルの「X/Y/Z」欄（`updateElectricalPositionFields()`/`applyElectricalPositionEdit()`）から座標を直接タイプして微調整できる。Yは`heightRef`（floor/ceiling）の違いを吸収し、常に「その階の床(FL)からの高さ」として統一表示・入力する（旧「取付け高さ」欄を統合・置き換え）。`mount:wall`は壁に沿う側の軸だけ編集可能で、固定側（壁面＝`wallAt`）は`disabled`にして壁ロックを可視化する（ドラッグ移動も元々壁沿いの1次元にしか動かせない設計だったため、既存の制約を数値入力でも同じ形で表現しただけ）。数値入力も`wallRangeForElectrical()`と同じ式でクランプする。`mount:exterior`は3欄とも参考表示のみで`disabled`（ドラッグ移動と同じくスコープ外、位置を変えたい場合は`data/electrical.json`を直接編集する運用のまま）
  - **壁面変更（2026-08-20追加）**：`mount:wall`の設備は、XYZ欄と「向き」欄の間に「設置している壁」セレクトを表示し、**別の壁面へ丸ごと移動**できる。壁の候補は電気設備「追加」機能と同じ`wallsForRoom(roomId, level)`（[:3821](interior-white-model.html#L3821)付近）を再利用し、対象の部屋は選択中アイテムの現在位置から`electricalRoomProbePoint()`＋`findRoomIdAt()`で動的に判定する（部屋フォーカス中かどうかに関わらず動作する）。壁を変えると新しい壁の空き位置を`findFreeWallSlot()`（[:3739](interior-white-model.html#L3739)、`excludeId`引数を追加し選択中アイテム自身を重なり判定から除外できるようにした）で求め、`wallAt`/`orientation`/`side`/`center`をまとめて差分に書き込む。壁の向きが変わる＝`rotation.y`の再計算が必要なため、位置だけを直接書き換える軽量パス（`repositionElectricalItem()`）ではなく、型変更と同じ`rebuildElectricalItem()`（削除→作り直し）を使う。選択中の壁は`updateWallHighlight()`が黄色半透明のボックス（`electricalSelectionHelper`と同じ`0xffcf3a`）で3D上にハイライトする（`wallHighlightMesh`、選択解除や`mount:wall`以外への切替で消える）
  - 編集内容は`electricalEdits`という差分オブジェクトとして持ち、`effectiveElectrical()`で重ねて描画（`localStorage`キー`ryuka-electrical-edits-v1`）。「electrical.jsonを書き出す」ボタンでダウンロードし`data/electrical.json`へ上書きコミットする運用
  - **削除（2026-08-19追加）**：既存項目の書き換え（`electricalEdits`）とは別に、項目の増減を`electricalAdded`（追加した項目そのもの）・`electricalDeleted`（削除したidの一覧、いわば墓標）という2つのdiffで表現する（`localStorage`キーはそれぞれ`ryuka-electrical-added-v1`/`ryuka-electrical-deleted-v1`）。既存項目の書き換えと項目自体の増減を1つの構造に混ぜると「削除したのに編集が残る」のような復元時の不整合が起きやすいため、意図的に分けている。`ELECTRICAL_ITEMS`（`data/electrical.jsonから生成された不変の元データ）への直接参照は、この2つのdiffを踏まえた`allElectricalItems()`（表示・配置対象。追加分を加え削除済みを除く）・`findElectricalBase(id)`（削除済みも含めて探す、復元用）の2関数に集約し、初期配置ループ・`exportElectricalJSON()`・`buildElectricalSummary()`など全ての参照元をこの2関数経由に置き換えた。パネルの「🗑 この設備を削除」ボタン（`deleteSelectedElectrical()`）は`confirm()`の後`electricalDeleted`にidを積んで`removeElectricalMesh()`するだけで、`data/electrical-catalog.json`の型定義や元データは変えない（即座にデータを消さない）ため、一覧モーダルの「削除した設備」欄からいつでも`restoreDeletedElectrical(id)`で復元できる

### 俯瞰モードの部屋フォーカス

平面図では小さい電気設備が視認できず、俯瞰モードは壁が多く別室の壁が邪魔になるという施主指摘（2026-08-18）を受けて追加。左メニューの部屋選択セレクトから選ぶと、対象室だけを表示し、他室の壁・家具・電気設備・ドア窓・寸法ラベル・グリッド・屋根を隠してカメラをその部屋にフィットさせる。俯瞰モード限定（`mode!=='orbit'`で自動解除、内覧モードへ入る際も`enterWalkMode()`冒頭で防御的に解除する）。

- **部屋選択セレクトのoptgroup分け（2026-08-20更新）**：1Fは民泊棟・自宅棟の2棟にまたがるため「1F（民泊）」「1F（自宅）」に分け、2Fは全室自宅棟のため「2F（自宅）」の1つにまとめる（`populateRoomFocusSelect()`）。棟の判定は部屋名の文字列一致には頼らず、`SOUND_WALL.x`（民泊-自宅防音壁のx座標、7.28）を境に各部屋のbbox中心が西側か東側かで機械的に決める（部屋が増減しても追従する）

- `scripts/build-web-data.mjs`の`buildRoomsApprox()`が`ROOMS_APPROX`各要素に部屋ID（`house.rooms[].id`）を出力するようになった
- `roomMeshesById: Map<id,{mesh,label,level,bbox}>`：`ROOMS_APPROX`から部屋メッシュを生成するループで、部屋ごとに`roomGroup`（THREE.Group）を挟んでから`groups.approx1/2`へ追加し保存する。**`boxWire()`/`polyWire()`は本体メッシュと輪郭線(EdgesGeometry)を別オブジェクトとして`parent`に直接addするため、本体メッシュだけを`visible=false`にしても輪郭線が残ってしまう**ことに対する回避策（部屋ごとに小さなGroupでまとめてから親へ足すことで、Group単位でまとめて表示/非表示にできるようにした）。同じ理由でSOUND_WALL（`soundWallGroup`）・GUARD_WALLS各要素（`guardWallGroups`）もGroupで包んでいる
- `pointInPolygon(x,z,pts)`（レイキャスティング法）／`findRoomIdAt(x,z,level)`：座標がどの部屋に属するかを`ROOMS_APPROX`から動的に判定する。家具・電気設備の既存`room`フィールドは使わない（ドラッグで位置が変わっても追随せず陳腐化するため）
- `electricalRoomProbePoint(eff)`：壁付け設備は壁面から`side`が向く方向へ0.1mオフセットした点で部屋所属を判定する（壁自体は2部屋の境界にあり内外判定できないため）。屋外(`exterior`)設備は常にどの部屋にも属さない扱いで、フォーカス中は非表示
- `doorMatchesFocusedRoom(entry, targetLevel, targetId)`（2026-08-19追加）：`doorWindowMeshes`の各エントリに配置時点で持たせた`probe`メタ情報を使い、ドア・窓も部屋所属で表示/非表示を判定する。内部ドア（H/V）・斜め開口（D）は2部屋の境界にあり片側の情報（壁付け設備の`side`に相当するもの）を持たないため、壁の両側をプローブしていずれかが対象室ならtrue（対象室への出入口のドアは表示され続ける）。外部開口は`outSign`の逆方向（屋内側）の1点だけで判定する
- **防音壁・腰壁は部屋フォーカス中、常に非表示**：特定の部屋に紐付かない構造物のため、部屋所属の判定はせずフォーカス中は一律隠す（対象室に接していても表示しない。「対象室以外に色を付けない」という要望を最も単純に満たす形）
- `focusRoom(id)`/`clearFocus()`：カメラは対象室のbboxにフィット（`camera.fov`から必要な`camDist`を逆算）。**ラベル（DOM要素）はメッシュの`visible`に連動しない**ため（`updateLabels()`は一度`display:'none'`にした要素をそのまま維持し、`refreshLabelVis()`はチェックボックスの状態だけを見て毎回block/noneを決め直す実装のため、単純に`style.display`へ直接書き込むと後からチェックボックスを操作した際に部屋フォーカスと無関係に復活してしまう）、`l.hiddenByFocus`という専用フラグを立て、`refreshLabelVis()`側でこのフラグも判定に含めることで恒久的に非表示を維持する設計にした（ドア・窓・防音壁・腰壁はラベルを持たないため、この仕組みの対象外＝メッシュの`visible`切替だけで完結する）

### 電気設備の追加：どの壁面に付けるかを選ぶ（2026-08-19追加）

削除に比べ、追加は「どこに置くか」の指定が必要な分やっかい。特に壁付け設備（`mount:wall`）は、追加後のXYZ編集パネルで壁面側の座標をロックする設計（前段の「XYZ数値入力パネル」参照）にしているため、「とりあえず置いてから動かす」ができない。**追加する時点で壁を選ばせ、`side`（壁のどちら側＝部屋の内側を向くか）まで確定させる**設計にした（施主指摘：「追加は注意が必要。どの面に追加するかを選べるようにしてくれないと、設置した後、特定の座標がロックされている」）。

- **入口**：部屋フォーカス中の右上パネル（`#roomFocusElecPanel`）の「＋ この部屋に設備を追加」ボタン（`openElectricalAdd()`）。部屋フォーカス中にしか出さないことで、追加先の部屋・階が文脈から自動的に確定する
- **`wallsForRoom(roomId, level)`**：部屋に接する壁セグメント（`wallSegmentsByLevel`＝内壁+外壁+ドア切り欠き済み、腰壁`guardHeight`ありは対象外）を、部屋の内側を向く`side`込みで返す。`electricalRoomProbePoint()`（壁面から`side`の方向へ`ROOM_PROBE_OFFSET`だけずらした点で部屋所属を判定する）の逆変換：壁セグメントと部屋のbboxの重なり区間を取り、その中点の両側をそれぞれ`ROOM_PROBE_OFFSET`だけずらして`findRoomIdAt()`で判定し、対象室に入った側を`side`として採用する。壁の呼び名（北側/南側/西側/東側）も`orientation`+`side`から機械的に決まる（建物座標系はx=西→東、z=北→南のため、H&side>0→北側／H&side<0→南側／V&side>0→西側／V&side<0→東側）
- **追加ダイアログ**（`#electricalAddOverlay`、`#spawnOverlay`と同じモーダル骨格）：型はカタログ全型からカテゴリ順に選択（`mount:exterior`は既存のドラッグ移動・XYZ編集と同じくスコープ外のため候補から除く）。選んだ型が`mount:wall`のときだけ`wallsForRoom()`の候補（例：「北側の壁（幅910mm）」）を壁面セレクトに出し、`mount:ceiling/floor`のときは「部屋の中央付近に配置します」という案内文に切り替わる
- **追加の確定**（`#eaSubmit`）：`ELECTRICAL_CATALOG[type]`（プロファイル）の`category`/`mount`/`width`/`depth`/`height`/`mountHeight`/`heightRef`/`shape`をそのまま複製した完全な形の項目を作る（`scripts/build-web-data.mjs`の`buildElectricalItems()`がNode側でカタログのプロファイルを展開して`ELECTRICAL_ITEMS`を生成しているのと同じことをブラウザ側でも行う必要がある。これを怠ると`shape`欠落で`placeElectricalItem()`が何も描画できず`electricalMeshes`にも登録されない、という実装中に踏んだ不具合がある）。壁付けは選んだ壁の中点に`center`/`wallAt`/`orientation`/`side`を設定、天井/床付けは部屋bboxの中心（L字部屋で外れる場合は`pointInPolygon()`＋`centroid()`で重心へフォールバック、`scripts/seed-electrical.mjs`の`placeCeilingItem()`と同じ考え方）。idは`elec-m01`のように「m(manual)+連番」で採番し（`nextManualElectricalId()`、`ELECTRICAL_ITEMS`・`electricalAdded`の両方と衝突しないことを確認しながら採番）、ラベルは追加前時点の`buildElectricalSummary()`の部屋別内訳から同室・同型の既存数を数えて連番を振る（動的な部屋所属判定を使うため、内壁付け設備のように元データに`room`フィールドが無い項目が既にあっても正しく数えられる）。追加後はその場で選択状態にし、電気設備編集パネル（XYZ欄）を開いてすぐ微調整できるようにする

### 電気設備一覧（型ごとの集計＋見積との差分＋部屋ごとの内訳、2026-08-19追加）

「電気計画を真剣に検討したい」という施主要望を受け、型ごとの総数と部屋ごとの設置内訳を俯瞰できる一覧を追加した。新規データは持たず、`allElectricalItems()`＋`effectiveElectrical()`（追加・削除・編集差分を反映した実効値）から`buildElectricalSummary()`が都度集計する（154件程度は再計算コストが無視できるため、キャッシュは持たない）。部屋所属の判定は部屋フォーカスと同じ`electricalRoomProbePoint()`＋`findRoomIdAt()`の動的判定を再利用し、`ELECTRICAL_ITEMS`の静的な`room`フィールド（シードスクリプト由来、ドラッグ編集後は追随しない）には依存しない。カテゴリの分類・並び順（コンセント/スイッチ/照明/情報系配線/関連設備）・色（`EMAT`と同じパレット）は`ELEC_CATEGORY_ORDER`にJS側で固定的に持たせている（表示専用のため`data/electrical-catalog.json`側は変更していない）。

- **見積との差分表示**：削除・追加を始めると見積書の数量と何が違うか追いにくくなるため、`data/electrical-estimate.json`（見積書の明細。正本、下記参照）の明細ごとに「現在数 / 見積数」を突き合わせる。見積の明細は「電灯配線」のように複数のカタログ型をまとめた用途単位で数量を計上しているため、比較も型単位ではなく明細単位で行う（`buildElectricalSummary()`が`typeToLine`＝型→明細idのMapを作り、集計と同時に明細ごとの現在数`lineCounts`を積み上げる）。差が出ている明細は`renderEstimateLines()`が`.elecEstimateDiff`で強調し、明細の下には内訳として実際に使われている型ごとの件数をぶら下げる。見積のどの明細にも属さない型（LANコンセント等）は「見積外」としてまとめる
- **一覧モーダル**（左メニュー「電気設備一覧」→「一覧を表示」、`#electricalSummaryOverlay`）：既存の`#spawnOverlay`と同じモーダル骨格に、154件を収めるスクロール領域（`#electricalSummaryBody`）を持たせた。冒頭に合計件数（現在/見積）と見積明細ごとの内訳、続けて1F/2Fの全部屋を`ROOMS_APPROX`の順に列挙（0件の部屋も「部屋名：0件」の一行で表示し、計画漏れを見逃さないようにする）、屋外設備・部屋未判定（本来空だが、編集で部屋外に出た場合の検知用）、末尾に「削除した設備」（`deletedElectricalItems()`、行ごとに`restoreDeletedElectrical(id)`を呼ぶ復元ボタン付き）のセクションを表示する。部屋フォーカス中は合計・見積差分はフィルタせず、階見出し以下（部屋別内訳）だけを対象室に絞る（施主指摘：「フォーカスした部屋だけ見たい」）
- **部屋フォーカス時の設置物リスト**（`#roomFocusElecPanel`）：`focusRoom(id)`が同じ集計関数からその部屋の内訳だけを`renderRoomFocusElecList()`で描画し表示、`clearFocus()`で非表示にする。当初は左メニュー（`#ui`）内に置いていたが、「常設の設定・凡例と、部屋フォーカス中だけ意味を持つ一時的な読み取り情報が混在して見づらい」との施主指摘を受け、`#electricalEditToggle`（俯瞰モード限定・画面右上のボタン）の直下に独立したカードとして切り出した。モバイル幅では`#topBar`の折り返しと、下側から52vhを占有する`#ui`の両方を避けるオフセット・`max-height`を`@media (max-width:640px)`側で個別に調整している。ヘッダー・行一覧・追加ボタンの3段は`display:flex;flex-direction:column`で組み、行一覧だけを`overflow-y:auto`のスクロール領域にすることで、部屋の設備数によらず追加ボタンが常に見える位置に固定される
- **行クリックで選択**：どちらのリストの行も`data-elec-id`を持ち、クリックすると`selectElectricalFromSummary(id)`（一覧モーダル）／直接`setSelectedElectrical(id)`（部屋フォーカスリスト、既にその部屋にフォーカス済みのため）でその設備を選択し、電気設備編集パネル（X/Y/Z欄）まで開く。一覧モーダル側は俯瞰モードでなければ`setMode('orbit')`で切り替え、対象の部屋へ`focusRoom()`も合わせて行ってから選択する。復元ボタン（`data-elec-restore-id`）は行クリックとは別のdata属性にし、委譲ハンドラ側で先に判定する

### 見積データ（`data/electrical-estimate.json`）

施工会社の見積書（電気工事）の明細を機械比較できる形で持つ正本。1明細＝複数の`data/electrical-catalog.json`の型をまとめたもの（見積書自体が型ではなく用途の単位で数量を計上しているため）。`scripts/build-web-data.mjs`は`ELECTRICAL_ESTIMATE`定数として素通しで出力する（導出ロジックは持たない）。`tests/validate_electrical.py`は、明細が参照する型が全てカタログに存在すること・1つの型が複数の明細に重複して属さないこと（重複すると差分計算が二重計上になる）を確認する。

### シードスクリプト（`scripts/seed-electrical.mjs`）

見積書の項目・数量から機械検算した部屋別配分（`light`/`outlet_general`/`outlet_dedicated`/`outlet_ac`/`outlet_ih`/`switch_3way_pairs`/`switch_1p`/`tv`/`intercom`/`distribution_board`/屋外2種、合計154）をスクリプト内に埋め込み、`data/house.json`（rooms）・`generated/interior-walls.json`・`generated/exterior-walls.json`から実際の壁・部屋データを読んで機械的に配置する**一回限りの生成ツール**（`data/electrical.json`を丸ごと置き換える、常設のビルドパイプラインには含めない）。

- 壁付け設備：部屋ごとに使える壁セグメントを`wallSegmentsForRoom()`で集め、セグメントを順に回しながら重ならないよう`center`をずらして配置する（`roomWallState`で部屋ごとにカーソル状態を保持し、同室内の全カテゴリ・複数回の呼び出しをまたいで重複を避ける）
  - **壁セグメントは部屋自身のポリゴン辺で切り詰める**：`generated/interior-walls.json`・`exterior-walls.json`の壁データ1件は複数の部屋にまたがっていることが多い（内壁は`mergeCollinearWalls()`が3部屋以上の通し壁を1本にまとめる仕様、外壁はそもそも建物外周の連続した1本）。壁データの`from`/`to`をそのまま使うと、配置カーソルが隣室・別室にまで漏れ出す（2026-08-20、施主報告で発覚：154件中53件がこの原因で意図した部屋の外に配置されていた）。`wallSegmentsForRoom()`は壁データを部屋のポリゴン辺と直線が一致する区間だけへ毎回切り詰めてから使う
  - **`side`（壁のどちら側が室内か）はポリゴンの内外判定で決める**：以前は部屋全体のbbox中心と壁座標の大小比較という単純な方法だったが、L字・凹型の部屋では、bbox中心から見た方向と、細い張り出し部分の壁から見た実際の室内方向が逆転することがあり、隣室側を向いて配置されてしまっていた。`sideForSegment()`が壁の両側を`pointInPolygon()`で直接調べる方式にした（電気設備一覧の部屋所属判定・`wallsForRoom()`の追加機能と同じ考え方）
- 天井付け設備（照明）：部屋bbox内に等間隔で分散配置し、L字部屋で`poly`の外に出た場合は`pointInPolygon`で検知して重心へフォールバックする
- 同室・同型が複数ある場合は家具ラベルの命名規則と同じく連番を振る（例：「コンセント（アース付） 1」「コンセント（アース付） 2」）
- 実行後は必ず`node scripts/build-web-data.mjs`→`python tests/validate_electrical.py`を実行すること

### 電気設備編集の使い勝手改善（クリック判定・右ドック統合・効率化・視認性、2026-08-28追加）

施主の実際の使い方（俯瞰→電気設備編集→部屋フォーカスで絞って編集、隣接部屋との兼ね合いを確認したいときだけフォーカスを戻す）をヒアリングした上で、電気設備編集機能全体を多角的に見直した回。個別の機能追加ではなく、これまで施主指摘のたびに継ぎ足してきたUI（左メニュー・上バー・上部ヒント帯・右上パネル・右下パネル・左下バー・モーダル2種の計8箇所に分散）を含めて一括で整理している。

- **クリック判定の根本修正**：`pickElectricalAt()`が`editRaycaster.intersectObject(electricalAll, true)`の全ヒットを対象にしていたため、電気設備の各形状に付けている輪郭線（`fPartEdged()`の`LineSegments`）がThree.js r128のデフォルト`Raycaster.params.Line.threshold`（1m）でヒット判定され、狙った設備から画面上80〜120px（実寸9cm前後の器具に対して）離れた場所をクリックしても近くの別の設備が選択されてしまっていた（施主指摘：「壁をクリックしても近くの設備が勝手に選択される」）。`if(!hit.object.isMesh) continue;`を追加し、`Mesh`（実体）だけをヒット対象にして`LineSegments`（輪郭線）を除外する1行で解消した（Playwright実測で誤差±80〜120px→±10〜20pxに改善）。家具・窓ドアの当たり判定（`pickFurnitureAt`等）は同じ問題を抱えていないため対象外とした
  - **ホバーフィードバック**：`electricalEditMode`かつ`orbit`モードかつドラッグ中でない間、`pointermove`のたびに`pickElectricalAt()`を呼び、ヒットした設備があればカーソルを`pointer`に変え、`BoxHelper`（水色`0x8fd3ff`、選択中の黄色`0xffcf3a`とは別系統の色）でハイライトする（`updateElectricalHover()`/`hoveredElectricalId`/`electricalHoverHelper`）
  - **選択マーカーの強化**：`BoxHelper`だけでは実寸9cm前後の器具が俯瞰で見えづらいため、最低半径0.15mを保証する円形リング（`makeElectricalRingMarker()`、`THREE.RingGeometry`＋`depthTest:false`で他のメッシュに隠れにくくしている）を選択マーカーに追加した
- **右ドックへの統合**：`electricalEditMode`のときだけ表示される単一の`#electricalDock`（画面右、`flex-direction:column`）に、旧`#roomFocusElecPanel`・`#electricalPanel`・`#electricalBar`・`#electricalEditHint`と左メニューの「部屋フォーカス」「電気設備一覧」節を統合した。ナビ段（`#edNav`：部屋選択・フォーカス解除・一覧を表示、常時表示）→リスト段（`#edListSection`：部屋フォーカス中の設備一覧、内部だけスクロール）→編集段（`#edEditSection`：選択中設備の編集パネル）→フッター段（`#edFooter`：編集件数・Undo/Redo・書き出し・全取消）の4段構成で、リスト段だけを`flex:1 1 auto;overflow-y:auto`にすることで狭い画面（1280×720で実測）でもナビ・編集・フッターの3段が常に隠れず、リストだけが内部スクロールする設計にした。既存のDOM要素ID（`roomFocusSelect`・`epLabel`・`epWallSelect`等）は据え置き、コンテナの入れ替えだけでJS側のイベント配線を変えずに済ませている
- **編集効率化**：`electricalEditMode && mode==='orbit'`のときだけ有効な新規キーボードショートカット（Escapeで選択解除、Delete/Backspaceで削除、矢印キーで微調整）と、`electricalEdits`/`electricalAdded`/`electricalDeleted`の3状態をまとめて1スナップショットとして扱うUndo/Redo（`pushElectricalUndoSnapshot()`/`undoElectrical()`/`redoElectrical()`、Ctrl+Z/Ctrl+Shift+Z）を追加した。コマンドパターンで個々の操作を反転するのではなく状態を丸ごと複製・復元する方式（最大でも150件程度のJSONなので毎回のディープコピーで十分軽量、かつ「何を戻すか」を個別実装しないので確実）。復元は初回描画ループと同じ「全部消して作り直す」方式（`restoreElectricalSnapshot()`）。ドラッグ・キー長押しのような連続入力ジェスチャーは、ジェスチャー開始時にフラグを立てて最初の1回だけスナップショットを積む「ホールドセッション」方式にし、1ジェスチャー＝1回のUndoになるようにしている。あわせて「複製」ボタン（`duplicateSelectedElectrical()`、壁付けは`findFreeWallSlot()`、天井/床付けは座標オフセットで新規配置。空きが無い場合は正しく失敗する）と「高さ(Y)を標準に戻す」ボタン（`resetSelectedElectricalHeight()`、X/Z/壁面はそのままYだけ`ELECTRICAL_CATALOG[type].mountHeight`基準に戻す）を追加した
- **視認性向上**：`electricalEdits`にエントリがある設備（変更＝水色`0x29b6f6`）・`electricalAdded`に含まれる設備（追加＝緑`0x43a047`）に、選択中でなくても常時うっすらとしたリング（`makeElectricalRingMarker()`を再利用、不透明度0.45）を表示し、「このセッションでどこを触ったか」を一目で分かるようにした（`updateElectricalChangeHighlights()`、選択中の設備は選択マーカーの黄色と紛らわしくなるため除外する。`updateElectricalBar()`・`setSelectedElectrical()`・`setElectricalEditMode()`から呼び、全ミューテーション後・選択変更・編集モードのON/OFFで作り直す）。また、部屋フォーカス中は`#chkElectricalLabels`のチェック状態に関わらず、その部屋に属する電気設備のラベルだけ強制的に表示するようにした（`refreshLabelVis()`に`if(focusedRoomId && l.isElectrical && !l.hiddenByFocus) vis = true;`を追加。33室中1室に絞った状態なら密集の心配がないため、デフォルトOFFの理由＝154件表示時の密集には抵触しない）

なお、部屋レビューのループ機能（前/次の部屋ボタン等）とスイッチ⇔照明の対応付け（`data/electrical.json`のスキーマ拡張が必要）は、この回では意図的に対象外とした（施主判断で後日別途検討）。

## 方位コンパス（俯瞰モード限定、2026-08-20追加）

俯瞰モードで方位がわかるようにしたいという施主要望を受け、`#topBar`（`#electricalEditToggle`の直後）に方位コンパスを追加した。`#compass`は`applyModeChrome()`で`mode==='orbit'`のときだけ表示する（他のモード限定ボタンと同じ表示切り替えパターン）。

- **回転角の導出**：`updateCamera()`（`camera.position = camTarget + camDist*(sinφsinθ, cosφ, sinφcosθ)`という極座標配置）の`camTheta`（水平方向の回転角）だけに依存し、`camPhi`（仰角）には依存しない。建物座標系は`x`=西→東、`z`=北→南で`toScene()`は平行移動のみのためシーン座標もそのまま+X=東・-X=西・+Z=南・-Z=北になる。カメラの`lookAt`から導かれる画面右方向（ワールド座標、`up×zaxis`から導出）は`(cosθ,0,-sinθ)`になり、北ベクトル`(0,-1)`をこの基準系に投影すると「北は画面の『上』から時計回りに`θ`ラジアンの位置に現れる」という関係になる（`θ=0`のとき東が画面右＝カメラが南から北を向く初期配置と整合）。よって`#compassDial`（N/E/S/Wの4ラベルを円周上に配置した内側レイヤー）に`transform: rotate(${camTheta}rad)`を適用するだけで正しい向きになる
- 毎フレーム`animate()`ループ内（`mode==='orbit'`のときだけ）で`compassDialEl.style.transform`を更新し、ドラッグ回転中も追従させる

## 階段（stairs）

- `data/house.json`の`stairs`配列：階段の「経路」をパラメトリックに表現する。個々の段のジオメトリ・平面図記号・内覧モードでの歩行判定は、すべてこの経路データから`interior-white-model.html`側で導出する（段を1段ずつ列挙してデータ化するのではなく、経路＋段数から均等割りする方式）
  - `levelFrom`/`levelTo`：この階段が結ぶ階（`levelTo`は`levelFrom+1`）。`width`：踏み面の幅（m）。`totalSteps`：総段数（蹴上の数）。levelFromのFLからlevelToのFLまでの高さを`totalSteps`で均等に割った値が1段の蹴上高さになる
  - `segments`：`straight`（直進、`x0/z0`→`x1/z1`）と`arc`（廻り部、`pivotX/pivotZ`を中心に半径`radius`で`startAngleDeg`から`endAngleDeg`まで掃引する円弧）を並べた経路。廻り階段（曲がり階段）はこの2種類の組み合わせで表現する（実際のキッチンウィンダー段のような扇形の踏み面形状までは再現せず、経路を弧長で等分した位置に矩形の段を並べることで近似する）
  - `opening`：2F側（`levelTo`側）の床に開ける吹き抜けの矩形（`x0/x1/z0/z1`）。省略時は床に穴を開けない
  - `hiddenBelow`：階段が`levelFrom`側の**別の部屋の天井の上**を素通りする区間がある場合、その部屋の矩形（`x0/x1/z0/z1`）。省略時はなし。この矩形は`levelFrom`側の平面図記号を破線にする判定と、内覧モードでの歩行判定の両方に使う（後述）
  - 例：`stair-1f-01`（自宅1Fの曲がり階段）は、room-1f-10の西側柱状部分を直進で上り、凹角（x=14.561,z=0.91）を中心に**180度**の円弧で北東の張り出し部分へ曲がり込み、さらに南へ直進してroom-1f-21「パントリー（階段下）」の真上をパントリーの南端（z=1.82、room-1f-21の境界かつ2F開口の南端）まで通って2F(room-2f-02)へ着地する。当初は90度の円弧＋パントリーの中間までの短い直進で設計していたが、施主から「廻り階段はパントリーの真上を回り込んで南端まで届く必要がある」と実際の動線を矢印で描いた指摘を2回受け、180度の円弧＋パントリー南端までの直進に訂正した（`hiddenBelow`もこの訂正で追加）
- `interior-white-model.html`側の実装：
  - `sampleStairPath(stair)`：`segments`を弧長付きの折れ線（サンプル点列）に変換する。円弧は16分割で近似
  - `stairPointAt(path, s)`：経路上の弧長`s`における位置・進行方向（単位ベクトル）を返す
  - `stairLayout(stair)`：`totalSteps`等分した各段の境界点・中点をまとめて返す。3D段差ジオメトリ（`boxWireRotated()`で進行方向に向きを合わせた箱を段数ぶん積み上げる）と、平面図記号（各段境界に直交する踏み面線＋左右の側線＋UP/DN矢印とラベル）の両方がこのレイアウトを共用する
  - 3Dの段差ジオメトリは常時表示（`groups_stairs`、俯瞰・平面図・内覧のいずれでも同じ実体を見せる）。平面図記号は`groups.approx1`/`groups.approx2`に追加され、1F側の平面には「UP」（levelFromから見た上り方向）、2F側の平面には「DN」（levelToから見た下り方向）を表示する
    - 輪郭線マテリアル`stairEdgeMat`は通常の深度テスト（`depthTest`のデフォルト`true`）のまま使う。他の平面図線画用マテリアル（`approxEdge`等、内覧モードでは非表示になる`groups.approx1/2`専用）と違い、階段の実体は内覧モードでも常時sceneに存在するため、`depthTest:false`にすると手前の壁を無視して輪郭線が透けて見えてしまう（2026-08-16、施主指摘で発覚・修正。3章の教訓の表参照）
  - 2F側の床（`groups.floor2`）・内覧モードの1F天井面（`walkGroup`内、`FLOOR1`ゾーンの天井プレーン）は、`rectMinusRect()`で`stair.opening`ぶんの矩形を差し引いてから描画し、階段の吹き抜けを実際に素通しで見えるようにする
  - **階段下（`hiddenBelow`）の平面図表現**：階段が`levelFrom`側の別の部屋（例：パントリー）の真上を通る区間は、その部屋の天井裏に隠れて`levelFrom`側からは実際には見えない。建築図面で「上階の構造物が下階の天井裏に隠れている」ことを示す破線の慣習にならい、`levelFrom`側の平面図記号（踏み面線・側線・UP矢印）のうち`hiddenBelow`矩形の内側を通る区間だけを`addStairPlanLine()`が`THREE.LineDashedMaterial`（`stairPlanDashedMat`）で破線描画する。`levelTo`側の平面ではその階段区間自体がその階の実体そのものなので、常に実線（`stairPlanMat`）。あわせて、下に隠れる部屋（room-1f-21）のラベルに「（階段下）」を付記し、階段下収納であることを文字でも明示している
  - **内覧モードでの歩行**：`stairProgressAt(x,z,currentLevel)`が、現在位置が階段の経路（`width/2`＋余白0.35m以内）に乗っているかを判定し、乗っていれば経路上の進捗`t`(0=levelFrom側、1=levelTo側)とその高さ`y`を返す。`updateWalkCamera()`はこの`y`をそのまま目線の高さの基準にする（`walkLevel`の2値ではなく連続的に補間される）ため、階段を歩くと滑らかに視点が上下する。`updateWalkMovement()`は`t<0.5`か否かで`walkLevel`（床・家具の表示切替に使う離散値）を切り替える。当たり判定自体は各階の`wallSegmentsByLevel[walkLevel]`をそのまま使う（階段室専用の特別扱いはしていない）ため、1F側はroom-1f-10のL字型の実壁で、2F側はroom-2f-02の矩形の実壁で、それぞれ自然に囲われる
    - **`stair.opening`による範囲の絞り込み**：`stairProgressAt()`は、まず`inRect(x,z,stair.opening)`（`opening`が定義されている場合のみ）で足切りしてから経路との距離判定を行う。これがないと、経路の端点（例：終端の直進部分）付近で、壁を挟んだ隣室が`width/2+STAIR_CORRIDOR_MARGIN`（合計0.805m）以内に入ってしまい、そこを歩いているだけで「階段に乗っている」と誤判定されることがある（2026-08-16、施主指摘：自宅LDKから東の廊下(room-1f-13)へ抜けようとすると突然2Fへワープする不具合。廊下の南西角(15.471,1.82)が階段の終端直進部分(x=15.016)からわずか0.455mしか離れておらず、壁1枚を挟んで誤検知していた）。`stair.opening`は元々2F床の吹き抜け穴として定義されている矩形だが、1Fの階段室（room-1f-10∪room-1f-21）の外接範囲でもあるため、この用途にもそのまま転用できる
    - `currentLevel`引数は`hiddenBelow`の判定に使う。まだ登っていない状態（`currentLevel===stair.levelFrom`）で`hiddenBelow`の矩形内に入った場合は「階段の上を歩いている」のではなく「階段下の部屋を、その部屋自身のドアから歩いている」ということなので、階段としては扱わない（経路との幾何的な近さだけで判定すると、パントリーの中を歩いているだけなのに天井裏を通る階段の一部に引っ張られて視点が浮いてしまうため）。既にlevelToまで登り切っている（`currentLevel!==stair.levelFrom`）場合は、この矩形内でも通常どおり経路の補間高さを使う
  - 階段の下端（LDKへの開口、`door-029`）・上端（廊下(2F)への開口、`door-030`）は、他の room 分割と同じ`operation:'open'`の室内ドアとして`data/interior-doors.json`に登録してある。これがないと内覧モードで階段へ出入りできない（壁で塞がれてしまう）

### 腰壁（guardWalls、吹き抜けの転落防止）

`data/house.json`の`guardWalls`配列：`rooms`の隣接関係からは導出されない、独立した壁データ（`specialWalls`＝防音壁と同じ位置づけ）。階段の吹き抜け（`stair.opening`）は、`door-030`（階段(2F)⟷廊下(2F)）が全幅を壁のない開口にしているため、そのままでは2Fの廊下から吹き抜けへ誤って踏み込める状態になっていた（2026-08-16、施主が俯瞰スクリーンショットに赤線で図示して指摘：「いまのままだと2階から1階に飛び降りれてしまうような状態」）。吹き抜けの南辺(z=1.82、x:13.651-15.47)のうち、階段経路の最後の直進（x:14.561-15.471、上端の着地部分の真上）を除いた西側（x:13.651-14.561、階段の廻り部分の真上＝まだ2F床がない吹き抜け）に、床から1.5mの腰壁（`guard-2f-01`）を追加した。東側は実際に階段へ出入りする通路として開放したまま残している。

- **フィールド**：`{id, label, level, orientation('H'|'V'), at, from, to, height, status, note}`。`orientation`/`at`/`from`/`to`は壁セグメントと同じ規約（`H`＝z一定、`from`/`to`はx範囲。`V`＝x一定、`from`/`to`はz範囲）
- **`scripts/build-web-data.mjs`**：`buildGuardWalls()`が`GUARD_WALLS`定数を生成する（`buildSoundWall()`と同様、`house.guardWalls`をほぼそのまま整形するだけ）
- **`interior-white-model.html`側の使われ方**：
  - **当たり判定**：`wallSegmentsByLevel`構築時、防音壁と同じ位置（`cutGaps()`の後）に`{orientation, at, from, to, thick:INTERIOR_WALL_T, guardHeight:g.height}`として追加する。`resolveWalk()`・`segListBlocked()`は`thick`しか見ないため、既存のロジックを一切変更せずにそのまま転落防止の当たり判定として機能する
  - **内覧モードの見た目**：壁メッシュ生成ループ（`wallSegmentsByLevel[level].forEach(...)`）の先頭で`s.guardHeight!==undefined`を判定し、天井（`CEIL_H`）ではなく`guardHeight`までの高さで描画してから`return`する（窓の切り欠き判定はスキップ）。これにより、当たり判定は壁と同等でも、見た目は腰の高さで途切れた低い壁になり、吹き抜けを覗き込める
  - **俯瞰・平面図の見た目**：`GUARD_WALLS.forEach(...)`が、通常の`ROOMS_APPROX`と同じ`mats.approx`/`mats.approxEdge`を使い、`groups.approx1/2`（1F/2F表示切替・内覧モードでの非表示に自動的に連動する）へ`boxWire()`で追加する。真上から見る平面図モードでは高さの違いは見えない（他の壁と同じ塗りで、区間だけが目印になる）が、俯瞰（オービット）モードでは低い壁として見える

## 勾配天井（ceiling:sloped）

施主指摘（2026-08-16）：「民泊LDK・自宅LDKのうち、片流れ屋根がかかっている範囲は、天井の高さを片流れの形に合わせてほしい」。`rooms`の該当2部屋（`room-1f-06`＝LDK(民泊)、`room-1f-11`＝LDK）に`ceiling:"sloped"`を付け、それ以外はすべて既存データ（`roofs`の片流れ屋根・`footprints`）から自動導出する。現時点では**内覧モードのみ対応**（俯瞰・平面図の部屋ボックスは従来通りCEIL_Hのまま。下記「今後の課題」参照）。

- **`scripts/build-web-data.mjs`側の導出（`computeSlopedCeilingPieces()`）**：
  1. `decomposeRectilinearPolygon(polygon)`が、`ceiling:"sloped"`な部屋のポリゴン（軸並行前提。`isRectilinear()`の対象と同じ）をz方向の走査線で矩形群（バンド）に分解する
  2. 各バンドを、片流れ屋根（`roofs[].kind==='lean_to'`）のfootprintと矩形の交差判定にかけ、重なった部分を`sloped:true`（交差した屋根の`base`/`pitch`/`thickness`を保持）、残りを`sloped:false`（2階直下などフラットなまま）の区画として`SLOPED_CEILING_PIECES`に書き出す
  3. 屋根が複数（`roof-a1`/`roof-a2`）ある場合も、区画ごとに交差した方の勾配式をそのまま持つため、将来2つの屋根の勾配が異なっても正しく扱える（現状はたまたま両方とも同じ`base`/`pitch`のため、`room-1f-11`のx=9.1の継ぎ目で区画は分かれるが高さの見た目は連続する）
  4. `CEILING_ALLOWANCE`（`house.defaults.ceilingAllowance`、既定0.15m）：垂木・断熱・天井仕上げの見込み。屋根裏面（`roof.thickness/2`を引いた面）からさらにこの分だけ天井を下げる。実際の天井高は屋根裏面よりこの見込みぶん低い、という意味
- **`interior-white-model.html`側（内覧モードのみ）**：
  - **`slopedCeilingHeightAt(x,z)`**：`SLOPED_CEILING_PIECES`から該当区画を探し、`sloped:true`なら`yAtHiraya(z,base,pitch) - roofThickness/2 - CEILING_ALLOWANCE - LEVELS.fl1`（屋根の勾配式そのまま、`yAtHiraya()`は屋根描画と共通）、`sloped:false`または対象外なら`CEIL_H`を返す
  - **天井パネル**：階段の吹き抜け穴と同じ要領で、`SLOPED_CEILING_PIECES`の`sloped:true`区画ぶんを平らな天井面（`FLOOR1`）から`rectMinusRect()`で切り欠き、代わりに`walkSlopedCeilingPanel()`（`roofPanel()`と同じ「2点を結ぶ傾いた板」の考え方だが、内覧の天井パネルは輪郭線を持たない仕様に合わせた専用の軽量版）で傾いたパネルを描画する
  - **壁の高さ**：勾配天井の対象範囲付近の壁（`nearSlopedCeiling(s)`でまず大まかに絞り込む）は、天井まで届くよう高さを伸ばす。ルールは「壁の高さ＝両側の天井高のうち高い方」（`slopedCeilingHeightAt()`を壁面の両側で±`SLOPE_SAMPLE_EPS`だけオフセットしてサンプリングし、`Math.max()`を取る）
    - **H向き（z一定）の壁**：屋根の勾配式はzだけに依存するため、z一定の壁は区間内で高さが変わらない。ただし壁の途中でx方向に「屋根がかかる／かからない」の境界（`room-1f-11`のx=12.74）をまたぐことがあるため、`heightRunsForHWall()`がその境界で壁を区間分割し、区間ごとに一定の高さ（段差）で描画する（施主承認：「フラットに戻るところは素直に段差でOK」）。窓（例：自宅LDK南面の掃き出し窓`op-010`）がある区間は、区間ごとの高さを天井としてこれまでの窓の切り欠きロジックをそのまま適用する
    - **V向き（x一定）の壁**：x一定なので「屋根がかかる／かからない」の判定自体は壁の全長で変わらないが、屋根の高さ自体がzの一次式で連続的に変わるため、壁の上端も連続的に傾く。`ceilingProfileRuns(x,zFrom,zTo)`（H向きの`heightRunsForHWall()`と同じ考え方を一般化した共通関数）が、両側の天井高が変わらない区間ごとに両端の高さを求め、`slopedTopWallPanel()`（`archSpandrelShapes()`と同じ「ローカルXY平面のShapeをZ方向に押し出し、position+rotation.yで配置する」手法）で区間ごとに上端が傾いた台形パネルを描く。民泊-自宅の防音壁（`SOUND_WALL`、x=7.28）もこの対象に含まれる（両側とも勾配天井の部屋のため、内覧モードでは天井なりに傾く。平面図・俯瞰モード側の防音壁表示（`topY=3.4`固定）は今回未対応、下記参照）
    - **区間分割が必要な理由（実装時のバグと教訓）**：当初は壁の両端(`from`/`to`)の高さだけを求め、その2点を単純に直線で結んでいた（`heightEndsForVWall()`という名前だった）。しかし民泊-自宅の防音壁のように、壁の一部だけが勾配天井の部屋に接し、残りは接しない（例：北側はヌックなど非対象の部屋に接し、南側だけが対象の2部屋に接する）場合、真の高さのプロファイルは「フラット→勾配」の折れ線であり、両端を直線で結ぶと本来フラットなはずの区間まで誤って傾いて描画されてしまう（施主指摘：「境界壁がおかしくなっている」「ヌックを囲う壁も変になっている」）。`ceilingProfileRuns()`は`SLOPED_CEILING_PIECES`の境界も区間の切れ目として使うことで、区間の中では常に片方の式だけが有効という前提を保証し、この誤りを解消した
  - **アーチ開口の垂れ壁（`addWalkArchInfill()`）**：ヌック⟷LDKのアーチ開口（`door-006`）のように、勾配天井の対象範囲に接する壁上にあるアーチの「弧の頂点から天井までの垂れ壁」も、天井が上がった分だけ高さを合わせる必要がある。当初はここが`CEIL_H`決め打ちのままだったため、アーチの上に隙間ができ、その先の勾配天井が透けて見えていた（施主指摘の一因）。`heightRunsForHWall()`を流用して修正した（現状はH向きのアーチのみ対応。V向きの勾配天井対象アーチは現状データに存在しない）
  - **フラット⇔勾配の境界の蹴込みパネル（同じ部屋の中で壁を挟まない場合）**：自宅LDKのx=12.74のように、同じ部屋の中で勾配区画とフラット区画が壁を挟まずに接する境界では、天井の高さが不連続に変わるのに何も塞ぐものがない。そのままでは内覧モードで見上げると隙間から2階側が見えてしまう（施主指摘：「片流れとフラット天井の境目が抜けて2Fが見えてしまっています」）。`SLOPED_CEILING_PIECES`を部屋ごとにグループ化し、同じ部屋のsloped区画とflat区画が接するx境界を`sp.x0/x1`と`fp.x0/x1`の一致で検出、`ceilingProfileRuns()`と`slopedTopWallPanel()`（`baseY`を`LEVELS.fl1+CEIL_H`にして、フラット天井の高さから勾配天井の高さまでを塞ぐ薄い垂直パネルとして使う）で塞いだ
- **見込み（`CEILING_ALLOWANCE`）について**：施主に「屋根裏面そのまま」か「見込みを引く」かを確認し、見込みを引く方針で確定（2026-08-16）。実際の垂木せい・断熱厚は施工会社未確認のため、0.15mは目安値（`status`の考え方に準じ、今後の検証対象）
- **今後の課題（未対応、次回以降の対象）**：
  - 俯瞰・平面図モードの部屋ボックス（`ROOMS_APPROX`）は、勾配天井を考慮せず一律CEIL_Hのまま（内覧モードのみ先行対応。将来的にはORTHOカメラでの見た目にも反映したい）
  - Blender（`blender/build_house.py`）は未対応
  - `SOUND_WALL`の俯瞰・平面図モード側の表示（`groups.sound`、`topY=3.4`固定）は、南側で新しい勾配天井（最大約3.5m）より低くなる場合があるが、今回は内覧モードの壁高さ計算（`wallSegmentsByLevel`経由）だけを直し、`groups.sound`自体の`topY`は変更していない

## 面の永続ID（surface-registry.json、W03-C・2026-09-08追加）

W04（面ごとの仕上げ設定）がキーとして参照するための、部屋境界面（壁・床・天井）の識別設定。`data/visual/surface-registry.json`（schemaVersion 1.0.0）に、手動で確定したASCII文字列のID（例：`surf-guest-wall-001`）と、壁なら対応する`house.json`のroom polygon辺の両端座標（`edge`、source座標・メートル）、床・天井ならroomIdを記録する。**建物形状の新しい正本ではない**（形状は常にhouse.json等から取得）。壁番号・メッシュ名は配列順・開口分割で変わるため永続IDにしていない。

- `scripts/surface_registry.py`：`resolve_from(root)`が現在の`house.json`と照合し、壁は端点座標一致（順序不問、許容差1e-6m）で辺を再特定、床・天井はroomIdでその部屋の現在のpolygon/ceilingへ追従する。一致なし・複数一致・部屋が消えている場合は`unresolved`として`issues`（対象ID・理由・修正案内）に記録する。座標の近さや部分一致・方位だけでの推測、登録の自動更新は行わない。ラベル・家具・開口の変更だけでは登録IDは変わらない（窓移動でできる複数の壁片も同じ部屋境界面として同じIDを維持できる）。壁位置が変わった／辺が分割・結合された場合は、登録の`edge`を明示的に更新するまで`unresolved`のまま。旧IDは自動では新しい辺へ引き継がれず、他の面へも再利用しない。
- `scripts/check-study-surfaces.py --output <新規ディレクトリ>`：Blender/UEを起動せず`surface-resolution.json`と部屋輪郭の簡易SVGを含む`index.html`を出力する軽量CLI。未解決・重複・登録の欠落/不正schemaがあれば終了コード1。
- 接続：`scripts/build-visual-twin.py --interior`はBlender起動前に検証し、未解決があれば停止する（`--interior`なしの白模型のみの生成はこの検証の対象外）。`scripts/refresh-visual-study.py`もBlender起動前（W03-Bの参照確認の直後）に検証し、未解決があれば同様に停止して`surface-resolution.json`を案内する。`scripts/build-visual-twin.py`の既存`inputs()`（`data/`配下のJSON全体を対象）が`surface-registry.json`のハッシュ計算・`SourcePackage/inputs/`へのコピーも自動的に含む。

初期登録は`room-1f-06`（ゲストLDK）の6辺と床1面・天井1面の計8面。共有壁は両側の部屋がそれぞれ別のroomId・別のIDで登録する想定（同一室内の同一辺・同一室のfloor/ceilingの重複、id自体の重複は拒否）。他の部屋は未登録でもエラーにならない。**現在の`data/visual/surface-registry.json`自体の欠落は`resolve_from()`がエラーとします**（`check-study-surfaces.py`は空の成功結果を返しません）。一方、過去のパッケージ・W03-Aの案（scenario.json）にこの登録が無かったことは許容します（旧形式として読めるだけで、現在の正しい登録を拒否する理由にはしません）。面ごとの材質適用・UEでの面選択は次項「面ごとの仕上げ変更」（W04）で実装済み。メッシュの部屋境界での分割（壁の一つの面が複数部屋にまたがらないようにするジオメトリ側の対応）も同項に含む。梁・段差の立ち上がり・窓枠・開口の見込み・巾木は引き続き対象外。

## 面ごとの仕上げ変更（surface-bindings.json、W04・2026-09-08追加）

登録済みの永続ID（上記`surface-registry.json`）を、実際にBlenderが生成したメッシュ面・UEのマテリアルスロットへ対応付け、面単位で色・粗さ（roughness）・仕上げバリアントを個別に上書きできるようにする仕組み。`study-bindings.json`（全体バリアントの役割割り当て、W02から既存）と二層構造になっており、**全体基準（study-bindings.json）→面別上書き（surface-bindings.json＋`surfaceOverrides`）**の順で解決する。面別上書きが無い面は、これまで通り全体バリアントの仕上げがそのまま使われる。

- **壁のどちら側かの判定（`blender/surface_bindings.py`の`wall_cap_for_room()`）**：壁パネルは薄いプリズムとして生成しており（`build_interior.py`の`prism()`）、押し出し前後の2つの大きな面（cap 0/cap 1）がそれぞれ壁の表側・裏側にあたる。どちらが対象の部屋に属するかは、壁の中心線から法線方向に±epsilon（3cm）だけ離れた2点で`point_in_room()`（既存の点-in-polygon判定）を呼んで判定する。**方位（東西南北）からの推測は行わない**（施主宅の壁は東西南北に厳密に沿っていない箇所があるため、方位ベースの判定は誤判定の元になる）。共有壁は、両側の部屋がそれぞれ別のcap・別の永続IDとして登録されるため、片方だけ色を変えても裏側の部屋には影響しない。
- **範囲の分割（`split_wall_range()`）**：1つの登録済み壁面（登録時のedge座標）が、開口分割等で複数のメッシュ片にまたがる/一部だけ重なる場合、`interior_geometry.clip()`（半平面クリップ、階段吹き抜け等で既に使用）を再利用して、登録範囲に含まれる部分だけを対象にする。
- **床・天井の部屋ごとの切り出し（`decompose_rectilinear()`/`subtract_rects()`/`intersect_rect()`）**：床スラブ・フラット天井は複数の部屋にまたがる矩形として生成されることがあるため、対象の部屋自身の矩形群（部屋のpolygon頂点から作るグリッドを`point_in_room()`でセルごとに判定）と、その矩形を含むスラブ/天井の矩形とを厳密に交差（`intersect_rect`）させてから、他の登録済み矩形の重複部分を差し引く（`subtract_rects`）。**部屋のbboxが重なるだけで無条件に対象と判定すると、隣室にも同じ色が適用されてしまう**（実装中に発見・修正した不具合）。この矩形自体に加えて対象の階（`room['level']`とスラブ/天井の`level`）も一致を確認する（平面位置が同じでも階が違う部材は対象にしない。現在の登録は1階のみのため未検証の防御的対応）。
- **床上面・天井下面だけへの適用（2026-09-09 GPTレビュー修正、R5）**：壁と同様、床・天井も対象の主面（床の歩行面＝上面、天井の室内側＝下面）だけに専用スロットを割り当てる（`prism()`/`block()`の`face_materials`引数、壁のcap指定と同じ仕組み）。下面/裏面・厚みの端面は元の材質のまま変えない。勾配天井の段差立ち上がり（riser）は仕様通り対象外で、専用スロット・`surface-bindings.json`への登録のどちらも行わない。
- **Blender側の対応付け（`build_interior.py`の`SurfaceBinder`）**：登録済みの永続IDごとに、専用のマーカーマテリアル（`Surf_<kind>_<surfaceId>`、例：`Surf_wall_surf-guest-wall-005`）を割り当てた追加マテリアルスロットを作り、対応するメッシュ・スロット・部屋ID・日本語ラベル（`surface-registry.json`の`label`をそのまま引き継ぐ）・状態（`bound`/`no-surface`）を`surface-bindings.json`として出力する。壁の元の一枚岩の材質（全体バリアント用スロット）はそのまま残り、登録された面だけが追加スロットで上書きされる。referenceバリアントのタイル・板目パターンは、上書き後の色（`resolve_finish()`の結果）を使って適用する（元のパレット色を使うと上書きの色指定が打ち消されるため）。
- **UEインポート時（`import_study.py`）**：`surface-bindings.json`の各面について、`unreal/surface_finish_overrides.py`の`resolve_finish(finish_document, study_variants, kind, base_variant, override=None)`（全体バリアントのパレット→バリアント別詳細→明示的上書きの順で色・粗さ・パターン/ノイズ詳細を決める共通ロジック。戻り値の`detail`が該当）で初期値を計算し、`unreal/material_builder.py`の`marker_material()`に渡す。
- **登録面はパターン・ノイズを保持し、variant切替で模様自体も切り替わる（2026-09-09 GPTレビュー修正、R1／2026-09-09 v2レビュー継続修正）**：`marker_material()`は`material()`（全体バリアント材質と同じ、パターン/ノイズのノードグラフを組み立てる関数）へ委譲し、Color/Roughnessだけを`MaterialExpressionVectorParameter`/`ScalarParameter`にする（`parametric=True`）。パターン・ノイズのノード自体はこのパラメータ化されたColorに対して乗算されるため、上書きが無い登録面は周囲と同じ質感のまま、上書きがあれば模様を保ったまま色・粗さだけが変わる。**ただしパターンの形状（tile/planks/noiseの種類・寸法）自体はマテリアル作成時に焼き込まれ、MIDのパラメータでは変えられない**ため、`import_study.py`は面ごとにstudy variantの数だけ親材質（`M_Surf_<surfaceId>_<variant>`、各variant自身のディテールを保持）を生成する。全体バリアント切替・面別variant上書き・A/B・案の読込のいずれも、シーンに既にある材質を再利用するのではなく、その時点のeffective variant（上書きがあればそのvariant、無ければ全体バリアント）に対応する親を都度ロードしてMIDを作るため、模様自体が正しく切り替わる（当初は親を使い回していたため、Color/Roughnessは変わっても模様は最初にロードされたvariantのまま固定されていた）。
- **実行時の上書き適用（エディタ・C++ウォークスルー共通）**：面ごとの色・粗さ変更は、マテリアル**アセット**を新規作成せず（アセット生成はエディタ専用APIで、実行中のウォークスルーからは呼べない）、`UMaterialInstanceDynamic`（MID、エディタでは`component.create_dynamic_material_instance()`、C++では`UMaterialInstanceDynamic::Create()`）を、上記のeffective variantに対応する親材質から都度作り、Color/Roughnessパラメータを設定する方式に統一している。C++の`Walkthrough.cpp`の`ApplyConditions()`は、`resolve_finish()`と同じロジックをC++側にも実装している（言語をまたいだコード共有ができないため、Python版とC++版を個別に保守する必要がある。ロジックを変える場合は両方の更新が必要）。C++側は適用前に、保存データの`surfaceOverrides`全体（型・未知フィールド・colorHex形式・roughness範囲・対象面が実際に`bound`かつ同じ部屋か）をPython版の`validate_surface_overrides()`/`resolve_overrides()`と同水準で検証してから一括適用する（無効な保存データは他の項目と同様に復旧処理へ渡す）。この検証は「フィールドが存在するなら値の取得成功と制約の両方を要求する」形で行う（`HasField()`で存在を確認したうえで`TryGet*Field()`の失敗＝型不正を拒否；取得に失敗したら検証せず既定値へ進む、という書き方は型不正を素通りさせてしまうため避けている）。1.1.0の状態で`surfaceOverrides`自体が欠落している場合も、schemaVersionを見て拒否する（1.0.0だけがこの項目の欠落を許容される）。
- **比較状態の互換性（`unreal/study_state.py`）**：保存状態のschemaVersionは`'1.0.0'`（W04以前）と`'1.1.0'`（`surfaceOverrides`を含む、W04以降の新規保存）の両方を受理する。`surfaceOverrides`はキー＝永続ID、値は`variant`/`colorHex`（6桁16進、`#`無し）/`roughness`（0〜1）の任意の組み合わせで、構造的な妥当性（値の形式）はここで検証するが、対象IDが実際に`bound`かどうか（参照的妥当性）は`resolve_overrides()`が別途チェックし、`no-surface`・未知ID・**別の部屋の登録面**（`room_id`引数で照合）の上書きはエラーにせず「issues」として無視して残りを適用する（施主の操作ミスで比較全体が壊れないようにするため）。1.0.0（この項目自体が存在しない旧形式）だけを空の上書きとして許容し、1.1.0で値がnull/配列/false等の型不正な場合は許容せず拒否する（2026-09-09 GPTレビュー修正、R4：以前は`or {}`で両者を区別せず受理していた）。
- **保存・生成パイプラインでの伝搬**：`scripts/build-visual-twin.py --interior --state <study-state.jsonのパス>`でBlenderに直接状態を渡せる（`--state`は`--interior`専用）。`scripts/refresh-visual-study.py`は`--previous`（直前の保存状態）または`--scenario`（W03-Aの名前付き案）で選んだ状態を、この`--state`経由でBlenderへ渡す。未登録の永続IDを対象にした上書きが含まれる場合、`build-visual-twin.py`が現在の面登録（`surface_registry.resolve_from()`）と突き合わせてBlender起動前に停止する（2026-09-09 GPTレビュー修正、R4：以前はこの確認がBlender起動後の`build_interior.py`内でしか行われておらず「Blender起動前」の説明と実装が食い違っていた。登録が実在するかの確認はここで行い、登録はあるが実メッシュが無い＝no-surfaceの判定は仕様通りBlender後・UEインポート前のまま）。
- **UEエディタでの操作**：既存の「内装比較」Toolsメニュー（`unreal/study_controls.py`、Slate不使用の`unreal.ToolMenus`ベース）に「面編集」（`surface-bindings.json`のstatus=='bound'な面の一覧・対象選択・色/roughness直接入力・プリセット・対象リセット・部屋一括適用）と「案の保存・比較」（W03-Aの名前付き案の保存・一覧・読み込みに加えて、A/B固定条件比較の開始/終了）サブメニューを追加した。自由入力（色コード・roughness・案の名前）はPowerShellの`Microsoft.VisualBasic.Interaction.InputBox`をシェルアウトして取得する。面一覧には`surface-bindings.json`の日本語ラベルを表示し、対象選択のログにも「変更対象は部屋側の面のみ」と明記する（Actorの選択輪郭は壁の裏側にも付くため）。選択中の面・A/B比較の状態（表示中の案・固定条件）は、クリック後のログだけでなく各サブメニュー先頭の常設項目としてラベル表示し続ける（2026-09-09 GPTレビュー修正、R3）。色・roughnessの入力は選択中の面の既存の上書き（プリセットで選んだvariant等）へマージし、片方の入力を空欄にしても他方の指定を消さない（以前は入力のたびに上書き全体を丸ごと置き換えており、プリセット選択後に色だけ変えるとプリセット指定が失われた）。保存直前には、Undo等でシーンの実際の材質が管理中の状態と食い違っていないかを検証し、食い違いがあれば理由を示して保存を拒否する。名前付き案の保存・読込・比較は、生成時に書き出す`repo-root.json`経由でこのworktree自身の`scripts/refresh_inputs.py`（`save_scenario_package()`/`scenario_inputs()`）をプロセス内で直接呼び出す（UE埋め込みPythonの`sys.executable`はUnrealEditor自身であり通常のpython.exeではないため、外部プロセスとして起動する方式は使わない。2026-09-09 GPTレビュー修正、R3）。読込・比較開始時は`scenario_inputs()`でパッケージ内のファイルハッシュ・room/variant整合を検証してから適用し、A/B比較は両案を先に検証してから開始する（不整合な案は一覧から消さず、比較の開始・適用だけを拒否する。2026-09-09 GPTレビュー修正、R2）。周辺条件（`site-context.json`）の適合は、シーンを変更しない専用の関数（`_context_compatible()`）で現在のプロジェクトと**双方向**に比較してから読込・比較を許可する：現在プロジェクトに周辺条件がある場合はハッシュが一致することを要求し、現在プロジェクトに周辺条件が無い場合は案も周辺条件を期待していないことを要求する（2026-09-09 v2レビュー継続修正：以前は案がexpectedを持たない＝「周辺条件なしで保存した案」の場合に現在値を自動採用しており、周辺条件ありの現在プロジェクトへ黙って読み替えてしまっていた）。この確認は案の読込・A/B比較専用で、`apply_state()`自身が持つ「まだ一度もこのプロジェクトのapply_state()を通っていない状態（新規インポート直後の初期状態等）に現在値を採用する」という初回のブートストラップ処理とは明示的に分けている。

## 採光条件・日時比較（site.local.json、W05・2026-09-09追加）

ゲストLDKで日時（太陽位置）を選んで比較し、根拠を確認して保存・再生成できる仕組み。太陽位置計算そのものは既存の`unreal/solar_position.py`（`noaa-meeus-geometric-v1`、W02から既存）をそのまま使い、置き換えていない。

- **ローカル敷地入力（`site.local.json`）**：`solar_position.validate_site()`の1.0.0形式（`latitudeDeg`/`longitudeDeg`/`planNorthAzimuthDeg`/`locationStatus`/`northStatus`/`note`）をそのまま使う。実座標を含むため公開Gitのdataには置かず、生成プロジェクト直下の`site.local.json`にのみスナップショットとして保持する（`site-context.json`と同じ「ローカル限定・build配下限定」の扱い）。UEエディタの「内装比較 → 採光」メニューから、①`build/`配下の既存JSONファイルを読み込む（`load_site()`、パスをプロンプト入力）、②緯度・経度・図面北方位・確度・根拠メモを順に入力して新規ファイルを作る（`create_site_input()`、既存ファイルは上書きしない）のどちらかで設定する。位置・方位・確度・根拠は「採光」サブメニュー先頭の常設ラベルで確認できる（このラベルはローカルのUEエディタ画面にのみ表示され、コミットや報告には転記しない）。
- **日時ケース（`sun-cases.json`）と敷地の対応確認**：既存の`plan-sun-study.py`（CLI）・`sun-cases.json`の構造（W02由来）をそのまま使う。`solar_position.py`に`site_sha256(site)`（`make_case()`が元々siteSHA256へ埋め込んでいたのと同じ正規化JSONハッシュを独立関数として切り出したもの）と`cases_match_site(cases, site)`を追加し、「敷地ファイルの生バイト」と「ケースへ埋め込まれた意味上のハッシュ」を混同しないようにしている。UEエディタからは、任意の日時を1件追加（`add_datetime_case()`）、季節代表日（3/21・6/21・9/21・12/21の9/12/15時、JST基準。**その年の正確な春分・夏至等の瞬間ではない**）をまとめて追加（`add_season_cases()`、同じ日時は重複追加しない）、現在の敷地でケース全体を再計算（`recompute_sun_cases()`）ができる。敷地を変更してもケースは自動再計算しない（来歴を保ったまま角度だけ変わることを防ぐ）。「採光」メニューの日時ケース状態ラベルは「現在の敷地と一致」「不一致・再計算が必要」「敷地原本なし」のいずれかを常に表示する。範囲外（`elevation`が[1,89]度の外）の日時もケースとしては追加・表示され、適用しようとすると理由付きで拒否される（`solar_position.apply_case()`が`ValueError(case['reason'])`を送出）。
- **日時比較（W04の仕上げA/Bとは別機能）**：`study_controls.py`に`start_daylight_compare()`/`show_daylight_compare_a()`/`show_daylight_compare_b()`/`end_daylight_compare()`を追加。W04の仕上げA/B（`start_compare()`等、視点・太陽・露出を固定して仕上げ側を切り替える）とは逆に、**仕上げ（面別上書き含む）・視点・露出・光源強度・周辺条件を固定し、選んだ2つの日時ケースの太陽角度/`solar`来歴だけを切り替える**。両ケースが「適用可能（昼間）」であること、両ケースの状態が現在のモデルに適用可能であること（下記の共通事前検証）を、実際にシーンへ触れる前に確認してから比較を開始する。
- **共通の適用前検証（`_validate_applicable()`）**：周辺条件（`site-context.json`）の適合確認（`_context_compatible()`）と、面別上書きが実在する登録面を指しているかの確認（`resolve_overrides()`）をまとめた、シーンを変更しない純関数。W04の仕上げA/B・名前付き案の読込・W05の日時A/Bのすべてで、2つの候補状態を切り替え始める**前に**両方を検証するために使う（片方だけ有効なまま比較を「開始してしまう」ことを防ぐ。W04-v1レビューで指摘された、A/B比較開始時の面参照事前確認の不足もこれで解消している）。
- **内覧（C++ウォークスルー）のHUD表示**：`Walkthrough.cpp`に`CurrentSolarLabel()`を追加し、「太陽条件：〈日時〉（日時・位置概算/入力確認済み）」または「太陽条件：手動角度（未校正）」をHUDへ常設表示する。`State->solar`は既存の汎用パススルー`FJsonObject`のフィールドの一つに過ぎないため、F5/F9の保存・復元は追加のC++変更なしにそのまま対応する（`SetSun()`が手動変更時に`solar`を消す処理も既存のまま）。
- **Blenderの太陽角度が`--state`から伝わっていなかった不具合の修正**：`blender/build_interior.py`の`setup_lighting()`は、`--state`が渡されても`state.variant`/`surfaceOverrides`だけを使い、`azimuthDeg`/`elevationDeg`は`--elevation`（無指定なら既定値）しか見ていなかった。日時比較の状態をBlenderへ渡しても、レンダリングされる太陽角度は常にゲストLDKの既定値（方位155°・高度30°）のままになる欠落があったため、`--state`がある場合は`state.azimuthDeg`/`elevationDeg`（`--elevation`より優先）を使うよう修正した（実ビルドで、日時ケースの角度が`study.json`の`lighting`へ正しく反映されることを確認済み）。
- **保存・再生成パイプラインでの伝搬**：`ALLOWED_SCENARIO_FILES`に`site.local.json`を追加し、`scripts/refresh_inputs.py`の`retained_inputs()`/`scenario_inputs()`が`site-context.json`と同様の要領で拾う。ただし周辺条件と違い、**`site.local.json`の欠落自体はエラーにしない**（敷地原本の無い旧案でも、有効な`solar`/`sun-cases.json`があれば引き続き使えるという仕様上の要件）。`site.local.json`と`sun-cases.json`が両方揃っている場合だけ、`cases_match_site()`で意味的な対応を確認し、不一致なら停止する。`scripts/build-unreal-study.py`に`--site`引数を追加（`--sun-cases`と併用時は同様に整合確認）。`scripts/refresh-visual-study.py`は`retained`に`site`があれば`build-unreal-study.py`へ`--site`を転送する（`context`/`sunCases`と同じ扱い）。
- **日時比較専用の撮影ツール（`scripts/compare-unreal-daylight.py`）**：既存の`compare-unreal-studies.py`は「日時ケース×仕上げvariant」の総当たりを撮影する設計で、撮影のたびに`--variant`を明示的に指定するため、面別上書きを含む「今の仕上げ」を維持したまま日時だけを変える比較ができなかった。新しいスクリプトは`capture-unreal-study.py`を`--variant`無しで（＝現在保存されている仕上げ・面別上書きを一切変えずに）`--sun-case`だけ変えて複数回呼び出し、視点・仕上げ・面別上書き・露出・光源強度・周辺条件が全カット同一であることを確認しながら、2〜12枚のローカルHTMLギャラリーを作る。
- **既知の限界**：季節代表日は暦日固定（年ごとの正確な春分・夏至等の瞬間ではない）。天候・実照度・ガラス透過率は引き続き未校正（`siteDaylightCalibrated: false`のまま）。窓・庇・屋根形状はW04以前のまま（明白な日照計算上の欠落は今回は見つからず、追加のジオメトリ変更はしていない）。
- **敷地と太陽状態の一致確認（R1、W05-v1レビュー修正・2026-09-09）**：`cases_match_site()`は当初、日時ケースに記録された`siteSHA256`と敷地のハッシュが一致するかしか見ておらず、(a)敷地を切り替えても古い日時ケースの適用・日時比較が止まらない、(b)敷地変更後に`recompute_sun_cases()`で一覧を再計算しても、現在シーンの`solar`（適用中の日時）が古いまま保存・refreshが通る、(c)同じハッシュのまま角度だけ改変されたケースを検出できない、という3点の抜けがあった。`solar_position.py`に`case_matches_site(case, site)`（`siteSHA256`の一致に加え、`make_case()`で同じ日時を敷地から再計算し直した角度との一致も確認）を追加し、`cases_match_site()`はこれを内部で使うよう変更した（呼び出し側のシグネチャは不変）。`study_controls.py`の`set_sun_case()`・`start_daylight_compare()`は適用前に`_verify_case_site()`（現在の敷地が設定されていれば`case_matches_site()`で照合、敷地原本の無い旧ケースは従来通り素通り）を呼ぶようにし、`save()`は現在の`solar`が現在の敷地と一致しない場合に保存そのものを拒否するようにした（`scene_state()`自体は変更していない。`current_state()`など単に現在状態を読むだけの経路まで拒否すると、日時比較の「開始前状態」を読む処理などが壊れるため）。`scripts/refresh_inputs.py`の`retained_inputs()`/`scenario_inputs()`、`scripts/build-unreal-study.py`の`--state`/`--site`も同じ`case_matches_site()`で状態の`solar`を敷地と照合するようにした。「採光」「日時比較」メニューの一覧も、敷地と不一致なケースを（適用不可の理由付きで、または一覧から除外して）示すよう更新した。
- **名前付き案の読込が敷地・日時ケースを一緒に採用しない不具合（R2、W05-v1レビュー修正・2026-09-09）**：`load_scenario()`は`scenario_inputs()`が返す入力一式のうち`state`しか採用しておらず、別の敷地で保存した案を読み込んでも現在プロジェクトの`site.local.json`/`sun-cases.json`がそのまま残っていた（読込後に日時変更・再保存をすると、案とは無関係な敷地/一覧が混ざる）。`load_scenario()`を、検証済みの`state`/`site`/`sun-cases`を一組の入力として採用するよう変更した：`_validate_applicable()`による検証が全て通った**後**（＝検証失敗時は何も書き換えない）、案が`site`/`sunCases`を持てばそれぞれ`site.local.json`/`sun-cases.json`へ書き込み、持たなければ現在のプロジェクトのそれらを削除する（現在の別敷地を黙って補うのではなく「原本なし」の状態へ戻す）。W04の仕上げA/B（`start_compare()`。`_load_scenario_state()`を引き続き使用）は対象外のまま：視点・太陽・露出を固定し仕上げだけを切り替えるモードなので、敷地/日時ケースを切り替える意味がないというレビューの指摘に沿っている。

## 電気設備の再生成反映・夜間照明比較（lighting-bindings.json、W06・2026-09-09追加）

ゲストLDKで、正本（`data/electrical.json`）の照明配置をBlender/UEへ反映し、夜間の点灯・調光・色温度を比較・保存・再生成できる仕組み。既存の電気設備データモデル（上記「電気設備（electrical）」節）・太陽計算・保存/refresh基盤をそのまま再利用し、置き換えない。

- **対応範囲**：`data/electrical-catalog.json`の`category:lighting`のうちdownlight/ceiling/bracket/pendantが必須対応。indirect（間接照明の造作）とexterior（屋外灯）はW06の対象外とし、`data/visual/lighting-settings.json`の`unsupportedTypes`に理由を明記した上で、該当typeを持つ器具があれば生成前に明示的なエラーで案内する（黙って捨てない）。ゲストLDKには検証用にdownlight（`elec-200`）・pendant（`elec-201`）を新規追加し、既存`elec-008`と合わせ2グループ（`guest-ldk-main`＝シーリング+ダウンライト、`guest-ldk-dining`＝ペンダント）に編成した。light-bracketは現時点で配置インスタンスが無く、型・検証経路のみ用意している。
- **光学プロファイル（`data/visual/lighting-settings.json`、新規）**：型ごとの光源種別（point/spot）・光束(lm)・色温度(K)・spot角度・ローカル発光方向・status/noteと、比較用グループ（`groups`、器具ID一覧を持つ操作ショートカット。電気配線の回路ではない）。位置・寸法は複製せず`data/electrical.json`/`-catalog.json`のまま参照する。全プロファイルは`estimated`（実測配光・IES・実採用品番未確認）。
- **取付け位置の解決（`blender/electrical_assets.py`、新規）**：`resolve_mount()`が既存のWeb編集（`interior-white-model.html`の`placeElectricalItem()`/`electricalGroupY()`）と同じ`wallAt`+`orientation`+`center`+`side`（壁付け）／`x`+`z`（天井付け）の契約を再解決するが、**天井付けの高さは`electricalGroupY()`の平坦`CEIL_H`ではなく、`interior_geometry.ceiling_y()`（勾配天井の実形状。壁・天井生成が実際に使っているのと同じ関数）による実際の天井高からmountHeightを引いた値を使う**（W06要件：勾配天井の器具高さを平坦近似しない）。光の照射方向は器具の取付け姿勢（メッシュの向き）とは別に管理し、天井付けは勾配に関わらず常に鉛直下向き固定。壁付けの光方向は既定で器具正面（壁から外向き）とし、profile側で将来上書きできる形にしている。`build_lighting_bindings()`がroom-1f-06の対応器具を`lighting-bindings.json`（新規、schemaVersion 1.0.0）へ**一度だけ**解決し、器具メッシュ（簡易プレースホルダ、高精細モデリングは対象外）とUE側の光源の両方がこの1つの解決結果を使う。`blender/build_interior.py`の`main()`が`surface-bindings.json`と同様にBlenderパッケージの出力として書き出す。
- **UE側の反映（`unreal/import_study.py`）**：`lighting-bindings.json`を読み、器具ごとに簡易プレースホルダ（`LightFixture_<id>`、Cylinder）と`PointLight`/`SpotLight`（`Light_<id>`、`intensity_units=LUMENS`、`use_temperature=True`）を解決済み位置・方向で配置する。UE側は幾何を再解決せず、Blenderが1度だけ計算した結果を使うだけ。
- **状態の契約（`study_state.py`、schemaVersion 1.2.0）**：必須`lighting`（`mode`：day/night、`fixtures`：器具IDをキーにした疎な上書き`{on, dimming, temperatureK}`）を追加。`validate_lighting()`は型・範囲のみの構造検証（surfaceOverridesと同じ二層設計）で、欠落器具の既定値はoff・調光率1・プロファイル色温度。1.2.0は`lighting`欠落/型不正を握り潰さず必ず拒否し、1.0.0/1.1.0（lighting未対応）は自動的にday・全器具offへ正規化する（旧状態の見た目を維持し、勝手に灯った夜を作らない）。器具IDが実在するかのモデル依存チェックは`unreal/lighting.py`の`resolve_fixture_overrides()`（surface_finish_overrides.resolve_overrides()と同型）が別途行う。
- **昼夜切替と光源制御（`study_controls.py`の`apply_state()`）**：nightでは太陽（`Sun_manual_angle`）の輝度を0にし、`Sky`（SkyAtmosphere）・`SkyLight`をゲーム内非表示にする（月光なしの共通固定環境、初版の仮仕様）。dayは保存された`sunLux`をそのまま復元する（`scene_state()`は夜間中の太陽の実測輝度0をsunLuxとして読み戻さないよう、night中はbase値を信頼し、live intensityとの矛盾はUndo検知として拒否する）。各器具は`lighting.fixtures`の上書きとプロファイルから実効光束(lm×dimming)・色温度を求め、`PointLight`/`SpotLight`のIntensity/Temperatureへ反映する。光束→Blenderのenergy(W)変換は`lm/683`という単純な近似（Blender/UE間の画素値一致は要求しない、既存のW05露出近似と同じ考え方）。
- **UEの「照明」「照明比較」メニュー**：昼夜切替、器具/グループの選択→ON/OFF/調光率/色温度指定/既定へ戻す、常設の状態ラベルを提供する（`register_menu()`のラベル生成はレベル未オープン時にも呼ばれるため、`current_state()`（要:生きたシーン）ではなく直近適用済み状態/既定状態を読む设计にしている）。「照明比較」は名前付き2案の`lighting`だけを切り替えるA/B（W04の仕上げA/Bの構成を踏襲、`_validate_applicable()`が両案の周辺条件・面別仕上げ・照明器具の整合を事前確認）で、開始条件は両案ともnight（day案が混じっていれば拒否）。既存の仕上げA/B・日時A/Bは`lighting`を比較開始時点の値へ固定する。nightから日時A/Bを開始しようとした場合は「昼間へ戻してください」と案内して停止し、黙って昼へ切り替えない。
- **内覧（C++）**：`Walkthrough.cpp`の`ApplyConditions()`が1.2.0のとき`lighting`を構造検証（型・範囲・未知フィールド拒否、surfaceOverridesと同じ厳格さ）し、太陽/Sky/各`Light_<id>`アクターへ反映する。`lighting.fixtures`が参照する器具IDは`lighting-bindings.json`の実在器具と照合し、未知IDがあれば適用全体を拒否する。HUDに「照明：昼間／夜間（仮仕様）」を常設表示する（`CurrentLightingLabel()`）。`State->lighting`は既存の汎用パススルーJSONの一部のため、F5/F9の保存・復元に追加のシリアライズ処理は不要（スキーマ判定の1.2.0許可のみ追加）。
- **保存・再生成パイプラインでの伝搬**：`lighting`は`study-state.json`の一部としてそのまま既存の保存/名前付き案/refresh経路に乗る（`ALLOWED_SCENARIO_FILES`の変更は不要）。`lighting-bindings.json`は`surface-bindings.json`と同様、常に現在の正本から再解決する生成物のため、案には同梱しない。`scripts/build-unreal-study.py`は`data/visual/lighting-settings.json`を`lighting-settings.json`として、`unreal/lighting.py`を他の共有Pythonモジュールと同様にプロジェクトへコピーする。`compare-unreal-daylight.py`の固定条件チェックに`lighting-bindings.json`/`lighting-settings.json`のハッシュを追加した。
- **既知の限界**：光束・色温度は全て`estimated`（実測配光・IES・実採用品番未確認）。初版の夜間環境は月光なしの共通固定条件で、天候・実照度は校正していない。器具ジオメトリは簡易プレースホルダ（高精細モデリングは対象外）。light-bracket（壁付け照明）は配置インスタンスが無いため、取付け位置の座標検証のみ実施し、実機の見た目確認はしていない。indirect/exteriorはW06未対応（明記済み）。電気回路・消費電力・法規評価は対象外。

## 複数室対応（study-scopes.json、W07-G1・2026-09-09追加）

W02〜W06の内装比較・内覧は`room-1f-06`（ゲストLDK）単室を前提にしていた。W07-G1は、この土台を崩さずに複数室（初回はLDK＋`room-1f-05`の洋室）へ拡張する基盤を追加した。部屋間の歩行（W07-G2）自体は今回未着手。

- **スコープ（`data/visual/study-scopes.json`、新規）**：`scopeId`ごとに、その比較・生成が対象とする`roomIds`一覧と既定の対象室（`defaultRoomId`）を定義する。既存の単室運用は`guest-ldk`スコープ（`room-1f-06`のみ）としてそのまま残り、新設の`guest-pilot`スコープが`room-1f-06`＋`room-1f-05`を束ねる。**部屋自体の正本はhouse.jsonのまま**（スコープは「今回どの部屋群を比較対象にするか」という運用上の切り口にすぎない）。
- **部屋別の初期カメラ・既定バリアント（`data/visual/room-render-settings.json`、新規）**：旧来の単室カメラは`guest-ldk-study.json`に残したまま（後方互換の「読み取りアダプタ」として維持し、書き換えない）、新設のこのファイルへ部屋ごとの初期視点・既定バリアントを持たせた。`multi_room_state.room_render()`が、新設ファイルに該当室があればそれを、無ければ`guest-ldk-study.json`（LDKのみ）へフォールバックする。
- **比較状態のschemaVersion 2.0.0（`unreal/multi_room_state.py`、新規の共有モジュール）**：状態を「家全体で1つ」の項目（`scopeId`・`activeRoomId`・`activeLevel`・視点・太陽・露出・昼夜モード）と、`roomStates`（部屋IDをキーに`variant`・`surfaceOverrides`・`fixtures`を持つ）へ分離した。**Blender・UEエディタ・全CLIスクリプトが、状態の検証・移行・マージのすべてでこの1つのモジュールだけを使う**（ロジックの二重実装を避けるため）。旧1.0.0〜1.2.0（単室・トップレベルの`variant`/`surfaceOverrides`/`lighting.fixtures`）は自動的に2.0.0（自室のみを持つ`roomStates`）へ移行する。`activeLevel`は常にhouse.jsonの対象室の現在の階から導出し、保存データの自己申告を信用しない。対象外・未登録ジオメトリは固定の基準バリアント`natural`（`BASE_VARIANT`定数、C++側は`static const FString BaseVariant`で同じ値をミラー）を維持する。
- **部分適用によるマージ（`multi_room_state.partial_apply()`）**：旧LDK単室案を2室モデルへ読み込む際、対象室（LDK）のroomStateだけを置き換え、スコープ内の他室（洋室）のroomStateは現在の状態から保持する。マージの責任は`refresh-visual-study.py`（CLIの完全refresh）と`study_controls.load_scenario()`（UEエディタの案読込）の2箇所だけに限定し、Blender/UEインポータ本体（`build_interior.py`・`import_study.py`・`build-unreal-study.py`）は常に**スコープ全室を覆う`--state`**を要求し、足りない室があれば呼び出し側の誤りとして明確なエラーで停止する（生成器側での黙った補完・マージは行わない）。`refresh-visual-study.py`は新規室を許可する場合のみ明示的な`--allow-new-rooms`を要求する。
- **共有壁の両側を独立登録（壁パネル分割の修正）**：1つの壁エンティティ（`generated/interior-walls.json`）が複数室の境界を兼ねる場合、旧実装は登録済み範囲を先着順に消費しており、後から処理される側の登録が範囲を確保できず表側だけしか材質を持てなかった。`blender/surface_bindings.py`の`split_wall_at(polygon, breakpoints)`（全登録の境界の**和集合**でまず分割してから、各断片をcapごとに分類）へ変更し、`build_interior.py`の`build_envelope()`の壁ループを、1つの断片が最大2つの登録（cap 0/cap 1、それぞれ別の永続ID）を同時に持てるよう書き換えた。**実装中に、同じ断片に2つの登録がある場合、両方とも同じマテリアルスロット番号（1）で`surface-bindings.json`へ記録してしまうバグを発見・修正した**（`mesh()`のスロット割当は`face_materials`辞書への挿入順で1,2,...と決まるため、`bound`リストの挿入順どおりに`enumerate(bound, start=1)`でスロット番号を対応付けるよう修正。実UEインポート後の保存検証（`scene_state()`の材質整合チェック）が実際にこの不一致を検出して停止したことで発見した）。
- **家具・装飾の役割材質を部屋ごとに所有（`role-bindings.json`、新規のBlender出力）**：壁・床・天井（envelope）は登録済みスコープ全体を`surface-registry.json`が覆うため個別の仕組みは不要だが、家具・装飾（whole-scene role材質、旧`study-bindings.json`の単一置換対象）は生成時点でBlenderが知っている「どの家具がどの部屋か」をそのまま`role-bindings.json`（`{schemaVersion, actors: {actorName: roomId}}`）として書き出す方式にした（GLB/Interchangeのカスタムプロパティ透過に賭ける経路は採らなかった）。UEインポート・エディタ双方は、各Actorの所属室の現在バリアントから材質を選ぶ（所属室が無い＝対象外ジオメトリは`BASE_VARIANT`）。**Blender側は室のvariantごとに1組の材質セット（`mats_by_variant`/`mats_by_room`、`build_interior.py`）を用意し、`build_furniture()`/`build_decor()`が各アイテム自身の室のセットを使う**（v1レビューR5：以前は家具も常に外皮の固定基準材質を使っており、UEとBlenderのプレビューで仕上げが食い違っていた）。**材質名の区切り文字は`_`（アンダースコア）に固定している**：UEのInterchangeインポートが材質名の`.`（ドット）を`_`へサニタイズするため（実UEインポートで確認）、Blender側で`.`区切りにすると`unreal/import_study.py`の役割材質検出（インポート後の実際の材質名を室ごとの既知variantのprefixで照合するロジック）が一致せず、`study-bindings.json`が空になってしまう（v2で発見・修正）。
- **照明の部屋タグ付けとグループ検証の緩和**：`blender/electrical_assets.py`の`build_lighting_bindings()`は`room_ids`（複数）を受け取り、スコープ全体をまとめて1回だけ解決する（部屋ごとに再解決しない）。各器具は自分の`roomId`/`level`を持つ。`lighting-settings.json`のグループ検証は、「実在しないID」だけを拒否し、「実在するが今回のスコープ外の部屋に属するID」は拒否しない（対象外室だけの正常なグループを理由に生成全体を止めない、W07-G1仕様どおり）。UE側（Blender/生成レベル）は同様にスコープ外IDを許容し、操作面（UEエディタのグループ選択・`_target_fixture_ids()`）だけがアクティブ室外のメンバーを拒否する。
- **UEエディタの「対象室」メニュー（`unreal/study_controls.py`）**：新設の`select_room()`が対象室・カメラを切り替え、選択中の面・照明選択をリセットする（他室の状態・モード・太陽・露出には触れない）。面編集・照明編集メニューの一覧は対象室のものだけに絞り込む。仕上げA/B・照明A/Bは対象室のroomStateだけを比較対象に抽出し、日時A/Bは変わらず家全体（全室のroomStateを含む状態のディープコピー）の太陽条件だけを切り替える。
- **内覧（C++ Walkthrough）**：歩行対象はスコープの`walkableRoomId`（今回はLDKのみ、W07-G2で室間移動に対応予定）のまま変更していないが、`ApplyConditions()`/`SetFinish()`/F5・F9保存復元は2.0.0の`roomStates`全体を読み書きする。歩行対象室（LDK）以外のroomState（洋室）は、内覧の起動・保存・復元を通じて変更されない。
- **保存・再生成パイプラインでの伝搬**：`scripts/build-visual-twin.py`・`scripts/build-unreal-study.py`に`--scope`引数を追加（省略時は`--state`自身の`scopeId`、それも無ければ`guest-ldk`）。`scripts/refresh-visual-study.py`は保存済み状態を`multi_room_state.validate_state_own_scope()`で2.0.0へ移行してから、直前の状態と`partial_apply()`でマージした結果を新設の`merged-study-state.json`へ書き出し、これをBlender/UEへの`--state`として使う（改ざん検証用にハッシュ比較する元の`study-state.json`自体は書き換えない）。`scripts/refresh_inputs.py`・`scripts/list-study-scenarios.py`・比較系スクリプト（`compare-unreal-studies.py`/`compare-unreal-daylight.py`）も、単一の`roomId`/`variant`ではなく`scopeId`/`activeRoomId`/`roomStates`を見るよう更新した。
- **v1レビュー（CHANGES_REQUESTED）のR1〜R5修正**：R1（起動時メニュー登録が実シーン必須の`current_state()`を呼び、Houseレベル未オープン時に毎回例外）は、実シーンに触れない`_display_state()`を新設し統一。R2（`partial_apply()`のマージ結果が`incoming`側の狭いscopeIdを持ち越し、再検証で拒否される）は`partial_apply()`に`scope_id`引数を追加し常に呼び出し元の対象scopeを持たせるよう修正、範囲外室を含む`incoming`も明示的に拒否するようにした。R3（`--scenario`使用時も無条件に旧いエディタ保存だけを基準にし、より新しい内覧F5保存を無視／全室カバーの案でも不要に基準状態を要求）は、`refresh_inputs.latest_state_path()`（エディタ保存と内覧F5保存の新しい方を選ぶ共通ロジック）を新設し、全室カバー時は基準状態を一切読まないよう変更。R4（仕上げA/Bが対象室の照明まで一緒に切り替えていた）は`show_compare()`をvariant/surfaceOverridesだけ採用しfixturesを保持するよう修正。R5は上記の室別材質セット。**R5の実装過程で実UEインポートを通じて、材質名の`.`→`_`サニタイズによる`study-bindings.json`空欄化と、`_compare_status_text()`が存在しない`_compare['fixed']`を参照して仕上げA/B開始が必ず失敗する別の不具合（v1から存在）を追加で発見・修正した**。
- **検証**：Blender実行・実UEインポート（`unrealImportVerified: true`）に加え、**`--state`付き完全refresh（`refresh-visual-study.py --scenario <旧案> --scope guest-pilot`）が終了コード0で最後まで成功することを確認**（v1では終了コード非ゼロの事象を報告していたが、上記R1・R5関連の修正後は再現しない）。UEエディタでの室切替・共有壁両側の独立編集・**照明の室別独立性（対象室切替後も他室の点灯状態が保持されること）**・仕上げA/Bのfixtures保持・実在の旧1.0.0単室案（`build/scenarios/guest-a-v1`）読込による洋室roomState保持・簡単な異常系（未知の対象室・非対象室の面選択の拒否）を実機スクリプトで確認、`-RyukaSmoke`によるF5/F9往復を実機確認した。詳細は[W07-G1-report.md](tasks/W07-G1-report.md)を参照。
- **既知の限界**：室間の歩行移動（G2）・残り6室の登録（G3）は未着手。`role-bindings.json`は今回`decoration.*`オブジェクトを一律LDK扱いにしている（洋室の装飾は今回未追加のため）。

## ゲスト室間移動・扉の開閉（circulation.py、W07-G2・2026-09-10追加）

W07-G1は編集対象2室（LDK・洋室）の基盤のみで、内覧（UE Walkthrough）は歩行できる室を1室（LDK）に固定していた。W07-G2は、ゲスト8室（`room-1f-02`玄関・`room-1f-24`ホール・`room-1f-06`LDK・`room-1f-05`洋室・`room-1f-01`トイレ・`room-1f-03`洗面脱衣・`room-1f-04`UB・`room-1f-23`収納）を実際に歩いて行き来し、扉を開閉できるようにした。**編集対象scope（LDK・洋室の2室、`study-scopes.json`）と、内覧が歩ける室の集合（8室、後述の`walkthrough-profiles.json`）は別概念のまま**（同じ室が両方に属することはあるが、集合として一致しない）。

- **扉・室の接続はジオメトリのみで解決し、ラベルは根拠にしない（`unreal/circulation.py`、新規の共有モジュール）**：`resolve_connections(rooms_by_id, interior_doors, catalog, room_ids)`が、各内部扉の`(orientation, wallAt, center, width)`（幾何情報のみ）と各室ポリゴンの辺を照合し、どの2室を実際に繋いでいるかを求める。`interior-doors.json`自身の`label`テキストは一切参照しない。今回の調査で、複数の扉ラベルが「ホールが玄関から分離される前」の古い室名のまま（例：door-002は「玄関⟷洗面脱衣室」と書かれているが実際はホール⟷LDK、door-004は「玄関⟷LDK張り出し」と書かれているが実際はホール⟷洗面脱衣）であることが判明しており、ジオメトリだけで解決することでこの食い違いに影響されない。解決結果は7接続（door-001 引き戸：トイレ⟷ホール、door-002 開き戸：LDK⟷ホール、door-003 開き戸：洗面脱衣⟷UB、door-004 開き戸：洗面脱衣⟷ホール、door-005 引き戸：洋室⟷ホール、door-024 両開き：洋室⟷収納、door-025 開放：玄関⟷ホール）。今回は`swing`/`double-swing`/`slide`/`open`のみ対象（`fold`等、自宅で必要になる操作は今回一般化していない）。`open`は扉本体を持たず常時通行可能・状態も持たない。
- **内覧が歩ける室の集合は編集scopeと別の「歩行プロファイル」（`data/visual/walkthrough-profiles.json`、新規）**：`profileId`ごとに対応する`scopeId`・歩行対象`roomIds`・開始室`entryRoomId`を持つ。新設の`guest-circulation`プロファイル（`scopeId: guest-pilot`、8室、開始室は玄関）に加え、旧`guest-ldk`スコープはそのまま`guest-ldk-solo`プロファイル（単室・0扉）として残し、**旧来の単室内覧の挙動をそのまま保持**する（歩行ロジック自体はどちらも同じC++コードパスで、単室・0接続のプロファイルはそこへ自然に縮退するだけで、別実装ではない）。
- **扉の実体・開閉ジオメトリ（`door-bindings.json`、新規のBlenderが出力する共有中間ファイル）**：`build_interior.py`が、生成時点のプロファイルに含まれる扉（＝上記`resolve_connections()`の結果）ごとに、独立して動く扉パネル（`swing`は1枚、`double-swing`は2枚、`slide`は1枚）を実体のメッシュとして生成し、`doorId→{roomIds, operation, openable, leaves:[{actor, kind, openYawDeltaDeg|openOffsetCm}]}`として書き出す。`unreal/import_study.py`がこれを読み、扉パネルのActorだけをMovable化する（このプロジェクトの全体方針「メッシュ頂点はワールド座標へ焼き込み、Actorの原点は常に(0,0,0)」の**唯一の例外**が開き戸パネルで、原点を蝶番位置へ再配置する。UEの`SetActorRotation()`はActor自身の原点まわりに回転するため）。引き戸パネルは原点をワールド原点のままにし、`openOffsetCm`（沿い方向の平行移動量、UE cm単位）だけで開閉する。
- **回転・平行移動の角度・距離はBlender生成時にPythonで確定し、C++実行時には一切再計算しない**：`circulation.py`の`swing_hinge_and_delta()`/`double_swing_hinges_and_deltas()`/`slide_open_offset()`が、`hingeSide`/`swingDir`/`slideDir`から開き角（基準85度）・平行移動量（扉幅ぶん）をソース単位で計算し、`door-bindings.json`へそのまま書き出す。C++側は`SetActorRotation(FRotator(0,Delta,0))`／`SetActorLocation(SpawnBase+Offset)`をそのまま適用するだけで、Blender側の内部座標規約を一切知る必要がない。
- **whole-house比較状態のschemaVersion 2.1.0（`unreal/multi_room_state.py`）**：`doorStates: {doorId: {open: bool}}`（家全体、部屋別ではない）と、任意の`walkthrough: {profileId, roomId, level}`（内覧自身が最後にいた位置の自己申告、家全体の付随情報）を追加した。`V2_SCHEMA_VERSIONS=('2.0.0','2.1.0')`とし、2.0.0（W07-G1、扉・内覧位置の概念自体が無い）は「扉指定なし＝全扉閉、内覧位置なし」として2.1.0へそのまま正規化する（1.0.0〜1.2.0からの移行と同じ「その項目が存在しなかった時代の状態」という扱い）。`doorStates`の未知IDや非対象扉（`open`操作など扉本体を持たない接続）は、surfaceOverrides/fixturesと同じ厳格さで（構造検証はスキーマ側、モデル存在チェックは`circulation.resolve_door_overrides()`側という役割分担も既存の`resolve_overrides()`/`resolve_fixture_overrides()`と同型）、適用前に拒否する。`walkthrough`の`roomId`は内覧自身が復元時に**現在のモデルに対して自己検証**し（存在しない室なら開始室へフォールバック）、自己申告を鵜呑みにしない。
- **「現在いる室（歩行位置）」と「編集対象室（activeRoomId）」の分離（`Walkthrough.cpp`）**：C++のみが持つ`CurrentRoomId`（歩行位置。JSON上は見えない）と、既存の`State->activeRoomId`（編集対象。JSON上に見え、仕上げキー1/2/3の対象）を明確に分離した。編集scope内の室（LDK・洋室）へ歩いて入ったときだけ、`CurrentRoomId`→`activeRoomId`への**一方向同期**が起こる（ホール等の非編集室へ入っても`activeRoomId`は変わらない、逆方向の同期は無い）。非編集室にいる間は、HUDが「この部屋は編集対象外です」と表示し、`SetFinish()`／`CurrentVariantLabel()`は何もしない（メニュー自体は無いが、内覧のキー入力・native自己診断の双方でこの分岐を持つ）。室切替それ自体は仕上げ・照明・太陽・露出を一切変更しない。
- **室の判定は「現在の室を優先する厳密判定」→「隣接室だけを1ホップで確認」（`UpdateCurrentRoom()`）**：まず`CurrentRoomId`自身の室ポリゴンに（境界余裕なしで）まだ含まれるかを確認し、含まれていれば即座に確定する（扉の厚み部分で直前の室を維持するのはこの優先順が理由）。含まれなくなっていた場合のみ、`walkthrough.json`の接続情報から**直接繋がっている室だけ**を1ホップで確認する。移動は連続的（テレポートではない）なので、1ホップの探索で必ず正しい室へ辿り着く。
- **安全境界の緩和は開閉状態と無関係（`InsideRoomPolygon()`のマージン緩和）**：通常の26cm境界余裕は、その室の「開口窓」（`RoomOpenings`、扉・通路の位置とスパン）の位置では、扉が開いているか閉じているかに関わらず**常に**緩和される。実際に通行を止めるのは、閉じた扉パネル自身の物理コリジョン（`Prepare()`が家具と同じ規則で全Actorへ付与するBlockAll＋complex-as-simple、扉パネルはW07-G2でMovable化されただけで判定方式は変更していない）であり、この境界判定はあくまで「壁のない開口部分の柔らかい境界」を扱うためのもの。
- **扉の操作（`InteractDoor()`、Eキー）**：正面付近（`FindNearestDoor()`、毎Tick、対象は`CurrentRoomId`に接する開閉可能な接続のみ、距離250cm・向き概ね一致）にいる扉をトグルする。仕上げ・照明と同じ「候補をすべて集めてから一括適用（`ApplyConditions()`のトランザクション方式）」規律に従い、扉パネルの移動を含む適用が失敗するか、適用後にプレイヤー自身の位置が安全でなくなる（扉に干渉している）場合は、扉状態・パネル位置とも元へ戻し理由をHUDへ表示する（先に扉を閉じてから安全確認する、という順序にはしない）。
- **F5/F9は扉状態・内覧位置も含めて往復する**：F5（`SaveView()`）は視点・レンズに加え、`walkthrough`（`profileId`・現在室・現在階）を書き込む（`doorStates`・`roomStates`自体は各操作のたびに`State`へ反映済みのため、F5時点で追加の書き込みは不要）。F9（`RestoreView()`→`Restore()`）は、**候補（保存データ）の扉状態を先に適用してから**（`State`と`CurrentRoomId`を候補へ切替→`ApplyConditions()`）安全な開始位置を探す（先に現在の扉状態のままプレイヤーを動かし、後から扉を切り替えて壁に押し込む、という順序を避けるための順序）。保存位置が新しい扉状態のもとで塞がっている場合は、同じ室内で15cm間隔の候補を探索し、見つからなければ現在のシーン・保存データを維持して拒否する（歩行対象がホール等の非編集室になった今回も、この安全探索ロジック自体はW07-G1から変更していない）。
- **名前付き案の比較は、扉状態を比較開始時点の値に固定し、案の扉状態は採用しない**：`unreal/study_controls.py`の仕上げA/B・照明A/Bは、対象室のvariant/surfaceOverridesまたはfixturesだけを候補から採用し、`doorStates`は常に`_compare['before']`（比較開始時点のディープコピー）のまま変更しない構造になっている（比較中に候補の`doorStates`を一切参照しないため、追加のガードなしで自然にこの契約を満たす）。一方、**名前付き案の通常読込（`load_scenario()`）は`doorStates`を家全体の項目として案の値を丸ごと採用**する（`multi_room_state.partial_apply()`が`doorStates`/`walkthrough`を`roomStates`と同様に「案の値」として扱う）。読込前に`circulation.resolve_door_overrides()`で案の`doorStates`が現在のモデルと整合するかを検証し（敷地・日時と同じく、シーン・ファイルへ触れる前に検証を完了する）、扉トグル用のUIは今回のエディタメニューには追加していない（仕様上必須ではなく、`doorStates`自体は上記の経路で正しく往復することを確認済みのため）。
- **`refresh-visual-study.py`の入力ハッシュ・引き継ぎ検証**：`unreal/circulation.py`・`data/visual/walkthrough-profiles.json`は既存の再帰的ソースハッシュ（`data/**/*.json`・`unreal/**/*.py`）にそのまま含まれる。`door-bindings.json`は生成物のため`build-visual-twin.py`の成果物マニフェスト（`artifacts`）に追加した。`tests/validate_study_transfer.py`は`doorStates`／`walkthrough`が完全refreshを通じて完全に一致することを追加検証する。
- **W07-G1-v2レビューの「進行を止めない改善事項」対応（部分案refreshの基準保存の記録・変更検出）**：G1-v2レビューで指摘された「部分案refreshの基準保存（`--previous`の対象外室ぶんを補う元データ）自体が、選択元ファイルパス・ハッシュを記録されておらず、生成中の変更も検出できない」という残件を本ラウンドで対応した。`refresh-visual-study.py`は、部分案（対象scopeの全室をカバーしない選択）の場合に読む基準保存（`latest_state_path()`が選んだファイル）を`saved/base-study-state.json`へスナップショットし、`refresh.json`の`baseState`へ`{source, sha256}`を記録する。`unchanged()`（各工程の前後で呼ばれる改ざん検出）は、この基準ファイルの実体とスナップショットの両方のハッシュを既存のretainedHashes等と同じ規律で再確認する。全室カバーの選択（`covers_all_rooms`）では基準保存を一切読まないため、`baseState`は`null`のまま記録される。
- **実装中に発見・修正した実際の幾何/コリジョン不具合**：`blender/build_interior.py`の開口枠生成（窓・扉に共通）は、扉のsill（敷居）部分にも他の枠部材（左右・上枠）と同じ厚み・コリジョンの帯（frameWidthぶん、4.5cm）を生成していた。`openings()`の内部扉ぶんの`bottom`計算（`base`＝階の絶対床高、例：1階0.707m）は、扉カタログ自身の`sill`値（本物件は全種`sill=0`）を一切加味しないため、**すべての内部扉のsill帯が常に床レベルぴったりに生成される**。W07-G1までは内覧が単室（開口部を横断する必要が無い）だったため気づかれなかったが、W07-G2で実際に扉を横断する段になって、このsill帯の高さ(4.5cm)がキャラクターの`MaxStepHeight`(2cm、W01から変更なし)を上回り、**扉を開けても敷居部分で必ず通行がブロックされる**ことが実UE走行で判明した。外部開口（窓、`o['exterior']==True`）のsillは本来の高さのまま（`base+o['sill']`、常に歩行位置より高い）で影響が無いため、内部扉（`o['exterior']==False`）のsill帯生成だけをスキップするよう修正した（真正の敷居がある扉は本物件のカタログに存在しないため、内部扉のsill帯を完全に省略する形とした）。
- **検証**：実Blenderビルド・実UEインポート（`unrealImportVerified: true`）・C++ Walkthroughモジュールの実コンパイルに加え、`-RyukaSmoke`ネイティブ自己診断、UEエディタでの`study_controls.py`検証（`verify_w07_g2.py`）、完全refresh1回を実施（v1の内容。レビューv1対応後の最新の確認項目・件数は下記「レビューv1（R1〜R4）対応」節と[W07-G2-report.md](tasks/W07-G2-report.md)を参照）。
- **既知の限界**：`fold`／`double-fold`操作の扉（自宅で使用予定）は今回一般化していない（本ラウンドのゲスト8室に該当する扉が無いため）。残り6室（G3）の内覧・扉登録は未着手。エディタメニューに扉トグルの直接操作UIは無い（`doorStates`自体の往復は確認済みだが、F5/F9・名前付き案経由以外で編集画面から扉を開閉する手段は今回追加していない）。

### レビューv1（R1〜R4）対応（2026-09-10）

W07-G2の初回提出（`89d07af`）はGPTレビューでCHANGES_REQUESTED。同じG2ラウンドで以下を修正した（BASE `60d8cd6` は不変）。詳細は[W07-G2-report.md](tasks/W07-G2-report.md)。

- **R1：`doorStates`を「実際の扉パネル」へ適用する**。以前は`apply_state()`が扉IDを検証するだけ、Blenderは常に閉で生成、インポートは葉をMovable化するだけで、保存済みの「扉開」がエディタ／Blenderの見た目・採光・比較へ反映されなかった。修正：葉ごとに`bakedOpen`（bool、生成が実際に開ポーズで焼いたか）を`door-bindings.json`→`walkthrough.json`／`study.json`へ記録し、**Blender生成・UE初期インポート・`apply_state()`／案読込の3経路すべて**が同じ`doorStates`を実葉のtransform（回転は絶対値、位置は「閉基準＋オフセット」の絶対セット）へ適用する。閉基準は`bakedOpen`から復元し「いま見えているポーズ＝閉」と決め打ちしない。引き戸は**アウトセット引き戸**としてモデル化（壁の片面へ寄せる分を閉配置へ焼き込み、`openOffsetCm`は純粋な沿い方向平行移動）し、開いた生成物がモデル化されていない壁ポケットへ埋め込まれる問題も解消した。
- **R2：エディタ視点変更後の古い`walkthrough.roomId`で復帰先を誤らない**。`select_room()`／`remember_view()`は`state['walkthrough']=None`（どちらのカメラも内覧が実際にいた位置ではないため再解決でなく解除）。C++`Restore()`は、`walkthrough`が無ければ`EntryRoomId`（初回起動）、有れば`profileId`・`roomId`実在・`level`一致を全て満たすときだけその室を復帰対象にし、1つでも外れたら「保存データの内覧位置が現在のモデルと整合しません」で`return false`（黙って玄関へ読み替えない）。安全補正は解決済み同室内に限定、既存の全室`roomStates`／`doorStates`／`solar`は保持。
- **R3(a)：両開きの両葉が同じ室へ開く**。`double_swing_hinges_and_deltas()`の右葉への`sign=-1.0`を削除（`_swing_delta_deg()`が葉の`hingeSide`で既に符号反転しており、二重反転で両葉が別々の室＝片方収納・片方洋室へ開いていた）。修正後door-024は左`-85`／右`+85`。あわせて開く向きを`swingDir`/`hingeSide`（外部開口用で室内は不定）でなく**ジオメトリ由来の`swingToward`**（共有壁からの到達距離が長い＝部屋の側へ開く）で決める。
- **R3(b)：可動葉の移動領域・近距離遮蔽の検査**。`LeafMotionClear()`（新規、`Walkthrough.cpp`）：葉の`From`→`To`を6ポーズ×葉幅方向4点の小球で離散サンプリングし、家具・内装・別の扉の葉・設置障害物が経路に重なる開扉を拒否する（始点/終点が個別に空いていても中間ポーズで拒否できる）。構造壁（`wall_`/`Ground_`）と扉自身の枠・兄弟葉は除外（壁は「どこまで開くか」の固定制約、壁越し操作は`FindNearestDoor()`のライントレースが担当）。**開扉方向のみ検査**（閉扉は検証済みの焼きポーズへ戻すだけ）。物理シミュレーション・アニメーションは無し。`FindNearestDoor()`は正面判定を`Controller->GetControlRotation()`へ変更（`Eye`の前方ベクトルは1フレーム遅延）し、視点→扉のライントレースで壁越しの扉を除外する。
- **R4：指定経路の実機確認**。`-RyukaSmoke`を「扉ごとのテレポート分離」から**1本の連続スイープ**へ置換：玄関→ホール(door-025)→door-002開扉→LDK→ホール→door-002閉扉→door-005開扉→洋室→（洋室でFinish2→F5→ホールへ→door-005閉→F9で室/位置/扉/両室状態を復元）→洋室→ホール→door-001開扉→トイレ到達。両開きdoor-024は焦点確認（閉時ブロック／`fur-007`がアーク内にあると開扉拒否／`fur-007`のコリジョンを一時無効化すると両葉が動いて通行可・収納側へ到達／閉扉可）。NullRHI・DX12の両方でPASS、`walkthrough-smoke.png`取得。
- **文書化した固定幾何の限界**：door-024（洋室⟷収納の両開き）の開き角はゲスト用冷蔵庫`fur-007`（`data/furniture.json`、`status:"estimated"`、施主指示で270°へ回転・位置調整済み）の扉部分がアーク内にあるため制限される。収納は宿泊客の必須動線ではないため、機構（R3(a)/(b)）は代表確認済み・実通行は`fur-007`を除いた状態で確認、として記録する。door-002（LDK⟷ホール）の全開はLDK内側のL字壁で制限される（開扉・通過は成立）。

## 内覧モード（walk）

俯瞰・平面図の間取りを実際に歩いて体験できることを目的としたモード。壁の当たり判定は上記「rooms / walls について」の自動導出壁（`wallSegmentsByLevel`）を使い、これに加えてドアの扉本体（近づくと開く演出）と家具の当たり判定を持つ。

- **窓（`windowGapsForLevel()`）**：ドアと同じ`OPENINGS`配列に含まれるが、`category`が`'door'`以外（`'window'`）のものは、壁を全高では切り欠かない。`openingWallGeom(o, level)`（面(N/S/E/W)から`{orientation, at, from, to}`を求める、ドア・窓で共通のヘルパー）に`sill`（下端高さ）・`h`（窓の高さ）を加えたものを`windowGapsByLevel`として一度だけ計算しておき、壁メッシュ生成時（後述）に使う。`wallSegmentsByLevel`（当たり判定用）には含めないため、窓のある位置は今まで通り実体としては壁のまま＝通り抜けられない（窓を開けて出入りする、という状態までは表現しない）
  - 壁メッシュ生成（`[1,2].forEach(level=>{...})`）では、各壁セグメントの範囲に重なる窓があれば、そのセグメントを「沿い方向(u)×高さ方向(v、床からの相対高さ)」の矩形とみなし、階段の吹き抜け穴と同じ`rectMinusRect()`を使って窓の帯（`u:[from,to]`, `v:[sill, sill+h]`）を切り欠いた残りの矩形群を壁として描画する。窓自体の範囲には、半透明の水色（`walkWindowMat`）＋枠線（`walkWindowFrameMat`）のガラス面を追加し、内覧モードでも「ここに窓がある」とわかるようにする（すりガラス風の半透明で、外の様子がうっすら透けて見える）
- **開口（アーチ、`addWalkArchInfill()`）**：`doorGapsForLevel()`自体はアーチ開口（`operation:'open-arch'`）も他の開口と同じ「壁を全高で切り欠いた矩形の通路」として扱う（当たり判定上はこれで十分。弧の形まで衝突判定はしない）。そのままだと内覧モードでは天井まで抜けた四角い開口に見えてしまうため、`archOpeningMesh()`と同じ弧の式を使って、弧の外側（左右の迫り持ち＝スパンドレル部分。頂点で接するため`archSpandrelShapes()`が左右別々のシェイプとして返す）と、弧の頂点からドアの高さ・天井高の差ぶんの垂れ壁を、壁と同じ色・厚みで追加描画し、アーチらしい輪郭を内覧モードでも再現する。`INTERIOR_DOORS`・`OPENINGS`（`category==='door'`）の両方の`open-arch`に対応する
- **ドアの扉本体（`interior-white-model.html`、`walkDoorAnimators`）**：平面図モードのドア記号（`groups.doors1/2`・`groups.openings1/2`）は内覧モードでは非表示にしている（`enterWalkMode()`）代わりに、`addWalkDoorLeaves()`が実際に厚み(0.04m)のある扉パネルを閉位置で`walkGroup`に常設する。`data/interior-doors.json`・`data/openings.json`の`operation`が`swing`/`fold`/`double-swing`/`double-fold`/`slide`のものだけが対象（`open`/`open-arch`/窓は扉本体を持たないので何も作らない）
  - 開き戸は`addWalkSwingLeaf()`が、蝶番位置を原点にしたグループを`rotation.y`で回転させて開閉する。閉位置・開位置の角度は、沿い方向／壁に直交する方向の単位ベクトルから`Math.atan2()`で求める（`boxWireRotated()`と同じ「ローカル+Zがワールド(sinθ,cosθ)方向を向く」規約）。2つの角度の差が180度を超える組み合わせ（蝶番側・開く向きの取り方によっては起こりうる）で遠回りに回転しないよう、`shortAngleLerp()`で最短経路を補間する
  - 両開き戸は、開口の両端をそれぞれ蝶番にした2枚の`addWalkSwingLeaf()`呼び出し（平面図記号の`double-swing`表現と同じパターン）。引き戸は`addWalkSlideLeaf()`が沿い方向に平行移動する
  - **折れ戸・両開き折れ戸（`addWalkFoldLeaf()`）は、実際の2枚折れの機構をそのまま再現する**（2026-08-16、当初は開き戸と同じ回転運動で近似していたが、施主指摘によりモーションを作り直した）。蝶番(A、`hingeAt`)を壁に固定した親グループ（パネル1、長さ`L=w/2`）の子に、Aから局所距離Lの位置（＝折れ点B）を原点にした孫グループ（パネル2、同じ長さL）をぶら下げる構成にし、パネル2をパネル1に対して**常に逆向きに2倍の角度**で回転させる（鏡映の関係）。この幾何拘束により、自由端(C)は常に壁面の延長線上（沿い方向の直線上）に留まったまま、折れ点Bだけが壁から張り出す、という実際の折れ戸と同じ動きになる。開いた状態の折れ角は、平面図の折れ戸記号（`drawFoldLeaf()`、A-B=B-C=A-C=w/2の正三角形）と同じ60度（全開=90度に対して2/3）を終点にし、平面図・内覧の見た目を揃えている。両開き折れ戸は、開口の両端をそれぞれ固定蝶番にした2組の`addWalkFoldLeaf()`呼び出し（閉状態では両者が開口中央で合わさる）
  - 毎フレーム`updateWalkDoors(dt)`が、プレイヤー座標(`walkPos`)と各ドアの中心（`anchorX`/`anchorZ`）との距離を測り、`WALK_DOOR_OPEN_RADIUS`（1.8m）以内なら開き位置、それ以外なら閉じ位置へなめらかにイージングする（`t`：0=閉、1=開）。別の階にいる間（`level !== walkLevel`）は`t`を強制的に0に戻す
  - **通行そのものはドアの開閉状態と無関係**：施主指示により、壁側の開口（`doorGapsForLevel()`）は今まで通り常に開いたままで、扉パネルはあくまで見た目の演出。「閉まっている間は通れない」という厳密な当たり判定は実装していない
- **家具の当たり判定（`furnitureSegmentsByLevel`）**：家具の回転は0/90/180/270度のみ（`data/furniture.json`の前提）なので、回転後の外形は必ず軸に沿った矩形になる。`FURNITURE_ITEMS`の各アイテムについて、回転に応じて`width`/`depth`を入れ替えた実効矩形を求め、その4辺を壁と同じ「線分＋当たり判定半径」の仕組み（`segListBlocked()`、旧`resolveWalk()`内の`blockedBy()`を独立関数化したもの）にそのまま追加する（厚みは0＝辺そのものが家具の表面）。「物との距離が狭いか広いか」を体感できるように、家具の種類を問わず一律に当たり判定の対象にしている
- **三人称視点（`walkView`）**：マインクラフト風に、キャラクターを背後から追従するカメラで空間の広さ・狭さを外から把握できるモード。内覧モードのHUDのボタン（🧍）または`V`キーで一人称（`'first'`）と切り替える（`toggleWalkView()`、モードに入るたびに一人称にリセットされる）
  - **キャラクターモデル（`walkCharacterGroup`）**：成人男性の平均身長170cmを想定した簡易ブロック体型（脚0.85m＋胴0.55m＋頭0.30m）。横幅（肩幅、腕を含めた最大幅）は日本人成人男性の平均的なbideltoid幅（約44〜46cm、産総研の人体寸法データベースを参考）に合わせて約46cmにしている（2026-08-16、施主指摘により調整。当初は胴体の外側にそのまま腕を足す作り方だったため肩幅だけで64cmとかなり広くなっていた。腕は自然に立った姿勢を想定し、胴体の縁にほぼ重なる位置に置くことで実寸に近づけた）。あくまでスケールの目安であり、実際の体型・服装は表現しない。局所座標は足元をy=0、正面を+Z向きとして組み、`group.rotation.y = walkYaw`をそのまま使えるようにしている（`boxWireRotated()`や扉の開閉演出と同じ「ローカル+Zがワールド(sinθ,cosθ)方向を向く」規約）。一人称モードでは非表示（`updateWalkCamera()`が`walkView`に応じて`visible`を切り替える）
  - **歩行アニメーション（手足の振り、`walkCharLimb()`）**：脚・腕は`walkCharPart()`（固定位置のボックス）ではなく`walkCharLimb()`で作る。こちらは関節の高さ（脚なら股関節y=0.85、腕なら肩y=1.40）を原点にしたグループを返し、箱はその関節から下にぶら下がる形で配置する。関節グループの`rotation.x`を変えると、関節を中心に前後（ローカルZ方向）へ振り子のように振れる。`updateWalkMovement(dt)`が、移動入力があるかどうか（`len>1e-4`）に応じて`walkCycleAmount`（0=静止〜1=全振幅）をなめらかにフェードさせつつ、動いている間だけ`walkCyclePhase`を進め、`Math.sin(walkCyclePhase)*walkCycleAmount`を基準に4本の関節の`rotation.x`を設定する。左脚と右脚は逆位相（左右交互）、腕は同じ側の脚と逆位相＝対側の脚と同位相（左脚⟷右腕、右脚⟷左腕が同時に振れる、実際の対側性歩行と同じパターン）にしている（2026-08-16、施主指摘により追加：「歩くと手足が動くようにしてほしい」）
  - **カメラ位置**：注視点（キャラの頭部付近、床から`THIRD_PERSON_TARGET_HEIGHT`=1.5m）から、一人称と同じ`(fx,fy,fz)`のforwardベクトルの逆方向へ`THIRD_PERSON_DISTANCE`=1.7m離れた位置に**常に固定**する。`walkPitch`で見上げ・見下ろしすると、その分カメラも上下に弧を描くように動く（forwardベクトルを一人称・三人称で共用しているため）
  - **壁・家具への追従による自動ズームは行わない**：当初は壁・家具に応じてカメラ距離を自動的に詰める実装（`pointBlocked()`で衝突判定し、ぶつかる手前まで距離を縮める）だったが、この家は部屋の中央でも壁・家具まで1m未満のことが多く、歩くたびにカメラがズームイン/アウトを繰り返して落ち着かないと施主から指摘があり、距離を常に一定にする方式に変更した（2026-08-16）。壁にめり込む場合はそのまま許容する（カメラが壁の裏側に回り込み、壁の内側の面が大写しになることはあるが、通行や当たり判定には影響しない）。距離自体も当初の3.2mから1.7mに詰めた（施主指摘）
- **ミニマップ（`drawMinimap()`）**：画面右上に、現在階（`walkLevel`）の平面図とプレイヤーの位置・向きを表示する2Dキャンバス（`#minimap`、Three.jsの3D描画とは独立した`CanvasRenderingContext2D`）。クリックでその場所へワープできる
  - 壁の線は`wallSegmentsByLevel[walkLevel]`（当たり判定・壁メッシュ生成と同じ導出結果）をそのまま使うため、実際に歩ける壁の配置と常に一致する。表示範囲は`FLOOR1`/`FLOOR2`の外接矩形から`floorBounds()`で求め、階段で階を跨ぐと自動的に表示階が切り替わる
  - `minimapTransform(level)`が建物ローカル座標⇔キャンバスピクセル座標の変換（アスペクト比を保った単純な拡大縮小＋中央寄せ）を提供する。プレイヤーは点＋`walkYaw`方向の短い線（一人称・三人称のforwardベクトルと同じ`(sin(walkYaw), cos(walkYaw))`の向き）で表示する
  - クリック時は、クリック位置を`minimapTransform().toWorld()`で建物ローカル座標に変換し、`segListBlocked()`で壁の中でないか確認してから`walkPos`を直接書き換える（＝視線方向はそのまま、位置だけ瞬間移動）。壁の中をクリックした場合は何もしない

## 変更手順

### 建物の寸法・間取りを変更する

1. `data/house.json` を編集する（既存IDの値を変更するだけなら自由。要素の追加・削除は次の点に注意）
2. `python tests/validate_house.py` でデータを検証する。任意でDraft 2020-12対応のJSON Schemaバリデータで `data/house.schema.json` に対してフル検証してもよい
3. `node scripts/build-web-data.mjs` で `generated/house-data.js` を再生成する
4. `interior-white-model.html` をブラウザで開いて確認する（`node scripts/build-web-data.mjs --check` で生成物が最新か機械的に確認できる。CIやコミット前チェックに使える）
5. 壁・床・階高・窓・ドア・部屋の輪郭など、Blenderにも影響する変更なら以下を実行する

   ```
   blender --background --python blender/build_house.py -- --input data/house.json --output build/ryuka-white-model.blend
   ```

要素を追加・削除する場合は、その配列（`footprints` / `rooms` など）の中で一意なIDを新規発番し、`status` を適切に設定すること。壁（`walls`）は`rooms`から自動導出されるため、`rooms`を編集するだけでよい（上記「rooms / walls について」参照）。窓・ドアは`house.json`ではなく`data/openings.json`/`data/interior-doors.json`側で管理する（下記「窓・ドアの種類を追加する、または直接JSONを編集する」参照）。

### 家具・設備の位置・向き・サイズを調整する（Web UI、推奨）

1. ブラウザで平面図モードを開き、「✎ 家具編集」をONにする
2. 家具をクリック/タップで選択→ドラッグで移動。パネルから90度回転・幅/奥行/高さを変更する（編集は自動的にlocalStorageへ下書き保存される）
3. 決まったら「furniture.jsonを書き出す」でJSONをダウンロードし、リポジトリの`data/furniture.json`を上書きする
4. `python tests/validate_furniture.py` で検証し、`node scripts/build-web-data.mjs` で再生成してコミットする

### 家具・設備の種類を追加する、または直接JSONを編集する

1. 新しい種類を置きたい場合は `data/furniture-catalog.json` に`type`を追加する（`shape`が既存のものと違う形なら`interior-white-model.html`の`FURNITURE_SHAPES`にも描画関数を追加する）
2. `data/furniture.json` の `items` に配置を追加・編集する。`room`は`house.json`の`rooms`のidを参照させると、`tests/validate_furniture.py`が部屋の外形と大きく外れていないか機械チェックしてくれる。`label`は上記「`label`の命名規則」に従うこと
3. `python tests/validate_furniture.py` で検証する
4. `node scripts/build-web-data.mjs` で再生成し、ブラウザで確認する

### 窓・ドアの位置・種類・サイズを調整する（Web UI、推奨）

1. ブラウザで平面図モードを開き、「✎ 窓・ドア編集」をONにする
2. 窓・ドアをクリック/タップで選択→壁に沿ってドラッグでスライド（壁の外へは出せない）。パネルから種類切替・幅/高さ/シル高の変更・開き勝手の変更ができる（編集は自動的にlocalStorageへ下書き保存される）
3. 決まったら「openings.json」「interior-doors.json」の両方（編集した方だけでよい）を書き出し、リポジトリの`data/openings.json`・`data/interior-doors.json`を上書きする
4. `python tests/validate_openings.py` で検証し、`node scripts/build-web-data.mjs` で再生成してコミットする

### 窓・ドアの種類を追加する、または直接JSONを編集する

1. 新しい種類を置きたい場合は `data/door-catalog.json`（ドア）または`data/window-catalog.json`（窓）に`type`を追加する
2. `data/openings.json`（外部）または`data/interior-doors.json`（室内）の `items` に配置を追加・編集する。ドアは型の`operation`に応じて`hingeSide`+`swingDir`（開き戸）または`slideDir`（引き戸）を設定する（`open`/`open-arch`は不要）
3. `python tests/validate_openings.py` で検証する（型の参照・寸法・壁/footprintとの整合をチェックする）
4. `node scripts/build-web-data.mjs` で再生成し、ブラウザで確認する

### HTML表示だけを変更する（カメラ・色・メニュー・レイアウト等）

`interior-white-model.html` を直接編集してよい。`data/house.json` の再生成は不要。ただし `<script src="generated/house-data.js">` より後ろの部分（Three.jsセットアップ以降）のみを触ること。データ定義部分はもう存在しない。

### Blenderのマテリアル・レンダリング設定を変更する

`blender/build_house.py` の該当箇所（`material()` 呼び出しやレンダー設定）を編集する。ジオメトリ生成ロジック自体は `house.json` の構造に依存しているので、データ契約を変えない範囲で調整する。

## 検証チェックリスト

1. `python tests/validate_house.py` が通ること
2. `python tests/validate_furniture.py` が通ること
3. `python tests/validate_openings.py` が通ること
4. `node scripts/build-web-data.mjs --check` が「up to date」と報告すること（生成物のコミット漏れがないか）
5. Blenderが利用可能なら、上記のBlender生成コマンドが正常終了すること
6. Blenderの上面正射投影ビューと、Three.js側の平面図モード（910mmグリッド）を見比べて整合を確認する
7. 4つの1F求積ゾーン、2Fフットプリント、階高、開口部、室内ドア、部屋数、壁数、防音壁、屋根（1F片流れ2枚＋2F切妻1式）を数の上で確認する（現在の数はSTATUS.mdに記載）
8. 不整合を見つけたら、該当する正本ファイル（`house.json`/`openings.json`/`interior-doors.json`等）側のデータ問題として記録する。生成された `generated/house-data.js` やBlenderジオメトリを直接手で編集しない

## 公開（GitHub Pages / PWA）

**https://kenryuuuuuuuuuu.github.io/Ryuka-Interior-Designer/** で公開している（2026-08-14、`main`ブランチのルートから配信。GitHub Pages設定は`gh api`で有効化した）。

- `index.html` はPagesのルートURL（`/`）が解決される先。中身は`interior-white-model.html`への即時リダイレクトのみで、建物データや表示ロジックは持たない
- `manifest.webmanifest`・`icon.svg`・`sw.js`によりPWA化している。スマホでURLを開き「ホーム画面に追加」すると、アイコンから直接起動できる（`Ryuka-Landscape-Designer`と同じ構成）
- オフライン起動のため、Three.js本体は`vendor/three.min.js`にローカル同梱している（CDN参照はしていない）。ローカルで`file://`から開く場合も同じファイルを読む
- `sw.js`はHTML/JSをネットワーク優先・キャッシュフォールバックで扱う。**`house.json`を変更してPagesに反映した後は、`sw.js`の`CACHE`定数（バージョン文字列）を更新すること。** 更新しないと、既にホーム画面に追加したユーザーの端末に古いキャッシュが残り続ける場合がある
- `file://`で直接開いたときはService Workerを登録しない（`location.protocol.startsWith("http")`でガード）

### iPhoneのノッチ・ホームインジケーターとUIの重なり対策（`--safe-t`等）

`display:"standalone"`（PWA）＋`<meta name="viewport" content="...,viewport-fit=cover">`の組み合わせでは、Webページの描画領域がノッチ／Dynamic Island／ホームインジケーターの下（＝ステータスバーの裏）まで拡張される。そのため、`top:12px`のような固定オフセットだけで配置した要素は、実際にはステータスバーの背後に隠れて押せなくなる（2026-08-16、施主指摘：「メニューの表示が画面の上部に全て寄っていることで...メニュー全般が押せないようになっています」）。

- `:root`に`--safe-t`/`--safe-r`/`--safe-b`/`--safe-l`という4つのCSS変数を定義し、それぞれ`env(safe-area-inset-top, 0px)`等を参照する。`viewport-fit=cover`のない環境（Android・PC等）やCSS環境変数非対応ブラウザでは自動的に`0px`にフォールバックするため、常にこれらの変数を使っておけば安全（Chromiumでの開発・検証時は常に`0px`になり実機のノッチ値は再現できないため、実際の見え方は最終的に実機のiPhoneで確認する必要がある）
- 画面の四隅・上下端に固定配置されているUI（`#topBar`・`#ui`・`#walkHud`・`#minimap`・`#tip`・`#moveHint`・`#joyBase`・家具/窓ドア編集パネル・`#spawnOverlay`）はすべて、素の`12px`のようなオフセットを`calc(var(--safe-t) + 12px)`のような形に置き換えてある
- あわせて、スマホ幅（`@media (max-width:640px)`）で見つかった2つの別の不具合も修正した。(1) 内覧モードのHUD（部屋名＋ボタン3つ）が1行に収まらず、部屋名のテキストが1文字ずつ縦に折り返っていた（`white-space:nowrap`を追加し、`flex-wrap:wrap`で折り返しを許可）。(2) 平面図モードの`#topBar`（`justify-content:space-between`で折り返さない設定）に「窓・ドア編集」ボタンまで並ぶと画面幅に収まらず、はみ出した分がページスクロール無効（`overflow:hidden`）のため物理的に押せなくなっていた（`flex-wrap:wrap`に変更し、はみ出す場合は2行目に折り返すようにした）
- `#minimap`は、スマホでは`#walkHud`と同じ右上に置くと折り返した`#walkHud`と重なってしまうため、`@media`内で右下（バーチャルジョイスティックの反対側の空きスペース）へ移すオーバーライドを追加した

## 移行状況

- HTML側の生成データ読み込みへの切り替え：完了（2026-08-14）
- `web/` ディレクトリへの本格的なビューア分離（Three.jsコードと表示ロジックを `data/house.json` から完全に切り離す）：未着手。当面は `interior-white-model.html` 内のThree.jsロジックをそのまま維持する
- rooms→walls変換の自動化：完了（2026-08-16。`scripts/build-web-data.mjs`が`rooms`から機械的に導出し、`data/house.json`の手動保守`walls`配列は廃止した）
