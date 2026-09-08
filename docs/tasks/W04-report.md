# W04 実装報告

状態：READY_FOR_REVIEW（v3、W04-v2レビューのR1/R2/R4継続対応）
開始BASE（完全SHA）：`37fb6a9543f1ad40da33185e4239ab704bd11463`（維持）
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境：Windows 11 Pro 10.0.26200 / UE 5.8.2 / Blender 5.2.0 LTS。変更した設定なし。

## 結果（v3時点）

ゲストLDK（room-1f-06）の壁・床・天井を面単位で仕上げ変更できるようになりました。共有壁は法線方向の点-in-polygon判定（`wall_cap_for_room()`）で表裏を判定し、床・天井も主面（床上面・天井下面）だけへ専用材質を割り当てます。UEエディタの「内装比較」メニューに「面編集」と「案の保存・比較」（名前付き案の保存・一覧・読込、A/B比較）を追加しました。比較状態は`schemaVersion 1.1.0`で`surfaceOverrides`を保持し、F5/F9保存・復元、`--previous`/`--scenario`いずれの再生成でも引き継がれます。

**[W04-v2レビュー](W04-review-v2.md)（対象`939cc52`、CHANGES_REQUESTED）のR1・R2・R4継続分をすべて同じW04内で修正しました**（この報告のv3）。R3・R5はv2レビューで受入済みのため今回は変更していません。各項目の対応は以下の通りです。

| 項目 | v2までの状態 | v3での対応 |
|---|---|---|
| R1（プリセット切替で模様が変わらない） | marker_materialにパターンは付いたが、親材質はstudy.variantで生成した1種類のみで、editor/内覧の切替はColor/Roughnessだけを変え、模様（親材質）自体は切り替わらなかった。 | `import_study.py`が面ごとに**variantの数だけ**パラメトリック親材質（`M_Surf_<surfaceId>_<variant>`、各variant自身のpattern/planks/noiseを保持）を生成するよう変更。`study_controls.py`の`apply_state()`と`Walkthrough.cpp`の`ApplyConditions()`は、現在シーンにある材質を再利用せず、**effective variant（全体基準または面別上書きのvariant）に対応する親を都度ロード**してMIDを作るよう変更。全体変更・面上書き・A/B・案の読込のすべてが同じ`resolve_finish()`/C++版ロジックを経由するため、同じ解決規則に従います。Blender側`SurfaceBinder`も、登録面のpaletteRoleが'wood'/'fabric'の場合（floorのnatural/warm等）は全体材質と同じ`texture=`を渡すよう修正し、登録するだけで木目等のディテールを失わないようにしました。 |
| R2（周辺条件なしの案を、周辺条件ありへ黙って読み替える） | `apply_state()`はexpectedがNoneなら現在のcontextハッシュを自動採用しており、「周辺条件なしで保存した案」を「周辺条件ありの現在プロジェクト」へ読込・比較すると不一致を案内せず適用していた。start_compareも両案の現在モデルとの適合を表示時までチェックしていなかった。 | シーンを変更しない新規の純関数`_context_compatible(state)`を追加（現在の`site-context.json`の有無・ハッシュと、状態の`siteContextSHA256`を**双方向**で比較。周辺条件なしの状態は、現在プロジェクトに周辺条件があれば不適合と判定）。`load_scenario()`/`start_compare()`は、状態を読み込んだ直後・シーンに触れる前にこれで両案を検証し、不適合なら適用前に拒否します（A/Bどちらが不適合でも、Aを適用してからBで失敗する、という順序にはなりません）。`apply_state()`自身の「初回の自動採用」ロジック（新規インポート時など）はそのまま維持し、案の読込とは明示的に分離しています。 |
| R4（C++の型判定がPythonとまだ一致しない） | `surfaceOverrides`自体が欠落（HasField=false）の場合、schemaVersionを見ずに検証を素通りしていた。colorHex/roughness/variantが存在するが型が違う場合（例：roughness="bad"）、TryGet*Fieldが失敗すると値を検証せず既定値へ進み、不正値を拒否できなかった。 | `ApplyConditions()`が`schemaVersion`を読み、1.0.0以外で`surfaceOverrides`が欠落していれば拒否するよう変更。各上書きフィールドは、まず`HasField()`で存在を確認し、存在するなら`TryGet*Field()`の成功と値の制約（colorHexの16進6桁、roughnessの範囲、variantが文字列であること）の両方を要求するよう変更（取得失敗＝黙って既定値ではなく拒否）。 |

| 条件ID | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| AC1（壁1面の色変更、窓分割面へ反映、他面・共有壁裏・隣室床が不変） | PASS（v1/v2から変更なし、再確認） | v1/v2報告の証拠に加え、`build/W04-v3-refresh-v1`で修正後コードによる完全refreshでも上書きが単一面に留まることを再確認（下記AC3参照）。 |
| AC2（床・勾配天井のプリセット変更、対象解除、部屋一括適用、開口・重複ちらつきなし、既存歩行可） | PASS（v2から変更なし） | v1/v2報告の証拠（面別マテリアルスロットの直接検査）を維持。v2レビューでR5は受入済みのため今回の再検証は行っていません。 |
| AC3（A/B同条件切替、名前付き保存、F5/F9または editor→歩行の代表往復、再起動復元、完全refreshに--scenario、旧1.0.0状態読込確認） | PASS | 今回追加：実UEエディタ実行（`build/W04-v3-ue-v1/v2-fixes-verification.json`）で、①床の全体variant切替（natural→reference→warm）ごとにマーカーMIDの親アセット名が`M_Surf_surf-guest-floor-001_<variant>`と一致して切り替わること（`pattern_actually_switches: true`）、②面別のvariant上書き（床をreferenceへ）でも同様に親が切り替わること、③周辺条件なしの案（`w04-v3-context-missing`、自己整合性は保った状態で周辺条件情報だけを除去）を周辺条件ありの現在プロジェクトへ`load_scenario()`/`start_compare()`しようとすると拒否され、Aも適用されず`_compare`も開始されないこと、④周辺条件が一致する案は問題なく読み込めることを確認。完全refresh＋`--scenario`（周辺条件付きの案`w04-v3-final-refresh-test`）を`build/W04-v3-refresh-v1`として実行し、全7工程`complete`、`surfaceOverrides`と`siteContextSHA256`の両方が選択した案と一致することを確認。 |
| AC4（消えたsurface ID/no-surfaceへの上書き1件、型不正1件、元の案は保持） | PASS | v1/v2の証拠に加え、C++側の型不正拒否を実機（DX12、`-RyukaSmoke`）で確認：`roughness: "bad"`を含む1.1.0状態を`study-state.json`に置いて起動すると、`ApplyConditions()`が拒否してキャラクターが起動不能のまま停止し（`bReady`が立たない）、HUDに「保存データの仕上げ・太陽条件を適用できません」と表示、クラッシュせず`walkthrough-smoke.txt`は`FAIL`（この文脈では意図通りの結果）。正しい状態に戻すと同じプロジェクトで通常通り`renderVerified: true`のDX12描画・保存復元が成功することも確認し、型不正の拒否がその後の正常系を壊していないことを確認しています。 |
| 回帰 | PASS | `python -m pytest tests/`：117 passed, 35 subtests passed（v2から変更なし。今回の修正はすべてUE/Blender/C++実行時ロジックで、既存のPython純粋関数の入出力契約は変えていません）。`node scripts/build-web-data.mjs --check`成功。`python tests/validate_house.py`：33室・35壁 |

## 変更と判断（v3で追加・変更した分）

- 変更（v2報告分に追加）：`unreal/import_study.py`（面ごとに全variant分のパラメトリック親材質`M_Surf_<id>_<variant>`を生成）、`unreal/study_controls.py`（`apply_state()`がeffective variantで親をロード、`scene_state()`の不整合検出が親アセットの一致も確認、新規`_context_compatible()`、`load_scenario()`/`start_compare()`が適用前にこれで両案を検証）、`unreal/walkthrough/Source/RyukaInterior/Walkthrough.cpp`（`ApplyConditions()`がSchemaVersionを見て1.1.0のsurfaceOverrides欠落を拒否、各上書きフィールドを`HasField`＋型/範囲チェックへ変更、`SurfacePlan`が`M_Surf_<id>_<EffectiveVariant>`を都度ロード）、`blender/build_interior.py`（`SurfaceBinder`が`finish['paletteRole']`に応じて`texture='wood'/'fabric'`を渡す）。
- 設計からの差異：なし（レビュー指摘への直接対応）。
- 追加依存：なし。環境変更：なし。
- 未追跡/ignored成果物（v2報告分に追加）：`build/W04-v3-package-v1`（Blender側R1修正の確認、natural floorのノイズテクスチャ確認用）、`build/W04-diag/site-context-v3-test.json`（R2検証用の周辺条件フィクスチャ）、`build/W04-v3-ue-v1`（`--context`付きUEインポート、per-variant親材質の実機検証、C++再ビルド、型不正拒否のDX12スモーク、正常系DX12スモーク）、`build/W04-v3-refresh-v1`（修正後コードでの完全refresh代表1回、周辺条件付き）、`build/scenarios/w04-v3-context-ok`／`-context-missing`（R2検証用）・`w04-v3-final-refresh-test`（最終refresh用）。いずれも`.gitignore`対象で未コミットです。

## 残ること

- 床・天井のレベル（階）一致チェック（R5、v2で対応済み）は引き続き実データで再現できていません（変更なし）。
- 共有壁を両室とも登録した場合の一般化されたcap所有の扱いは今回も対応していません（v1レビューの非阻害の将来注意のまま）。
- レイクリックによる面選択（仕様上は任意）は未実装のままです。
- W05へは着手していません（DRAFT段階のまま）。

## 再現・復旧

```powershell
# R1: Blender側（natural floorがwood質感を保持することを確認）
python scripts/build-visual-twin.py --interior --output build/<新規ディレクトリ> --variant natural
# interior.blendを開き、Surf_floor_surf-guest-floor-001にTEX_NOISEノードがあることを確認

# --context付きのUEフル生成→C++ウォークスルー再ビルド
python scripts/build-unreal-study.py --blender 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --engine 'C:/Program Files/Epic Games/UE_5.8' --cache '../../ddc' --package build/<パッケージ> --output build/<UEプロジェクト> --context build/W04-diag/site-context-v3-test.json
python scripts/enable-unreal-walkthrough.py --project build/<UEプロジェクト> --engine 'C:/Program Files/Epic Games/UE_5.8' --cache '../../ddc'

# R4異常系：roughnessが文字列の1.1.0状態をstudy-state.jsonに置いてDX12スモーク（FAILとHUDの理由表示を確認）
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/<UEプロジェクト> --cache '../../ddc' --smoke

# 名前付き案（周辺条件付き）を使った完全refresh
python scripts/refresh-visual-study.py --previous build/W04-v3-ue-v1 --scenario build/scenarios/w04-v3-final-refresh-test --output build/<新規ディレクトリ> --cache '../../ddc'

# テスト・回帰
python -m pytest tests/ -q
node scripts/build-web-data.mjs --check
python tests/validate_house.py
```

全ログ・成果物はv1/v2報告記載の各ディレクトリに加え、`build/W04-v3-package-v1/`・`build/W04-v3-ue-v1/`・`build/W04-v3-refresh-v1/`配下にあります。
