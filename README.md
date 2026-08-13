# Ryuka Interior Designer

自宅新築プロジェクトの内装デジタルツイン。施工会社の実施図面と参考資料（マイホームクラウド間取り図）の突き合わせ検証を通じて構築した建物データを、Three.jsの白模型とBlenderの再生成パイプラインの両方から利用できるようにしている。

## 現状のステータス（2026-08-13時点）

- 1F：民泊棟・自宅（ヌック〜LDK）・A4水回りまで、全区画が確度「高」
- 2F：全区画が確度「高」
- 室内ドア：19箇所配置済み。全てが対応する壁エンティティの範囲内に収まることを機械検証済み
- 窓・外部ドア：施工会社図面ベースの確定データ＋セッション中に調整した箇所あり
- 室内壁（`data/house.json`の`rooms`/`walls`）：Phase 1bで部屋データから抽出済み。24室・23本の壁
- 天井高：全室2,400mm（**推測値、施工会社への確認が必要**）
- ドア高さ：Blender生成時2.0mを暫定使用（**建具表の実データ未反映**）
- 家具配置：未着手（次のステップ）

## アーキテクチャ

このリポジトリは移行期にある。**建物の寸法データは最終的に`data/house.json`だけで管理し、そこからThree.js表示用データとBlenderモデルの両方を生成する**構成を目指している。ただし現時点では、`interior-white-model.html`が実際に編集されている一次資料であり、`house.json`はそこから同期される形を取っている。

```
現在：  interior-white-model.html （実際の編集はここで行う）
              ↓ node scripts/sync-house-from-html.mjs
        data/house.json （levels/footprints/openings/interiorDoors/specialWalls）
              ↓ blender/build_house.py
        Blenderモデル

将来：  data/house.json （唯一の編集対象）
              ├─ generate → Web表示用データ
              └─ blender/build_house.py → Blenderモデル
```

### rooms / walls は例外（一度きりの変換）

`data/house.json`の`rooms`（部屋の輪郭）と`walls`（重複を除いた壁芯データ）は、`interior-white-model.html`内の`ROOMS_APPROX`から**一度だけ**変換して作成したものであり、`sync-house-from-html.mjs`による自動同期の対象外。ROOMS_APPROXを今後編集した場合、`sync-house-from-html.mjs --check`はハッシュ差分を検知して警告するが、rooms/walls自体の再生成はまだ自動化していない。警告が出たら、部屋の輪郭を壁芯データへ変換するスクリプト（重複統合・外壁除外のロジックを含む）を再実行し、`provenance.roomsSourceHash`を更新する必要がある。

## ファイル構成

- `interior-white-model.html` — Three.js製の内装白模型。単体でブラウザに開ける
- `data/house.json` — 建物データの正本。寸法・開口部・室内ドア・部屋・壁・屋根
- `data/house.schema.json` — `house.json`のデータ契約（JSON Schema）
- `data/electrical.json` / `data/furniture.json` — 次フェーズ（電気設備・家具配置）用の領域。現在は空
- `blender/build_house.py` — `house.json`からBlender白模型を再生成するスクリプト
- `scripts/sync-house-from-html.mjs` — HTML→house.json の一方向同期・差分検知ツール
- `tests/validate_house.py` — `house.json`の整合性チェック（依存ライブラリなしで動作）
- `docs/PHASE-1.md` — Phase 1（再現可能なジオメトリ基盤）の実装仕様
- `docs/WORKFLOW.md` — 運用手順の詳細
- `AGENTS.md` — このリポジトリで作業する際のルール（人間・AIエージェント共通）

## 使い方

### Three.jsビューアを見る

`interior-white-model.html` をブラウザで直接開く。ビルド不要、外部依存はCDN経由のThree.js（r128）のみ。

- 左上「☰」：メニューの表示/非表示
- 右上「▦ 平面図モード」：真上からの正射投影ビュー（寸法比較用）
- メニュー内チェックボックス：レイヤーごとの表示切替（外皮・室内間仕切り・窓ドア・防音壁・屋根・室内ドア位置・寸法値・部屋ラベル・910mmグリッド）

### 建物の寸法を変更する

現在の正式な運用手順:

1. `interior-white-model.html` を調整し、ブラウザで確認する
2. `node scripts/sync-house-from-html.mjs --check` で差分を確認する（rooms/walls由来の警告が出ないかも確認）
3. 意図した変更なら `node scripts/sync-house-from-html.mjs --write` で `house.json` へ同期する
4. `python tests/validate_house.py` でデータを検査する
5. `blender --background --python blender/build_house.py -- --input data/house.json --output build/ryuka-white-model.blend` でBlenderモデルを再生成する

カメラ・色・メニューなどHTML表示だけの変更はBlenderへ反映する必要がない。壁・床・階高・窓・ドア・部屋の輪郭など建物データの変更だけを同期する。追加・削除でID管理が必要になる変更は同期ツールが停止するため、`house.json`側でIDと`status`を確認してから反映する。

## データの確度について

各部屋・開口部・壁には`status`（またはThree.js側では`conf`）が付与されている。

| 表記 | 意味 |
|---|---|
| verified（●高） | 実施図面または複数資料の相互検算で確定 |
| derived（◐中） | 1辺確定＋面積からの逆算など、部分的な根拠あり／他データから機械的に導出 |
| estimated（○低） | 目視のみ、または未検証 |

「estimated」が残っている箇所は、より詳細な参考資料が入手でき次第、精緻化する。

## 既知の制約

- 天井高は施工会社の断面図が存在しないため推測値（2,400mm）
- 室内ドアの高さはBlender生成時2.0mの暫定値。建具表の実データ未反映
- 一部の低確度区画は内部の細分が未解決
- CAD原本（DXF等）があれば、この白模型全体の精度を大きく上げられる
- `rooms`/`walls`は一度きりの変換であり、HTML編集との自動同期はまだない（上記「アーキテクチャ」参照）

## 今後の予定

1. 家具の箱配置（実寸ボックスでの動線・干渉チェック）
2. コンセント・スイッチ・照明位置の検討
3. 施工会社への確認事項の反映（天井高・建具表など）
4. rooms/walls の自動同期化（sync-house-from-html.mjs の拡張）
5. （検討中）Blenderへの移行によるマテリアル・質感の作り込み
