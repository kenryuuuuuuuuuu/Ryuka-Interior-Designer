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

- `data/house.json` が建物の寸法・部屋・屋根の正本。壁は部屋から導出する。開口は `data/openings.json` / `data/interior-doors.json`、家具は `data/furniture.json`、電気設備は `data/electrical.json` と各カタログが正本。生成物へ直接書き込まず、詳細はARCHITECTURE.mdを参照
- `interior-white-model.html` は表示・操作ロジックのみを持ち、建物データを直接埋め込まない。`generated/house-data.js`（`house.json`から自動生成）を`<script src>`で読み込む
- 詳細な変更手順とデータ契約は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照

## ブランチを切るか、mainに直接コミットするか

**指示された作業に着手する前に、毎回この判断をすること。** 施主から都度「ブランチを切って」と言われるのを待たない。

判断基準は「その機能が完成しているか」ではなく、**壊れたときの影響範囲（ブラストレディウス）と、既存の検証スクリプトで安全性を機械的に保証できるか**。

| 変更の種類 | 具体例 | 判断 |
|---|---|---|
| 仕組み・挙動の変更 | 新しい編集UI、当たり判定、新しい描画方式、データ構造そのものの変更、既存機能への大きな手入れ | ブランチを切ってPR相当の単位で作業する。試行錯誤が多く、既存の表示・動作を壊すリスクがあるため |
| 既存の仕組みに乗ったデータの追加・調整 | 家具の新しい種類を1つ追加、部屋の壁位置を1つ調整、家具の配置を動かす、注記(note)の追記 | `python tests/validate_house.py` / `python tests/validate_furniture.py` / `node scripts/build-web-data.mjs --check` が通ることで安全性が機械的に保証できるので、**mainに直接コミットしてよい** |

判断に迷う場合（新しい種類のデータで検証スクリプトのカバー範囲外になる、複数の変更が絡み合っている等）は、作業前に施主に一言確認する。

過去の実例：house.jsonの構造変更・内覧モード追加・PWA化などの大きな仕組みの変更はすべてmainに直接コミットしてきたが、これは各回が単発の完結した作業だったため。家具配置機能で最初にブランチを切ったのは「家具データが多いから」ではなく「編集の仕組み自体を試行錯誤しながら作る、規模の大きい作業だったから」。

## 変更ルール

- `data/house.json` を編集したら、`python tests/validate_house.py` で検証し、`node scripts/build-web-data.mjs` で `generated/house-data.js` を再生成すること。手順の詳細は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- `generated/house-data.js` は自動生成物。手で編集しない
- データを移動・変換する際は、根拠・確度・検証メモ（`note`フィールド）を必ず引き継ぐ。観測値を推測値で無断置換せず、`estimated`と明示し理由を記録する
- Blenderが利用可能な環境では、寸法に影響する変更のあとに `blender/build_house.py` を実行して `.blend` を再生成する。生成された `.blend` やレンダー画像は成果物であり、承認済みの参照アーティファクトとして明示的に依頼された場合を除きコミットしない
- コミット前に `data/house.json` を検証する
- コミュニケーションは「ですます調」。個人名は使わず「施主」、施工会社名も「施工会社」と汎用化する。このリポジトリはGitHub無料枠のためPublicなので、個人情報を含めないこと。個人情報を含む資料（施工会社図面PDFなど）は `.gitignore` で除外し、ローカル参照のみに留める

## 設計・実装の分担（2026-09-08）

現在の施主指定は、GPTが仕様設計・レビュー、Claude Codeが実装・実行検証です。[開発手順](docs/DEVELOPMENT_WORKFLOW.md) と [残りの計画](docs/IMPLEMENTATION_ROADMAP.md) を使用します。実装指示・結果・レビュー対象コミットを文書に残します。

施主の最新指定：完成速度を優先し、検証は一般的な正常系と簡単な異常系を基本とします。過剰な障害注入・全分岐確認・レビューの追加往復は求めません。過去の厳格な検証要求より、この方針を優先します。詳細は開発手順の「施主指定：完成を優先するレビュー基準」を参照してください。

## 日常利用への統合（2026-09-11）

トップのmainが日常版です。入口と保存先はdocs/DAILY_USE.md、残課題はdocs/BACKLOG.mdを参照します。過去のbuild/worktrees/visual-twin継続指示は当時の記録です。新しい仕組み変更はブランチで行い、worktreeが必要ならプロジェクト外に作成します。build内にソース一式を再入れ子にしません。
