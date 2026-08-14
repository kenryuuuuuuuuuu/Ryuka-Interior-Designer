# リポジトリ作業ガイド

**最初に読むこと：** 作業開始前に必ず [docs/BACKGROUND.md](docs/BACKGROUND.md) を読むこと。CAD原本がなく、壁位置を撮影した間取り画像のピクセル解析で再構築した経緯、既に一度発見・修正したThree.js/データパイプラインの不具合、施主に確認待ちの未解決事項がまとめてある。読み飛ばすと、既に出した結論を再導出したり、一度直したバグを再発させたりするリスクがある。

このリポジトリは、ブラウザで動くThree.js製の建築白模型と、そこから再生成可能なBlenderデジタルツインパイプラインを持つ。

## ドキュメント地図

| ファイル | 内容 |
|---|---|
| [docs/BACKGROUND.md](docs/BACKGROUND.md) | プロジェクトの目的、データの作り方、過去の教訓（**最初に読む**） |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 正本・データ契約・座標系・変更手順（技術仕様） |
| [docs/STATUS.md](docs/STATUS.md) | 現在の進捗、未解決事項、次のステップ |
| [README.md](README.md) | 人間向けの概要・ビューアの使い方 |

## 正本（Source of truth）

- `data/house.json` がこのリポジトリの唯一の正本。建物の寸法・開口部・部屋・壁はここだけを編集する
- `interior-white-model.html` は表示・操作ロジックのみを持ち、建物データを直接埋め込まない。`generated/house-data.js`（`house.json`から自動生成）を`<script src>`で読み込む
- 詳細な変更手順とデータ契約は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照

## 変更ルール

- `data/house.json` を編集したら、`python tests/validate_house.py` で検証し、`node scripts/build-web-data.mjs` で `generated/house-data.js` を再生成すること。手順の詳細は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- `generated/house-data.js` は自動生成物。手で編集しない
- データを移動・変換する際は、根拠・確度・検証メモ（`note`フィールド）を必ず引き継ぐ。観測値を推測値で無断置換せず、`estimated`と明示し理由を記録する
- Blenderが利用可能な環境では、寸法に影響する変更のあとに `blender/build_house.py` を実行して `.blend` を再生成する。生成された `.blend` やレンダー画像は成果物であり、承認済みの参照アーティファクトとして明示的に依頼された場合を除きコミットしない
- コミット前に `data/house.json` を検証する
- コミュニケーションは「ですます調」。個人名は使わず「施主」、施工会社名も「施工会社」と汎用化する。このリポジトリはGitHub無料枠のためPublicなので、個人情報を含めないこと。個人情報を含む資料（施工会社図面PDFなど）は `.gitignore` で除外し、ローカル参照のみに留める
