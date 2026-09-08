# W03-B 実装報告

状態：READY_FOR_REVIEW
開始BASE（完全SHA）：`6ec8e460b06bde3e1cd6777820fe1194ee624acd`
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境：Windows 11 25H2 / UE 5.8.2 / Blender 5.2.0 LTS。変更した設定なし。

## 結果

前回モデルと現在の正本を比較し、家具・部屋・家具カタログの追加/削除/変更をID単位で一覧表示できるようになりました。削除した家具に装飾設定が残っている等の参照切れを、Blender/UEの重い処理を始める前に、対象IDと設定ファイルを添えて案内します。W03-Aの名前付き案・W02の内覧C++は変更していません。

- `scripts/source_changes.py`：`compare(previous, root)`が比較（`SourcePackage/inputs/data/`の原本コピーとハッシュ照合）と参照確認（現在のdata/以下、7種類の参照先）の両方を行う共通モジュール。`render_html()`・`summarize()`も提供。
- `scripts/check-study-changes.py --previous <UEプロジェクト> --output <新規ディレクトリ>`：Blender/UEを起動せず`source-changes.json`と`index.html`を出力する軽量CLI。参照切れ・重複があれば終了コード1。
- `scripts/refresh-visual-study.py`：`01-source-check`の直後（Blender起動前）に比較・参照確認を実行し、`source-changes.json`・`changes.html`を出力先へ保存。現在の参照切れがあれば既存の`failed`扱いで停止し、完成ページを作りません。成功時の`index.html`に「前回モデルからの変更」の要約と`changes.html`へのリンクを追加しました。

比較対象はhouse.jsonのrooms（キーid）、furniture.jsonのitems（キーid）、furniture-catalog.jsonのtypes（キーtype）。参照確認は`furniture.room/type`・`guest-ldk-study.roomId`・`asset-bindings.furnitureId`・`guest-decor.roomId/furnitureId/openingId`の7種です。

| 条件ID | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| 軽量確認1（まとめた変更・ID単位の差分・配列順のみは無変更） | PASS | `tests/test_source_changes.py::test_representative_changes_are_diffed_by_id_not_array_order`（家具の移動・追加・カタログ寸法変更・部屋名変更を1回で確認）、`::test_array_reorder_alone_is_not_a_change` |
| 軽量確認2（参照切れで案内・停止、解消で通過、比較元欠落は警告） | PASS | `tests/test_source_changes.py`の`test_removed_furniture_with_dangling_decor_reference_is_an_issue`・`test_removing_the_dangling_reference_too_clears_the_issue`・`test_missing_baseline_snapshot_is_a_warning_not_all_added`・`test_tampered_baseline_hash_is_unavailable` |
| 軽量確認3（実データでCLI1回・既存回帰・Blender/UE不起動をモック確認） | PASS | `check-study-changes.py --previous build/W02-refresh-v5/ue --output build/W03-B-check-v1`（終了コード0、`issues:[]`）。`tests/test_refresh_study.py::test_current_reference_issue_stops_before_blender_or_unreal`（参照切れ時、`subprocess.run`が`node --check`の1回のみで`02-blender`以降は未呼び出しであることをモックで確認、`refresh.json`は`status:"failed"`、`index.html`未生成） |
| 軽量確認4（通常refreshへの接続、代表1件） | PASS | `refresh-visual-study.py --previous build/W03-A-refresh-v1/ue --output build/W03-B-refresh-v1`実行、終了コード0。`refresh.json`の`steps`に`01b-source-changes:complete`、`sourceChanges.baselineStatus:"available"`・`issueCount:0`。`index.html`に「前回モデルからの変更」欄と`changes.html`リンクを確認。UEフル再生成の追加実行は行っていません（今回は幾何/描画を変更しないため既存生成成功を活用、仕様が明示的に許容） |
| 回帰 | PASS | `python -m pytest tests/`：67 passed（既存58件＋新規9件）。`node scripts/build-web-data.mjs --check`成功。`python tests/validate_house.py`：33室・35壁 |

## 変更と判断

- 新規：`scripts/source_changes.py`、`scripts/check-study-changes.py`、`tests/test_source_changes.py`。
- 変更：`scripts/refresh-visual-study.py`（`01b-source-changes`ステップ追加、`summary()`への要約表示追加）、`tests/test_refresh_study.py`（参照切れ時にBlender/UEが呼ばれないことを確認するテストを追加）。
- 設計からの差異：なし。仕様の裁量部分（モジュール名`scripts/source_changes.py`、フィールド分類の具体的なグルーピング）は仕様の例に沿って実装しました。
- 追加依存：なし。環境変更：なし。
- 未追跡/ignored成果物：`build/W03-B-check-v1`（単独CLIの実データ確認）、`build/W03-B-refresh-v1`（refresh接続の代表確認）。いずれも`.gitignore`対象で未コミットです。

## 残ること

- 選択された案/保存状態のroomIdが現在のhouse.rooms[].idに存在するかの確認は、既存の`validate_state`（`retained_inputs`/`scenario_inputs`経由、`--scenario`のroomId不一致等を検出）と一部重複します。仕様が「既存state validatorも併用」としている通り、本タスクでは独立した重複チェックの追加はしていません。
- 家具配置案そのものの複数管理、自動マージ、IDの自動再発行、消えた家具の自動復活、壁面ID、全館内覧、UE C++改修は仕様通り対象外です。
- W03-Cへは着手していません。

## 再現・復旧

```powershell
# 単独確認（Blender/UEを起動しない）
python scripts/check-study-changes.py --previous build/W02-refresh-v5/ue --output build/<新規ディレクトリ>

# 通常refreshへの接続確認
python scripts/refresh-visual-study.py --previous build/W03-A-refresh-v1/ue --output build/<新規出力> --cache '../../ddc'

# テスト
python -m pytest tests/test_source_changes.py tests/test_refresh_study.py -q
```

全ログ・比較結果は`build/W03-B-check-v1/`・`build/W03-B-refresh-v1/`配下にあります。
