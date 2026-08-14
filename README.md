# Ryuka Interior Designer

自宅新築プロジェクトの内装デジタルツイン。施工会社の実施図面と参考資料（マイホームクラウド間取り図）の突き合わせ検証を通じて構築した建物データを、Three.jsの白模型とBlenderの再生成パイプラインの両方から利用できるようにしている。

進捗・未解決事項は [docs/STATUS.md](docs/STATUS.md)、プロジェクトの目的・経緯は [docs/BACKGROUND.md](docs/BACKGROUND.md)、データ契約・変更手順は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照。エージェント向けの作業ルールは [AGENTS.md](AGENTS.md)。

## ファイル構成

- `interior-white-model.html` — Three.js製の内装白模型。単体でブラウザに開ける。`generated/house-data.js` を読み込んで表示する
- `index.html` — GitHub PagesのルートURL用リダイレクト（`interior-white-model.html`へ転送するだけ）
- `manifest.webmanifest` / `sw.js` / `icon.svg` — PWA化（ホーム画面に追加・オフライン起動）用の設定一式
- `vendor/three.min.js` — Three.js本体のローカル同梱コピー（オフラインでも動くように、CDN参照ではなくここから読み込む）
- `data/house.json` — 建物データの正本。寸法・開口部・室内ドア・部屋・壁・屋根
- `data/house.schema.json` — `house.json`のデータ契約（JSON Schema）
- `data/electrical.json` / `data/furniture.json` — 次フェーズ（電気設備・家具配置）用の領域。現在は空
- `generated/house-data.js` — `house.json`から自動生成されるHTML表示用データ（手で編集しない）
- `scripts/build-web-data.mjs` — `house.json` → `generated/house-data.js` の生成スクリプト
- `blender/build_house.py` — `house.json`からBlender白模型を再生成するスクリプト
- `tests/validate_house.py` — `house.json`の整合性チェック（依存ライブラリなしで動作）

## 使い方

### Webアプリとして開く

**https://kenryuuuuuuuuuu.github.io/Ryuka-Interior-Designer/**

GitHub Pagesで公開している。スマホのブラウザで開き、共有ボタン→「ホーム画面に追加」（iPhone/Safari）または「アプリをインストール」（Android/Chrome）を選ぶと、アイコンをタップするだけでアプリのように開けるようになる（オフラインでも起動する）。

### ローカルで開く

`interior-white-model.html` をブラウザで直接開く。ビルド不要、外部依存はローカル同梱の Three.js（r128、`vendor/three.min.js`）のみ。

- 左上「☰」：メニューの表示/非表示
- 上部中央のモード切替：「俯瞰」（自由回転）／「平面図」（真上からの正射投影、寸法比較用）／「内覧」（一人称視点で歩ける。玄関を選ぶとその場所からスタートし、壁に当たり判定がある。デスクトップはWASD/矢印キー移動＋ドラッグで視点操作、スマホはバーチャルジョイスティック＋ドラッグ）
- メニュー内チェックボックス：レイヤーごとの表示切替（室内間仕切り・窓ドア・防音壁・屋根・室内ドア位置・寸法値・部屋ラベル・910mmグリッド）。内覧モード中はこれらの代わりに実壁・天井を表示する

### 建物の寸法を変更する

`data/house.json` を編集し、`python tests/validate_house.py` → `node scripts/build-web-data.mjs` → ブラウザで確認、の順で進める。詳しい手順とID運用のルールは [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照。

## データの確度について

各部屋・開口部・壁には`status`（またはThree.js側では`conf`）が付与されている。

| 表記 | 意味 |
|---|---|
| verified（●高） | 実施図面または複数資料の相互検算で確定 |
| derived（◐中） | 1辺確定＋面積からの逆算など、部分的な根拠あり／他データから機械的に導出 |
| estimated（○低） | 目視のみ、または未検証 |

「estimated」が残っている箇所は、より詳細な参考資料が入手でき次第、精緻化する。
