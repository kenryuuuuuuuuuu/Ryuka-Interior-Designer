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
| `tests/validate_openings.py` | `door-catalog.json` / `window-catalog.json` / `openings.json` / `interior-doors.json` の整合性チェック（house.jsonのfootprints/wallsとの照合含む） |
| `index.html` | GitHub PagesのルートURL用リダイレクト。`interior-white-model.html`へ転送するだけ |
| `manifest.webmanifest` / `sw.js` / `icon.svg` | PWA化（ホーム画面追加・オフライン起動）の設定一式。詳細は下記「公開（GitHub Pages / PWA）」 |
| `vendor/three.min.js` | Three.js本体のローカル同梱コピー（CDN非依存。オフライン起動のため） |

## rooms / walls について

`rooms`（部屋の輪郭ポリゴン）は間取りの一次情報。`walls`（重複を除いた壁芯データ、Blenderのみが使用）は `rooms` から人手＋半自動で重複統合・外壁除外して作られた二次情報で、`rooms` を編集しても自動追従しない。`rooms` を編集した場合は、影響する `walls` エントリ（`sourceRooms` に対象の部屋ラベルを含むもの）を手動で見直すこと。将来的にはこの変換も自動化したい（[STATUS.md](STATUS.md) の未解決事項を参照）。

Three.js側（`ROOMS_APPROX` 相当）は `rooms` を直接使い、`walls` は使わない。`walls` はBlenderの `build_house.py` だけが使う。

`rooms`の`polygon`は矩形・L字（軸に沿った頂点のみ）が基本だが、斜め框のような斜めの境界線を持つ部屋も表現できる（`polyWire()`はThree.js側で任意の多角形を描画できるため）。ただし`rooms`→`walls`変換（Blender用）は軸に沿った壁しか扱えないため、斜めの境界を持つ部屋を追加した場合は`walls`側の対応する更新ができない（Blenderは現状未使用のため実害は小さいが、[STATUS.md](STATUS.md)に記録しておくこと）。

**間取りの精細化（部屋の分割）の進め方**：家具・窓ドアのような「既存の枠内で位置を調整する」編集とは異なり、部屋を分割する作業（例：1つの部屋を2部屋に割る、部屋の中に収納区画を切り出す）はトポロジーそのものを変える。編集モードは作らず、施主からスクリーンショット＋書き込み線などで指示を受け、`rooms`を直接編集する方式にしている（検討の経緯は[BACKGROUND.md](BACKGROUND.md)参照）。

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
  - ドアの`operation`：`swing`=開き戸／`slide`=引き戸／`open`=ドアなしの開口／`open-arch`=ドアなしの開口（天端アーチ）。窓は`openable`=開閉可／`fixed`=FIX
  - `open-arch`のみ`archRise`（円弧が占める高さ）を追加で持つ。`height`はアーチ頂部までの全高で、springline（円弧が始まる高さ）は`height-archRise`
- `data/openings.json`：外部（外壁）の窓・ドアの配置インスタンス。`type`でカタログを参照し、`face`（N/S/E/W）＋`offset`（その面に沿った建物ローカル座標の絶対値。**中心ではなく開始端（西端/北端）**）で位置を表す。E/W面は`wallX`を省略すると建物端（x=0またはx=19.11）とみなす
- `data/interior-doors.json`：室内ドアの配置インスタンス。`type`でカタログを参照し、`wallAt`（壁の固定座標）＋`orientation`（H/V）＋`center`（壁沿いの位置、こちらは中心）で位置を表す
  - **`orientation:'D'`（斜め壁）**：`wallAt`/`center`の代わりに`x0`/`z0`/`x1`/`z1`（始点・終点、建物ローカル座標）で位置を表す。壁のない開口（`operation:open`/`open-arch`）専用の想定で、開き戸・引き戸（`hingeSide`/`swingDir`/`slideDir`）や壁線スライド編集（Stage 2 UI）の対象外。`interior-white-model.html`の`placeDiagonalInteriorDoor()`が、始点・終点を結ぶ厚みのない平板で描画する
- どちらも任意で`widthOverride`/`heightOverride`/`sillOverride`（このインスタンスだけ標準寸法から変える場合）を持つ
- **ドアの開き勝手**：`operation:swing`の型を使うインスタンスは`hingeSide`（`L`/`R`、蝶番側）＋`swingDir`（`in`/`out`）、`operation:slide`なら`slideDir`（`L`/`R`、引き込み方向）を持つ。`operation:open`/`open-arch`（ドアなしの開口）はどちらも不要（扉本体を描かない）。外部の窓・ドア（`openings.json`）は`face`（N/S/E/W）から「外側」の方向が一意に決まるため、`swingDir:'out'`は文字通り建物の外側へ開く向きになる。室内ドア（`interior-doors.json`）には「外」の概念がないため、`swingDir`は「壁を挟んでどちら向きに開くか」を軸ベースで簡易表現したものにとどまる。隣接する部屋同士の内外関係までは今のデータモデルにはない（見た目を見ながら調整する運用）
- **開口（アーチ）の描画**：`interior-white-model.html`の`archOpeningMesh()`が、天端が円弧になった平板（厚みのない板、door系マテリアルは両面表示なので厚みなしでも見える）を描く。平面図（真上から）ではアーチかどうかは見た目に出ないため、俯瞰・内覧モードで確認すること
  - 現在の室内ドア19件はすべて開き戸として移行しており、`hingeSide`/`swingDir`は施工会社の建具表が未確認のため暫定値（[STATUS.md](STATUS.md)の未解決事項を参照）
- `house.json`から2026-08-15に分離した（元は`openings`/`interiorDoors`という配列としてhouse.json内にあった）。理由は、家具編集の「書き出しボタンでファイルを上書き」という運用を安全に行うため。house.jsonに残したままだと、書き出しは`rooms`/`walls`/`roofs`等を含むファイル全体が対象になり、ブラウザ側が保持していない付帯情報を巻き込んで構造データを壊すリスクがある
- **Web UI上での配置編集（第2段階、`interior-white-model.html`内に実装）**：平面図モードで「✎ 窓・ドア編集」ボタンをONにすると、窓・ドアのクリック/タップ選択→壁に沿ったドラッグでスライドができる。家具編集とは仕組みが異なる点が2つある
  - **自由な2D移動ではなく、壁線上の1次元スライドに制約される。** 室内ドアは`WALLS`（重複統合済みの壁芯データ）、外部の窓・ドアは`footprints`（求積図のゾーン区分）から対応する壁の区間を求め、その範囲内にクランプする（`wallRangeForInteriorDoor()`/`wallRangeForOpening()`。ロジックは`tests/validate_openings.py`の壁突合せチェックと同じ考え方）。「別の壁・別の面へ移動」はドラッグでは扱わない
  - **家具編集と同時にはONにできない（排他）。** `setDoorEditMode(true)`は`setEditMode(false)`を呼び、逆も同様
  - パネルからは種類（`type`）の切替、幅/高さ/シル高の変更、開き勝手（開き戸は蝶番側+開く向き、引き戸は引き込み方向）の変更ができる。種類を切り替えると寸法は新しい型の標準値にリセットされ、`operation`が変われば開き勝手の項目も対応するものに切り替わる（例：開き戸→引き戸で`hingeSide`/`swingDir`は無視され`slideDir`が使われる）
  - 編集内容は`OPENINGS`/`INTERIOR_DOORS`（生成データ、正本ではない）を直接書き換えず、`doorWindowEdits`という差分オブジェクトとして持ち、`effectiveOpening()`/`effectiveInteriorDoor()`で重ねて描画する。ブラウザの`localStorage`（キー`ryuka-door-window-edits-v1`）に自動保存される、あくまで作業中の下書きという位置づけは家具編集と同じ
  - 「openings.json」「interior-doors.json」の2つの書き出しボタンで、それぞれ編集を反映した完全なJSONをダウンロードできる。データが2ファイルに分かれているため、家具のような単一の書き出しボタンにはしていない。**これらを`data/openings.json`・`data/interior-doors.json`に上書きしてコミットするのが、正本を更新する唯一の手段**

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

要素を追加・削除する場合は、その配列（`footprints` / `rooms` / `walls` など）の中で一意なIDを新規発番し、`status` を適切に設定すること。`walls` は上記「rooms / walls について」の注意を確認する。窓・ドアは`house.json`ではなく`data/openings.json`/`data/interior-doors.json`側で管理する（下記「窓・ドアの種類を追加する、または直接JSONを編集する」参照）。

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

## 移行状況

- HTML側の生成データ読み込みへの切り替え：完了（2026-08-14）
- `web/` ディレクトリへの本格的なビューア分離（Three.jsコードと表示ロジックを `data/house.json` から完全に切り離す）：未着手。当面は `interior-white-model.html` 内のThree.jsロジックをそのまま維持する
- rooms→walls変換の自動化：未着手
