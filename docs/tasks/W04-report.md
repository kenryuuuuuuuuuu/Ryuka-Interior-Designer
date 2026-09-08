# W04 実装報告

状態：READY_FOR_REVIEW
開始BASE（完全SHA）：`37fb6a9543f1ad40da33185e4239ab704bd11463`
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境：Windows 11 Pro 10.0.26200 / UE 5.8.2 / Blender 5.2.0 LTS。変更した設定なし。

## 結果

ゲストLDK（room-1f-06）の壁・床・天井を面単位で仕上げ変更できるようになりました。共有壁は法線方向の点-in-polygon判定（`wall_cap_for_room()`）で表裏を判定するため、裏側の部屋・隣接部屋には影響しません。UEエディタの「内装比較」メニューに「面編集」（対象選択・色/roughness編集・プリセット・対象リセット・全解除・部屋一括適用）と「案の保存・比較」（W03-Aの名前付き案の保存・一覧・読込に加え、同一視点・照明条件でのA/B比較）を追加しました。比較状態は`schemaVersion 1.1.0`で`surfaceOverrides`を保持し、旧`1.0.0`状態もそのまま読み込めます。F5/F9保存・復元、`--previous`/`--scenario`いずれの再生成でも上書きが引き継がれます（既存のF5/F9・named-scenario機構自体はコード変更なしでそのまま対応）。W03-Cレビューの残件2点（`build-visual-twin.py`の`inputs()`への`surface_registry.py`明記、ARCHITECTURE.mdの登録欠落の扱いの記述訂正）も本タスクで対応済みです。

| 条件ID | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| AC1（壁1面の色変更、窓分割面へ反映、他面・共有壁裏・隣室床が不変） | PASS | `build/W04-package-override-v1`：`surf-guest-wall-005`（窓で分割された壁）を赤へ上書きしBlenderレンダリング（`interior.png`）で確認。`build/W04-ue-v1`：同上書きをUEへインポートし`Saved/overrides-check.png`でエディタキャプチャ確認、`import-verification.json`の`unrealImportVerified: true`。`build/W04-refresh-v1/ue/Saved/walkthrough-smoke.png`：完全refresh成果物でC++ウォークスルー（DX12）から見ても該当壁のみ赤・他の壁は元の仕上げのまま。単体：`tests/test_surface_bindings_geometry.py`（`wall_cap_for_room`が中心線±epsilonの点-in-polygon判定のみで表裏判定し方位を使わないこと、共有壁が両側で別capになることを含む11件） |
| AC2（床・勾配天井のプリセット変更、対象解除、部屋一括適用、開口・重複ちらつきなし、既存歩行可） | PASS | 床：`build/W04-package-override-v1`／`W04-ue-v1`で`surf-guest-floor-001`をcolorHex+roughness上書きし確認（同上のレンダリング・キャプチャ）。天井プリセット変更・対象解除・部屋一括適用：`build/W04-ue-v1/verify_editor_controls.py`を実UEエディタ（NullRHI、`-run`不使用の通常エディタ起動）で実行し`editor-controls-verification.json`に記録——`surf-guest-ceiling-001`へ`apply_preset_to_selected('reference')`適用→`reset_selected()`で解除→`apply_preset_to_room('warm')`で登録済み8面（壁6・床1・天井1）全てに一括適用（`room_apply_covers_all_bound_surfaces: true`）。開口非閉塞・床天井の重複ちらつき無し・既存歩行可：`build/W04-refresh-v1`のDX12ウォークスルースモーク（`checks: ["safe spawn","blocking capsule sweep","finish and sun switch","state save and restore"]`が全通過、上書き適用中の状態で衝突判定・当たり判定が正常動作）。床/天井の隣室非干渉は`tests/test_surface_bindings_geometry.py`の`subtract_rects`/`intersect_rect`関連7件で確認（実装中に「部屋bboxが重なるだけで無条件に対象と判定すると隣室天井にも同じ扱いが付く」不具合を発見・修正済み。詳細は下記） |
| AC3（A/B同条件切替、名前付き保存、F5/F9または editor→歩行の代表往復、再起動復元、完全refreshに--scenario、旧1.0.0状態読込確認） | PASS | A/B比較：`verify_editor_controls.py`実行で`start_compare()`→`show_compare_b()`→`end_compare()`を実施。`compare_fixed_conditions_held: true`（視点・太陽角度・光源強度・露出は固定のまま）、`compare_a_differs_from_b: true`（仕上げ内容は切り替わる）、`after_end_compare`は比較開始前の状態に復帰。名前付き保存：`build/scenarios/w04-overrides-test`（`save-study-scenario.py`、既存W03-A機構をそのまま利用、コード変更なし）。`load_scenario()`直接読込も実UEエディタで確認（`after_load_scenario_b`が保存済みoverridesと一致）。F5/F9・再起動復元：`build/W04-ue-v1`・`build/W04-refresh-v1`のDX12ウォークスルースモークが`state save and restore`チェックを通過し、スクリーンショットに「視点を復元しました」表示、復元後の`savedState.surfaceOverrides`が保存直前と一致。完全refresh＋`--scenario`：`build/W04-refresh-v1`（`--scenario build/scenarios/w04-overrides-test`）を実行し全7工程`complete`、`ue/import-verification.json`の`comparisonState.surfaceOverrides`が選択した案のoverridesと完全一致、`walkthrough-verification.json`で`renderRHI: "d3d12"`・`renderVerified: true`を確認。旧1.0.0状態の読込：`tests/test_surface_finish_overrides.py::test_1_0_0_state_normalizes_to_empty_overrides`に加え、上記A/B比較のA側に使った`build/scenarios/guest-a-v1`が実際にW03-A時代の`schemaVersion: "1.0.0"`（`surfaceOverrides`欄なし）のままの実データで、実UEエディタでの`load_scenario()`/`start_compare()`が正常に`{}`へ正規化して適用できることを実機で確認済み |
| AC4（消えたsurface ID/no-surfaceへの上書き1件、型不正1件、元の案は保持） | PASS | 消えたID：実UEエディタで`select_surface('surf-does-not-exist')`を実行し`RuntimeError`（`unknown_surface_raises: true`）、直後の状態が呼び出し前と同一であること（`state_unchanged_after_invalid_select: true`）を確認。no-surface：`tests/test_surface_finish_overrides.py::ResolveOverridesTests::test_no_surface_override_is_an_issue_not_a_crash`（クラッシュせず`issues`へ記録、他の上書きは維持）。型不正：同ファイルの`SurfaceOverrideValidationTests`（未知variant／colorHex不正4種／roughness範囲外・型不正4種／未知フィールドの計7件がいずれも`ValueError`）。Blender側の未解決IDによる停止：既存のW03-C機構をそのまま利用（`build_interior.py`の`main()`が未知/no-surface対象IDで`RuntimeError`、Blender起動前に停止） |
| 回帰 | PASS | `python -m pytest tests/`：108 passed, 35 subtests passed（既存82件＋新規26件：`test_surface_bindings_geometry.py` 11件、`test_surface_finish_overrides.py` 15件）。`node scripts/build-web-data.mjs --check`成功。`python tests/validate_house.py`：33室・35壁 |

## 変更と判断

- 新規：`blender/surface_bindings.py`（壁の表裏判定・範囲分割・床天井の矩形分解/差分/交差、純Python）、`unreal/surface_finish_overrides.py`（`resolve_finish`/`resolve_overrides`、全体バリアント＋面別上書きの共通解決ロジック）、`unreal/material_builder.py`（`marker_material()`：Color/Roughnessパラメータ化マテリアル。既存`material()`もここへ集約）、`tests/test_surface_bindings_geometry.py`、`tests/test_surface_finish_overrides.py`。
- 変更：`blender/build_interior.py`（`SurfaceBinder`クラス、壁ループの表裏判定・範囲分割接続、床/天井ループを部屋ごとの矩形交差方式へ変更、`--state`引数と未登録対象のBlender前エラー）、`unreal/import_study.py`（`surface-bindings.json`を読みマーカーマテリアルを追加スロットへ割当）、`unreal/study_state.py`（`schemaVersion 1.0.0/1.1.0`両対応、`surfaceOverrides`の構造検証）、`unreal/study_controls.py`（面編集・部屋一括適用・A/B比較・名前付き案の保存/一覧/読込のメニュー化、MID生成による上書き適用）、`unreal/walkthrough/Source/RyukaInterior/Walkthrough.{h,cpp}`（`ApplyConditions()`にC++版`resolve_finish`相当のロジックとMID適用、`Restore()`のschemaVersion許容範囲拡張）、`scripts/build-visual-twin.py`（`--state`引数、`surface_registry.py`を`inputs()`へ明記＝W03-C残件1）、`scripts/build-unreal-study.py`（新規Pythonモジュールのコピー、`repo-root.json`書き出し）、`scripts/refresh-visual-study.py`（Blenderへ`--state`を渡す）。
- 設計からの差異：仕様は「マーカーマテリアルの見た目」を具体的に指定していないため、パラメトリック（単色＋roughnessのみ、手続き型ノイズ/パターン無し）な実装を選択しました（裁量の範囲）。この結果、面を上書きするとその面だけ手続き型の質感（referenceバリアントの床タイル・天井目地等）を失いフラットな色になります。仕様5章の「実描画を変える今回はDX12で代表的な操作・画像を確認します」「色管理の差による画素一致を完了条件にしません」の範囲内と判断しています。
- 自由入力（色コード・roughness・案の名前）はUE埋め込みPythonにtkinter等のダイアログ機構が無いため、PowerShellの`Microsoft.VisualBasic.Interaction.InputBox`をシェルアウトして取得する方式にしました（既存の内装比較メニュー自体がSlate不使用の`unreal.ToolMenus`ベースであることに合わせた選択）。
- 追加依存：なし。環境変更：なし。
- 未追跡/ignored成果物：`build/W04-package-v1`（上書きなしBlender生成、全8面`bound`確認）、`build/W04-package-override-v1`（赤壁・青床の上書きBlender生成＋レンダリング）、`build/W04-ue-v1`（上記のUEインポート＋エディタキャプチャ＋DX12ウォークスルースモーク＋`verify_editor_controls.py`による面編集/A/B比較の実機検証）、`build/W04-diag/state-red-wall-blue-floor.json`（検証用の状態JSON）、`build/scenarios/w04-overrides-test`（W04上書きを含む名前付き案）、`build/W04-refresh-v1`（`--scenario`を使った完全refresh、Blender→UE→ウォークスルーDX12まで一括）。いずれも`.gitignore`対象で未コミットです。

## 残ること

- マーカーマテリアルはパラメトリック（単色＋roughness）で、Blender側の手続き型ノイズ・パターン（referenceバリアントの床タイル・天井目地等）は再現しません。上書きした面はその質感を失いフラットな色になります（仕様の完了条件の範囲内と判断済み、上記参照）。
- 梁・段差の立ち上がり・窓枠・開口の見込み・巾木は引き続き対象外です（仕様通り）。
- 登録・検証済みはroom-1f-06の8面のみです。他室は未登録でもエラーになりませんが、面編集メニューの対象にもなりません。
- レイクリックによる面選択（仕様上は任意）は未実装です。一覧からの選択のみで対象選択の確認（アクター選択によるUE標準のハイライト表示）を満たしています。
- W05へは着手していません。

## 再現・復旧

```powershell
# Blenderのみ：面ごとの色上書きを含む生成
python scripts/build-visual-twin.py --interior --output build/<新規ディレクトリ> --state build/W04-diag/state-red-wall-blue-floor.json

# UEフル生成（Blender→UEインポート）
python scripts/build-unreal-study.py --blender 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --engine 'C:/Program Files/Epic Games/UE_5.8' --cache '../../ddc' --interior --state build/W04-diag/state-red-wall-blue-floor.json --output build/<新規ディレクトリ>

# 名前付き案を使った完全refresh（Blender→UE→ウォークスルー確認まで一括）
python scripts/refresh-visual-study.py --previous build/W04-ue-v1 --scenario build/scenarios/w04-overrides-test --output build/<新規ディレクトリ> --cache '../../ddc'

# DX12スモーク（保存・復元・当たり判定の実機確認）
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/<UEプロジェクト> --cache '../../ddc' --smoke

# エディタメニュー（面編集・A/B比較）の実機確認スクリプト
# build/W04-ue-v1/verify_editor_controls.py を対象プロジェクトへコピーして実行
"C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" build/<UEプロジェクト>/RyukaInterior.uproject `
  "-ExecCmds=py import runpy; runpy.run_path(__import__('unreal').Paths.project_dir()+'verify_editor_controls.py')" `
  -unattended -RenderOffscreen -NoSound -nosplash -NoSourceControl -NullRHI

# テスト・回帰
python -m pytest tests/ -q
node scripts/build-web-data.mjs --check
python tests/validate_house.py
```

全ログ・成果物は`build/W04-package-v1/`・`build/W04-package-override-v1/`・`build/W04-ue-v1/`・`build/W04-refresh-v1/`・`build/W04-diag/`配下にあります。
