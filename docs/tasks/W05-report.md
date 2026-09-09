# W05 実装報告

状態：READY_FOR_REVIEW（v2、W05-v1レビューのR1/R2対応）
開始BASE（完全SHA）：`b478a9f4bf85cd309ea1e446a9d9cbae6b91cb39`（維持）
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境：Windows 11 Pro 10.0.26200 / UE 5.8.2 / Blender 5.2.0 LTS。変更した設定なし。

## 結果（v2時点）

**[W05-v1レビュー](W05-review.md)（対象`a27b62a`、CHANGES_REQUESTED）のR1・R2をすべて同じW05内で修正しました**（この報告のv2）。各項目の対応は以下の通りです。

| 項目 | v1までの状態 | v2での対応 |
|---|---|---|
| R1（現在の敷地と実際の太陽状態の一致を確認する） | `cases_match_site()`は日時ケースの`siteSHA256`と敷地ハッシュの一致だけを見ており、①敷地を切り替えても古い日時ケースの適用（`set_sun_case()`）・日時比較（`start_daylight_compare()`）が止まらない、②敷地変更後に`recompute_sun_cases()`で一覧を再計算しても、現在シーンの`solar`（適用中の日時来歴）が古いまま`save()`が成功する、③同じ`siteSHA256`のまま角度だけ改変されたケースを検出できない、という3点が抜けていた。 | `solar_position.py`に`case_matches_site(case, site)`を追加（`siteSHA256`の一致に加え、`make_case()`で同じ`localTimestamp`を敷地から再計算した角度との一致も確認）し、`cases_match_site()`はこれを内部で使うよう変更（シグネチャ・呼び出し側は不変）。`study_controls.py`に共通ヘルパー`_verify_case_site()`を追加し、`set_sun_case()`・`start_daylight_compare()`の両方が適用前にこれで現在の敷地との一致を確認（敷地原本の無い旧ケースは従来通り素通り）。`save()`は、現在の`solar`が現在の敷地と一致しない場合に保存そのものを拒否するよう変更（`scene_state()`/`current_state()`自体は変更せず、単に現在状態を読むだけの経路は壊さない）。`scripts/refresh_inputs.py`の`retained_inputs()`/`scenario_inputs()`、`scripts/build-unreal-study.py`の`--state`/`--site`も同じ`case_matches_site()`で状態の`solar`を敷地と照合するよう追加。「採光」「日時比較」メニューの一覧も、敷地と不一致なケースを適用不可として示す／一覧から除外するよう更新。 |
| R2（名前付き案の読込でsiteと日時一覧も一緒に採用する） | `load_scenario()`は`scenario_inputs()`が返す入力一式のうち`state`しか採用しておらず、別の敷地で保存した案を読み込んでも現在プロジェクトの`site.local.json`/`sun-cases.json`がそのまま残り、その後の日時変更・再保存で案とは無関係な敷地/一覧が混ざり得た。 | `load_scenario()`を、`_validate_applicable()`の検証が全て通った**後**（検証失敗時は何も書き換えない）、案が`site`/`sunCases`を持てばそれぞれ`site.local.json`/`sun-cases.json`へ書き込み、持たなければ現在のプロジェクトのそれらを削除する（「原本なし」へ戻す）よう変更。W04の仕上げA/B（`start_compare()`、`_load_scenario_state()`を引き続き使用）は対象外のまま：視点・太陽・露出を固定し仕上げだけを切り替えるモードのため、レビュー自身が「モード間の意味を維持」と明記した通り、敷地/日時ケースを切り替える必要がない。 |

| 条件ID | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| R1代表検証（site A→Bへ変更し、旧ケースの適用/比較が止まること。Bで再計算した後もAのstateを保存できないこと、Bの日時を適用すれば保存/refresh可能なことを1つの流れで確認。角度不一致は純Python） | PASS | 実UEエディタ実行（`build/W05-ue-v1/w05-v2-verification.json`）：site A基準で日時を適用・保存後、site Bへ切替 → 旧A基準ケースの`set_sun_case()`（`stale_case_apply_raises: true`）・`start_daylight_compare()`（`stale_compare_raises: true`、`no_compare_started_after_stale_rejection: true`）がいずれも拒否されることを確認。`recompute_sun_cases()`でケース一覧をBへ更新した直後（シーンの`solar`はまだA）に`save()`を試みると拒否（`stale_state_save_after_recompute_raises: true`）、B基準ケースを`set_sun_case()`で適用してからの`save()`は成功（`post_fix_save_succeeded: true`、`post_fix_saved_solar_b`が新しい日時と一致）。角度不一致の純Python例は`tests/test_solar_position.py::test_case_matches_site_detects_tampered_angle`（`siteSHA256`はそのまま、`elevationDeg`だけ改変したケースを`case_matches_site()`/`cases_match_site()`が偽と判定）。終了コード0。 |
| R2代表検証（異なるsiteと日時一覧を持つ2案を同じcontext条件で用意し、Bの読込後はUIの敷地・ケース・solarがBで揃い、保存し直した案にもBが入ること） | PASS | 同実行内：同一context（`site-context.json`）のまま、site A案（`w05-v2-r2-site-x`）とsite B案（`w05-v2-r2-site-y`）を保存し、Y読込後に`current_site()`（`after_load_y_site`）・`_sun_cases_status_text()`（`after_load_y_cases_status`＝「現在の敷地と一致」）・`current_state().solar`（`after_load_y_solar`）のすべてがBで揃うことを確認。Yの状態のまま再保存した`w05-v2-r2-site-y-resaved`の`site.local.json`もBと一致（`resaved_scenario_has_site_y: true`）。 |
| 修正後の完全refresh 1回（R2で読込・再保存した案から） | PASS | `build/scenarios/w05-v2-r2-site-y-resaved`（site B・B基準の`sun-cases.json`・状態・周辺条件を同梱）を`refresh-visual-study.py --previous build/W05-ue-v1 --scenario ... --output build/W05-v2-refresh-v1`で完全refresh。`refresh.json`は7工程すべて`complete`、`stateVerification`が`statePreserved: true`/`geometryVerified: true`/`cameraRotationPreserved: true`。`unrealVerification.comparisonState.solar.siteSHA256`と`ue/site.local.json`がいずれもsite Bと一致することを確認。終了コード0。 |
| 関連テスト・回帰 | PASS | `python -m pytest tests/`：125 passed, 35 subtests passed（v1の122+3件から、R1のタンパリング検知1件・retained_inputs/scenario_inputsのstate.solar不一致拒否2件を追加）。`node scripts/build-web-data.mjs --check`成功。`python tests/validate_house.py`：33室・35壁（変更なし）。 |

v1で提出したAC1〜AC4（section 6の代表検証）はコード変更が直接及ぶ範囲ではなく（R1/R2はいずれも敷地/日時ケースの整合性確認の追加で、日時比較そのものの撮影・保存経路は変更していない）、上記R1/R2代表検証と完全refreshの再実行で該当パスの健全性を再確認しています。個別の再検証はレビューの指示通り実施していません（「多数の季節画像やW04の再検証一式は不要です」）。v1報告のAC1〜AC4の内容は変更ありません（下記に維持）。

## 結果（v1、変更なし）

ゲストLDK（room-1f-06）で、UEエディタからローカル敷地情報（緯度経度・真北・確度、`site.local.json`）を読み込み・新規作成し、既存の太陽計算（`noaa-meeus-geometric-v1`）で日時ケースを追加・季節代表日を一括生成できるようにしました。仕上げ・視点・露出・光源強度・周辺条件を固定したまま日時だけを切り替える新しい「日時比較」A/Bを追加し、比較開始前に両案の面参照・周辺条件の適合を検証してから初めてシーンへ適用する仕組み（既存の`_context_compatible`と面上書き参照確認を統合した共通関数）にしました。この共通適用前検証は、W04-v1レビューで指摘された「A/B両案の面参照事前確認」の不足も合わせて解消しています。

実装の過程で、Blenderの生成が`--state`引数の太陽角度（`azimuthDeg`/`elevationDeg`）を実際には反映しておらず、常に既定値または`--elevation`だけを使っていた不具合を発見し修正しました（UEだけ日時条件が反映され、Blender側は反映されていない、という不整合を解消）。`site.local.json`は名前付き案の保存・一覧・読込・完全refreshに他の入力と同様に同梱され、旧来の敷地情報を持たない案は引き続き有効です（同梱するsite/日時ケースが揃った場合のみ、対応を厳密照合）。

**実敷地の緯度経度・真北・隣棟寸法・採用建材の仕様はまだ確認できていません。** 今回の検証はすべて仮の合成敷地情報（`build/W05-diag/site-sample-a.json`ほか、実座標ではない架空値）で行った「機能確認済み（仮条件）」であり、「実敷地確認済み」ではありません。必要な情報は「残ること」に記載します。

| 条件ID | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| AC1（2日時を選び、視点・画角・露出・sunLux・面別設定が不変で日差しだけ変わることを実DX12画像2枚と条件記録で確認。代表日時の角度を既存参照値で照合） | PASS | `build/W05-daylight-gallery-v1/`（`compare-unreal-daylight.py --sun-cases 0 1`。同一UEプロジェクト・同一finish/camera/exposure/sunLux/siteContextで`case-0.png`（2026-03-21T09:00 JST、az122.6°/el37.2°）と`case-1.png`（2026-03-21T12:00 JST、az185.0°/el54.5°）を撮影。`comparison.json`に両者の`variant`/`surfaceOverrides`/`camera`/`sunLux`/`exposureEV100`/`roomId`/`siteContextSHA256`が同一であることを記録。画像を目視確認し、窓越しの日差しの角度・範囲が明確に異なることを確認）。角度の照合は`tests/test_solar_position.py::test_independent_spa_reference`（NREL TP-560-34302 Appendix A.5のSPA参照値、独立実装との0.05°以内一致）を再利用。終了コード0。 |
| AC2（主要な遮蔽boxの有無で影が変わる代表例。実資料なしなら架空明記） | PASS（架空の検証物、実資料なし） | `build/W05-shadow-nocontext/`（`--site`のみ、`--context`なし）と`build/W05-shadow-withcontext/`（同一`--state`/`--site`/`--sun-cases`に加え、架空の隣棟box `build/W04-diag/site-context-v3-test.json`を`--context`で追加）を同一Blenderパッケージ（`build/W05-package-v1`）から生成。boxはbuild東側20mに位置するため、まず西寄りの日差し（`--sun-case 5`）で比較したところ差はほぼ無く（目視差なし、ピクセル差分の最大18/255・0.001%）、box位置と無関係な日差しでは遮蔽が効かないことをまず確認した。次に、boxとほぼ同方位（真東寄り）かつ低仰角の日差し条件（`make_case`で追加生成した2026-03-21T06:30 JST、az95.99°/el8.48°、`sun-case`索引12）で同条件比較したところ、`shadow-nocontext-lowsun.png`/`shadow-withcontext-lowsun.png`間で天井・壁面の間接照度が明確に暗くなる差を目視確認し、ピクセル差分でも851px（全体の0.06%）が10/255超・最大66/255の差を示した（`build/W05-shadow-capture-both-3.log`）。周辺条件box（遮蔽物）の有無・位置関係が実際にシーンの日差しへ反映されることを確認。 |
| AC3（名前付き案保存→再読込→`--scenario`の完全refreshを1回通し、site/solar/context/面別仕上げの対応を確認。内覧保存復帰は代表1回） | PASS | `build/scenarios/w05-final-refresh-test-v2/`（`study-state.json`/`sun-cases.json`/`site.local.json`/`site-context.json`の4ファイルを同梱）を`build/W05-ue-v1`から保存し、`refresh-visual-study.py --previous build/W05-ue-v1 --scenario build/scenarios/w05-final-refresh-test-v2 --output build/W05-refresh-v2`で完全refreshを実行。`build/W05-refresh-v2/refresh.json`は7工程すべて`complete`、`stateVerification`が`statePreserved: true`/`geometryVerified: true`/`cameraRotationPreserved: true`、`unrealVerification.comparisonState.solar.localTimestamp`・`siteContextSHA256`・`camera`が保存案と一致することを確認。内覧の保存復帰（F5/F9でsolarと面別仕上げを保持）は`build/W05-ue-v1/w05-verification.json`の`saved_solar_localTimestamp`（日時比較適用後に`save()`し、`current_state().solar.localTimestamp`が一致）で代表1回確認。終了コード0。 |
| AC4（site/ケース不一致または必須入力不足を1例、範囲外時刻を1例。元の案は変更せず通常条件へ復旧可能） | PASS | `build/W05-ue-v1/w05-verification.json`：①敷地不一致例＝site Bへ読替後`status_after_load_b`が「日時ケース：12件（現在の敷地と不一致・再計算が必要）」と案内し、再計算（`recompute_sun_cases()`）後は「一致」に復旧、元のsite Aへ戻して再計算すれば通常条件へ完全復旧（`status_after_reload_a`で確認）。②範囲外（夜間）時刻例＝2026-08-15T02:00 JSTを追加すると`night_case_usable: false`かつ`night_case_reason_present: true`で一覧には残り、`set_sun_case()`・`start_daylight_compare()`はいずれも`ValueError`/`RuntimeError`で適用を拒否し（`night_case_apply_raises: true`、`compare_with_night_case_raises: true`）、拒否後も`_daylight_compare`は`None`のまま（`no_compare_started_after_rejection: true`）で半端な状態を残さない。いずれも既存案・シーンは変更されず、通常の日時ケース（idx0/1）でのA/B比較・保存は同じ実行内で問題なく成功。 |
| 回帰 | PASS | `python -m pytest tests/`：122 passed, 35 subtests passed（新規3件`tests/test_solar_position.py`、1件`tests/test_refresh_study.py`、1件`tests/test_study_scenarios.py`を含む）。`node scripts/build-web-data.mjs --check`成功。`python tests/validate_house.py`：33室・35壁（変更なし）。 |

## 変更と判断

- 目的：既存の太陽計算・周辺遮蔽・保存/refresh基盤を再利用し、ローカル敷地情報の入力・根拠確認、日時選択による日差し変更、固定条件下での日時A/B比較、比較条件の保存・内覧・再生成への引き継ぎを追加すること。
- v2で追加した変更（R1/R2対応）：
  - `unreal/solar_position.py`：`case_matches_site(case, site)`を追加（`siteSHA256`一致＋`make_case()`による角度再計算一致の両方を確認）。`cases_match_site()`は内部でこれを使うよう変更（シグネチャ不変）。
  - `unreal/study_controls.py`：`_verify_case_site(case, label)`を追加し`set_sun_case()`/`start_daylight_compare()`から呼び出し。`save()`に、現在の`solar`が現在の敷地と一致しない場合の保存拒否チェックを追加。`load_scenario()`を、`scenario_inputs()`の`site`/`sunCases`パスも含めて一組として採用する実装へ変更（検証成功後にのみファイルを書き換え、案に無ければ現在のものを削除）。「採光」「日時比較」メニューの一覧表示に敷地不一致の案内・除外を追加。
  - `scripts/refresh_inputs.py`：`retained_inputs()`/`scenario_inputs()`に、`site`が存在する場合の`state['solar']`と`case_matches_site()`による照合を追加（既存の`cases_match_site()`によるsun-cases側の照合とは別に、状態自体の`solar`も確認）。
  - `scripts/build-unreal-study.py`：`--state`の`solar`と`--site`の`case_matches_site()`照合を追加。
  - `tests/test_solar_position.py`・`tests/test_refresh_study.py`・`tests/test_study_scenarios.py`：R1のタンパリング検知・state.solar不一致拒否の代表テストを追加（計3件）。
- 主な変更（v1）：
  - `unreal/solar_position.py`：`site_sha256()`（`make_case()`から抽出、敷地の意味上のハッシュを一元化）、`cases_match_site()`、`SEASON_REFERENCE_DATES`/`SEASON_REFERENCE_HOURS`/`season_reference_timestamps()`（3/21・6/21・9/21・12/21の9/12/15時、暦上の代表日と明記）を追加。
  - `unreal/study_controls.py`：敷地の読込・新規作成・状態表示（`load_site`/`create_site_input`/`_site_status_text`ほか）、日時ケースの追加・季節一括追加・再計算・状態表示（`add_datetime_case`/`add_season_cases`/`recompute_sun_cases`/`_sun_cases_status_text`ほか）、新しい日時比較A/B（`start_daylight_compare`/`show_daylight_compare_*`/`end_daylight_compare`/`pick_daylight_compare_*`）を追加。W04の面参照検証と周辺条件検証を統合した共通の適用前検証`_validate_applicable()`を新設し、`load_scenario()`/`start_compare()`（W04の仕上げA/B）も同じ関数で検証するよう変更（W04-v1レビューの非阻害残件に対応）。UEメニューに「採光」「日時比較」の2サブメニューを追加。
  - `blender/build_interior.py`：`setup_lighting()`が`--state`の`azimuthDeg`/`elevationDeg`を全く読んでいなかった不具合を修正（`state`引数を追加し、指定があれば`--elevation`より優先して反映）。
  - `unreal/walkthrough/Source/RyukaInterior/Walkthrough.h`/`.cpp`：HUDに「太陽条件：」表示行を追加（`CurrentSolarLabel()`。日時由来か手動角度かを表示し、日時由来の場合は確度も表示）。
  - `scripts/plan-sun-study.py`：`--season YEAR`オプションを追加（`--times`と排他）。
  - `scripts/refresh_inputs.py`：`ALLOWED_SCENARIO_FILES`に`site.local.json`を追加。`retained_inputs()`/`scenario_inputs()`は、site単体の欠落は許容しつつ、site+日時ケースが揃った場合のみ`cases_match_site()`で対応を検証するよう変更。
  - `scripts/build-unreal-study.py`：`--site`引数を追加（`--sun-cases`と組の場合は対応を検証してから`output/site.local.json`へコピー）。
  - `scripts/refresh-visual-study.py`：`03-unreal`工程のコマンド構築に`site`→`--site`の転送を追加。
  - 新規`scripts/compare-unreal-daylight.py`：仕上げ・視点・露出を固定したまま複数日時だけを撮影する専用ギャラリー生成（既存`compare-unreal-studies.py`は`--variant`必須で仕上げ×日時の積を撮る設計のため、日時固定比較には別スクリプトとした）。
- 設計からの差異：なし（仕様どおり既存機構の拡張として実装）。
- 追加依存：なし。環境変更：なし。
- 未追跡/ignored成果物（`build/`配下、すべて`.gitignore`対象）：
  - `build/W05-diag/`：合成の敷地フィクスチャ（`site-sample-a.json`/`-b.json`）、季節日時ケース（`sun-cases-a.json`）、Blender修正確認用状態（`state-daylight-case5.json`）、editor経由で作成した敷地ファイル（`site-created-by-editor.json`）
  - `build/W05-package-v1`/`build/W05-package-base-v1`：Blenderの太陽角度反映バグ修正の確認（`--state`ありなしでの`study.json.lighting`比較）
  - `build/W05-ue-v1`：`--site`/`--sun-cases`/`--context`付きUEインポート、`verify_w05.py`実行、`w05-verification.json`、C++再ビルド、DX12スモーク（`Saved/walkthrough-smoke.png`）
  - `build/W05-shadow-nocontext`/`build/W05-shadow-withcontext`：周辺条件の有無だけを変えた同条件比較（AC2証拠）
  - `build/W05-daylight-gallery-v1`：`compare-unreal-daylight.py`による日時固定比較の実撮影（AC1証拠）
  - `build/scenarios/w05-final-refresh-test-v2`：完全refresh確認用の名前付き案
  - `build/W05-refresh-v2`：修正後コードでの完全refresh代表1回（AC3証拠）
  - `build/W05-ue-v1/verify_w05_v2.py`・`w05-v2-verification.json`：R1/R2代表検証の実UEエディタ実行結果
  - `build/scenarios/w05-v2-r2-site-x`／`-y`／`-y-resaved`：R2検証用の異なる敷地を持つ名前付き案（同一context）
  - `build/W05-v2-refresh-v1`：R2で読込・再保存した案からの完全refresh代表1回

## 残ること

- **実敷地確認待ち**：以下は未確認・未入力のままで、今回の検証はすべて仮の合成値によるものです。
  - 実際の緯度経度（施主所在地の測量値または信頼できる地図座標）
  - 真北の実測・図面確認（`planNorthAzimuthDeg`の根拠資料）
  - 隣棟・塀の実寸法・位置（`site-context.json`のbox形状の根拠。現状は`build/W04-diag/site-context-v3-test.json`という架空のフィクスチャのみ）
  - 採用予定の窓・ガラス・外壁仕上げの品番・仕様（現在の窓・庇・屋根・ガラスは正本の形状はあるが、断熱ガラスの透過率・実際の建材反射率などは未校正の仮設定のまま）
- 定量照度（lux実測値との対応）・実天候の校正は対象外のまま（仕様どおり、W06以降）。
- 窓・庇・屋根・ガラスの棚卸し：ゲストLDKの主要開口・庇はshape/正本ありで生成対応済み。屋根全体の形状作り直しや新しいガラス透過モデルは今回不要と判断（日影を妨げる明白な欠落は見つからず）。ガラスの影・透過は既存の簡易近似のまま（現実の透過率は保証しない、仕様どおり明記）。
- `verify_w05.py`実行中に一度だけ`end_daylight_compare()`直後の角度が厳密一致でないケースがあったが（浮動小数点差、太陽アクターの3D回転往復に起因）、同じ入力でのクリーンな再実行ではビット単位で一致することを確認済み。`end_daylight_compare()`自体はW04の`end_compare()`と同じ復元パターンを使っており、コード変更は行っていない。
- R1の修正は「敷地が現在設定されている場合」の照合であり、敷地原本を持たない旧来のsun-cases/状態はこれまで通り検証対象外です（仕様上の要件どおり）。
- W04の仕上げA/B（`start_compare()`）はR2の対象外のままです（意図的。レビュー自身が確認済み）。
- 共有壁の両室登録・全館状態・別階への展開は計画通りW07・W08の範囲。
- W06（夜間照明）には着手していません。

## 再現・復旧

```powershell
# ローカル敷地情報の作成・日時ケース追加・日時比較・不一致/範囲外の確認（実UEエディタ、対話プロンプトはモックで代入）
python scripts/enable-unreal-walkthrough.py --project build/W05-ue-v1 --engine 'C:/Program Files/Epic Games/UE_5.8' --cache '../../ddc'
# build/W05-ue-v1/verify_w05.py をUEエディタのPythonコンソール/起動引数で実行し、w05-verification.json を確認

# Blender側の太陽角度反映バグ修正の確認（--state ありなしの比較）
python scripts/build-visual-twin.py --interior --output build/<新規ディレクトリ> --state build/W05-diag/state-daylight-case5.json
# study.json の lighting.azimuthDeg/elevationDeg が既定値(155/30)ではなく状態の値(267.9/45.9)と一致することを確認

# 日時固定の実撮影比較（AC1）
python scripts/compare-unreal-daylight.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W05-ue-v1 --cache '../../ddc' --output build/<新規ディレクトリ> --sun-cases 0 1

# 周辺条件の有無だけを変えた比較（AC2）
python scripts/build-unreal-study.py --engine 'C:/Program Files/Epic Games/UE_5.8' --package build/W05-package-v1 --output build/<新規A> --cache '../../ddc' --state build/W05-diag/state-daylight-case5.json --sun-cases build/W05-diag/sun-cases-a.json --site build/W05-diag/site-sample-a.json
python scripts/build-unreal-study.py --engine 'C:/Program Files/Epic Games/UE_5.8' --package build/W05-package-v1 --output build/<新規B> --cache '../../ddc' --state build/W05-diag/state-daylight-case5.json --sun-cases build/W05-diag/sun-cases-a.json --site build/W05-diag/site-sample-a.json --context build/W04-diag/site-context-v3-test.json
python scripts/capture-unreal-study.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/<新規A> --cache '../../ddc' --sun-case 5
python scripts/capture-unreal-study.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/<新規B> --cache '../../ddc' --sun-case 5

# 名前付き案の保存・完全refresh（AC3）
python scripts/save-study-scenario.py --project build/W05-ue-v1 --name '<名前>' --note '<メモ>' --output build/scenarios/<新規案>
python scripts/refresh-visual-study.py --previous build/W05-ue-v1 --scenario build/scenarios/<新規案> --output build/<新規ディレクトリ> --cache '../../ddc'

# テスト・回帰
python -m pytest tests/ -q
node scripts/build-web-data.mjs --check
python tests/validate_house.py
```

```powershell
# v2（R1/R2）代表検証：site A→B切替での旧ケース拒否・再計算後の保存拒否・修正後の保存成功、
# および名前付き案の敷地/日時ケース一括採用（実UEエディタ、対話プロンプトはモックで代入）
# build/W05-ue-v1/verify_w05_v2.py をUEエディタのPythonコンソール/起動引数で実行し、w05-v2-verification.json を確認

# R2で読込・再保存した案からの完全refresh
python scripts/refresh-visual-study.py --previous build/W05-ue-v1 --scenario build/scenarios/w05-v2-r2-site-y-resaved --output build/<新規ディレクトリ> --cache '../../ddc'

# テスト・回帰（v2）
python -m pytest tests/ -q
node scripts/build-web-data.mjs --check
python tests/validate_house.py
```

全ログ・成果物は上記各`build/`ディレクトリにあります（すべて`.gitignore`対象）。
