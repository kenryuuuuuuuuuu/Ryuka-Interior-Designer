# W06 実装報告

状態：READY_FOR_REVIEW
開始BASE（完全SHA）：`d4fabb229a2b53e2478486e3913f4dd4563fbbbf`
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境：Windows 11 Pro 10.0.26200 / UE 5.8.2 / Blender 5.2.0 LTS。変更した設定なし。

## 結果

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

## 変更と判断

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
- `source_changes.py`の変更履歴トラッキングは電気設備へ拡張していません（上記「変更と判断」参照）。
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
