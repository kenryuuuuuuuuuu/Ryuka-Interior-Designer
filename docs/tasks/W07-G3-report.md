# W07-G3 実装報告：ゲスト全8区画の仕上げ・設備・照明（v2）

- **仕様書**：[W07-G3-guest-interiors.md](W07-G3-guest-interiors.md)
- **レビュー**：[W07-G3-review.md](W07-G3-review.md)（v1＝CHANGES_REQUESTED、R1〜R3）。本 v2 で一括対応。
- **BASE**：`e9113b94d03f6eaf5c83bede32fc9532bca470c0`（G3着手時HEAD＝G2受入HEAD。v1から不変）
- **HEAD**：`__HEAD__`（v1: 〜`b255f2f` → `f352042`〔R1〜R3コード修正〕→ `ad185f3`〔水回り視点・報告のID訂正〕→ 本SHA記録docsコミット。BASEは不変）
- **提出**：`build/reviews/W07-G3-v2`
- **作業場所**：`build/worktrees/visual-twin`、ブランチ：`feature/visual-twin-foundation`
- **範囲**：G2受入済み実装へゲスト8区画のデータ展開。全館化・自宅・階段・新ランチャー・配布導線（W08-G）は含みません。
- **代表プロジェクト（v2）**：`build/W07-G3-blender-v2` → `build/W07-G3-ue-v3`（`unrealImportVerified: true`、712メッシュ）、完全refresh `build/W07-G3-refresh-v2`。旧scope取込確認は `build/W07-G3-pilot-blender-v1` → `build/W07-G3-pilot-ue-v1`。

## レビュー v1 対応（R1〜R3）

| # | 指摘 | 対応 | 確認 |
|---|---|---|---|
| R1 | 旧2室scope（guest-pilot）のUE取込が、対象外室（玄関等）の roomState を参照して `KeyError` | `blender/build_interior.py` の `SurfaceBinder` が、正本registryは全52面を検証しつつ、**編集bindingは現在の編集scope内の室の面だけ**に限定。対象外の壁/床/天井は遮蔽形状＋基準材質のまま。 | `tests/test_surface_binding_scope.py`（pilot=16面／guest=52面／ldk=8面、scope外roomIdなし）。**実機**：`build/W07-G3-pilot-ue-v1` の取込が `unrealImportVerified: true`（16面bound、room-1f-05/06のみ）＝以前クラッシュした経路が通る。 |
| R2 | 空室（役割スロット幾何なし）の面を全面上書きすると、`scene_state()` が上書き後variantを室の基本variantと誤認。上書き解除で戻らない。 | `unreal/study_controls.py`：空室の基本variantは**マーカー読み戻しをやめ、管理状態（`base['roomStates']`）から取得**。面ごとの実材質整合チェックは従来どおり `resolve_finish(基本, 上書き)` と突き合わせて未管理変更を拒否。 | **実機** `verify_w07_g3.py` に4項目追加：玄関を natural のまま6面すべて warm 上書き → 保存/再読込で室variantは natural のまま → 上書き解除で壁材質が natural へ戻る。全項目 True。 |
| R3 | 洗面ボウルがキャビネットの固体に埋没。洗濯機の丸ドアが縦長の板になる向き。 | `blender/furniture_assets.py`：洗面キャビネットを低いベース＋ボウル外周のパネルに分割し**実際のボウル空間を確保**。洗濯機ドアは新しい `kind='disc'`（`build_interior.py`）で**前面の垂直円**、ガラスを縁より前へ。便器/洗面/UB の仮視点も設備が入る画角へ調整。 | `tests/test_furniture_assets.py` にボウル空間・ドア向きの検査を追加。代表画像（洗面昼/夜・UB昼/夜・トイレ昼）で確認。 |

- 報告書の家具ID一覧も訂正（洋室＝fur-036/037/041/042、fur-045/046/049はLDK）。

## 室別の棚卸し（実装時にIDから再集計）

| 区画 | roomId | 家具/設備ID | 照明ID | 登録面（壁/床/天井） |
|---|---|---|---|---|
| 玄関 | room-1f-02 | なし | elec-002 | surf-genkan-wall-001〜004 / -floor-001 / -ceiling-001（6） |
| ホール | room-1f-24 | なし | elec-003 | surf-hall-*（6） |
| LDK | room-1f-06 | fur-006/007/008/009/010/011/012/038/043/044/045/046/047/048/049（15） | elec-008, elec-200, elec-201 | surf-guest-*（8、G1のまま） |
| 洋室 | room-1f-05 | fur-036/037/041/042（4） | elec-006 | surf-western-*（8、G1のまま） |
| トイレ | room-1f-01 | fur-035（toilet） | elec-001 | surf-toilet-*（6） |
| 洗面脱衣 | room-1f-03 | fur-001（vanity）、fur-002（washing-machine） | elec-004 | surf-washroom-*（6） |
| UB | room-1f-04 | fur-003（bathtub） | elec-005 | surf-ub-*（6） |
| 収納 | room-1f-23 | なし | elec-007 | surf-closet-*（6） |

- 家具：`guest` scope で 23 点（既存配置のみ、創作なし）。
- 面：**合計 52 面すべて解決・bind**（`surface-registry.py` の resolve、`build/W07-G3-ue-v3/surface-bindings.json` の全 status=bound）。6室はいずれも house.json の 4 頂点矩形・フラット天井。
- 照明：**10 灯を 1 回で解決**（`lighting-bindings.json`、器具外観と実光源の二重生成なし）。

## 1. 編集scopeと歩行profile

- `data/visual/study-scopes.json`：**scopeId=guest**（8室、defaultRoomId=room-1f-06）を追加。`guest-ldk`/`guest-pilot` の roomIds・意味は不変。既定CLIは変更していません（`--scope` 明示）。
- `data/visual/walkthrough-profiles.json`：`guest-circulation` の `scopeId` を **`scopeIds: ["guest-pilot", "guest"]`** へ拡張。同じ8室/7接続/開始室（玄関）を新profileへ複製していません。`unreal/circulation.py` の `validate_profiles()`/`resolve_profile_for_scope()` が `scopeIds`（配列）・`scopeId`（旧・文字列）の両方を受け付け、同一 scope を2つのprofileが主張する不正定義を拒否します。`guest-ldk-solo`（旧単室）は `scopeId: guest-ldk` のまま。
- `data/visual/room-render-settings.json`：残り6室の仮初期視点（room ごとに調整可）・仮 defaultVariant（natural）を追加。house.json のポリゴン/床高さは複製していません。
- **guest では 8 室が編集対象**：G2の「歩けるが編集対象外」の6室でも、現在室への編集対象同期・面/照明一覧・仕上げキーが機能します。`guest-pilot` は引き続き 2 室のみ編集対象。

## 2. 面と基本仕上げ

- `data/visual/surface-registry.json`：6室 × (4壁 + 床 + 天井) = 36 面を安定IDで追加。LDK/洋室の既存ID・勾配天井・品質は不変。
- 共有壁は両面を別室へ正しく割り当て（`surface_registry.py` の辺一致、両面で別ID）。扉・開放開口は塞がず、別メッシュの重ね貼りはしていません。
- 初期仕上げは既存パレット・模様・粗さの再利用（仮仕様）。水回りは清潔感のある明るい簡易材質（種類が分かる程度）。新しい仕上げカタログ・採用品選定UIはありません。「製品選定済み」「防水仕様確認済み」表示はしていません。
- **旧scopeの退行なし**：`guest-pilot`/`guest-ldk` 生成では従来どおり scope 内の面だけを編集対象に bind（`build_interior.py` は既に scope 汎用。対象外の壁/床/天井形状は採光遮蔽として残り基準材質を維持）。
- **空室の対応（`unreal/study_controls.py`）**：玄関/ホール/収納（および家具1点のトイレ/UB）は whole-scene の役割スロット幾何を持たないため、`scene_state()` が室の基本 variant を導出できません。**基本 variant は管理状態（`base['roomStates']`）から取得**し、面ごとの実材質は従来どおり `resolve_finish(基本, 上書き)` と突き合わせて未管理変更を拒否します（レビュー R2：マーカーの実 variant を読み戻すと、全面上書き時に基本 variant が上書き値へ汚染され、解除で戻らなくなるため撤回）。保存・再読込・上書き解除がすべて往復します。

## 3. 既存家具・水回り設備の適用

- 家具の位置/寸法/向き/所属は `furniture.json` とカタログのまま。G1の scope 選択・室別役割材質を再利用、同じ設備の二重生成なし。既存LDK装飾は維持、全室への小物追加なし。
- **便器・洗面台・洗濯機・浴槽**：`blender/furniture_assets.py` に parametric 部品を追加し、`data/visual/asset-bindings.json` にバインディング（`status: estimated` ＋ provenance note）を登録。
  - 便器（`toilet-v1`）：タンク・便器ボウル（楕円）・便座リング・蓋。
  - 洗面台（`vanity-v1`）：カウンター（洗面ボウルの周りを枠取り、ボウルに板を渡さない）・一段下げた楕円の底・縁・水栓・鏡。
  - 洗濯機（`washer-v1`）：本体・前面の丸ドア（枠＋暗いガラス面）・操作パネル。
  - 浴槽（`bathtub-v1`）：外殻・エプロン・縁（左右/頭）・一段下げた内側の底（**内部を固体で埋めない**）・水栓。
- 陶器/金属は固定材質（`stone`/`metal`/`black`/`frame`）。室variantで木へ置換しません。カタログ外形寸法（浴槽は widthOverride 1.82 を含む）・向き・位置は保持。部品寸法は推定で `estimated`。
- 市販品探索・配管/水流/家電動作シミュレーション・採用品再現はしていません。

## 4. 10灯と室別比較

- `build_electrical_lighting()`（scope 汎用）が guest の8室・10灯を `lighting-bindings.json` へ 1 回で解決。既存の on/off・調光・色温度、昼夜条件、太陽来歴は不変。
- `data/visual/lighting-settings.json` のグループは既存3件のまま（室別グループ追加は仕様上任意。未知ID/室混在の検証は `validate_lighting_settings()`）。
- 室切替・歩行で隣室の灯りは消えません。旧案に器具指定が無ければ既定 off。照明は光束・配光未校正の仮仕様である旨を明示。
- 仕上げA/B＝対象室 variant/surfaceOverrides のみ、照明A/B＝対象室 fixtures のみ、日時A/B＝全体太陽のみの契約を維持。**対象室を含まない比較案は理由を示して拒否**（`start_compare()` の既存チェック）。

## 5. 保存・8室への拡張・旧案

- 状態 schema 2.1.0 を継続。guest の通常保存は 8 室の roomStates ＋ 全体の doorStates/solar/視点/敷地条件。
- G2の2室モデルを guest へ広げるのは `--scope guest --allow-new-rooms` のみ（`refresh-visual-study.py` の既存フラグ）。この時だけ不足6室を各室の初期 variant・空の面上書き/fixtures で初期化。既存2室の設定・扉・視点・来歴は保持。通常の部分案適用では不足室を初期化しません。
- 8室モデルへ旧1室/2室案を通常読込：全体条件は案から、案の roomStates だけ置換、他室は現在状態を保持（`mrs.partial_apply()`）。マージ後 scopeId は guest、旧案原本は不変。G2と guest で歩行 profileId が共通なので有効な保存位置を引き継げます。
- G2の安全開角・引き戸の不変閉基準は不変。設備追加で扉が家具に干渉すれば開閉を拒否（`LeafMotionClearFraction()`、角度/家具/壁/カプセル幅を無断で変えない）。

## 受入条件（AC）結果

| AC | 結果 | 根拠 |
|---|---|---|
| 1 | **満たす** | `verify_w07_g3.py`：`scope_is_guest`・`eight_rooms_in_state`・`all_registered_surfaces_bound`（52面）・`six_new_rooms_have_surfaces`。`tests/test_circulation.py`（23件）、`tests/test_surface_registry.py`（52面 resolve）、`tests/test_surface_binding_scope.py`（pilot=16面）。`guest-pilot` の実機取込も成立（R1）。 |
| 2 | **満たす（実シーン）** | `verify_w07_g3.py`：`washroom_variant_change_moved_its_own_wall_material`（洗面脱衣を warm へ → その壁の実 MID 親が `M_Surf_..._warm` へ変化）、`neighbour_ub_wall_material_unchanged`（隣室 UB の壁材質は不変）、`fixture_on_recorded_only_for_its_room`（洗面の器具 on が洗面の fixtures にだけ記録、UB は不変）。 |
| 3 | **満たす** | `verify_w07_g3.py`：`water_fixture_fur-035/001/002/003_multipart`（便器/洗面台/洗濯機/浴槽が 2 部品以上の Actor 群としてインポート）。要所画像・LDK代表画像は下記「証跡」。設備ID対応は棚卸し表。 |
| 4 | **満たす** | `verify_w07_g3.py`：`new_room_setting_survives_save_reload`（トイレを reference にして保存→レベル再読込→reference 保持）、`compare_rejects_scenario_without_active_room`（対象室 roomState を持たない旧単室案で A/B 開始 → RuntimeError）。scope拡張の初期化は `--allow-new-rooms` の既存経路。 |
| 5 | **満たす（実シーン）** | 完全refresh `build/W07-G3-refresh-v2`（`--previous build/W07-G3-ue-v3 --scope guest`、8室 roomStates ＋ door-002 open ＋ 非nullカメラ（洗面脱衣内）＋新旧室で異なる variant/点灯）：`status: complete`、終了コード0、`comparisonState` が 8室 roomStates・doorStates・walkthrough・camera を保持、`validate_study_transfer.py` 成功。 |
| 6 | **満たす** | 上記 refresh：非null視点・開扉・8室状態を保持。再生成された `door-bindings.json` の `openYawDeltaDeg`（door-002=73°）も一致＝実葉の共通開ポーズ維持。 |
| 7 | **満たす** | `pytest tests/`：**201 passed**。`validate_house.py`/`validate_furniture.py`/`validate_electrical.py`/`validate_openings.py`・`build-web-data.mjs --check` すべて成功。昼夜代表画像は「証跡」。未指定設備/仮仕上げ/狭所は「不足・未決定一覧」。 |

## 実施した検証

### 単体・軽量確認

- `python -m pytest tests/ -q`：**201 passed, 55 subtests passed**（circulation `scopeIds`、`test_surface_registry` 52面、`test_surface_binding_scope` scope限定、`test_furniture_assets` の水回り部品検査を含む）。
- `node scripts/build-web-data.mjs --check`・`validate_house.py`/`validate_furniture.py`/`validate_electrical.py`/`validate_openings.py`：すべて成功。

### Blender / Unreal Engine（実行）

- `build-visual-twin.py --interior --scope guest --output build/W07-G3-blender-v2`：GLB 往復成功。`study.json` の scopeId=guest・8室、`surface-bindings.json` 全 52 面 bound、`lighting-bindings.json` 10 灯。
- `build-visual-twin.py --interior --scope guest-pilot --output build/W07-G3-pilot-blender-v1`：GLB 往復成功。`surface-bindings.json` は **16 面**（room-1f-05/06 のみ）＝R1。
- `build-unreal-study.py ... --output build/W07-G3-ue-v3`：`unrealImportVerified: true`（712 メッシュ、maxBoundsErrorCm < 1e-3）。
- `build-unreal-study.py ... --package build/W07-G3-pilot-blender-v1 --output build/W07-G3-pilot-ue-v1`：`unrealImportVerified: true`（16 面 bound、`KeyError` なし）＝R1 の実機確認。
- `enable-unreal-walkthrough.py`：`walkthrough.json` は `guest-circulation`（8室・7接続・開始室 玄関）を解決。C++ ソース変更なし（`error C`/`error LNK` 0）。
- `-RyukaSmoke`（NullRHI・DX12、`build/W07-G3-ue-v3`）：G2 の連続経路（玄関→ホール→door-002→LDK→…→トイレ）＋AC4＋R2＋R3が **PASS**、`walkthrough-smoke.png` 取得。※`verify_w07_g3.py` の後片付けが `study-state.json` を消すため、smoke は verify の前に実行するか、間に `build/W07-G3-ue-v3/g3_regen_state.py`（`study_controls.save()` を1回呼ぶビルド成果物スクリプト）で復元してから実行する。
- `verify_w07_g3.py`（`-run=pythonscript`）：**20 項目すべて成功**（AC1〜4 の 16 項目＋R2 の 4 項目）。`build/W07-G3-ue-v3/verify_w07_g3_result.json` の `_all_passed: true`。
- 完全refresh 1 回（`--previous build/W07-G3-ue-v3`）：`build/W07-G3-refresh-v2`、`status: complete`、終了コード0。

## 検証コマンド（実行済み）

```
python -m pytest tests/ -q                       # 201 passed
node scripts/build-web-data.mjs --check
python tests/validate_house.py
python tests/validate_furniture.py
python tests/validate_electrical.py
python tests/validate_openings.py

# guest（8室、代表）
python scripts/build-visual-twin.py --blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --interior --scope guest --output build/W07-G3-blender-v2
python scripts/build-unreal-study.py --engine "C:/Program Files/Epic Games/UE_5.8" --package build/W07-G3-blender-v2 --output build/W07-G3-ue-v3 --cache C:/UE_DDC/w07g3b
python scripts/enable-unreal-walkthrough.py --project build/W07-G3-ue-v3 --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g3b
python scripts/launch-unreal-walkthrough.py --project build/W07-G3-ue-v3 --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g3b --smoke   # PASS
# UEエディタ検証：UnrealEditor-Cmd.exe <v3>/RyukaInterior.uproject -run=pythonscript -script=<v3>/verify_w07_g3.py -unattended -NullRHI ...   # 20/20
python scripts/refresh-visual-study.py --previous build/W07-G3-ue-v3 --output build/W07-G3-refresh-v2 --blender "..." --engine "..." --cache C:/UE_DDC/w07g3refresh --scope guest   # status: complete

# guest-pilot（旧2室、R1 の退行確認）
python scripts/build-visual-twin.py --blender "..." --interior --scope guest-pilot --output build/W07-G3-pilot-blender-v1     # surface-bindings.json = 16面
python scripts/build-unreal-study.py --engine "..." --package build/W07-G3-pilot-blender-v1 --output build/W07-G3-pilot-ue-v1 --cache C:/UE_DDC/w07g3b   # unrealImportVerified: true（KeyErrorなし）
```

### 証跡ファイル

- `build/W07-G3-ue-v3/verify_w07_g3.py`・`verify_w07_g3_result.json`（`_all_passed: true`、20項目）
- `build/W07-G3-ue-v3/Saved/walkthrough-smoke.txt`（PASS）・`walkthrough-smoke.png`（DX12 実描画）・`g3_regen_state.py`
- `build/W07-G3-ue-v3/surface-bindings.json`（52面）・`lighting-bindings.json`（10灯）・`import-verification.json`
- `build/W07-G3-pilot-ue-v1/import-verification.json`・`surface-bindings.json`（16面、R1）
- `build/W07-G3-refresh-v2/refresh.json`（`status: complete`）・`ue/state-transfer-verification.json`・`blender/door-bindings.json`
- 昼・夜の代表画像：`build/W07-G3-images/`（`g3-ldk-{day,night}`・`g3-washroom-{day,night}`・`g3-ub-{day,night}`・`g3-toilet-day`・`g3-genkan-day`・`g3-hall-day`）。取得は `build/W07-G3-ue-v3/g3_one.py`（ビルド成果物のエディタスクリプト。正本コード非改変。1枚1エディタプロセスで `scripts/unreal/capture_study.py` と同じ単発 tick を使う）。各室の `study_controls.select_room()` で `room-render-settings.json` の仮視点へ移動し、`lighting.mode`・室別 variant・当該室の照明1灯（既定off対策）を与えて描画。レベルは保存しない。所見：LDK昼夜は白飛び/真っ黒/天井抜け/面重なり無し・器具視認可。R3対応後の洗面はボウルの凹み・洗濯機の丸ドアが視認可。水回り3室は実寸が狭く（洗面/UB 1.82m角、トイレ 0.91m幅）単一視点では画角が窮屈。浴槽内部は中空（正本どおり）。玄関/ホールは奥行0.91mの浅い区画で室内視点の自由度が低い（仮視点、下記「不足・未決定」1）。
- `tests/test_circulation.py`・`tests/test_surface_registry.py`・`tests/test_surface_binding_scope.py`・`tests/test_furniture_assets.py`

## 変更ファイル一覧

- `data/visual/study-scopes.json`：scopeId=guest（8室）
- `data/visual/walkthrough-profiles.json`：guest-circulation の scopeId → scopeIds[guest-pilot, guest]
- `data/visual/surface-registry.json`：6室 × 6面 = 36面を追加（合計52面）
- `data/visual/room-render-settings.json`：残り6室の仮初期視点・既定variant
- `data/visual/asset-bindings.json`：fur-035/001/002/003 の水回り設備バインディング（parametric、estimated）
- `blender/furniture_assets.py`：`toilet_parts`/`vanity_parts`/`washer_parts`/`bathtub_parts` を新設・登録。**v2**：洗面キャビネットを分割してボウル空間を確保、洗濯機ドアを `kind='disc'` 化。
- `blender/build_interior.py`：**v2** `SurfaceBinder` を編集scope内の面だけに限定（R1）、`kind='disc'`（前面の垂直円）の消費を追加（R3）。
- `unreal/circulation.py`：`validate_profiles`/`resolve_profile_for_scope` が `scopeIds`（配列）を受け付け、scope重複主張を拒否
- `unreal/study_controls.py`：`scene_state()` の空室 variant を、**v2** ではマーカー読み戻しではなく管理状態から取得（R2）。
- `data/visual/room-render-settings.json`：**v2** 洗面/トイレ/UB の仮視点を設備が入る画角へ調整。
- `tests/test_circulation.py`（`scopeIds`）、`tests/test_surface_registry.py`（52面 resolve）、**v2** `tests/test_surface_binding_scope.py`（scope限定binding）、`tests/test_furniture_assets.py`（水回り部品：ボウル空間・ドア向き）。
- `docs/ARCHITECTURE.md`・`docs/STATUS.md`・`docs/tasks/W07-staged-design.md`：G3の内容を反映

## 不足・未決定一覧（仮仕様・観測値を推測で上書きしていない箇所）

1. **残り6室の初期視点**（`room-render-settings.json`）は仮設定。実運用時の見え方は未確認。室ごとに調整可能。特に玄関・ホール（奥行0.91m）と水回り3室（洗面/UB 1.82m角、トイレ 0.91m幅）は狭く、単一の室内視点では画角が窮屈になる（昼夜代表画像参照）。
2. **水回り設備の部品寸法・材質**は `estimated`。カタログ外形寸法・向き・位置のみ正本準拠。採用品番・防水仕様は未確認。
   - `furniture.json` の `fur-002`（洗濯機）は `rotation: 0`。この向きだと丸ドア（モデル前面＝ローカル+z）が北側（UB側の壁）を向き、洗面脱衣室内からドア正面が見えません。R3で形状（`kind='disc'` の垂直円）は修正済みですが、**設置向きは正本のままにしています**（推測で回転を変えていません）。実運用時の配置レビューで `rotation` を見直す想定です。
3. **仕上げ**（全室）：既存パレット・模様・粗さの再利用による仮仕様。製品選定・防水確認前。
4. **狭所**：トイレ・UB・収納は実寸のまま内部にカメラ/カプセルが入れない箇所がある。内覧では入口からの確認と制限を案内（壁抜けは通行と呼ばない）。収納の内部が空なのは現行正本どおり（棚の未指定を不具合として埋めていない）。
5. 玄関/ホールの照明はブラケット型の配置インスタンスが正本に無く、`light-bracket` プロファイルは型のみ（既存の制約、G3で変更なし）。

## 残件（次段階へ持ち越し）

1. **W08-G**：施主向けの起動・更新・試用導線（G3受入後）。
2. 自宅（H1〜H4）・全館化・階段・配布パッケージは W07-G3 の範囲外。
3. 手動エディタ視点 `remember_view` の室帰属は activeRoomId 基準（G2-v4 で継続と判定された既知の制限、G3で変更なし）。

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
