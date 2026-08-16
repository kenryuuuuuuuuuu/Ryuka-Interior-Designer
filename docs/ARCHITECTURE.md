# アーキテクチャ・データ契約

このリポジトリの「正本はどこか」「どう変更するか」を定義する。技術的な仕組みの解説。プロジェクトの背景・経緯は [BACKGROUND.md](BACKGROUND.md)、現在の進捗・未解決事項は [STATUS.md](STATUS.md) を参照。

## 正本と生成パイプライン

**`data/house.json` がこのリポジトリの唯一の正本（Single Source of Truth）。** 建物の寸法・部屋・壁・屋根はすべてここで管理し、Three.js表示用データとBlenderモデルの両方をここから生成する。**家具・設備の配置は`data/furniture.json`（型のライブラリは`data/furniture-catalog.json`）が正本で、こちらはHTML側（Three.js）でのみ扱い、Blenderへは今のところ生成しない**（施主の判断：配置の試行錯誤はインタラクティブ性が命なのでHTML側で詰める。詳細は[BACKGROUND.md](BACKGROUND.md)の変更履歴ログ参照）。**窓・ドアの配置は`data/openings.json`（外部）・`data/interior-doors.json`（室内、型のライブラリはドアが`data/door-catalog.json`・窓が`data/window-catalog.json`）が正本で、こちらはThree.js・Blenderの両方が読み込む**（外壁・室内壁の開口の切り欠きに使うため）。窓・ドアは2026-08-15に`house.json`から分離した（元は`openings`/`interiorDoors`という配列としてhouse.json内にあった）。`blender/build_house.py`は`data/house.json`と同じディレクトリにある`door-catalog.json`/`window-catalog.json`/`openings.json`/`interior-doors.json`を自動的に読み込む

```
data/house.json（建物データの正本）
data/furniture-catalog.json（家具・設備の型ライブラリ）
data/furniture.json（家具・設備の配置インスタンス）
data/door-catalog.json（ドアの型ライブラリ）
data/window-catalog.json（窓の型ライブラリ）
data/openings.json（外部の窓・ドアの配置インスタンス）
data/interior-doors.json（室内ドアの配置インスタンス）
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
| `data/electrical.json` | 次フェーズ（電気設備）用の領域。現在は空 |
| `scripts/build-web-data.mjs` | 上記の正本ファイル群 → `generated/house-data.js` を生成する |
| `generated/house-data.js` | 生成物。`interior-white-model.html` が `<script src>` で読み込む |
| `interior-white-model.html` | Three.js製の内装白模型。表示・操作ロジックのみを持つ。単体でブラウザに開ける |
| `blender/build_house.py` | `house.json`・`door-catalog.json`・`window-catalog.json`・`openings.json`・`interior-doors.json`からBlender白模型を再生成するスクリプト（家具は対象外） |
| `tests/validate_house.py` | `house.json` の整合性チェック（依存ライブラリなしで動作） |
| `tests/validate_furniture.py` | `furniture-catalog.json` / `furniture.json` の整合性チェック（house.jsonのroomsとの照合含む） |
| `tests/validate_openings.py` | `door-catalog.json` / `window-catalog.json` / `openings.json` / `interior-doors.json` の整合性チェック（house.jsonのfootprints、および`generated/interior-walls.json`との照合含む。実行前に`node scripts/build-web-data.mjs`が必要） |
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
