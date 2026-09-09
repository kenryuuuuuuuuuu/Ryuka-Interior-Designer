# W05 実装報告

状態：READY_FOR_REVIEW
開始BASE（完全SHA）：`b478a9f4bf85cd309ea1e446a9d9cbae6b91cb39`
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境：Windows 11 Pro 10.0.26200 / UE 5.8.2 / Blender 5.2.0 LTS。変更した設定なし。

## 結果

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
- 主な変更：
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

## 残ること

- **実敷地確認待ち**：以下は未確認・未入力のままで、今回の検証はすべて仮の合成値によるものです。
  - 実際の緯度経度（施主所在地の測量値または信頼できる地図座標）
  - 真北の実測・図面確認（`planNorthAzimuthDeg`の根拠資料）
  - 隣棟・塀の実寸法・位置（`site-context.json`のbox形状の根拠。現状は`build/W04-diag/site-context-v3-test.json`という架空のフィクスチャのみ）
  - 採用予定の窓・ガラス・外壁仕上げの品番・仕様（現在の窓・庇・屋根・ガラスは正本の形状はあるが、断熱ガラスの透過率・実際の建材反射率などは未校正の仮設定のまま）
- 定量照度（lux実測値との対応）・実天候の校正は対象外のまま（仕様どおり、W06以降）。
- 窓・庇・屋根・ガラスの棚卸し：ゲストLDKの主要開口・庇はshape/正本ありで生成対応済み。屋根全体の形状作り直しや新しいガラス透過モデルは今回不要と判断（日影を妨げる明白な欠落は見つからず）。ガラスの影・透過は既存の簡易近似のまま（現実の透過率は保証しない、仕様どおり明記）。
- `verify_w05.py`実行中に一度だけ`end_daylight_compare()`直後の角度が厳密一致でないケースがあったが（浮動小数点差、太陽アクターの3D回転往復に起因）、同じ入力でのクリーンな再実行ではビット単位で一致することを確認済み。`end_daylight_compare()`自体はW04の`end_compare()`と同じ復元パターンを使っており、コード変更は行っていない。
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

全ログ・成果物は上記各`build/`ディレクトリにあります（すべて`.gitignore`対象）。
