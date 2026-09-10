# W07-G2 実装報告：ゲスト室間移動・扉の開閉

- **仕様書**：[W07-G2-guest-circulation.md](W07-G2-guest-circulation.md)
- **前段レビュー**：[W07-G1-review-v2.md](W07-G1-review-v2.md)（ACCEPTED）
- **レビュー履歴**：[v1](W07-G2-review.md)（`89d07af`、CHANGES_REQUESTED）→ [v2](W07-G2-review-v2.md)（`e7d6106`、CHANGES_REQUESTED）→ 本報告（v2のR1〜R3に対応）
- **BASE**：`60d8cd644d00e57f11708dbbb1a1aa263095b2bc`（W07-G2着手時HEAD、W07-G1-v2のHEADと同じ。**v1・v2から変更していません**）
- **HEAD**：`__HEAD__`（`W07-G2-v3: fix review-v2 R1-R3 (immutable slide baseline, walkthrough re-resolution, walls+close+capsule interference)`。本行を記録するdocsコミットがその上に1つ乗ります）
- **提出**：`build/reviews/W07-G2-v3`
- **作業場所**：`build/worktrees/visual-twin`、ブランチ：`feature/visual-twin-foundation`
- **範囲**：G2のみ。G3（残り6室の登録）には着手していません。
- **代表プロジェクト**：`build/W07-G2-blender-v8` → `build/W07-G2-ue-v8`（`unrealImportVerified: true`）、完全refresh `build/W07-G2-refresh-v3`。

## 再レビューv2（R1〜R3）への対応

### R1（高）：引き戸の閉基準が保存・再起動でずれる

**対応：引き戸葉の閉基準を「生成直後に一度だけ捕捉した不変のワールド座標」にし、`door-bindings.json` に `closedLocationCm` として記録。以後どの経路もライブポーズから毎セッション推定しません。**

- `unreal/import_study.py`：インポートは**確実に生成ポーズのシーン**で走るので、その時点で各引き戸葉の閉ワールド座標を捕捉し（`bakedOpen` なら開分を引く）、プロジェクトの `door-bindings.json` の各葉へ `closedLocationCm: [x,y,z]` を書き込みます。`enable-unreal-walkthrough.py` が `walkthrough.json` へそのまま引き継ぎます。
- `unreal/study_controls.py:apply_state()`：`openOffsetCm` 葉は `unreal.Vector(*leaf['closedLocationCm'])`（＋開なら `openOffsetCm`）を**絶対位置**としてセットするだけ。セッションキャッシュ `_door_leaf_closed_location` は撤去しました。
- `unreal/walkthrough/.../Walkthrough.cpp`：`FLeafInfo` に `ClosedLocationCm` を追加し、`ApplyConditions()` はこれを直接参照。`DoorLeafSpawnLocation`（初回ライブポーズ捕捉）は撤去しました。
- レビューが指摘した経路：**閉生成した引き戸を開く→エディタ保存（`save_current_level()` は `.umap` に葉位置も保存）→再起動**でも、閉基準は `door-bindings.json` の固定値なので、開位置を閉と誤認しません。
- **確認**：`verify_w07_g2.py`（UEエディタ）—
  - `slide_leaf_starts_at_closed_baseline`：door-005（引き戸）の閉葉が `closedLocationCm` に一致（<1cm）。
  - `slide_leaf_open_at_baseline_plus_offset`：開葉が `closedLocationCm + openOffsetCm` に一致。
  - `reloaded_session_keeps_door_open` / `reloaded_session_leaf_still_open`：開いて `sc.save()`（`.umap` + `study-state.json`）→`level.load_level()` で**新セッション相当のレベル再読込**→扉状態も葉位置も開のまま。
  - `closing_returns_slide_leaf_exactly_to_closed_baseline`：そこから閉じると葉が `closedLocationCm` へ**厳密復帰**（<1cm）。v1実装ならここで開位置に留まるため、この検証で退行を検出できます。

### R2（高）：エディタの洋室視点が内覧で玄関へ戻る

**対応：`select_room()`/`remember_view()` は `walkthrough` を「解除」でなく「その室へ再解決」して保存。C++ `Restore()` は帰属先の室に保存カメラの実XYが入っているかも照合します。**

- `unreal/study_controls.py`：`_walkthrough_attribution(room_id)` を新設（`walkthrough-profiles.json` を `scopeId` で引き、室が歩行プロファイル内なら `{profileId, roomId, level}` を返す）。`select_room(room_id)` は `state['walkthrough']=_walkthrough_attribution(room_id)`、`remember_view()` は同 `state['activeRoomId']`。編集scope室（LDK・洋室）は必ずプロファイル内なので必ず解決します。v1は `None` にしていたため、C++ が「`walkthrough` 無し＝初回起動」として常に `EntryRoomId`（玄関）を選んでいました。
- `unreal/walkthrough/.../Walkthrough.cpp:Restore()`：既存の `profileId`/`roomId`実在/`level`一致に加え、**保存カメラの実XYが帰属先の室に入っているか**を `InsideRoomPolygon()` で確認。明らかに別の歩行プロファイル室に入っていれば「保存データの内覧位置と視点が一致しません」で拒否（室の縁付近の視点は許容し、別室に確実に入っている場合だけ拒否）。`walkthrough` が本当に無い状態（生成直後）だけが玄関開始です。
- 既存の全室 `roomStates`／`doorStates`／`solar` の保持、F9の「候補扉状態を先に適用してから安全位置探索」は不変。
- **確認**：
  - `verify_w07_g2.py`：`select_room_reresolves_walkthrough_to_that_room`（洋室以外へ `walkthrough` を立てた状態で `select_room('room-1f-06')` → `walkthrough == {profileId:'guest-circulation', roomId:'room-1f-06', level:1}`）、`select_room_camera_is_inside_that_room`（`state['camera']` の実XYがその室ポリゴン内）、`select_room_reresolves_on_switch_back`。
  - ネイティブ `-RyukaSmoke`：`r2EditorAttributionRestoresToThatRoom`（`walkthrough={洋室}`＋洋室内カメラの候補を `Restore()` → `CurrentRoomId==洋室`、玄関ではない）、`r2StaleAttributionRejected`（`walkthrough={洋室}` だがカメラがLDK内 → `Restore()` が false）、`r2NoAttributionIsFirstLaunchGenkan`（`walkthrough` 無し → `CurrentRoomId==EntryRoomId`）。
  - 完全refresh `build/W07-G2-refresh-v3` は**非nullカメラ**（LDK内の視点）を入力にし、`validate_study_transfer.py` が `camera`/`doorStates`/`walkthrough` の一致を照合。

### R3（高）：壁・閉方向・移動途中の施主を含む干渉判定

**対応：`LeafMotionClear()` を `LeafMotionClearFraction()` へ作り直し。壁を検査対象へ戻し、開閉両方向を検査し、開扉は衝突しない最大角へ制限（不可なら拒否）、閉扉は移動途中の施主・家具で拒否します。無効化して押し通す方式は削除しました。**

- **構造壁を検査対象へ**（v1は `wall_`/`Ground_` を一括除外）。除外は「その扉自身の枠・兄弟葉」と「あらゆる扉の枠部材（`opening_*_left/right/head/sill`＝壁体の見切り）」に限定。プローブ半径は「葉厚半分＋2cm」に縮小（人の余裕は葉には不要。通行できる開口幅かは経路の実スイープが判定）。蝶番端は掃かないよう、回転葉は**外側半分だけ**をサンプル（蝶番端は壁面上で枠切れ端をかすめる誤検出源）。引き戸は幅全体を対称サンプル。
- **開閉両方向を検査**。開扉が壁で85度まで許さない場合は、`LeafMotionClearFraction()` の返す割合から**衝突しない最大角の部分開放**を計算し、その角度でも人が通れる開口（葉が掃く後の残り開口 `幅×(1−cos角)` ≥ 48cm）が残るなら**その部分ポーズを適用**、残らなければ**拒否**。閉扉は、閉ポーズ自体は生成時検証済みなので壁は無視するが、**移動途中に施主のカプセルや家具・別の扉の葉があれば拒否**（`InteractDoor()` 経由のトグル時だけ施主カプセルを検査対象に含める。F9復元時など非対話の `ApplyConditions()` では含めない）。
- `ApplyConditions()` のトランザクション：検査は読み取りフェーズで行い、拒否時は状態も葉も触らず `return false`。`InteractDoor()` は拒否時に扉状態・パネル位置を元へ戻し「扉を開閉できません（壁・家具・人が扉の可動範囲にあります）」を表示。
- **door-002 の開き角制限が実装に入った**：west壁（`wall-1f-auto-009`）により **75度で頭打ち**。実装が実際に角度を制限し（v1報告の「壁で制限される」は文言だけで、実装は固定85度を `SetActorRotation` していた）、その角度で開いて通行できることを実機確認。
- **両開きの開く向きの符号（V壁）**：H壁とV壁では葉の沿い軸と掃き軸が入れ替わり、`swingToward` へ向かうyaw符号が反転します。`_swing_delta_deg()` に V壁のときの符号反転を追加しました。修正前は door-024 の両葉が（同一方向ではあるが）**収納側**へ開いていました。修正後は**両葉が洋室側へ開き、収納側から洋室へ歩いて抜けられます**（`-RyukaSmoke` の `doubleSwing_leafYaws: "L=85 R=-85"`、`doubleSwingOpenOrRejectCoherent`）。v1の「fur-007 のコリジョンを一時無効化した開通確認」は撤去しました。
- `FindNearestDoor()` の `Controller->GetControlRotation()` 化・視線トレースでの壁越し扉除外は v1 のまま維持。
- **確認**：`-RyukaSmoke`（v2レビュー R3 指定の代表2件）—
  - `r3CloseRejectedWithPersonInSwing`：door-002 を開けて**LDK側の閉扉アーク内に施主を置き**、閉じようとすると `LeafMotionClearFraction()` が施主カプセルで止め（ブロッカー `{WalkthroughCharacter0}`、`t=0.12`）、扉は**開のまま**・`doorStates` 不変。`r3ClosesOnceSwingClear`：アークから外れると通常どおり閉じる。
  - `r3Door002OpenPoseClearAndWalkable`：door-002 が **75度**の衝突しないポーズで開き（`r3_door002OpenYawDeg: 75.0`）、その開口を歩いて通れる。
  - `tests/test_circulation.py:test_every_swing_leaf_actually_travels_toward_its_swingToward_side`：生成の実回転を再現し、door-002/003/004（H壁）と door-024 両葉（V壁）の自由端の掃き方向が `swingToward` と一致することを検査。pytest 190→**191**。

## 扉・室の接続解決結果（ジオメトリのみ、ラベル不使用）

| 扉ID | 操作 | 接続室（実際） | ラベル上の記載 | 一致 |
|---|---|---|---|---|
| door-001 | 引き戸 | room-1f-01（トイレ）⟷room-1f-24（ホール） | トイレ⟷ホール相当 | 一致 |
| door-002 | 開き戸 | room-1f-06（LDK）⟷room-1f-24（ホール） | 「玄関⟷洗面脱衣室」（誤り） | **不一致（ラベルが古い）** |
| door-003 | 開き戸 | room-1f-03（洗面脱衣）⟷room-1f-04（UB） | 洗面脱衣⟷UB相当 | 一致 |
| door-004 | 開き戸 | room-1f-03（洗面脱衣）⟷room-1f-24（ホール） | 「玄関⟷LDK張り出し」（誤り） | **不一致（ラベルが古い）** |
| door-005 | 引き戸 | room-1f-05（洋室）⟷room-1f-24（ホール） | 洋室⟷ホール相当 | 一致 |
| door-024 | 両開き | room-1f-05（洋室）⟷room-1f-23（収納） | 洋室⟷収納相当 | 一致 |
| door-025 | 開放（扉本体なし） | room-1f-02（玄関）⟷room-1f-24（ホール） | 玄関⟷ホール相当 | 一致 |

開く向きは `swingToward`（共有壁からの到達距離が長い＝部屋の側）で決定。door-024 は洋室側（大きい方）へ両葉が開きます。

## 移動制限・前提

- LDK⟷洋室の直接接続は存在しません（両室ともホール経由）。捏造した直接開口はありません。
- 編集scope（LDK・洋室）と内覧の歩行対象8室は別概念。非編集室では仕上げキーが無効化されます。
- **door-002（LDK⟷ホール）**：west壁により開き角が**75度**で頭打ち（実装が制限する固定幾何制約。開扉・通過は成立）。
- **door-024（洋室⟷収納 両開き）**：現行のゲスト家具配置では、両葉が洋室側へ開いて収納へ抜けられます（`fur-007` の位置は実寸のまま。修正後の符号では `fur-007` はアーク外）。収納は宿泊客の必須動線ではありません。
- エディタメニューに扉トグルの直接操作UIはありません（レビューで不要と明記、フォーム反映は実装済み）。
- `fold`／`double-fold` 操作、残り6室（G3）は今回対象外です。

## 受入条件（AC）結果

「満たす」は**辞書（doorStates/walkthrough等）の一致**と**実シーン（実際の葉transform・実際の歩行）の一致**を区別して記載します。

| AC | 内容 | 結果 | 根拠 |
|---|---|---|---|
| 1 | ゲストの接続・建具bindingsが正本から解決し、ラベル相違に引きずられない | **満たす** | 上表7接続すべてジオメトリのみで解決。`tests/test_circulation.py`（21件）。 |
| 2 | 玄関→ホール→LDK→ホール→洋室を実際に歩いて往復、閉扉は遮り開扉で通過、水回り入口へ到達 | **満たす（実シーン）** | `-RyukaSmoke` の1本の連続スイープで全脚 `true`（NullRHI・DX12 とも PASS、`walkthrough-smoke.png` 取得）。 |
| 3 | 開き戸・引き戸・両開きの葉/衝突がともに移動、壁/対象外を抜けない、閉動作中の干渉を拒否 | **満たす（実シーン）** | door-001/002/005/024 実走行。door-002 は 75度の**衝突しないポーズ**で開き通行可（実装が角度を制限）。閉扉は**移動途中の施主で拒否**（`r3CloseRejectedWithPersonInSwing`）、外れれば閉じる。door-024 は両葉が洋室側へ開き収納へ通行可。引き戸はアウトセット化で壁へ埋め込まれない。 |
| 4 | 洋室相当の編集可能室で保存→別室で扉/仕上げ変更→F9で室・位置・扉・両室状態が戻る | **満たす（実シーン）** | 連続経路内で洋室 Finish2→F5→ホールで door-005 閉→F9。F9後に 現在室＝洋室／door-005 開／`room-1f-05.variant=="warm"`／`room-1f-06.variant=="natural"`（`ac4RestoredRoomPositionDoorAndBothRoomStates`）。 |
| 5 | 旧G1状態/旧LDK案を読込→新版保存。扉を開いた状態で比較A/B/終了を通して扉・他室が不変 | **満たす（辞書＋実シーン）** | `verify_w07_g2.py`：辞書（`compare_*_doors_json_unchanged`）と実葉回転（`compare_a/b/end_real_leaf_still_open` ＝85±1°固定）がともに不変。旧1.0.0単室案の通常読込で `doorStates` が空へ置換され**実葉も閉じる**（`legacy_load_closed_the_real_leaf`）。 |
| 6 | 保存案の開扉状態と位置を完全refresh1回で保持、内覧構築/転送検証まで終了コード0 | **満たす** | `refresh-visual-study.py --previous build/W07-G2-ue-v8 --scope guest-pilot`（前プロジェクトの `study-state.json` に `doorStates:{door-002:{open:true}}`・`walkthrough`・**非nullカメラ**）。`refresh.json` の `status: complete`、終了コード0。生成後の `comparisonState` が `camera`/`doorStates`/`walkthrough` を保持、`validate_study_transfer.py` の一致検証成功。 |
| 7 | 既存検証成功、通行できない狭所/未仕上げ区画/仮定を明示 | **満たす** | `pytest tests/`：**191 passed, 55 subtests**。`build-web-data.mjs --check`・`validate_house.py`/`validate_electrical.py`/`validate_furniture.py`/`validate_openings.py` すべて成功。仮定・限界は「移動制限・前提」「残件」節。 |

## v1で発見・修正済みの実際の不具合（維持）

1. **内部扉の敷居（sill）帯が通行をブロック**：内部扉の敷居帯生成を省略（全種 `sill=0`）。
2. **扉プロンプトが古いラベルを表示**：解決済み接続が指す2室の現在の室名から組み立てるよう修正。

## 実施した検証

### 単体・軽量確認

- `python -m pytest tests/ -q`：**191 passed, 55 subtests passed**（`tests/test_circulation.py` 21件）。
- `node scripts/build-web-data.mjs --check`：最新。
- `python tests/validate_house.py` / `validate_electrical.py` / `validate_furniture.py` / `validate_openings.py`：すべて成功。

### Unreal Engine（実行、代表プロジェクト `build/W07-G2-ue-v8`）

- 実インポート：`unrealImportVerified: true`。C++ Walkthroughモジュールの実コンパイル：`error C`/`error LNK` ともに0。
- ネイティブ `-RyukaSmoke`（NullRHI・DX12）：連続経路＋AC4＋R2 3件＋R3 2件＋両開き、全脚 `true`、`walkthrough-smoke.txt`＝PASS、`walkthrough-smoke.png` 取得。
- UEエディタ `verify_w07_g2.py`（`-run=pythonscript`）：**29項目すべて成功**（＋ビューポート非依存の `remember_view` 1件をヘッドレスのためスキップ、理由記録）。R1-v2の引き戸セッション跨ぎ・R2-v2の `select_room` 再解決とカメラ室内判定・A/B比較中の実葉固定・旧案読込での実葉クローズを含む。
- **完全refresh1回**（`refresh-visual-study.py --previous build/W07-G2-ue-v8 --scope guest-pilot`、非nullカメラ）：`status: complete`、終了コード0、`camera`/`doorStates`/`walkthrough` 一致（`state-transfer-verification.json`）。

## 検証コマンド（実行済み）

```
python -m pytest tests/ -q
node scripts/build-web-data.mjs --check
python tests/validate_house.py
python tests/validate_electrical.py
python tests/validate_furniture.py
python tests/validate_openings.py

python scripts/build-visual-twin.py --blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --interior --scope guest-pilot --output build/W07-G2-blender-v8
python scripts/build-unreal-study.py --engine "C:/Program Files/Epic Games/UE_5.8" --package build/W07-G2-blender-v8 --output build/W07-G2-ue-v8 --cache C:/UE_DDC/w07g2h
python scripts/enable-unreal-walkthrough.py --project build/W07-G2-ue-v8 --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g2h
python scripts/launch-unreal-walkthrough.py --project build/W07-G2-ue-v8 --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g2h --smoke --logic-only
python scripts/launch-unreal-walkthrough.py --project build/W07-G2-ue-v8 --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g2h --smoke
# UEエディタ検証：UnrealEditor-Cmd.exe <v8>/RyukaInterior.uproject -run=pythonscript -script=<v8>/verify_w07_g2.py -unattended -NullRHI ...
python scripts/refresh-visual-study.py --previous build/W07-G2-ue-v8 --output build/W07-G2-refresh-v3 --blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g2refresh3 --scope guest-pilot
```

### 証跡ファイル（実行したスクリプト自体も証跡として記載）

- `build/W07-G2-ue-v8/verify_w07_g2.py` と `build/W07-G2-ue-v8/verify_w07_g2_result.json`（`_all_passed: true`、29項目）
- `build/W07-G2-ue-v8/Saved/walkthrough-smoke.txt`（PASS）、`build/W07-G2-ue-v8/Saved/walkthrough-smoke-route.json`（連続経路＋R2/R3脚）、`build/W07-G2-ue-v8/Saved/walkthrough-smoke.png`（DX12実描画）
- `build/W07-G2-ue-v8/import-verification.json`、`build/W07-G2-ue-v8/door-bindings.json`（`closedLocationCm` 込み、door-024 左85/右-85）
- `build/W07-G2-refresh-v3/refresh.json`（`status: complete`）、`build/W07-G2-refresh-v3/ue/state-transfer-verification.json`
- `tests/test_circulation.py`（21件）

## 変更ファイル一覧（v2差分に対する今ラウンドの追加・変更）

- `unreal/import_study.py`：引き戸葉の閉ワールド座標を生成直後に捕捉し `door-bindings.json` へ `closedLocationCm` を記録（R1）
- `unreal/study_controls.py`：`apply_state()` の引き戸葉を `closedLocationCm` アンカーの絶対位置セットに変更（キャッシュ撤去）、`_walkthrough_attribution()` 新設、`select_room()`/`remember_view()` が `walkthrough` を再解決（R1・R2）
- `unreal/circulation.py`：`_swing_delta_deg()` に V壁の符号反転（R3）、`swing_leaf_free_end_travel()` 新設（掃き方向の幾何検査用）、`validate_door_bindings()` が `closedLocationCm` を検証
- `unreal/walkthrough/Source/RyukaInterior/Walkthrough.h`・`.cpp`：`FLeafInfo::ClosedLocationCm`、`LeafMotionClear()`→`LeafMotionClearFraction()`（壁含む・開閉両方向・部分開放/拒否・対話トグル時のみ施主カプセル）、`Restore()` の保存カメラ室内照合、`DoorLeafSpawnLocation` 撤去、`-RyukaSmoke` に R2 3件・R3 2件・両開き開通の脚を追加（R1・R2・R3）
- `tests/test_circulation.py`：`test_every_swing_leaf_actually_travels_toward_its_swingToward_side` 追加（190→191）
- `build/W07-G2-ue-v8/verify_w07_g2.py`：引き戸セッション跨ぎ（R1-v2）・`select_room` 再解決とカメラ室内判定（R2-v2）を追加
- `docs/ARCHITECTURE.md`・`docs/STATUS.md`：v2対応の内容を反映

## 残件（次段階へ持ち越し）

1. **G3：残り6室の登録**は未着手。
2. **自宅の `fold`／`double-fold` 操作の扉**は今回一般化していない。
3. エディタメニューに扉トグルの直接操作UIは無い（レビューで不要と明記）。
4. door-002 の開き角は west壁により75度で頭打ち（実装が制限する固定幾何制約。開扉・通過は成立）。

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
