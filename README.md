# Ryuka Interior Designer

自宅新築プロジェクトの内装デジタルツイン。施工会社の実施図面と参考資料（マイホームクラウド間取り図）の突き合わせ検証を通じて構築した建物データを、Three.jsの白模型とBlenderの再生成パイプラインの両方から利用できるようにしている。

進捗・未解決事項は [docs/STATUS.md](docs/STATUS.md)、プロジェクトの目的・経緯は [docs/BACKGROUND.md](docs/BACKGROUND.md)、データ契約・変更手順は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照。エージェント向けの作業ルールは [AGENTS.md](AGENTS.md)。

## ファイル構成

- `interior-white-model.html` — Three.js製の内装白模型。単体でブラウザに開ける。`generated/house-data.js` を読み込んで表示する
- `index.html` — GitHub PagesのルートURL用リダイレクト（`interior-white-model.html`へ転送するだけ）
- `manifest.webmanifest` / `sw.js` / `icon.svg` — PWA化（ホーム画面に追加・オフライン起動）用の設定一式
- `vendor/three.min.js` — Three.js本体のローカル同梱コピー（オフラインでも動くように、CDN参照ではなくここから読み込む）
- `data/house.json` — 建物データの正本。寸法・部屋・壁・屋根
- `data/house.schema.json` — `house.json`のデータ契約（JSON Schema）
- `data/furniture-catalog.json` — 家具・設備の「型」ライブラリ（種類ごとの標準寸法・形状指定）
- `data/furniture.json` — 家具・設備の配置（どこに何を置くか）。正本
- `data/furniture.schema.json` — `furniture.json`のデータ契約（JSON Schema）
- `data/door-catalog.json` / `data/window-catalog.json` — 窓・ドアの「型」ライブラリ（種類ごとの標準寸法・開閉方式）
- `data/openings.json` — 外部の窓・ドアの配置。正本
- `data/interior-doors.json` — 室内ドアの配置。正本
- `data/electrical-catalog.json` — 電気設備（コンセント・スイッチ・照明・情報系配線）の「型」ライブラリ
- `data/electrical.json` — 電気設備の配置（どこに何を置くか）。正本。見積書に基づく154箇所の完全配置（たたき台、屋外設備含む）＋Web UIでの削除・追加編集
- `data/electrical.schema.json` — `electrical.json`のデータ契約（JSON Schema）
- `data/electrical-estimate.json` — 電気工事の見積書の明細（数量）。正本。Web UI編集後の現在数と明細単位で比較するために使う
- `generated/house-data.js` — 上記JSON群から自動生成されるHTML表示用データ（手で編集しない）
- `generated/exterior-walls.json` — `house.json`のfootprintsから自動導出した外壁データ（手で編集しない）。屋外電気設備の配置検証に使う
- `scripts/build-web-data.mjs` — 上記JSON群 → `generated/house-data.js` の生成スクリプト
- `scripts/seed-electrical.mjs` — 電気設備154箇所を部屋別配分から機械的に配置する一回限りの生成ツール
- `blender/build_house.py` — `house.json`・`door-catalog.json`・`window-catalog.json`・`openings.json`・`interior-doors.json`からBlender白模型を再生成するスクリプト（家具・電気設備は対象外。HTML側だけで扱う方針）
- `tests/validate_house.py` — `house.json`の整合性チェック（依存ライブラリなしで動作）
- `tests/validate_furniture.py` — 家具データの整合性チェック
- `tests/validate_openings.py` — 窓・ドアデータの整合性チェック
- `tests/validate_electrical.py` — 電気設備データの整合性チェック

## 使い方

### Webアプリとして開く

**https://kenryuuuuuuuuuu.github.io/Ryuka-Interior-Designer/**

GitHub Pagesで公開している。スマホのブラウザで開き、共有ボタン→「ホーム画面に追加」（iPhone/Safari）または「アプリをインストール」（Android/Chrome）を選ぶと、アイコンをタップするだけでアプリのように開けるようになる（オフラインでも起動する）。

### ローカルで開く

`interior-white-model.html` をブラウザで直接開く。ビルド不要、外部依存はローカル同梱の Three.js（r128、`vendor/three.min.js`）のみ。

- 左上「☰」：メニューの表示/非表示
- 上部中央のモード切替：「俯瞰」（自由回転）／「平面図」（真上からの正射投影、寸法比較用）／「内覧」（一人称視点で歩ける。玄関を選ぶとその場所からスタートし、壁に当たり判定がある。デスクトップはWASD/矢印キー移動＋ドラッグで視点操作、スマホはバーチャルジョイスティック＋ドラッグ）
- メニュー内チェックボックス：レイヤーごとの表示切替（室内間仕切り・家具設備・電気設備・窓ドア・防音壁・屋根・室内ドア位置・寸法値・部屋ラベル・家具ラベル・電気設備ラベル・910mmグリッド）。部屋ラベル・家具ラベル・電気設備ラベルは別々にON/OFFできる。内覧モード中は概算レイヤーの代わりに実壁・天井を表示するが、家具・電気設備は内覧モード中も表示される（電気設備には当たり判定はない）
- メニュー内「部屋フォーカス」：俯瞰モード限定。部屋を選ぶと、その部屋だけを表示し他室の壁・家具・電気設備・ドア窓・防音壁・腰壁を隠してカメラを寄せる。電気設備のように平面図では小さすぎて確認しづらいものも、部屋単位で見やすく確認できる。フォーカス中は右上（電気設備編集ボタンの下）にその部屋の電気設備一覧パネルが表示され、行をクリックするとその設備を選択できるほか、「＋ この部屋に設備を追加」から新しい設備を追加できる
- メニュー内「電気設備一覧」→「一覧を表示」：見積書の明細ごとの現在数/見積数（差があれば強調表示）と、1F/2F全部屋（設置なしの部屋も含む）ごとの内訳を一覧表示する。行をクリックするとその設備の部屋へフォーカスし、編集パネルを開く。削除した設備は末尾の「削除した設備」欄からいつでも個別に復元できる
- 平面図モードで右上「✎ 家具編集」：家具をクリック/タップで選択し、ドラッグで移動。選択中に表示されるパネルから90度回転・幅/奥行/高さの変更ができる。編集内容はブラウザに自動保存されるが、それは下書き。「furniture.jsonを書き出す」でダウンロードしたJSONを`data/furniture.json`に上書きしてコミットするまでは正本に反映されない
- 平面図モードで右上「✎ 窓・ドア編集」：窓・ドアをクリック/タップで選択し、壁に沿ってドラッグでスライド（家具と違い、壁の外へは動かせない）。選択中に表示されるパネルから種類切替・幅/高さ/シル高の変更・開き勝手の変更ができる。「openings.json」「interior-doors.json」の書き出しボタンでダウンロードしたJSONをそれぞれ`data/openings.json`・`data/interior-doors.json`に上書きしてコミットするまでは正本に反映されない。家具編集とは同時にONにできない
- 俯瞰モードで右上「✎ 電気設備編集」：電気設備をクリック/タップで選択し、壁付け設備（コンセント・スイッチ等）は壁に沿ってドラッグでスライド、天井/床付け設備（照明等）は家具と同じ自由なドラッグで移動（屋外設備は選択のみ）。選択中に表示されるパネルから種類切替・幅/奥行/高さの変更・向きの反転・X/Y/Zの数値入力による微調整（壁付け設備は壁に沿う側の座標だけ編集でき、壁面側は固定・編集不可）ができるほか、「🗑 この設備を削除」で削除できる（削除は取り消せる下書きで、一覧モーダルから復元可能）。壁付け設備は「設置している壁」セレクトから別の壁面へ丸ごと移動でき、選択中の壁は3D上で黄色くハイライトされる。新規追加は部屋フォーカス中の右上パネルの「＋ この部屋に設備を追加」から行い、壁付け設備はその部屋に接する壁面を選んでから追加する（追加後にどの座標がロックされているか分かるように、先に壁面を決める設計）。「electrical.jsonを書き出す」でダウンロードしたJSONを`data/electrical.json`に上書きしてコミットするまでは正本に反映されない。平面図では電気設備が小さく視認・選択しづらいため俯瞰モード専用にしている。家具編集・窓ドア編集とは同時にONにできない
- 俯瞰モードの右上に方位コンパスを表示（N/E/S/Wがカメラの向きに合わせて回転する）

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
