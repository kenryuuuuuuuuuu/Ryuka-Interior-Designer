# W03-C 実装報告

状態：READY_FOR_REVIEW
開始BASE（完全SHA）：`55e9ab52e2456f335ab0909cd4d53c938ddb1f9f`
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境：Windows 11 25H2 / UE 5.8.2 / Blender 5.2.0 LTS。変更した設定なし。

## 結果

ゲストLDK（room-1f-06）の部屋境界面（壁6・床1・天井1の計8面）に手動確定の永続ID（`data/visual/surface-registry.json`）を登録し、現在の`house.json`形状へ解決できるかを軽い処理で確認できるようになりました。W04が仕上げ設定の対象として参照するデータ契約で、仕様通り**面ごとの材質適用・UEでの面選択・メッシュ分割・C++変更は今回対象外**です。「面IDがUEの実メッシュへ接続済み」とは主張していません。

- `scripts/surface_registry.py`：`resolve_from(root)`が登録の構造検証（重複ID・重複辺・不正形式）と、現在の`house.json`への解決（壁は端点座標一致・順序不問・許容差1e-6m、床/天井はroomIdで現在のpolygon/ceilingへ追従）を行う。座標の近さでの推測・登録の自動更新はしない。
- `scripts/check-study-surfaces.py --output <新規ディレクトリ>`：Blender/UE不起動の軽量CLI。`surface-resolution.json`と部屋輪郭の簡易SVGを含む`index.html`を出力。未解決・重複・不正schemaがあれば終了コード1。
- 接続：`scripts/refresh-visual-study.py`（W03-Bの参照確認の直後）と`scripts/build-visual-twin.py --interior`（白模型のみの生成は対象外）の両方で、Blender起動前に検証し未解決があれば停止。既存`inputs()`（`data/`配下JSON全体が対象）が`surface-registry.json`のハッシュ・`SourcePackage/inputs/`コピーも自動的に含む。

| 条件ID | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| 軽量確認1（実データ8面の解決） | PASS | `check-study-surfaces.py --output build/W03-C-check-v1`（終了コード0、`issues:[]`、8面すべて`resolved`） |
| 軽量確認2（部屋/頂点順変更・端点逆順でID維持、共有境界は別ID） | PASS | `tests/test_surface_registry.py`：`test_vertex_order_and_endpoint_reversal_keep_the_same_id_resolved`、`test_shared_wall_both_room_sides_resolve_as_distinct_ids` |
| 軽量確認3（辺移動/分割で未解決→明示更新で解決、重複ID異常系） | PASS | 同上：`test_moved_wall_is_unresolved_until_registry_is_updated`（未解決確認後、登録の`edge`を明示更新して再解決を確認）、`test_split_wall_leaves_old_id_unresolved_not_auto_migrated`、`test_duplicate_id_is_rejected`、`test_duplicate_wall_edge_in_same_room_is_rejected`、`test_removed_room_is_unresolved`、`test_missing_or_malformed_registry_is_a_hard_error_not_empty_success`、`test_unregistered_other_room_is_not_an_error` |
| 軽量確認4（refresh/interior生成の事前停止、パッケージ収集） | PASS | `tests/test_refresh_study.py::test_unresolved_surface_registry_stops_before_blender_or_unreal`（モック、`subprocess.run`が`node --check`の1回のみでBlender/Unreal未呼び出し）。`tests/test_build_visual_twin_surfaces.py`（`--interior`時は7回の事前チェック後に停止しBlender未起動、`--interior`なしは検証自体を呼ばないことを確認）。実際に`build-visual-twin.py --interior`を1回実行（Blenderのみ、UEなし）し、`SourcePackage/inputs/data/visual/surface-registry.json`が存在しmanifestのハッシュと一致することを確認 |
| 回帰 | PASS | `python -m pytest tests/`：82 passed（既存67件＋新規15件）。`node scripts/build-web-data.mjs --check`成功。`python tests/validate_house.py`：33室・35壁 |

## 変更と判断

- 新規：`data/visual/surface-registry.json`（room-1f-06の初期8面登録）、`scripts/surface_registry.py`、`scripts/check-study-surfaces.py`、`tests/test_surface_registry.py`、`tests/test_build_visual_twin_surfaces.py`。
- 変更：`scripts/refresh-visual-study.py`（`01c-surface-registry`ステップ追加）、`scripts/build-visual-twin.py`（`--interior`時のみBlender前に検証）、`tests/test_refresh_study.py`（refresh側の停止をモックで確認するテスト追加）。
- 設計からの差異：なし。ラベル（例：「北側の壁（主要面）」）はhouse.jsonの座標系（x:west→east、z:north→south）から各辺の外向き法線を計算して割り当てました（仕様に具体的な命名指定はなく、裁量の範囲）。
- 追加依存：なし。環境変更：なし。UEフル再生成は行っていません（仕様が明示的に不要としています）。
- 未追跡/ignored成果物：`build/W03-C-check-v1`（単独CLIの実データ確認）、`build/W03-C-package-v1`（Blenderのみの実パッケージ収集確認）。いずれも`.gitignore`対象で未コミットです。

## 残ること

- 面ごとの材質適用・UEでの面選択・メッシュ分割・法線/UEマテリアルslotの格納はW04で詳細化する契約で、今回は未実装です（仕様通り）。
- 登録はroom-1f-06のみです。他室は仕様通り未登録でもエラーになりません。
- W04へは着手していません。

## 再現・復旧

```powershell
# 単独確認（Blender/UEを起動しない）
python scripts/check-study-surfaces.py --output build/<新規ディレクトリ>

# テスト
python -m pytest tests/test_surface_registry.py tests/test_refresh_study.py tests/test_build_visual_twin_surfaces.py -q
```

全ログ・確認結果は`build/W03-C-check-v1/`・`build/W03-C-package-v1/`配下にあります。
