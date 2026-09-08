# W03-A 名前付きの検討案を保存し、更新後の家へ再適用する

状態：READY。実装担当：Claude Code / Sonnet。設計・レビュー：GPT。

## 利用者にできるようになること

内覧で決めた仕上げ・視点・太陽条件を「ゲストLDK・明るい木部案」等の名前で保存し、別の検討をしてもその案を失わず、現在の正本から再生成するときに選んで適用できます。

W03全体の最初の実装単位です。今回は**比較条件の複数保存と再適用**を完成させます。家具の配置案そのものの複数管理、壁面単位の仕上げ、永続的な壁面ID、部屋分割の自動移行、UE内の新しい選択UIは含めません。家の形状・家具配置は常に現在の共有JSONから生成します。

## 開始点・参照

専用ワークツリー `build/worktrees/visual-twin`、ブランチ `feature/visual-twin-foundation`。W02受入コードは `5c41a258d88d910a051b8b3a46ab78d47a26f359`。本仕様を含む着手時HEADを完全SHAでBASEとして記録し、未関連の変更は混ぜません。mainへ移動しません。

AGENTS.md、初回BACKGROUND.md、DEVELOPMENT_WORKFLOW.mdの「完成を優先するレビュー基準」を守ります。実装の参照は `scripts/refresh-visual-study.py`、`unreal/study_state.py`、`tests/test_refresh_study.py`、`docs/REFRESH_WORKFLOW.md`。

前提：最新の内覧は `build/W02-refresh-v5/ue`。W02検証用の識別マーカー/破損データが通常保存に残っていないか確認し、残っていれば案保存元には使いません。検証用コピーで有効なstudy-stateから開始してください。施主の保存を黙って削除/修復しません。

## 固定するデータ契約

### 正本と状態

- 建物・家具・設備・開口の共有JSONを唯一の形状/配置入力として維持します。Three.jsのlocalStorageはJSON書出し・正本反映後に初めて対象になります。
- 既存のstudy-state.jsonスキーマ1.0.0とC++のF5/F9形式を変更しません。UEのメッシュ/材質を直接編集した内容は案保存の対象外です。
- 検討案は状態ファイルを包む別の小さなパッケージです。プロジェクト/GLB/画像の複製は不要です。採用した材質設定ファイルや家具配置そのものを凍結する機能ではありません。
- 案は追記方式です。既存出力先の上書きを拒否し、修正版は別ディレクトリ/別IDで保存します。同じ案名は許容し、IDで識別します。複雑な履歴DBは作りません。

### 出力例

```text
build/scenarios/guest-natural-v1/
  scenario.json
  study-state.json
  sun-cases.json       # 元にあれば保存
  site-context.json    # 元にあれば保存。個人情報を含み得るためローカル限定
```

scenario.jsonの契約：

```json
{
  "schemaVersion": "1.0.0",
  "id": "UUIDを新規発行",
  "name": "ゲストLDK・明るい木部案",
  "note": "任意のメモ",
  "createdAt": "タイムゾーン付きISO8601日時",
  "roomId": "room-1f-06",
  "origin": {
    "sourceCommit": "保存元SourcePackage/manifest.jsonの値、なければnull",
    "sourceHashes": {"保存元の入力パス": "保存元manifestのハッシュ"},
    "stateSource": "runtime または editor"
  },
  "files": {
    "study-state.json": {"sha256": "ファイルのSHA-256"}
  }
}
```

存在するsun-cases/site-contextもfilesへ含めます。固定ファイル名のみ許容し、外部パス参照や任意ファイルの取り込みはしません。JSONはUTF-8で出力しますが、元状態/周辺ファイルは**バイト列のままコピー**し、siteContextSHA256との一致を維持してください。nameは空白だけを拒否（上限120文字）、noteは省略時空文字。roomIdは状態と一致させます。

originは「その案を作ったモデルの入力」であり、保存時の現在のGit HEADで代用しません。未コミットで生成したモデルもあるため、sourceHashesが実体の識別、sourceCommitは補助情報です。絶対パスはscenario.jsonへ記録しません。

## CLIと動作

### 1. 案保存

新規 `scripts/save-study-scenario.py`：

```powershell
python scripts/save-study-scenario.py --project build/W02-refresh-v5/ue --name 'ゲストLDK・木部案A' --note '午前の検討' --output build/scenarios/guest-a-v1
```

projectは既存UEプロジェクト、outputはこのworktreeのbuild内の未作成ディレクトリ。Blender/UEを起動せずに保存します。既存refreshのretained_inputsと同じ選択・整合検証を再利用してください（必要なら小さな共通Pythonモジュールへ抽出）。

状態選択：editorと通常runtimeの更新時刻が新しい方。同時刻はeditor。テスト/smoke保存は対象外。選ばれた状態が無効なら、別状態へ黙って切り替えず保存を中止して、UEで保存し直す案内をします。通常runtimeの.bakがあり本体ファイルがない復旧待ちの場合も、案保存を中止します。W02の復旧ロジックをPythonへ複製しません。

import-verification成功、状態・周辺・日時の整合は既存validatorを使います。コピー後にfilesのハッシュを記録します。コピー中に入力が変わった場合は、完成した案として返さず再実行を案内します。既存のハッシュ処理を活用し、新たなトランザクション基盤や多重障害対策は作りません。

### 2. 一覧

新規 `scripts/list-study-scenarios.py --root build/scenarios`。直下の各フォルダを読み、ID・名前・作成日時・部屋・仕上げ・相対パスを一覧表示します。軽いCLI表で十分です。不正な案は理由付きで表示し、他の正常な案の一覧を妨げません。再帰探索・UI・検索機能は不要です。

### 3. 再適用

既存refreshへ任意引数 `--scenario <案ディレクトリ>` を追加します。

```powershell
python scripts/refresh-visual-study.py --previous build/W02-refresh-v5/ue --scenario build/scenarios/guest-a-v1 --output build/W03-A-refresh-v1 --cache '../../ddc'
```

--previousは引き続き必要です。前回プロジェクトのimport済み確認、内覧モジュール有無、従来の変更ファイル比較に使います。--scenario指定時、引き継ぐ状態/日時/周辺は**案パッケージだけから**読み、previous側の最新保存や周辺を混ぜません。案に周辺がない場合はpreviousに周辺があっても取り込みません。案が指定された場合、previousの現在の保存状態を読み込む必要はありません（不正な保存で有効な案の適用を妨げないこと）。案作成元とpreviousが異なっていても対象部屋が一致すれば使用できます。

前処理でschemaVersion/必須ファイル/ハッシュ/roomId/現在の許可されたvariantを検証します。現在の対象ゲストLDKと別のroomIdは、理由を示して重い生成の前に停止します。削除された仕上げ案の自動置換・部屋名からの推定対応はしません。--galleryは従来同様、案に必要な太陽ケースがあれば使えます。

既存のretained/へ状態をコピーしてから、以降は従来の生成・内覧構築・状態照合を使います。--scenarioなしの動作は維持します。現在の形状/配置/材質生成設定で再生成するので、案作成時とソースが異なれば見た目は変わり得ます。これを画面/文書で短く説明します。

refresh.jsonへselectedScenario（id/name、scenario.jsonのSHA-256、origin）を追加し、retained/scenario.jsonも保存します。既存sourceHashesは今回の入力、changedSourceFilesはpreviousモデルとの比較という意味を変えません。案のoriginとの比較と混同しないラベルにします。更新中の案変更は既存unchanged相当で検出します。

更新結果index.htmlには案名と「現在の建物にこの案の比較条件を適用した」ことを表示します。name/noteはHTMLエスケープし、内部のハッシュや例外全文を利用者向け本文へ並べません。

## 変更範囲と裁量

Pythonの保存/一覧CLI、refreshの入力選択、必要最小限の共通モジュール、関連テスト、REFRESH_WORKFLOW/STATUSが中心です。C++内覧、Three.js、正本スキーマ、家具配置、壁の永続IDは変更しません。細かな関数分割やCLI表示は任せます。依存ライブラリ追加は不要です。

## 軽量な受入確認

1. 有効な状態から名前の異なる2案を保存し、一覧に出ること。元プロジェクトの条件を変更しても先に保存した案が変わらないことを確認します。
2. 選んだ案から新しい出力へ再生成し、仕上げ・カメラ・太陽条件が案と一致し、DX12の画面が出ることを1回確認します。最新の正本を読むことはコピーした入力の家具1件移動による小さなPythonテストでも確認可とし、UEフル生成を2回以上必須にはしません。正本へ試験変更を残しません。
3. 簡単な異常系は案ファイルの欠落/ハッシュ不一致と別部屋の拒否を少数のPythonテストで確認します。多重障害・全分岐・保存障害注入テストの再実行は不要です。
4. 既存のrefresh関連Pythonテストと `node scripts/build-web-data.mjs --check`、コミット前の `python tests/validate_house.py` を確認します。無関係なC++テストの再実行は求めません。

通常利用を妨げない小さな問題は報告して次へ進めます。実施していない項目をPASSにはしませんが、証拠を大量に作ることを目的にしません。

## 提出

W03-A-report.mdへ、できること・実行コマンド・簡潔な検証結果・残件を記載します。同じ開始BASEからbuild/reviews/W03-A-v1を作成し、代表的な案manifest、refresh結果、画面1枚程度を添えます。絶対パス/敷地情報を公開文書へ含めません。W03-BやW04へ自動着手しません。
