# W08-G 実装報告：ゲスト試用版の起動・更新・比較記録（v2）

- **仕様書**：[W08-G-guest-delivery.md](W08-G-guest-delivery.md)
- **前段レビュー**：[W07-G3-review-v2.md](W07-G3-review-v2.md)（ACCEPTED、HEAD `1d6a11b`）
- **本レビュー**：[W08-G-review.md](W08-G-review.md)（v1＝CHANGES_REQUESTED、R1〜R3）。本 v2 で一括対応。
- **BASE**：`1d6a11bb4f035b4aabaf9209766f54c677f18cc3`（W08-G着手時HEAD。v1から不変。着手時の未コミットの受入記録・仕様・STATUSは `224e7d7` で保持）
- **HEAD**：`361f74f`（v1: 〜`d6f17d8` → `ca2e876`〔v1レビュー記録〕→ `24e9466`〔R1〜R3コード修正〕→ 代表確認・報告更新・本SHA記録）
- **提出**：`build/reviews/W08-G-v2`
- **作業場所**：`build/worktrees/visual-twin`、ブランチ：`feature/visual-twin-foundation`（merge/pushはしていません）
- **範囲**：既存CLIとUE機能を薄いランチャーでまとめる。UE不要の配布exe・全館/階段・クラウド公開・採用品の精密モデル化は対象外。W07-H1以降は未着手。

## 起動入口（実パス）

| 種類 | パス | 説明 |
|---|---|---|
| ダブルクリック入口 | `guest-launcher.cmd`（ワークツリー直下） | `py -3` または `python` を探し、`scripts/guest_launcher/__main__.py` を起動。cwd非依存でワークツリー基準にパス解決。空白・日本語パスで動作 |
| GUI本体 | `scripts/guest_launcher/`（Python標準ライブラリ＋tkinter） | 新しいアプリ基盤・サーバー・インストーラーは作っていません |
| 補助CLI（実装者の操作確認・CI用） | `python scripts/guest_launcher/__main__.py <status\|detect\|furniture-report\|furniture-apply\|update-plan\|update\|scenario-save\|scenarios\|record-ab\|shared-copy>` | 施主の日常操作はGUI |

## 保存先

| 種類 | パス | git |
|---|---|---|
| 機械固有設定（エンジン/Blender/cache、選択中モデル、登録モデル、最新更新出力） | `build/launcher/config.json` | 除外（`.gitignore` の `build/`）。モデル参照は可能ならワークツリー相対 |
| 正本反映前の復元用コピー | `build/launcher/backups/furniture-<日時>.json` | 除外 |
| ログ | `build/launcher/logs/` | 除外 |
| 比較記録（画像＋条件） | `build/launcher/comparisons/<日時>/` | 除外 |
| 保存した案 | `build/scenarios/<名前>/`（既存 save_scenario_package と同じ） | 除外 |
| モデル更新の出力 | `build/W08-G-update-<日時>/`（前モデル・案は上書きしない） | 除外 |

## 再利用した既存の仕組み（契約は複製していません）

| 機能 | 呼び出す既存資産 |
|---|---|
| 内覧 | `scripts/launch-unreal-walkthrough.py`（`--smoke` なし＝描画付き） |
| 編集・比較 | `UnrealEditor.exe <uproject>`（面編集・A/Bは『ツール → 内装比較』） |
| モデル更新 | `scripts/refresh-visual-study.py`（`--previous`/`--scope guest`/`--output`）、`scripts/source_changes.py`（入力差分） |
| 案の保存 | `scripts/refresh_inputs.save_scenario_package()`（F5/エディタ保存の選択・検証は既存の `retained_inputs()`） |
| 案の一覧 | `scripts/list-study-scenarios.py` の `describe()` |
| 家具検証 | `tests/validate_furniture.py` の `validate(catalog, furniture, house)`（同じ検査を候補へ適用できるよう関数化） |
| Web生成データ | `node scripts/build-web-data.mjs`（`--write` で再生成、`--check` で最新確認） |
| 仕上げA/B撮影 | `scripts/capture-unreal-study.py`（`--variant`/`--elevation`、レベル非保存） |

## 各節の実装

### 1. 安定した入口とモデル選択

- `guest-launcher.cmd` を1つだけ用意。README（本報告と `docs/GUEST_TRIAL_GUIDE.md`）から示します。
- パス解決は `scripts/guest_launcher/paths.py:ROOT`（`Path(__file__).parents[2]`）。cwdに依存しません。外部CLIは `runner.run_logged(argv, ...)`（`shell=False`、引数配列）。パス・案名をシェルコードへ連結しません。
- 状態表示：現在のモデル（相対パス・有効/要確認・更新日時・メッシュ数）、保存状態（schema・日時。未保存なら明示）、依存の不足（日本語で不足箇所と次の操作）、エンジン/Blender/cache。
- ボタン：内覧を開く／編集・比較を開く／家具JSON取込／モデル更新／案と比較記録／モデルを選ぶ／設定／使い方。
- 初回：`models.detect_candidates()` が `build/` 直下（`*/RyukaInterior.uproject` と `*/ue/RyukaInterior.uproject`）を検出し、`import-verification.json` の `scopeId==guest` ＋ `unrealImportVerified` ＋ `walkthrough-verification.json` の `configured` を**実際に確認**。日付・名前だけで最新版と判定しません。要確認の理由も一覧に出します。
- 機械固有設定は `build/launcher/config.json`（git除外）。`set_current_model()` は相対パスで保存し登録もします。再起動後に選択と案を復元。
- 依存不足時：`config.missing_dependencies()` が「Unreal Engine が見つかりません（…）。「設定」でエンジンの場所を指定してください。」等を返します。

### 2. 内覧・編集・保存した案

- 「内覧を開く」＝ `launch-unreal-walkthrough.py`（`--smoke` なし）。smoke/verify/初期化スクリプトは通常起動に使いません。ランチャーは `study-state.json` を書かないので、保存したF5状態を基準状態で上書きしません。
- 操作キーは `walkthrough.WALKTHROUGH_KEYS` と `docs/GUEST_TRIAL_GUIDE.md` を実コード（`Walkthrough.cpp` の HUD 文言・`study_controls`）に合わせています。
- 「編集・比較を開く」＝ UEエディタ起動。面編集・詳細比較はエディタ側『ツール → 内装比較』へ誘導。ランチャーへ再実装していません。
- 案：`scenarios.list_scenarios()`（名前・対象範囲・保存日時・メモ・室:仕上げ）。「現在の保存を案にする」＝ `save_current_as_scenario()` → `save_scenario_package()`。保存元はF5/エディタの最新の有効な保存を既存共通処理が選択（未保存の画面状態は不可）。slug 衝突は `-2`,`-3`。既存案を上書きしません。読込・比較は既存メニュー/CLIへの導線を文言で提示（一覧表示だけで終わらせない）。
- ゲストの案は自宅生成と分離（`build/scenarios/`）。明示的に選んだ案以外を自動適用しません。旧scopeの案は既存の部分適用契約（`partial_apply`）に従います。

### 3. 家具JSONの取込と正本への反映

- 対象は Three.js「⬇ furniture.jsonを書き出す」の出力のみ。`furniture.read_candidate()` が `schemaVersion 1.0.0 / units m / items 配列` を先に確認し、house/電気/建具JSONは拒否。
- `furniture.build_report()`：現行正本と**全件差分**（ID単位の追加/削除/変更、追跡フィールド `type/room/label/level/x/z/rotation/*Override/elevation/status/note`）。ゲスト対象/ゲスト外を区別表示。削除件数・note/status が消える項目を明示。**検証前に正本を一切変更しません**。
- 検証：`validate_furniture.validate()`（ID重複・未知型・不正な寸法/室参照・階の食い違い）＋ `_asset_binding_warnings()`（asset-bindings.json が参照する家具の消失・型不一致を事前検出。更新成功前に未対応型を対応済みに見せない）。不正は正本変更前に `ok=False` で拒否。
- `furniture.apply_candidate()`：直前正本を `build/launcher/backups/` へコピー → `data/furniture.json` を一時ファイル経由で置換 → `node scripts/build-web-data.mjs`。node失敗時は `applied=True, webDataRegenerated=False` と実状態を返し「正本反映済み／Web生成失敗」を案内（途中を完了扱いしない）。`restore_backup()` で戻せます。
- **軽量確認（実行済み）**：現行 `data/furniture.json` から fur-047 を +0.05m 移動・fur-036 に `heightOverride: 0.9` を付けた候補で `furniture-report`（変更2件、`ok`）→ `furniture-apply`（`data/furniture.json` 置換・`generated/house-data.js` 再生成・`validate_furniture.py`／`build-web-data.mjs --check` 成功）→ `furniture-restore` で完全に復元。未知型の候補は `ok=False`（`fur-045: 未知のtype…`）で正本不変、`apply_candidate` も ValueError。

### 4. モデル更新と失敗時の復帰

- `update.plan_update()`：`source_changes.compare()` で rooms/furniture/catalog/照明設定の追加・削除・変更＋参照切れ、変更された入力ファイル数を表示。取込直後は「取込 ≠ UE反映」＝「モデル更新が必要」と区別。
- `update.run_update()`：`refresh-visual-study.py --previous <選択> --output build/W08-G-update-<日時> --scope guest`。`--previous` の最新の有効な保存（エディタ保存と内覧F5保存の新しい方）を既存 `retained_inputs` が選ぶ。既定で `--gallery` なし。前モデル・案は上書き/削除しません。工程名（`01-source-check`…`04-state-check`）・実行中/成功/失敗・経過秒・ログを表示。根拠のない進捗率は出しません。GUIはスレッド実行で応答継続。同一キー `model-update` の二重起動を `runner.BackgroundJob` が防止。既存refreshの入力変更検知（`unchanged()`）は維持。
- 切替は **終了コード0 ＋ `refresh.json` の `status: complete` ＋ `models.inspect_project(<out>/ue).valid` ＋ `state-transfer-verification.json` の `statePreserved`/`geometryVerified`** を確認してから。失敗時は工程・理由・ログ・`refresh.json` を示し、前モデルと案を維持。「モデルを選ぶ」で前モデルへ戻せます。中断/再起動で確定できないジョブは成功扱いしません（`refresh.json` の `status` と `import-verification.json` を照合）。
- **代表確認（実行済み・v2）**：`--previous` は `build/W08-G-update-v2/ue`。まず 施主がLDKでF5保存した状態に相当する編集保存（全室 natural・LDK視点）に加え、**内覧のF5保存に相当する `Saved/walkthrough-state.json`（新しい方）** を用意した：`activeRoomId: room-1f-03`（洗面脱衣へ移動）、LDK=warm・洗面脱衣=reference・UB=warm、`doorStates: {door-002: open}`、洗面脱衣の照明 elec-004 on、手動太陽 55°、洗面脱衣視点カメラ。ランチャーから `update build/W08-G-update-v2/ue --output build/W08-G-update-v3` → 既存 `refresh_inputs.retained_inputs` が**新しい方（F5保存）を選択**、全7工程 complete、`unrealImportVerified: true`、`walkthrough configured`、`state-transfer-verification.json` すべて true。更新後モデルは `activeRoomId: room-1f-03`・LDK warm/洗面 reference/UB warm・`doorStates: {door-002: open}`・洗面照明 on・手動太陽55°・洗面視点を保持、`door-bindings.json` の door-002 は `bakedOpen: true`／`openYawDeltaDeg: 73.0`（開扉が実ジオメトリにベイク）。 現行モデルが `build/W08-G-update-v3/ue` へ切替。**簡単な失敗確認**：`import-verification.json` が未検証の壊れた `--previous` を指定 → 重い生成前に `ok=False, status: failed`、`config.json` の `currentModel` は不変。
  - 旧参考（v1）：`--previous build/W07-G3-ue-v2` で全室 natural の基準状態から `build/W08-G-update-v2` を作成（`build` 配下の保存状態は git 除外の作業入力）。**簡単な失敗確認**：`import-verification.json` が未検証の壊れた `--previous` を指定 → 重い生成前に `ok=False, status: failed`、`config.json` の `currentModel` は不変。

### 5. 比較記録と共有用出力

- `comparison.record_finish_ab()`：**撮影開始時に、案保存と同じ共通処理（`refresh_inputs.retained_inputs`）でエディタ保存と内覧F5保存の新しい方を1つ選び検証**し、その状態（部屋・視点・fixtures・扉・太陽/来歴）を `selected-state.json` に固定。`capture-unreal-study.py --state`（新設）へ渡し、A と B の差は**対象室（activeRoomId）の仕上げだけ**。太陽高度は保存値のまま（v1 の無断45°を撤回）。`_verify_ab()` が両撮影の条件を選んだ保存と突き合わせ（対象室 variant 以外の視点・他室・fixtures・扉・太陽が一致するか）。撮影失敗・条件不一致は `ok=False`。元の保存ファイル（`study-state.json`／`Saved/walkthrough-state.json`）は書き換えません。
- `comparison.build_shared_copy()`：記録から**画像＋許可リストの条件のみ**を新規フォルダへ出力。許可キーは `schemaVersion/scopeId/activeRoomId/activeLevel/camera/azimuthDeg/elevationDeg/exposureEV100/lighting/roomStates` ＋ 導出した対象室ラベル・日時/手動太陽・仮仕様注記。出力前に JSON を走査し、`site.local.json`/`site-context.json`/`latitudeDeg`/`longitudeDeg`/絶対パス/`sourceHashes`/`projectFingerprint`/`sha256` 等が含まれていたら**全体を消して中止**。案名・メモは利用者の文章として `shared.json`/`README.txt` に出力（利用者が事前確認）。ネットへの自動公開・送信はしません。
- **代表記録（実行済み・v2）**：`build/W08-G-update-v2/ue` にエディタ保存（全室natural）と、それより新しい F5 相当保存（洗面脱衣へ移動・LDK warm/洗面 reference/UB warm・door-002 open・洗面照明 on・手動太陽55°）を用意 → `record-ab` → **F5保存が選択**（`record.json` の `selectedSave.source: 内覧のF5保存`）。両撮影の条件が F5保存と一致（活性室 room-1f-03、camera `[135,355,225.7]`、elev **55**（45でない）、`doorStates: {door-002: open}`、洗面照明 on、LDK warm/UB warm）。**natural/warm の差は洗面脱衣（対象室）の variant のみ**（natural.json→`room-1f-03: natural`、warm.json→`room-1f-03: warm`、他室不変）。撮影後に `study-state.json`／`walkthrough-state.json` の SHA-256 が不変。記録は `build/launcher/comparisons/20260911-084022/`。`shared-copy` → `build/W08-G-shared-v2`（画像2枚＋許可リスト条件のみ。禁止語走査でクリーン）。

### 6. 試用ガイドと既知の制限

- `docs/GUEST_TRIAL_GUIDE.md` に最短起動・操作キー・保存と案の違い・家具取込/更新・比較記録・失敗時の戻り方をまとめ、画面の名前と一致させています。
- G3から引き継ぐ制限：洗濯機（fur-002）の正本 `rotation: 0` で丸ドアが壁側／狭所（トイレ・UB・収納・玄関・ホール）／未確定製品・仮材質・未校正照明。**設置方向は推測で変えていません**。
- G3報告 AC5/6 の refresh-v2 条件を実出力（全室 natural・面上書き/fixtures 空・`doorStates: {}`・`bakedOpen: false`・camera 非null）へ訂正済み（`W07-G3-report.md`、コミット `224e7d7`）。開扉・室ごとに異なる仕上げ/点灯の転送は W07-G3-v1 で確認済みで、転送ロジックに変更はありません。G3受入記録（`W07-G3-review-v2.md`）は保持。

## 受入条件（AC）結果

| AC | 結果 | 根拠 |
|---|---|---|
| 1 | **満たす** | `guest-launcher.cmd` ダブルクリック → 選択済みguestを内覧起動。`config.json`（git除外）に選択・登録が残り、ランチャー再起動後も `status`/`detect` で復元。OS再起動は不要。 |
| 2 | **満たす** | 家具JSONの差分確認 → 反映。移動/寸法変更/既存型追加が検証を通り、不正JSON1件は正本不変で拒否。検証用家具は正本へ残さず復元。 |
| 3 | **満たす** | 更新成功で新モデルへ切替（`build/W08-G-update-v3/ue`）。壊れた `--previous` 1件では重い生成前に失敗し、前の成功先と案を維持。新旧入力ハッシュ・実条件を記録。更新画面を閉じても切替は `LauncherApp.apply_update_success` で完了（review R3）。 |
| 4 | **満たす（v2で実施）** | 代表更新の `--previous`（`build/W08-G-update-v2/ue`）の最新保存に**新旧室で異なる仕上げ**（LDK warm/洗面 reference/UB warm）・**点灯**（洗面 elec-004 on）・**開扉**（door-002 open）・**非nullの安全な視点**（洗面視点）を含め、`retained_inputs` がその F5保存を選択して更新。`build/W08-G-update-v3` は `state-transfer-verification.json` すべて true、door-002 が `bakedOpen: true`／`openYawDeltaDeg: 73.0` で再生成され、洗面照明 on・LDK warm 等も保持。基準状態へ戻す試験スクリプトは通常更新に流用していません。 |
| 5 | **満たす** | `save_current_as_scenario()` の関連テスト＋実操作（`build/scenarios/W08-G試用テスト`、scope guest・8室・保存元 editor）。再起動後に `scenarios` から一覧。仕上げA/B1組を条件付きで記録。 |
| 6 | **満たす** | 共有用コピーに許可リストの比較条件があり、絶対パス/座標/生ログ/元JSONは含まれない（`test_guest_launcher.py` の無害化テスト＋代表記録）。 |
| 7 | **満たす（画質・使用感は施主確認待ち）** | `docs/GUEST_TRIAL_GUIDE.md` で一連の試用が可能（「編集対象外」の pilot 時代の記述を guest 8室すべて編集対象へ訂正）。依存不足時に `missing_dependencies()` が次の操作を提示。画質・使用感は施主確認待ち。 |

## 実施した検証

- `python -m pytest tests/ -q`：**221 passed, 55 subtests**（`tests/test_guest_launcher.py` の20件を含む。R2の反映前sha照合、R3の `_drain_queue` 分離・`apply_update_success` の窓非依存・更新中のアプリ終了ブロックを追加。設定往復・モデル検証・家具候補の差分/検証/反映/復元・共有コピー無害化）。
- `python tests/validate_house.py` / `validate_furniture.py` / `validate_electrical.py` / `validate_openings.py` / `node scripts/build-web-data.mjs --check`：すべて成功。
- 補助CLIによる実操作：`status`・`detect`・`furniture-report`（sha付き・正常/不正）・`furniture-apply`（sha一致で反映・sha不一致で拒否）＋`furniture-restore`・`scenario-save`・`scenarios`・`update-plan`・`update`（成功2〔基準状態／変わったF5保存〕・失敗1）・`record-ab`（F5保存を選択）・`shared-copy`。
- GUI：tkinter でウィンドウ構築（`LauncherApp` 生成→`update()`）まで確認。施主による試用・画質評価は未実施（「施主確認待ち」）。

### 検証コマンド（実行済み）

```
python -m pytest tests/ -q
python tests/validate_house.py && python tests/validate_furniture.py && python tests/validate_electrical.py && python tests/validate_openings.py
node scripts/build-web-data.mjs --check

python scripts/guest_launcher/__main__.py detect
python scripts/guest_launcher/__main__.py furniture-report <候補furniture.json>
python scripts/guest_launcher/__main__.py furniture-apply <候補> --backup-dir <一時>
python scripts/guest_launcher/__main__.py furniture-restore <控え>
python scripts/guest_launcher/__main__.py scenario-save build/W07-G3-ue-v3 "W08-G試用テスト" "..."
python scripts/guest_launcher/__main__.py update build/W08-G-update-v2/ue --output build/W08-G-update-v3   # 変わったF5保存を選択
python scripts/guest_launcher/__main__.py furniture-apply <候補> --expect-source-sha <sha> --expect-candidate-sha <sha>
python scripts/guest_launcher/__main__.py record-ab build/W08-G-update-v2/ue "洗面脱衣 仕上げA/B（F5保存から）" "..."
python scripts/guest_launcher/__main__.py shared-copy build/launcher/comparisons/<日時> <出力先>
```

## 証跡ファイル

- `build/W08-G-update-v3/refresh.json`（`status: complete`、全7工程）・`ue/import-verification.json`・`ue/state-transfer-verification.json`・`ue/walkthrough-verification.json`・`ue/study-state.json`（F5保存由来の変わった条件）
- `build/launcher/comparisons/20260911-084022/record.json`（`selectedSave.source: 内覧のF5保存`）＋`capture/`（natural.png/warm.png＋条件）・`selected-state.json`、`build/W08-G-shared-v2`（共有用コピー）
- `build/scenarios/W08-G試用テスト/scenario.json`
- `scripts/guest_launcher/`・`guest-launcher.cmd`・`tests/test_guest_launcher.py`・`docs/GUEST_TRIAL_GUIDE.md`
- 機械固有パスはローカル証跡（`build/launcher/logs/`、`config.json`）に留め、本文書は相対パス・汎用記述。

## 変更ファイル一覧

- `scripts/guest_launcher/`（新規、13ファイル）：`paths`/`config`/`models`/`runner`/`furniture`/`scenarios`/`update`/`comparison`/`walkthrough`/`app`/`__main__`/`__init__`
- `guest-launcher.cmd`（新規、ダブルクリック入口）
- `tests/validate_furniture.py`：`validate(catalog, furniture, house)` を関数化（`main()` はこれを呼ぶ。既存テストは不変で通過）
- `tests/test_guest_launcher.py`（新規）
- `docs/GUEST_TRIAL_GUIDE.md`（新規）
- `docs/ARCHITECTURE.md`・`docs/STATUS.md`：W08-Gランチャーを反映
- `docs/tasks/W07-G3-report.md`：AC5/6 の refresh-v2 条件を実出力へ訂正（`224e7d7`）
- `scripts/capture-unreal-study.py`：`--state`（撮影する状態を呼び出し側が選ぶ）を新設。
- `unreal/capture_study.py`：`--state` パスで `current_state()`/`scene_state()` を通さず状態を直接適用（.umap基準と異なる F5保存も撮影可）。`--variant` を、無視されていた top-level キーではなく**対象室（activeRoomId）の roomState** へ適用（2.1.0 対応。`compare-unreal-studies.py` の仕上げA/Bも実際に切り替わる。既存CLIの不具合修正）
- `.gitignore` は不変（`build/` で既にランチャーのローカル状態を除外）

## 不足・未決定一覧

1. **施主による試用・画質評価**：未実施（「施主確認待ち」）。実装者の操作確認とは区別します。テスト数で写真同等品質を宣言しません。
2. **洗濯機（fur-002）の設置向き**：正本 `rotation: 0`。丸ドアが壁側。取込経路で位置・向きは変更できますが、既定の妥当性は配置レビューの残件。推測で変えていません。
3. **仮仕様の引き継ぎ**：仕上げ・照明・採光は未校正。実敷地の位置・真北・採用品番は確認待ち。狭所の視点制限も継続。
4. **比較記録の太陽条件**：A/B は選んだ保存の太陽条件（手動角度／日時ケース）をそのまま使います。日時ベースの複数ケース比較は `sun-cases.json` を持つモデルで既存の日時A/B機能を使います。

## 残件（次段階へ持ち越し）

1. **W07-H1以降（自宅）**：W08-G提出・レビュー後、施主の試用結果で次を決めます（自動着手しません）。
2. home/whole scope は設定で後から追加できる構成（`study-scopes.json` にエントリを足す既存の仕組み）。今回はゲスト8区画のみ対象。

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
