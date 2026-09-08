# W03-A 実装報告

状態：READY_FOR_REVIEW
開始BASE（完全SHA）：`784a9bc2eb940a579e524c04afeb11fdb90961bf`
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境：Windows 11 25H2 / UE 5.8.2 / Blender 5.2.0 LTS。変更した設定なし。

## 結果

比較条件（仕上げ・視点・太陽条件）を名前付きの案として保存し、一覧表示し、現在の正本から再生成した家へ適用できるようになりました。W02の内覧保存（F5/F9）・正本スキーマ・家具配置・C++は変更していません。

- `scripts/save-study-scenario.py --project <UEプロジェクト> --name '名前' --note 'メモ' --output build/scenarios/<id>`：Blender/UEを起動せず、既存のstudy-state.json/内覧保存を検証済みの選択ロジックでコピーし、`scenario.json`を発行します。
- `scripts/list-study-scenarios.py --root build/scenarios`：ID・名前・作成日時・部屋・仕上げ・パスを一覧表示します。
- `scripts/refresh-visual-study.py --scenario <案ディレクトリ>`（既存`--previous`と併用）：状態/日時/周辺を案パッケージだけから読み、previous側の最新保存とは混ぜずに再生成します。

`retained_inputs`（前回のstudy-state選択・検証ロジック）は`scripts/refresh_inputs.py`へ共通モジュールとして抽出し、refreshと案保存の両方が同じ検証（schemaVersion/roomId/variant/周辺ハッシュ）を再利用します。新たに、内覧の保存が復旧待ち（バックアップのみ残り本体がない状態）の場合は案保存・refreshとも中止するガードを追加しました（W02のC++復旧ロジック自体はPythonへ複製していません）。

| 条件ID | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| 軽量確認1（2案保存・一覧・不変性） | PASS | `build/scenarios/guest-a-v1`・`guest-b-v1`を実データから保存（終了コード0）。`list-study-scenarios.py`で両方表示。案A保存後に元の`study-state.json`のvariantを`warm`→`reference`へ変更して案Bを保存したが、`guest-a-v1/study-state.json`のvariantは`warm`のまま不変（`build/W03-A-diag/`のコマンド出力に記録） |
| 軽量確認2（再適用→DX12描画） | PASS | `refresh-visual-study.py --previous build/W02-refresh-v5/ue --scenario build/scenarios/guest-a-v1 --output build/W03-A-refresh-v1`（終了コード0、`status:"complete"`）。適用後のvariantは`warm`、camera/sunは案と一致（`import-verification.json`の`comparisonState`）。`state-transfer-verification.json`：statePreserved/geometryVerified/cameraRotationPreserved全てtrue。DX12 `--smoke`実行（終了コード0）で`Saved/walkthrough-smoke.png`生成を確認。UEフル生成はこの1回のみ |
| 軽量確認3（異常系：ファイル欠落/ハッシュ不一致/別部屋） | PASS | `tests/test_study_scenarios.py`（10件）：無効な状態の拒否、復旧待ち状態の拒否、名前欠落/超過の拒否、既存出力の拒否、案ハッシュ不一致の拒否、別roomIdの拒否、一覧での不正案の分離表示。実データでも、W02検証用マーカーが残った`build/W02-refresh-v5/ue`を直接`--project`に指定して拒否されること（スキーマエラーで終了コード1、出力ディレクトリ未作成）を確認 |
| 軽量確認4（既存回帰） | PASS | `python -m pytest tests/`：58 passed（既存48件＋新規10件、既存`test_refresh_study.py`はリファクタ後も無変更で成功）。`node scripts/build-web-data.mjs --check`成功。`python tests/validate_house.py`：33室・35壁 |

## 変更と判断

- 新規：`scripts/refresh_inputs.py`（`retained_inputs`の抽出＋`scenario_inputs`追加）、`scripts/save-study-scenario.py`、`scripts/list-study-scenarios.py`、`tests/test_study_scenarios.py`。
- 変更：`scripts/refresh-visual-study.py`（`retained_inputs`等を共通モジュールから読み込み、`--scenario`引数、`selectedScenario`のrefresh.json記録、`retained/scenario.json`保存、index.htmlへの案名表示を追加）。
- `data/visual/guest-ldk-study.json`のroomId/variantsをそのまま検証基準として再利用し、正本スキーマは変更していません。
- 設計からの差異：仕様は「小さな共通Pythonモジュールへ抽出」を裁量としており、`scripts/refresh_inputs.py`という新規ファイルへ抽出しました（`unreal/`配下ではなく、CLIのファイルパス選択ロジックのため`scripts/`配下）。
- 追加依存：なし。環境変更：なし。
- 未追跡/ignored成果物：`build/scenarios/guest-a-v1`・`guest-b-v1`（実データでの保存確認）、`build/W03-A-refresh-v1`（再適用の一括生成確認）、`build/W03-A-diag/clean-source`（W02検証用マーカーを含まない検証用コピー、施主の実データではない）。いずれも`.gitignore`対象で未コミットです。

## 残ること

- 「最新の正本を読む」ことは、`sources()`が`data`/`blender`/`unreal`/`scripts`/`generated`/`tests`を毎回再走査する既存実装（既存テストで検証済み）に依拠しており、本タスクでは追加の家具1件移動テストは実施していません（仕様が明示的に許容する軽量化）。
- 家具配置案そのものの複数管理、壁面単位の仕上げ、永続的な壁面ID、部屋分割の自動移行、UE内の新しい選択UIは仕様通り対象外のままです。
- W03-Bへは着手していません。

## 再現・復旧

```powershell
# 保存
python scripts/save-study-scenario.py --project build/W02-refresh-v5/ue --name '案名' --output build/scenarios/<新規ディレクトリ>

# 一覧
python scripts/list-study-scenarios.py --root build/scenarios

# 再適用
python scripts/refresh-visual-study.py --previous build/W02-refresh-v5/ue --scenario build/scenarios/<案> --output build/<新規出力> --cache '../../ddc'

# テスト
python -m pytest tests/test_study_scenarios.py tests/test_refresh_study.py -q
```

全ログ・案データは`build/scenarios/`・`build/W03-A-refresh-v1/`・`build/W03-A-diag/`配下にあります。
