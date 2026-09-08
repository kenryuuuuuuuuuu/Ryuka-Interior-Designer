# W04 実装報告

状態：READY_FOR_REVIEW（v2、W04-v1レビューのR1〜R5対応）
開始BASE（完全SHA）：`37fb6a9543f1ad40da33185e4239ab704bd11463`（維持）
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境：Windows 11 Pro 10.0.26200 / UE 5.8.2 / Blender 5.2.0 LTS。変更した設定なし。

## 結果（v2時点）

ゲストLDK（room-1f-06）の壁・床・天井を面単位で仕上げ変更できるようになりました。共有壁は法線方向の点-in-polygon判定（`wall_cap_for_room()`）で表裏を判定するため、裏側の部屋・隣接部屋には影響しません。床・天井も壁と同様に主面（床上面・天井下面）だけへ専用材質を割り当てます。UEエディタの「内装比較」メニューに「面編集」（対象選択・色/roughness編集・プリセット・対象リセット・全解除・部屋一括適用）と「案の保存・比較」（W03-Aの名前付き案の保存・一覧・読込に加え、同一視点・照明条件でのA/B比較）を追加しました。比較状態は`schemaVersion 1.1.0`で`surfaceOverrides`を保持し、旧`1.0.0`状態もそのまま読み込めます。F5/F9保存・復元、`--previous`/`--scenario`いずれの再生成でも上書きが引き継がれます。W03-Cレビューの残件2点も対応済みです。

**[W04-v1レビュー](W04-review.md)（対象`c234fdd`、CHANGES_REQUESTED）のR1〜R5をすべて同じW04内で修正しました**（この報告のv2）。各項目の対応は以下の通りです。

| 項目 | 対応 |
|---|---|
| R1（登録面が上書きの有無を問わず質感を失う） | `unreal/material_builder.py`の`material()`にパラメトリック（Color/Roughnessを`VectorParameter`/`ScalarParameter`にする）オプションを追加し、`marker_material()`はこれへ委譲。パターン/ノイズのノードはこれまで通り構築され、Colorパラメータに対して乗算されるため、上書きが無い登録面は周囲と同じ質感、上書きがあれば模様を保ったまま色だけ変わります。Blender側は`apply_pattern()`へ渡す色を「元のパレット色」から「上書き後の解決済み色」へ修正しました（以前は上書きしてもパターンの色計算が元の色を使っていたため、上書きの色指定がパターンで打ち消されていました）。 |
| R2（案読込・比較が既存の整合性確認を迂回する） | `study_controls.py`の`load_scenario()`/`start_compare()`が、W03-Aの`scripts/refresh_inputs.py`の`scenario_inputs()`（ファイルハッシュ・schema・room/variant整合の検証）をプロセス内で直接呼び出すよう変更。A/Bは両案を検証してから開始し、不整合な案は一覧から消さずに比較の開始・適用だけを拒否します。`apply_state()`の`site-context.json`ハッシュ照合を「無条件に現在値へ上書き」から「保存側ハッシュと現在値を比較し、不一致なら適用前に拒否」へ修正しました。 |
| R3（面編集・保存の通常操作） | `_apply_override()`を「置換」から「既存の上書きへのマージ」に変更（プリセット選択後に色だけ変えてもプリセット指定が消えない、roughnessだけの変更も可能）。面一覧・選択中の面・比較状態はメニュー先頭の常設項目としてラベル表示するようにしました（ログだけに頼らない）。保存直前に、シーンの実際の材質（MIDのColor/Roughness）が管理中の状態と一致するか検証し、Undo等での食い違いを検出したら理由付きで保存を拒否します。名前付き案の保存は、UE埋め込みPythonの`sys.executable`（UnrealEditor自身であり通常のpython.exeではない）を外部プロセスとして呼び出す実装が実際には動作しない不具合だったため、`refresh_inputs.py`から新規`save_scenario_package()`を切り出し、`study_controls.py`からプロセス内で直接呼び出す方式へ変更しました。 |
| R4（保存状態の検証をPython/内覧/事前確認で揃える） | `unreal/study_state.py`の`state.get('surfaceOverrides') or {}`が1.1.0のnull/配列/false等も無条件に空へ丸めていた問題を修正し、1.0.0の欠落だけを許容するようにしました。`Walkthrough.cpp`の`ApplyConditions()`に、保存データの`surfaceOverrides`全体を事前検証する処理を追加：型不正（`surfaceOverrides`自体がオブジェクトでない）、未知の上書きフィールド、colorHexの形式、roughnessの範囲、対象面が実際に`bound`かどうか、対象面が同じ部屋かどうかをPython版と同水準でチェックし、一つでも無効なら適用全体を中止します（以前は未知ID/no-surfaceのキーを黙って無視していました）。未登録の永続IDへの上書きは`build-visual-twin.py`がBlender起動前に検出するよう修正しました（以前はBlender起動後の`build_interior.py`内でしか検出しておらず、報告の「Blender起動前」という説明と実装が食い違っていました）。 |
| R5（床・天井の対象を主面へ限定する） | `blender/build_interior.py`の`block()`/`prism()`呼び出しに`face_materials`（壁と同じ仕組み）を渡すよう変更し、床は上面（cap 1）、天井は下面（cap 0）だけに専用スロットを割り当てます。勾配天井の段差立ち上がり（riser）は仕様通り対象外とし、専用スロットの割当・`surface-bindings.json`への登録のどちらも行わないようにしました。床・天井の対応判定に、部屋とスラブ/天井の階（level）の一致確認も追加しました（現在の登録はroom-1f-06のみ・1階のみのため、この階チェック自体は未検証の防御的対応です）。 |

| 条件ID | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| AC1（壁1面の色変更、窓分割面へ反映、他面・共有壁裏・隣室床が不変） | PASS（v1から変更なし、再確認） | v1報告の証拠に加え、`build/W04-v2-refresh-v1`で修正後コードによる完全refreshでも赤壁が単一面に留まることを再確認（下記AC3参照）。 |
| AC2（床・勾配天井のプリセット変更、対象解除、部屋一括適用、開口・重複ちらつきなし、既存歩行可） | PASS | v1の証拠に加え、R5修正後の実Blenderビルド（`build/W04-v2-package-v1`）でメッシュの面別マテリアルスロットを直接検査：`slab.*.surf-guest-floor-001.*`が2スロット`["wood","Surf_floor_..."]`・面数`{0:5,1:1}`（上面1面だけがマーカー）、`ceiling.room-1f-06.*`（勾配天井）が同様に`{0:5,1:1}`（室内側1面だけがマーカー）、`ceiling.riser.*`はマーカースロット無し（`["ceiling"]`のみ）であることを確認。 |
| AC3（A/B同条件切替、名前付き保存、F5/F9または editor→歩行の代表往復、再起動復元、完全refreshに--scenario、旧1.0.0状態読込確認） | PASS | v1の証拠に加え、修正後の実UEエディタ実行（`build/W04-v2-ue-v1/review-fixes-verification.json`）で以下を確認：①`_apply_override()`のマージ（`merge_keeps_variant_after_color`/`merge_keeps_variant_and_color_after_roughness_only`がいずれもvariant・colorHex・roughnessを保持）、②`save_scenario_package()`のプロセス内呼び出しが実際に成功（`save_scenario_package_succeeded: true`）、③改ざんした案（`scenario.json`のハッシュと一致しない`study-state.json`）の`load_scenario()`/`start_compare()`が`RuntimeError`で拒否し状態が変化しないこと、④Undoを模した状態不整合（シーンの材質を`apply_state()`外で直接差し替え）を`save()`が検出し拒否すること（`undo_divergence_detected: true`）。完全refresh＋`--scenario`は修正後コードで`build/W04-v2-refresh-v1`として再実行し、全7工程`complete`、`surfaceOverrides`が選択した案と完全一致することを確認（下記詳細）。C++側は再ビルド後にDX12スモークを再実行し、`renderVerified: true`・`renderRHI: "d3d12"`・4チェック全通過、保存・復元後も`surfaceOverrides`が一致することを確認（`build/W04-v2-ue-v1/walkthrough-verification.json`）。 |
| AC4（消えたsurface ID/no-surfaceへの上書き1件、型不正1件、元の案は保持） | PASS | v1の証拠（Python単体テスト、実UEエディタでの未知ID選択拒否）に加え、修正後コードで`apply_state()`に直接未知IDの上書きを含む状態を渡し`RuntimeError`・状態不変を確認（`unknown_override_id_raises`/`state_unchanged_after_unknown_override`）。1.1.0のnull/配列/false型不正は新規テスト`SurfaceOverride110StrictnessTests`（4件）で確認。C++側の型不正・未知ID・別部屋・no-surfaceの拒否ロジックはPython版と同じ判定を実装し、ビルド成功と上記の正常系実機確認（誤って有効な上書きを拒否しないこと）を確認済みですが、C++側の異常系そのものを実機で再現する専用テストは行っていません（詳細は「残ること」参照）。 |
| 回帰 | PASS | `python -m pytest tests/`：117 passed, 35 subtests passed（v1の108件＋新規9件：`resolve_overrides`の別部屋ケース2件、`resolve_finish`のdetail検証2件、`SurfaceOverride110StrictnessTests`5件）。`node scripts/build-web-data.mjs --check`成功。`python tests/validate_house.py`：33室・35壁 |

## 変更と判断（v2で追加・変更した分）

- 変更（v1報告分に追加）：`unreal/material_builder.py`（`material()`に`parametric`引数、`marker_material()`を委譲実装へ）、`unreal/surface_finish_overrides.py`（`resolve_finish()`が`detail`を返す、`resolve_overrides()`に`room_id`引数）、`unreal/import_study.py`（`marker_material()`へ`detail`を渡す、`surface-bindings.json`へ`label`を含める）、`unreal/study_state.py`（`surfaceOverrides`の1.0.0/1.1.0を区別した検証）、`unreal/study_controls.py`（大幅改修：R2〜R4節に記載）、`unreal/walkthrough/Source/RyukaInterior/Walkthrough.cpp`（`surfaceOverrides`の事前一括検証）、`blender/build_interior.py`（`apply_pattern`の色引数、`SurfaceBinder`の`label`保持、床/天井/勾配天井/riserの`face_materials`・レベル一致）、`scripts/build-visual-twin.py`（`--state`のsurfaceOverrides未知ID事前チェック）、`scripts/refresh_inputs.py`（新規`save_scenario_package()`、`SCENARIO_ROOT`分離）、`scripts/save-study-scenario.py`（CLIラッパー化）、`tests/test_study_scenarios.py`（`SCENARIO_ROOT`モック対応）、`tests/test_surface_finish_overrides.py`（新規9件）。
- 設計からの差異：v1では「マーカーマテリアルはパラメトリックだが模様は再現しない」という簡略化を裁量として選択していましたが、レビューで「仕様は既存模様の再利用を明示しており制限として受け入れられない」と指摘されたため撤回し、模様を保持する実装に変更しました（上記R1）。
- UE埋め込みPythonの`sys.executable`はUnrealEditor(-Cmd).exe自身であり、通常のpython.exeとして`python script.py`形式の外部プロセス起動には使えないことが実機検証で判明しました（v1の`save_scenario()`はこれが原因で実際には動作しない状態でした）。以後、UE埋め込みPythonから外部のCLIスクリプトの処理を再利用する場合は、プロセス内import＋直接呼び出しを基本方針とします。
- 追加依存：なし。環境変更：なし。
- 未追跡/ignored成果物（v1報告分に追加）：`build/W04-v2-package-v1`（上書きなし、R5の面別スロット検査用）、`build/W04-v2-package-reference-v1`／`-reference-override-v1`（reference variantのパターン保持・上書き色反映のBlender検査用）、`build/W04-v2-ue-v1`（修正後コードのUEインポート＋マーカーマテリアルのノードグラフ検査＋R2/R3/R4の実機検証＋C++再ビルド＋DX12スモーク）、`build/W04-v2-refresh-v1`（修正後コードでの完全refresh代表1回）、`build/scenarios/w04-v2-review-fix-test`（実機検証で保存した名前付き案）・`-tampered`（改ざん検証用、削除せず残置）。いずれも`.gitignore`対象で未コミットです。

## 残ること

- 床・天井のレベル（階）一致チェック（R5）は、現在room-1f-06（1階）しか登録がないため、異なる階の部材と誤って対応付けられるケースそのものは実データで再現・検証できていません（コードレビューレベルの防御的対応です）。
- 共有壁を両室とも登録した場合の一般化されたcap所有の扱い（W04-v1レビューの「非阻害の将来注意」）は今回も対応していません（施主指定通り、他室登録へ広げる段階の課題として残します）。
- C++（`Walkthrough.cpp`）側のsurfaceOverrides検証ロジック（型不正・未知ID・別部屋・no-surfaceの拒否）は、Python版と同じ判定をコードレベルで実装し、ビルド成功と「有効な上書きを誤って拒否しない」という正常系は実機（DX12）で確認済みですが、異常系（例えば未知IDを含む保存データを実際に内覧へ読み込ませて拒否させる）そのものは実機で再現していません。ロジックがPython版と1対1で対応していること、Python版はunittestと実UEエディタの両方で異常系を確認済みであることから、今回の確認範囲としています。
- レイクリックによる面選択（仕様上は任意）は未実装のままです。
- W05へは着手していません。

## 再現・復旧

```powershell
# R1: Blenderのreference variant、パターン保持・上書き色反映の確認
python scripts/build-visual-twin.py --interior --output build/<新規ディレクトリ> --variant reference
python scripts/build-visual-twin.py --interior --output build/<新規ディレクトリ2> --state build/W04-diag/state-reference-floor-green.json
# 各interior.blendを開き、Surf_floor_surf-guest-floor-001のBrick TextureノードのColor1/2を比較

# R5: 生成メッシュの面別マテリアルスロット確認（Blender --background）
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --background --factory-startup --python <確認スクリプト> -- build/<パッケージ>/interior.blend

# UEフル生成→C++ウォークスルー再ビルド→DX12スモーク
python scripts/build-unreal-study.py --blender 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --engine 'C:/Program Files/Epic Games/UE_5.8' --cache '../../ddc' --package build/<パッケージ> --output build/<UEプロジェクト>
python scripts/enable-unreal-walkthrough.py --project build/<UEプロジェクト> --engine 'C:/Program Files/Epic Games/UE_5.8' --cache '../../ddc'
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/<UEプロジェクト> --cache '../../ddc' --smoke

# 名前付き案を使った完全refresh（Blender→UE→ウォークスルー確認まで一括、修正後コード）
python scripts/refresh-visual-study.py --previous build/W04-v2-ue-v1 --scenario build/scenarios/w04-v2-review-fix-test --output build/<新規ディレクトリ> --cache '../../ddc'

# テスト・回帰
python -m pytest tests/ -q
node scripts/build-web-data.mjs --check
python tests/validate_house.py
```

全ログ・成果物はv1報告記載の各ディレクトリに加え、`build/W04-v2-package-v1/`・`build/W04-v2-package-reference-v1/`・`build/W04-v2-package-reference-override-v1/`・`build/W04-v2-ue-v1/`・`build/W04-v2-refresh-v1/`配下にあります。
