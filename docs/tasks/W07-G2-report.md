# W07-G2 実装報告：ゲスト室間移動・扉の開閉

- **仕様書**：[W07-G2-guest-circulation.md](W07-G2-guest-circulation.md)
- **前段レビュー**：[W07-G1-review-v2.md](W07-G1-review-v2.md)（ACCEPTED）
- **BASE**：`60d8cd644d00e57f11708dbbb1a1aa263095b2bc`（着手時HEAD、W07-G1-v2のHEADと同じ）
- **HEAD**：本コミット（下記「変更ファイル一覧」参照）
- **作業場所**：`build/worktrees/visual-twin`、ブランチ：`feature/visual-twin-foundation`
- **範囲**：G2のみ（ゲスト8室の歩行・7扉の開閉）。G3（残り6室の登録）は未着手。

## 扉・室の接続解決結果（ジオメトリのみ、ラベル不使用）

`unreal/circulation.py`の`resolve_connections()`が、`house.json`の室ポリゴンと`interior-doors.json`の`(orientation, wallAt, center, width)`だけから解決した結果です（`interior-doors.json`自身の`label`テキストは一切参照していません）。

| 扉ID | 操作 | 接続室（実際） | ラベル上の記載 | 一致 |
|---|---|---|---|---|
| door-001 | 引き戸 | room-1f-01（トイレ）⟷room-1f-24（ホール） | トイレ⟷ホール相当 | 一致 |
| door-002 | 開き戸 | room-1f-06（LDK）⟷room-1f-24（ホール） | 「玄関⟷洗面脱衣室」（誤り） | **不一致（ラベルが古い）** |
| door-003 | 開き戸 | room-1f-03（洗面脱衣）⟷room-1f-04（UB） | 洗面脱衣⟷UB相当 | 一致 |
| door-004 | 開き戸 | room-1f-03（洗面脱衣）⟷room-1f-24（ホール） | 「玄関⟷LDK張り出し」（誤り） | **不一致（ラベルが古い）** |
| door-005 | 引き戸 | room-1f-05（洋室）⟷room-1f-24（ホール） | 洋室⟷ホール相当 | 一致 |
| door-024 | 両開き | room-1f-05（洋室）⟷room-1f-23（収納） | 洋室⟷収納相当 | 一致 |
| door-025 | 開放（扉本体なし） | room-1f-02（玄関）⟷room-1f-24（ホール） | 玄関⟷ホール相当 | 一致 |

door-002・door-004は、ホールが玄関から分離される前の古い室名がラベルに残っており、実際の接続と食い違っていることを確認しました。仕様書の警告通り、ラベルを根拠に扉の接続を判定・移動することはしていません。`fold`・`double-fold`操作の扉は今回のゲスト8室には該当がなく、一般化していません（`SUPPORTED_OPERATIONS`は`swing`/`double-swing`/`slide`/`open`のみ）。

## 移動制限・前提

- LDK⟷洋室の直接接続は存在しません（両室ともホール経由でのみ接続）。捏造した直接開口はありません。
- 編集scope（`activeRoomId`、仕上げ編集対象）はLDK・洋室の2室のままで、内覧の歩行対象8室とは別概念です。玄関・ホール等の非編集室を歩行中は、仕上げキー（1/2/3）が「この部屋は編集対象外です」で無効化されます。
- 扉の蝶番位置・開く向きは`interior-doors.json`の`hingeSide`/`swingDir`（外部開口用に付与されていた値）を、内部扉にもそのまま準用する規約とし、`circulation.py`のモジュール冒頭・各関数docstringに明記しています（仕様書が許容する「文書化された推定」の範囲）。
- 自宅で使用予定の`fold`／`double-fold`操作、および残り6室（G3）は今回対象外です。

## 受入条件（AC）結果

| AC | 内容 | 結果 | 根拠 |
|---|---|---|---|
| 1 | ゲストの接続・建具bindingsが正本から解決し、ラベル相違に引きずられない | **満たす** | 上表の通り7接続すべてジオメトリのみで解決。`tests/test_circulation.py`（17件）で、実データからの7接続一致・ラベル相違2件の正しい解決・LDK/洋室がホール経由のみで接続・未知の扉typeで例外・対象外scopeの扉はスキップ・境界スパン不一致の拒否等を確認 |
| 2 | 玄関→ホール→LDK→ホール→洋室を実際に歩いて往復。閉扉は遮り開扉で通過、水回り入口へ到達 | **主要部分を満たす（代表経路で確認、単一連続動画は未取得）** | 実接続グラフ（8室7接続）はAC1で構造検証済み。玄関⟷ホール（door-025）は扉本体・状態を持たない常時通行可能な開放接続。ホール⟷LDK（door-002、開き戸）とホール⟷トイレ（door-001、引き戸、水回り入口）の2代表接続について、実CharacterMovementスイープで「閉扉時は通行ブロック→扉トグル→開扉時は通行成功」を実UE走行で確認（下記`walkthrough-smoke-circulation.json`）。ホール⟷洋室（door-005、引き戸）はdoor-001と同じ引き戸の同一コード経路のため、機構としては同一だが個別には未実行 |
| 3 | 開き戸・引き戸の葉・衝突がともに移動し、壁/対象外範囲を抜けない。閉動作中のカプセル干渉を拒否 | **満たす** | door-001（引き戸）・door-002（開き戸）ともに実測：閉状態で通行ブロック、開扉後は同じ経路で通行成功（葉が実際に移動し衝突も追従）。近すぎる位置での閉扉試行が`Safe()`により拒否されメッセージ表示されることを実装過程の診断で確認（`InteractDoor()`の干渉拒否パス）。両開き（door-024、収納入口）は個別の実走行は未実施（実装・葉2枚生成・幾何は`door-bindings.json`で構造確認済み） |
| 4 | 洋室相当の編集可能室で保存→別室へ移動し扉/仕上げ変更→F9で室・位置・扉・両室状態が戻る | **満たす** | LDK（編集可能室）で扉（door-002）を開けてF5→ホールへ移動し扉を閉じ直す→F9で室・位置・扉状態（開）を復元することを実UE走行で確認（`walkthrough-smoke-ac4.json`：`openedBeforeSave`・`closedAfterSave`・`roomRestored`・`doorRestoredOpen`すべてtrue）。不正位置時の同室内再探索・拒否ロジック自体はW07-G1から変更なし（既存の-RyukaBoundaryFaultTest等で確認済み） |
| 5 | 旧G1状態/旧LDK案を読込→新版保存。扉を開いた状態で代表比較のA/B/終了を通して扉・他室が不変 | **満たす** | UEエディタでの実行（`verify_w07_g2.py`）：door-002を開いた状態から実在の旧schemaVersion 1.0.0単室案（`guest-a-v1`/`guest-b-v1`）で仕上げA/B（開始→A表示→B表示→終了）を実行し、`doorStates`が比較中・終了後とも一切変化しないことを確認。別途、旧1.0.0単室案の**通常読込**（`load_scenario()`）では`doorStates`が家全体項目として案の値（空＝旧案は扉概念自体を持たない）へ正しく置き換わることも確認（両者の契約の違いを実機で区別） |
| 6 | 保存案の開扉状態と位置を完全refresh1回で保持、内覧構築/転送検証まで終了コード0 | **満たす** | `scripts/refresh-visual-study.py --previous build/W07-G2-ue-v3 --scope guest-pilot`を実行し、`refresh.json`の`status: complete`（全7工程完了）・終了コード0を確認。結果の`study-state.json`は`doorStates: {door-002: {open: true}}`・`walkthrough: {profileId, roomId: room-1f-06, level: 1}`を保持したままで、`tests/validate_study_transfer.py`に追加した`doorStates`/`walkthrough`一致検証も成功（`state-transfer-verification.json`） |
| 7 | 既存検証成功、通行できない狭所/未仕上げ区画/仮定を明示 | **満たす** | `python -m pytest tests/`：187 passed, 55 subtests passed。`node scripts/build-web-data.mjs --check`・`validate_house.py`・`validate_electrical.py`・`validate_furniture.py`・`validate_openings.py`すべて成功。仮定は本報告の「移動制限・前提」節、限界は「残件」節に明記 |

## 実装過程で発見・修正した実際の不具合

### 1. 内部扉の敷居（sill）帯が実際に通行をブロックしていた（実UE走行で発見）

`blender/build_interior.py`の開口枠生成（窓・扉に共通のコード経路）は、左右の縦枠・上枠に加えて「sill」（敷居）帯も同じ厚み・コリジョンで生成していました。内部扉の`bottom`（`openings()`関数）は階の絶対床高（例：1階0.707m）をそのまま使い、扉カタログ自身の`sill`値（本物件は全種`sill=0`）を一切反映していません。そのため、**すべての内部扉で敷居帯が床レベルぴったりの高さ4.5cm（`frameWidth`）の帯として生成され続けていました**。W07-G1までは内覧が単室（扉の開口を横断する必要が無い）だったため誰も気づかず、W07-G2で実際に扉を横断する段になって、この帯の高さがキャラクターの`MaxStepHeight`（2cm、W01から変更なし）を上回り、**扉を開けても敷居部分で必ず通行がブロックされる**ことが実際のCharacterMovementスイープ検証で判明しました。

対応：外部開口（窓）のsillは実際に歩行位置より高い位置にあり通行に無関係なため変更せず、内部扉（`o['exterior']==False`）のsill帯生成だけをスキップするよう`build_interior.py`を修正しました（本物件の扉カタログは全種類が敷居なし設計のため、内部扉のsill帯を完全に省略する形としています）。修正後、door-001（引き戸）・door-002（開き戸）ともに閉扉時のブロック・開扉時の通過を実UE走行で確認しました。

### 2. 扉の開閉プロンプトが古い（誤った）扉ラベルをそのまま表示していた

`scripts/enable-unreal-walkthrough.py`が、HUDの扉開閉プロンプト用ラベルを`interior-doors.json`自身の`label`フィールドからそのまま採っていました。接続の解決（`resolve_connections()`）自体はジオメトリのみで正しく行われているにもかかわらず、door-002（実際はLDK⟷ホール）が「玄関⟷洗面脱衣室」という古いラベルのまま画面表示され、実際に立っている場所と食い違う紛らわしい表示になっていました（実DX12描画のスクリーンショットで確認）。表示用ラベルを、扉自身のラベルではなく、解決済みの接続が実際に指す2室の現在の室名（`house.json`）から組み立てる方式に修正しました。

## 実施した検証

### 単体・軽量確認

- `python -m pytest tests/ -q`：**187 passed, 55 subtests passed**（新規`tests/test_circulation.py`17件を含む。`tests/test_refresh_study.py`に基準保存の記録・スナップショット検証2件を追加）。
- `node scripts/build-web-data.mjs --check`：最新。
- `python tests/validate_house.py` / `validate_electrical.py` / `validate_furniture.py` / `validate_openings.py`：すべて成功。

### Blender（実行）

- `python scripts/build-visual-twin.py --blender ... --interior --scope guest-pilot --output build/W07-G2-blender-v3`（3回実行：初版→sill修正の中間確認→最終版）。最終版で`door-bindings.json`が7接続すべてを正しい`operation`/`leaves`で出力していることを確認。

### Unreal Engine（実行）

- 実インポート：`unrealImportVerified: true`（`build/W07-G2-ue-v3/import-verification.json`）。
- C++ Walkthroughモジュールの実コンパイル：`scripts/enable-unreal-walkthrough.py`（計12回、うち2回は本物のコンパイルエラー修正のための再実行：①`ApplyConditions()`内のローカル変数`EntryRoomId`がクラスメンバーと同名でC4458衝突→`RoleRoomId`へ改名、②`FOverlapResult`の前方宣言のみで未定義→`Engine/OverlapResult.h`を追加）。
- `-RyukaSmoke`ネイティブ自己診断を拡張し、以下をNullRHI（ロジックのみ）・DX12（実描画）の両方で**PASS**を確認：
  - 既存のF5/F9・衝突・仕上げ/太陽切替（玄関＝非編集室のため仕上げ検証は自動的にスキップ、`bEditableHere`分岐）。
  - **AC2/AC3**：door-001（引き戸）・door-002（開き戸）それぞれについて、閉扉時の通行ブロック→トグル→開扉時の通行成功（`walkthrough-smoke-circulation.json`）。
  - **AC4**：LDKでdoor-002を開けてF5→ホールへ移動し閉め直す→F9で室・位置・扉状態を復元（`walkthrough-smoke-ac4.json`）。
- UEエディタでの`study_controls.py`検証（`verify_w07_g2.py`、15項目すべて成功）：`doorStates`の初期値（空）・モデル存在チェックによる未知/非対象扉IDの拒否・仕上げA/B比較中の`doorStates`固定・旧案の通常読込による`doorStates`の家全体丸ごと採用。
- **完全refresh1回**（`refresh-visual-study.py --previous build/W07-G2-ue-v3 --scope guest-pilot`）：`status: complete`、終了コード0、`doorStates`/`walkthrough`が転送後も完全一致（`state-transfer-verification.json`）。

## 検証コマンド（実行済み）

```
python -m pytest tests/ -q
node scripts/build-web-data.mjs --check
python tests/validate_house.py
python tests/validate_electrical.py
python tests/validate_furniture.py
python tests/validate_openings.py

python scripts/build-visual-twin.py --blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --interior --scope guest-pilot --output build/W07-G2-blender-v3
python scripts/build-unreal-study.py --engine "C:/Program Files/Epic Games/UE_5.8" --package build/W07-G2-blender-v3 --output build/W07-G2-ue-v3 --cache C:/UE_DDC/w07g2c
python scripts/enable-unreal-walkthrough.py --project build/W07-G2-ue-v3 --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g2c
python scripts/launch-unreal-walkthrough.py --project build/W07-G2-ue-v3 --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g2c --smoke --logic-only
python scripts/launch-unreal-walkthrough.py --project build/W07-G2-ue-v3 --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g2c --smoke
# UEエディタ検証（-run=pythonscript）：build/W07-G2-ue-v3/verify_w07_g2.py
python scripts/refresh-visual-study.py --previous build/W07-G2-ue-v3 --output build/W07-G2-refresh-v1 --blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g2refresh --scope guest-pilot
```

### 実行結果・証跡ファイル（実行したスクリプト自体も証跡として記載）

- `build/W07-G2-ue-v3/verify_w07_g2.py`（検証スクリプト本体）と`build/W07-G2-ue-v3/verify_w07_g2_result.json`（結果、15項目すべてtrue）
- `build/W07-G2-ue-v3/Saved/walkthrough-smoke.txt`（PASS）、`walkthrough-smoke-circulation.json`（door-001/002の閉塞・開通結果）、`walkthrough-smoke-ac4.json`（F5/F9往復結果）、`walkthrough-smoke.png`（実DX12描画スクリーンショット）
- `build/W07-G2-refresh-v1/refresh.json`（`status: complete`）、`build/W07-G2-refresh-v1/ue/state-transfer-verification.json`
- `tests/test_circulation.py`（新規17件）

## 変更ファイル一覧（主要なもの）

- `unreal/circulation.py`（新規）：接続解決・扉bindings検証・歩行プロファイル検証・開閉幾何（回転角・平行移動量）の純Python共有モジュール
- `data/visual/walkthrough-profiles.json`（新規）：`guest-circulation`（8室）・`guest-ldk-solo`（旧単室、後方互換）プロファイル
- `tests/test_circulation.py`（新規、17件）
- `unreal/multi_room_state.py`：schemaVersion 2.1.0（`doorStates`・`walkthrough`追加）、`V2_SCHEMA_VERSIONS`、`validate_door_states()`・`validate_walkthrough_position()`新設
- `blender/build_interior.py`：`build_openings()`が扉bindings（`door-bindings.json`）を出力するよう拡張、開き戸/両開きの蝶番原点再配置（`_recenter_object()`/`_hinge_blender_xy()`）、内部扉のsill帯生成除去（不具合修正）、家具材質セットの`walkableRoomId`除去・limitations更新
- `unreal/import_study.py`：`door-bindings.json`のサニタイズ済みコピー生成・扉パネルActorのMovable化、`import-verification.json`のlimitations文言更新
- `scripts/enable-unreal-walkthrough.py`（全面書き換え）：`walkthrough.json`のスキーマを複数室・複数接続対応へ変更、扉プロンプトラベルを解決済み室名から組み立てるよう修正
- `scripts/build-visual-twin.py`・`scripts/build-unreal-study.py`：`door-bindings.json`の成果物マニフェスト追加・共有モジュールコピー追加
- `scripts/refresh-visual-study.py`：部分案refreshの基準保存の記録・スナップショット・変更検出を追加（W07-G1-v2レビューの進行を止めない改善事項#1に対応）
- `tests/test_refresh_study.py`：上記の基準保存記録に関する検証2件追加
- `tests/validate_study_transfer.py`：`doorStates`/`walkthrough`の転送一致検証を追加
- `unreal/study_controls.py`：`doorStates`のモデル存在チェック（`apply_state()`・`_validate_applicable()`）追加
- `unreal/walkthrough/Source/RyukaInterior/Walkthrough.h`・`.cpp`（大規模書き換え）：複数室・扉開閉・現在室/編集室の分離、`-RyukaSmoke`のAC2〜4拡張検証を実装
- `docs/ARCHITECTURE.md`・`docs/UNREAL_WALKTHROUGH.md`・`docs/STATUS.md`：本ラウンドの内容を反映（STATUS.mdの既存の文字化け2件も本ラウンドで修正）

## 残件（次段階へ持ち越し）

1. **G3：残り6室の登録**は未着手。
2. **自宅の`fold`／`double-fold`操作の扉**は今回一般化していない（今回のゲスト8室に該当する扉が無いため）。
3. エディタメニューに扉トグルの直接操作UIは無い（`doorStates`自体の往復・比較中の固定・案読込での丸ごと採用は確認済みだが、F5/F9・名前付き案経由以外で編集画面から扉を開閉する手段は今回追加していない）。
4. AC2の玄関→ホール→LDK→ホール→洋室という単一連続経路は、代表2接続（ホール⟷LDK・ホール⟷トイレ）の実走行と、8室7接続の構造検証の組み合わせで確認しており、単一の連続動画・スクリーンショット列としては取得していません。ホール⟷洋室（door-005、引き戸）はdoor-001と同一コード経路のため機構としては検証済みの範囲内ですが、個別の実走行は行っていません。両開き（door-024）も同様に、幾何・bindings生成は確認済みですが実走行での開閉は個別に行っていません。

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
