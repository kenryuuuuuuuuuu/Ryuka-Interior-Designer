# W06 実装報告

状態：READY_FOR_REVIEW（v2、W06-v1レビューのR1〜R5対応）
開始BASE（完全SHA）：`d4fabb229a2b53e2478486e3913f4dd4563fbbbf`（維持）
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境：Windows 11 Pro 10.0.26200 / UE 5.8.2 / Blender 5.2.0 LTS。変更した設定なし。

## 結果（v2時点）

**[W06-v1レビュー](W06-review.md)（対象`81b3ddf`、CHANGES_REQUESTED）のR1〜R5をすべて同じW06内で修正しました**（この報告のv2）。v1報告のAC1〜5は「全AC PASS」としていましたが、実際にはR1（Web側の取付け高さが未反映）・R2（発光方向が水平だった）という2件の実バグが残った状態でのPASS表記であり、レビュー指摘の通り実態と合っていませんでした。各項目の対応は以下の通りです。

| 項目 | v1までの状態 | v2での対応 |
|---|---|---|
| R1（Web/Blenderの取付け高さ不整合） | `interior-white-model.html`側の天井付け照明のY座標・高さ編集（`electricalGroupY()`、XYZパネル、既定値リセット）が、Blenderの`ceiling_y()`で使っている勾配天井の実際の高さではなく、平坦既定値`CEIL_H`のまま計算していた。`elec-201`（`mountHeightOverride=1.9`）で試算するとWeb側y=1.207mに対しBlender側y=2.103m（差0.896m）という実害あるずれを確認。加えて`ceiling_height_at()`は対応するピースが1件も無い場合に黙って平坦既定値へ逃げており、勾配天井の部屋でのデータ不備を検出できなかった。 | 4箇所（`electricalGroupY()`、XYZパネルの表示・逆変換、既定値リセット）すべてを、Blenderと同じ考え方の`slopedCeilingHeightAt(eff.x, eff.z)`で解決するよう修正。Node.jsで`slopedCeilingHeightAt()`相当を再実装し、`baseY(fl1)+slopedCeilingHeightAt(x,z)-mountHeight`がBlenderの`ceiling_height_at(...)-mountHeight`と厳密一致することを室-1f-06の3器具すべてで数値確認。`ceiling_height_at()`は部屋の`ceiling`が`sloped`でなければ即座に平坦既定値を返し（探索不要な通常の平天井）、`sloped`の部屋だけその部屋自身のピースへの一致を必須にして、一致しない場合は`ValueError`にするよう区別を追加。 |
| R2（天井付け発光方向の誤り・二重メッシュ） | `data/visual/lighting-settings.json`の天井付け`directionLocal`が`[0,0,-1]`（水平・南向き）になっており、鉛直下向きの`[0,-1,0]`ではなかった。加えてBlender側の器具ランプ回転が太陽光用の「太陽へ向かう方向を反転する」ロジックを誤って流用しており、器具の発光方向ベクトル（すでに照射方向そのもの）を余計に反転していた。また`positionM.y`（器具の取付け原点＝上端）へそのまま光源を置いており、天井裏／器具本体へ光源が埋まる恐れがあった。`unreal/import_study.py`はBlenderのGLBに既に含まれる器具メッシュとは別に、同じ位置へプレースホルダー円柱を二重生成していた。 | `lighting-settings.json`の天井付け3型すべてを`[0,-1,0]`へ修正（壁付け`light-bracket`の`[0,0,1]`は元々正しいため変更なし）。Blender側のランプ回転から不要な反転を削除。新設`emitPositionM`（器具下端）を`resolve_mount()`/`build_lighting_bindings()`で算出し、UE側の光源は`positionM`ではなく`emitPositionM`へ配置。器具メッシュは`positionM.y`から下向きに生成するよう修正（従来は上向きに生成し天井裏へ食い込んでいた）。`import_study.py`のプレースホルダー円柱生成を削除（Blenderが生成した器具メッシュがGLB経由で既にシーンへ含まれるため）。 |
| R3（夜間でも太陽光が消えない） | `blender/build_interior.py`の`setup_lighting()`が`--state`の`lighting.mode`を一切見ておらず、夜間状態でBlenderレンダリングしても常に昼光（Sun/World strength）がフルで適用されていた。 | `state.lighting.mode=='night'`のとき、Sunの`energy`とWorld背景の`Strength`を0にするよう修正。 |
| R4（Blender前チェック・変更検出の不足） | `build_lighting_bindings()`の解決はBlender起動後（`build_interior.py`内）でしか行われず、`--state`の未知器具IDもBlenderが動き出してから発覚した。`refresh_inputs.py`にも照明の参照検証が無かった。`study_controls._target_fixture_ids()`はグループの不明メンバーを警告なしで黙って除外していた。`source_changes.py`の変更検出は`lighting-settings.json`（プロファイル/グループ）を対象にしていなかった。 | `scripts/build-visual-twin.py`にBlender起動前の照明解決プリフライトを追加（`--state`の未知器具IDもここで拒否）。`refresh_inputs.py`の`retained_inputs()`/`scenario_inputs()`双方に同種の検証を追加。`_target_fixture_ids()`はグループの不明メンバーがあれば都度`unreal.log()`で警告するよう修正（既知メンバーのみで処理は継続）。`source_changes.py`の`TARGETS`へ`lightingProfiles`/`lightingGroups`を追加し、rooms/furniture/catalogと同じ浅いキー単位差分をHTML/summaryへ表示（`data/electrical.json`本体の全項目差分は対象外のまま、レビューの明示的な了承通り）。 |
| R5（照明A/Bの日時保持漏れ・排他制御なし） | `show_lighting_compare()`が`solar`（日時来歴）を`fixed`に含めずに毎回`pop`しており、日時由来の状態から照明A/Bを開始すると日時来歴が消えていた（数値の太陽角度自体は保持されていたが、由来の表示が失われる）。3種のA/B（仕上げ/日時/照明）に相互排他が無く、比較中でも通常の照明編集（昼夜切替・ON/OFF・調光・色温度・リセット）がそのまま通ってしまっていた。選択中の照明の表示はIDのみで、調光・色温度プロンプトは常に固定既定値（'1'/'2700'）だった。 | `start_lighting_compare()`が`base.get('solar')`があれば`fixed['solar']`へ含め、`show_lighting_compare()`は`fixed`に`solar`がある場合だけ`pop`しないよう修正。新設`_active_compare_label()`/`_require_no_active_compare()`で、3種いずれかの比較中は新規の比較開始（同種でも）と通常の照明編集（昼夜切替・ON/OFF・調光/色温度変更・リセット）を拒否するよう統一。新設`_selected_lighting_effective()`で現在の実効on/dimming/色温度（グループは不一致時「混在」）を算出し、選択中照明のステータス表示・調光/色温度プロンプトの既定値に反映。 |

| 項目 | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| R1/R2代表検証（Web/Blender座標一致、下向きベクトル、器具メッシュ上下端の単体テスト） | PASS | `tests/test_electrical_assets.py`（14件、新規2件含む）：`ceiling_height_at()`の平坦部屋は探索なしで既定値、勾配天井部屋の未解決点は`ValueError`。`resolve_mount()`の`emitPositionM`が壁付けは`positionM`と同一、天井付けは`positionM.y-height`と一致。`build_lighting_bindings()`が`directionVector=[0,-1,0]`（旧テストの誤った期待値`[0,0,-1]`を修正）。`tests/test_lighting.py`（16件）：`emitPositionM`の型・範囲検証を追加。 |
| R1/R2実行確認（実Blender/UE） | PASS | `build/W06-v2-night-diag/interior.png`・`build/W06-v2-day-diag/interior.png`：修正版Blenderで夜間/昼間を実レンダリングし、夜間は窓が完全暗転（太陽光の漏れなし）、ペンダントの吊り棒がシェード上端から下へ正しく伸び、下向きの暖色照射が視認できることを目視確認。完全refresh後の`build/W06-v2-refresh-v1/ue/lighting-bindings.json`：3器具すべて`directionVector=[0.0,-1,0.0]`、`emitPositionM.y`が`positionM.y`より低いことを確認。同プロジェクトの実UEエディタ実行（`verify_w06_v2.py`→`w06-v2-verification.json`）：器具アクターが`Light_elec-008/200/201`の3つのみ（`no_duplicate_placeholder_mesh: true`）、ダウンライト（`elec-200`、spot）の前方ベクトルが`[0,0,-1]`で鉛直下向き（`elec_200_points_down: true`）を確認。 |
| R3代表検証（Blenderの夜間SUN/World設定） | PASS | 上記`build/W06-v2-night-diag`は`setup_lighting()`のnight分岐（Sun/World strength=0）を経由して生成しており、レンダリング結果自体が確認そのもの。`build/W06-v2-day-diag`は同一パイプラインでday分岐（変更なし）が従来通りであることの回帰確認。 |
| R4代表検証（Blender前の未知器具ID拒否・変更検出） | PASS | `python scripts/build-visual-twin.py ... --state build/W06-diag-unknown-fixture-state.json`：Blenderプロセスが1つも起動せず、出力ディレクトリも作られない時点で`error: lighting.fixtures references unknown fixture id(s): elec-does-not-exist`を確認。`tests/test_refresh_study.py`・`tests/test_study_scenarios.py`に、保存済み状態の器具IDを事後に不正な値へ書き換えて`refresh_inputs.retained_inputs()`/`scenario_inputs()`が拒否することを確認するテストを追加。`tests/test_source_changes.py`に新規`test_lighting_profile_and_group_changes_are_diffed`を追加し、プロファイル/グループの追加・変更が`compare()`/`render_html()`へ反映されることを確認。実行した完全refresh（下記）の`source-changes.json`でも、R2のdirectionLocal修正3件が実際に`lightingProfiles.modified: 3`として検出されていることを確認。 |
| R5代表検証（照明A/Bのsolar保持・排他制御） | PASS | 実UEエディタ実行（`verify_w06_v2.py`）：日時由来の`solar`を持つ状態を基点に照明A/Bを開始し、A表示中・B表示中とも`current_state().solar`が基点の値と完全一致（`compare_a_solar_preserved`/`compare_b_solar_preserved`いずれも`true`）。比較中の`turn_on_selected_lighting()`/`set_lighting_day()`/`reset_all_lighting()`はいずれも`RuntimeError`で拒否（`edits_blocked_during_compare`に理由文言を記録）。比較中に同じ照明A/Bを再度開始しようとしても拒否（`second_compare_start_blocked: true`）。比較終了後は`solar`が保持されたまま（`solar_after_end_compare: true`）、`_active_compare_label()`が`null`に戻ることを確認。グループの不明メンバー警告は同実行内で、プロジェクト自身の`lighting-settings.json`コピーへ不明IDを含むテスト用グループを一時追加し、`_target_fixture_ids()`呼び出し時に`unreal.log()`へ不明IDを含む警告が出ることを確認（`stale_group_warned: true`）。 |
| 修正版一式での完全refresh 1回 | PASS | `build/W06-v2-refresh-v1`：`--previous`に夜間・3器具ON状態を持つプロジェクトを与え、`refresh-visual-study.py`を実行。7工程すべて`complete`、`stateVerification`の`statePreserved`/`geometryVerified`/`cameraRotationPreserved`が全て`true`、`unrealVerification.lighting.fixtureIds`が3器具すべてを含み、`unrealImportVerified: true`（659メッシュ、`maxBoundsErrorCm`は6e-5cmと無視できる誤差）。この1回のUEプロジェクトに対して上記R1/R2/R4/R5の実行確認（`verify_w06_v2.py`）をまとめて実施しています。F5/F9往復・再起動復帰はv1報告（`build/W06-ue-v1/walkthrough-smoke.txt`＝PASS）のエビデンスを再利用し、今回は再実行していません（レビューの明示的な許可通り）。 |
| 関連テスト・回帰 | PASS | `python -m pytest tests/`：161 passed, 55 subtests passed（v1報告の156 passed, 54 subtestsから、R1/R2関連2件・R4関連3件（`test_refresh_study.py`1件・`test_study_scenarios.py`1件・`test_source_changes.py`1件）を追加）。`node scripts/build-web-data.mjs --check`・`python tests/validate_house.py`（33室・35壁、変更なし）・`python tests/validate_electrical.py`（23型・145配置、変更なし）いずれも成功。 |

v1報告のAC3（照明A/B・F5/F9・完全refresh）・AC4（旧状態互換・不正値拒否）は今回のR1〜R5修正が直接及ぶ範囲外（R5の排他制御・solar保持を除く）のため、上記R5代表検証と完全refreshの再実行で該当パスの健全性を再確認しています。個別の再検証はレビューの指示通り、修正箇所の代表確認に絞っています。v1報告のAC1〜5の内容・証拠は下記に維持しますが、**AC1・AC2の「PASS」判定は、上記R1・R2の実バグが残った状態での判定であり、v2の対応後の再判定は上記の表を参照してください**（AC1・AC2自体の記述は当時の記録として変更していません）。

## 結果（v1、レビュー未反映の記録として維持）

ゲストLDK（room-1f-06）で、正本の照明配置（`data/electrical.json`）をBlender/UEへ反映し、夜間の点灯・調光・色温度の比較・保存・再生成ができるようになりました。今回対象のdownlight/ceiling/bracket/pendantのうち、既存`elec-008`（シーリング）に加えdownlight（`elec-200`）・pendant（`elec-201`）をゲストLDKへ新規配置し、2グループ（`guest-ldk-main`＝シーリング+ダウンライト、`guest-ldk-dining`＝ペンダント）に編成しました。light-bracketは配置インスタンスが無いため型・検証経路のみ用意し、light-exterior/light-indirectはW06の対象外として明記しています。

取付け位置は既存のWeb編集（`interior-white-model.html`）と同じ`wallAt`+`orientation`+`center`+`side`（壁付け）／`x`+`z`（天井付け）の契約を再解決しますが、**天井付けの高さは平坦な`CEIL_H`近似ではなく、実際の勾配天井の高さ（`interior_geometry.ceiling_y()`、壁・天井生成が使っているのと同じ関数）から取付け高さを引いた値**を使います。この解決はBlender側で一度だけ行い（`lighting-bindings.json`）、器具メッシュとUE光源の両方がこの1つの結果を使います。光の照射方向は器具の取付け姿勢とは別に管理し、天井付けは勾配に関わらず常に鉛直下向きです。

UEエディタに「照明」（昼夜切替、器具/グループ選択、ON/OFF・調光率・色温度指定、既定へ戻す）と「照明比較」（名前付き2案の`lighting`だけを切り替えるA/B、両案とも夜間必須）メニューを追加し、内覧HUDに昼夜表示（仮仕様の明示付き）を追加しました。既存の仕上げA/B・日時A/Bは`lighting`を比較開始時点の値へ固定し、夜間から日時比較を始めようとした場合は昼間へ戻す案内をして停止します（黙って切り替えません）。`study-state.json`をschemaVersion 1.2.0へ拡張し（必須`lighting`）、旧1.0.0/1.1.0状態は自動的に昼間・全器具offへ正規化して従来の見た目を維持します。

**光束・色温度は全てestimated（実測配光・IES・実採用品番未確認）です。** 初版の夜間環境は月光なしの共通固定条件で、天候・実照度の校正はW06の対象外です。必要な情報は「残ること」に記載します。

| AC | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| 1（天井器具の移動/吊下げ寸法変更が器具と光源へ一緒に反映。勾配天井の代表位置でThree.js/Blender/UEの取付け座標を確認。壁付けは小さな座標テストで可） | PASS | `tests/test_electrical_assets.py`：`elec-008`（シーリング、mountHeight=0）・`elec-201`（ペンダント、`mountHeightOverride=1.9`）双方の取付け高さが`interior_geometry.ceiling_y()`から独立に再計算した期待値と一致することを確認（実Blenderビルド`build/W06-package-v1/lighting-bindings.json`の実測値とも一致：`elec-008`→y=3.9325、`elec-200`→y=3.94、`elec-201`→y=2.103）。壁付けは`light-bracket`型を使った合成インスタンスでH/V・side=±1の4通りの位置・回転を検証（配置インスタンス自体は現状ゼロ件のため座標テストのみ、実機見た目確認は対象外と明記）。実UEレンダー（`build/W06-ue-v1/Saved/walkthrough-smoke.png`）でペンダントがダイニングテーブル上に正しく吊り下がって表示されることを目視確認。天井付け発光方向は勾配に関わらず`[0,0,-1]`固定であることを`build_lighting_bindings()`の全出力で確認。 |
| 2（実DX12で夜間の2グループの点灯/調光/色温度差を固定露出で確認。比較画像2枚と現在条件を残す。昼へ戻した際も従来の採光が戻る） | PASS | `build/W06-ue-v1/Saved/night-group-main.png`（`guest-ldk-main`点灯）・`night-group-dining.png`（`guest-ldk-dining`点灯）を同一プロジェクト・同一カメラ/仕上げ/露出/光源強度で撮影。`comparisonState`の`variant`/`camera`/`exposureEV100`/`sunLux`/`roomId`は完全一致、`lighting`のみ異なることを確認（ピクセル差分：全体の63%が10/255超、最大194/255）。昼への復帰は`verify_w06.py`の`day_restores_sunLux: true`（夜間中は太陽の実測輝度0を`sunLux`として読み戻さず、切替後に保存済み値が復元されることを確認）。 |
| 3（照明A/B、内覧F5/F9、再起動、名前付き案→完全refresh代表1回で照明状態を保持。1つの連続操作へまとめてよい） | PASS | 実UEエディタ実行（`build/W06-ue-v1/verify_w06.py`→`w06-verification.json`）で一連の流れを確認：グループON→調光0.7→色温度3000→夜間切替→保存→ディスクから再読込（F9相当）で`lighting`完全一致（`reload_matches_saved: true`）。異なる夜間名前付き案2件（`w06-night-a`＝main点灯、`w06-night-b`＝dining点灯）を保存し、照明A/Bを開始→A/B間で`lighting`が明確に異なる（`compare_a_b_differ: true`）ことを確認、比較中も仕上げ・視点は不変（`compare_fixed_variant_held: true`）、終了で開始前の状態へ復元（`state_after_end_matches_before: true`）。この名前付き案（`w06-night-a`）から`refresh-visual-study.py --scenario`で完全refreshを実行（`build/W06-refresh-v1`）し、7工程すべて`complete`、`stateVerification`の`statePreserved`/`geometryVerified`/`cameraRotationPreserved`が全て`true`、再生成後の`comparisonState.lighting`が保存案（night、elec-008/elec-200 on）と一致することを確認。この再生成プロジェクトでDX12スモークを実行し、HUDに「照明：夜間（仮仕様）」が正しく表示され、F5/F9往復も成功（`walkthrough-smoke.txt`＝PASS）することを確認。 |
| 4（旧状態の昼互換と、未知器具IDまたは不正値の簡単な拒否を確認。Python単体テスト中心、異常系のUE全経路反復は不要） | PASS | `tests/test_study_state.py`：1.0.0/1.1.0状態（`lighting`欠落、または任意の値を持たせても）が常に`day`・空`fixtures`へ正規化されること、1.2.0状態は`lighting`欠落・不正な`mode`・型不正な`fixtures`を確実に拒否すること、`on`/`dimming`/`temperatureK`の型・範囲チェック（bool以外のon、範囲外のdimming/temperatureK、未知フィールド）を確認。実UEエディタでも1件、未知の器具ID（`elec-does-not-exist`）を含む状態の`apply_state()`が拒否され（`unknown_fixture_rejected: true`）、シーン・状態が変更されないこと（`state_unchanged_after_rejection: true`）を確認。 |
| 5（器具の正本/仮仕様/変更反映手順を文書化。関連回帰、validate_house、validate_electrical、build-web-data --check成功） | PASS | [ARCHITECTURE.md「電気設備の再生成反映・夜間照明比較」](../ARCHITECTURE.md#電気設備の再生成反映夜間照明比較lighting-bindingsjsonw062026-09-09追加)・[UNREAL_WALKTHROUGH.md](../UNREAL_WALKTHROUGH.md)・[STATUS.md](../STATUS.md)を更新。`python -m pytest tests/`：156 passed, 54 subtests passed（新規39件：`test_lighting.py`16件、`test_electrical_assets.py`12件、`test_study_state.py`に3件追加）。`node scripts/build-web-data.mjs --check`・`python tests/validate_house.py`（33室・35壁）・`python tests/validate_electrical.py`（23型・145配置＝既存142+新規3）いずれも成功。 |

## 変更と判断（v2で追加・変更した分）

- 主な変更：
  - `interior-white-model.html`：`electricalGroupY()`・XYZパネルの表示/逆変換・既定値リセットの計4箇所を`slopedCeilingHeightAt()`ベースへ修正（R1）。
  - `data/visual/lighting-settings.json`：天井付け3型の`directionLocal`を`[0,0,-1]`→`[0,-1,0]`へ修正し、`note`に座標系・修正内容を明記（R2）。
  - `blender/electrical_assets.py`：`ceiling_height_at()`に`room_id`引数を追加し部屋の`ceiling`種別で分岐、`resolve_mount()`/`build_lighting_bindings()`へ`emitPositionM`を追加、`create_fixture_mesh()`の天井シェード生成を下向きへ修正（R1・R2）。
  - `blender/build_interior.py`：欠けていた`ceiling_height_at`のインポートを追加、ランプ配置を`emitPositionM`へ、ランプ回転の誤反転を削除、`setup_lighting()`に夜間分岐を追加（R2・R3）。
  - `unreal/lighting.py`：`validate_lighting_bindings()`が`emitPositionM`も検証するよう修正（R2）。
  - `unreal/import_study.py`：プレースホルダー円柱の二重生成を削除し、光源位置を`emitPositionM`へ（R2）。
  - `scripts/build-visual-twin.py`：Blender起動前の照明解決プリフライト（未知器具ID拒否含む）を追加（R4）。
  - `scripts/refresh_inputs.py`：`retained_inputs()`/`scenario_inputs()`に照明器具ID参照検証を追加（R4）。
  - `scripts/source_changes.py`：`TARGETS`へ`lightingProfiles`/`lightingGroups`を追加し、`summarize()`/`render_html()`へ反映（R4）。`scripts/refresh-visual-study.py`のトップページ要約にも同2項目を追加。
  - `unreal/study_controls.py`：`_target_fixture_ids()`のグループ不明メンバー警告、`_active_compare_label()`/`_require_no_active_compare()`による3種A/Bの相互排他と比較中の通常照明編集の禁止、`start_lighting_compare()`/`show_lighting_compare()`の`solar`保持、`_selected_lighting_effective()`による状態表示・プロンプト既定値の実効値化（R5）。
  - テスト：`tests/test_electrical_assets.py`・`tests/test_lighting.py`・`tests/test_refresh_study.py`・`tests/test_study_scenarios.py`・`tests/test_source_changes.py`を更新・追加。
- 設計からの差異：なし。R4の`source_changes.py`拡張は`data/electrical.json`本体（145件）の全項目差分ではなく`lighting-settings.json`のプロファイル/グループのみに限定（レビューが明示的に許容した範囲）。
- 追加依存：なし。環境変更：なし。BASEは`d4fabb2`のまま維持し、v1のコミット（`81b3ddf`）に対する追加コミットとして提出します。
- 未追跡/ignored成果物（`build/`配下、すべて`.gitignore`対象、v2で新規追加分）：
  - `build/W06-v2-night-diag`・`build/W06-v2-day-diag`：修正版Blenderの夜間/昼間レンダリング（R1〜R3の視覚確認）
  - `build/W06-diag-unknown-fixture-state.json`：R4の未知器具ID拒否確認用state
  - `build/W06-v2-base`：v2完全refreshの`--previous`用ベース（`build/W06-ue-v1`の複製、夜間3器具ON状態に変更）
  - `build/W06-v2-refresh-v1`：修正版一式での完全refresh代表1回（`verify_w06_v2.py`によるR1/R2/R4/R5実行確認込み）

## 変更と判断（v1、記録として維持）

- 目的：既存の電気設備データモデル・太陽計算・保存/refresh基盤を再利用し、正本の照明配置のBlender/UE反映、夜間の点灯・調光・色温度比較、保存・内覧・再生成への引き継ぎを追加すること。
- 主な変更：
  - `data/electrical.json`：ゲストLDK（room-1f-06）へdownlight（`elec-200`）・pendant（`elec-201`、`mountHeightOverride`でダイニングテーブル上へ調整）を新規配置。既存`elec-008`は変更なし。
  - 新規`data/visual/lighting-settings.json`：型ごとの光学プロファイル（光源種別/光束/色温度/spot角度/発光方向、全て`estimated`）と比較用グループ（2件）。`light-indirect`/`light-exterior`は`unsupportedTypes`で対象外を明記。
  - 新規`unreal/lighting.py`：`validate_lighting_settings()`/`validate_lighting_bindings()`（構造検証）、`resolve_fixture_overrides()`（surface_finish_overrides.resolve_overrides()と同型のモデル依存解決）、`effective_fixture()`（on/dimming/温度の実効値計算）、`kelvin_to_rgb()`（Blender用の近似変換、UE側はネイティブのTemperatureプロパティを使うため未使用）。
  - `unreal/study_state.py`：`SUPPORTED_SCHEMA_VERSIONS`に`1.2.0`を追加。`validate_lighting()`（構造検証のみ）を新設し、1.2.0は必須・厳格検証、1.0.0/1.1.0は自動的に`day`・空`fixtures`へ正規化。
  - 新規`blender/electrical_assets.py`：`merged_item()`（カタログ+個別上書きの統合、既存Web編集と同じ優先順位）、`ceiling_height_at()`（`interior_geometry.ceiling_y()`を使った実際の天井高解決）、`resolve_mount()`（壁/天井の取付け位置・向き解決）、`build_lighting_bindings()`（`lighting-bindings.json`の生成、対象外type・未知type・プロファイル欠落を理由付きで拒否）、`create_fixture_mesh()`（簡易プレースホルダ生成）。
  - `blender/build_interior.py`：`build_electrical_lighting()`を追加（`lighting-bindings.json`生成・器具メッシュ生成・`state['lighting']`を反映したBlenderランプ生成）し、`main()`から呼び出し。`study.json`に`electricalLighting`（mode/fixtureIds）を追加。
  - `unreal/import_study.py`：`lighting-bindings.json`から器具プレースホルダ（StaticMeshActor）と`PointLight`/`SpotLight`（`intensity_units=LUMENS`、`use_temperature=True`）を生成。
  - `unreal/study_controls.py`：`apply_state()`に昼夜切替（太陽・Sky/SkyLightの表示制御）と器具ごとの実効光束・色温度反映を追加。`scene_state()`に夜間中の太陽輝度0を`sunLux`として誤読しないための分岐と、器具のUndo検知を追加。新規「照明」「照明比較」メニュー（`set_lighting_day/night`、`select_lighting`、`turn_on/off_selected_lighting`、`set_dimming/temperature_selected_lighting`、`reset_selected/all_lighting`、`start/show/end_lighting_compare`ほか）。`_validate_applicable()`に照明の整合確認を追加（W04/W05の全A/B・案読込へ自動適用）。既存の仕上げA/B・日時A/Bの`fixed`に`lighting`を追加。日時A/Bは夜間モードからの開始を拒否。
  - `unreal/walkthrough/Source/RyukaInterior/Walkthrough.h`/`.cpp`：`CurrentLightingLabel()`とHUD表示行を追加。`ApplyConditions()`に1.2.0の`lighting`構造検証・太陽/Sky/各`Light_<id>`アクターへの反映・未知器具ID拒否を追加。`Restore()`のスキーマ許可に`1.2.0`を追加。
  - `scripts/build-visual-twin.py`：`data/visual/lighting-settings.json`等を`--interior`の入力ハッシュ対象・複製対象に追加、`lighting-bindings.json`をマニフェストの成果物一覧に追加。
  - `scripts/build-unreal-study.py`：`data/visual/lighting-settings.json`を`lighting-settings.json`としてコピー、`unreal/lighting.py`を他の共有モジュールと同様にプロジェクトへコピー。
  - `scripts/compare-unreal-daylight.py`：固定条件チェックのハッシュ対象に`lighting-settings.json`/`lighting-bindings.json`を追加。
- 設計からの差異：なし（仕様どおり既存機構の拡張として実装）。`ALLOWED_SCENARIO_FILES`の変更は不要と判断（`lighting`は`study-state.json`の一部として既存経路に乗り、`lighting-bindings.json`は`surface-bindings.json`と同様に常に現在の正本から再解決する生成物のため案へ同梱しない）。
- 追加依存：なし。環境変更：なし。
- `scripts/source_changes.py`の変更/追加/削除の一覧トラッキング（rooms/furniture/catalog）は電気設備へ拡張していません。W06の「Blender/UEの重い処理前に対象IDと修正先を案内して停止」という要件は、既存の面登録プリフライトと同じ形で`build_lighting_bindings()`自体が生成前に理由付きで停止することで満たしており、変更履歴の比較（diff）機能の拡張は別の関心事と判断しました。
- 未追跡/ignored成果物（`build/`配下、すべて`.gitignore`対象）：
  - `build/W06-package-v1`：実Blenderビルド（`lighting-bindings.json`・照明器具メッシュ・ランプを含む）
  - `build/W06-ue-v1`：`--site`等付きUEインポート、C++再ビルド、`verify_w06.py`実行（`w06-verification.json`）、DX12スモーク（昼）、夜間比較実撮影（`Saved/night-group-main.png`/`night-group-dining.png`、AC2証拠）
  - `build/W06-refresh-v1`：夜間名前付き案からの完全refresh代表1回（AC3証拠）、再生成後のDX12スモーク（夜、HUD確認）
  - `build/scenarios/w06-night-a`／`w06-night-b`／`w06-day-c`：照明A/B・day候補拒否の検証用名前付き案

## 残ること

- **実仕様確認待ち**：以下は未確認・未入力のままで、今回の光束・色温度・器具配置は全て仮の推定値です。
  - 採用予定の照明器具の実品番・実測配光（IES）・実光束・実消費電力
  - ダウンライト/シーリング/ペンダントの実配置台数・位置（現状はW06検証用の仮配置。既存見積書「電灯配線41」との対応関係は未確認）
  - 夜間の実照度・実際の室内の見え方（施主による現地/実機確認）
- 定量照度（lux実測値との対応）・実天候の校正は対象外のまま（仕様どおり）。初版の夜間環境は月光なしの共通固定条件で、間接照明・外灯の演出は含みません。
- `light-bracket`（壁付け照明）は配置インスタンスが無いため、座標解決のみ検証済みで実機の見た目確認はしていません。壁付け器具を実際に配置する際は、光方向（既定：器具正面）の妥当性を再確認してください。
- `light-indirect`（間接照明の造作）・`light-exterior`（屋外灯）はW06の対象外です。将来対応する場合は取付け契約・発光方向の再設計が必要です。
- 電気回路・消費電力・法規評価は対象外のままです。
- `source_changes.py`の変更履歴トラッキングは、v2で`lighting-settings.json`のプロファイル/グループへ拡張済みですが、`data/electrical.json`本体（145件の配置インスタンス）の全項目差分は引き続き対象外です（レビューが明示的に不要と判断した範囲）。
- W07（全館内覧）には着手していません。

## 再現・復旧

```powershell
# 全体ビルド（正本検証→Blender→検証）
python scripts/build-visual-twin.py --blender 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --output build/<新規パッケージ> --interior --variant natural --samples 128 --width 1600

# UEインポート
python scripts/build-unreal-study.py --engine 'C:/Program Files/Epic Games/UE_5.8' --package build/<新規パッケージ> --output build/<新規UEプロジェクト> --cache '../../ddc'

# 内覧の有効化
python scripts/enable-unreal-walkthrough.py --project build/<新規UEプロジェクト> --engine 'C:/Program Files/Epic Games/UE_5.8' --cache '../../ddc'

# UEエディタのPythonコンソール/起動引数で build/W06-ue-v1/verify_w06.py を実行し、w06-verification.json を確認
# （照明メニューの操作・照明A/B・保存/再読込・未知ID拒否を一括確認）

# 夜間2グループの実撮影比較（AC2）：study_controls経由で各名前付き案を適用・保存後
python scripts/capture-unreal-study.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/<UEプロジェクト> --cache '../../ddc' --name <名前>

# 名前付き案（夜間）からの完全refresh（AC3）
python scripts/save-study-scenario.py --project build/<UEプロジェクト> --name '<名前>' --note '<メモ>' --output build/scenarios/<新規案>
python scripts/refresh-visual-study.py --previous build/<UEプロジェクト> --scenario build/scenarios/<新規案> --output build/<新規ディレクトリ> --cache '../../ddc'

# DX12スモーク（HUDの照明表示・F5/F9確認）
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/<UEプロジェクト> --cache '../../ddc' --smoke

# テスト・回帰
python -m pytest tests/ -q
node scripts/build-web-data.mjs --check
python tests/validate_house.py
python tests/validate_electrical.py
```

全ログ・成果物は上記各`build/`ディレクトリにあります（すべて`.gitignore`対象）。
