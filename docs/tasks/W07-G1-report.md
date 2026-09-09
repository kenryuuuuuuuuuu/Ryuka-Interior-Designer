# W07-G1 実装報告 v2：ゲストLDK＋洋室の複数室対応基盤

- **仕様書**：[W07-G1-multi-room-foundation.md](W07-G1-multi-room-foundation.md)（進行計画：[W07-staged-design.md](W07-staged-design.md)）
- **レビュー**：[W07-G1-review.md](W07-G1-review.md)（v1、CHANGES_REQUESTED。R1〜R5を本v2で修正）
- **BASE**：`5d4d3cbb06f4436a3574c12dea44ade7a20fb3f3`（着手時HEAD、v1から維持）
- **HEAD**：本コミット（下記コミットログ参照）
- **作業場所**：`build/worktrees/visual-twin`、ブランチ：`feature/visual-twin-foundation`
- **範囲**：G1のみ（ゲストLDK＋洋室の2室基盤）。G2（室間移動）以降は未着手。

## v1レビューのR1〜R5修正内容

| # | 指摘 | 対応 |
|---|---|---|
| R1 | 起動時メニュー登録が`current_state()`（＝実シーン必須）を呼び、Houseレベル未オープン時（エディタ/commandlet起動直後）に毎回例外を出していた | `unreal/study_controls.py`に`_display_state()`（実シーンに触れない、`_state`または`initial_state()`のみを読む安全版）を新設し、`register_menu()`の対象室メニュー構築・`_room_status_text()`をこれに切替。既存の`_lighting_status_text()`等と同じ確立済みパターンに統一 |
| R2 | `partial_apply()`が`incoming`（旧案の移行後scopeId、常に自室だけを含む最小スコープ）のscopeIdをそのまま結果へ持ち越し、マージ結果のscopeIdと実際のroomStatesが食い違っていた（再検証で拒否される） | `partial_apply()`に`scope_id`引数を追加し、結果のscopeIdは常に呼び出し元の対象scopeにする。あわせて、`incoming`がroom_ids範囲外の室を含む場合は黙って落とさず`ValueError`で拒否するようにした。呼び出し元（`study_controls.load_scenario()`・`refresh-visual-study.py`）を対応する`scope_id`を渡すよう更新 |
| R3 | `refresh-visual-study.py`が`--scenario`使用時も無条件に`--previous`の`study-state.json`（前回のエディタ保存）だけを基準状態として読んでおり、より新しい内覧F5保存（`Saved/walkthrough-state.json`）を無視していた。また全室をカバーする案でも不要にこのファイルを要求し、壊れていると停止していた | `scripts/refresh_inputs.py`に`latest_state_path()`（エディタ保存と内覧F5保存の新しい方を選ぶ、既存`retained_inputs()`から抽出した共通ロジック）を新設。`refresh-visual-study.py`は対象scopeの全室を案が既にカバーする場合は基準状態を一切読まず、不足がある場合だけ`latest_state_path()`で選んだファイルを読む |
| R4 | `show_compare()`（仕上げA/B）が対象室のroomState全体（`fixtures`含む）を候補で置換しており、仕上げの比較のはずが照明も一緒に切り替わっていた | 対象室のvariant/surfaceOverridesだけを候補から採用し、fixturesは比較開始時点の値を保持するよう修正 |
| R5 | Blenderの家具生成（`build_furniture()`）が常に外皮の固定基準材質（`natural`）を使っており、室ごとのvariantを反映していなかった（UEとBlenderで仕上げが食い違う） | `blender/build_interior.py`に室のvariantごとの材質セット（`mats_by_variant`/`mats_by_room`）を新設し、`build_furniture()`/`build_decor()`が各家具・装飾アイテム自身の室のセットを使うよう変更 |

## R5修正の実装過程で発見・修正した追加の不具合（実UE実行で発見）

R5の初回実装では、Blender側の材質名を`{variant}.{role}`（ドット区切り、例：`warm.wood`）へ変更したが、実UEインポートで確認したところ、**UEのInterchangeインポートが材質名の`.`を`_`へサニタイズする**ことが判明した（`natural.wall`が`mat.get_name()`で`natural_wall`として返る）。`unreal/import_study.py`の役割材質検出（`mat.get_name() in materials`）はBlender側の材質名をそのまま使っていたため、この不一致で全ての役割材質バインディング（`study-bindings.json`）が空になり、`scene_state()`の保存時整合チェックが「面の材質が保存内容と一致しません」という別の理由で失敗する新しい不具合を引き起こした。区切り文字を`_`（UE側の`M_{variant}_{role}`命名規則と同じ）へ修正し、`import_study.py`側もその室の実際のvariantから prefix を求めて除去する方式に修正して解消した。

さらに、この過程で実際に`start_compare()`→`show_compare()`をUEエディタで実行して初めて、`_compare_status_text()`が旧い`_compare['fixed']`（現在の`_compare`は`before`/`a`/`b`/`active_room_id`/`names`/`current`の形で、`fixed`キーは存在しない）を参照したままだったため`KeyError`で仕上げA/B開始が必ず失敗する、v1から存在していた別の不具合も発見・修正した（`fixed=_compare['before']`へ修正）。

これらはいずれも「実際にUEを起動して確認する」ことで初めて発見できた不具合であり、レビューの「実UE確認は原則不要とせず、まず特定できたコード上の問題を修正する」という方針に沿って対応した。

## 受入条件（AC）結果

| AC | 内容 | 結果 | 根拠 |
|---|---|---|---|
| 1 | guest-pilotで2室の家具/面/照明を同じプロジェクトへ生成し、メニューで切替表示できる | **満たす** | 実Blenderビルド・実UEインポート（`unrealImportVerified: true`、`study-bindings.json` 441エントリ）・UEエディタでの`select_room()`によるLDK⇄洋室切替を確認 |
| 2 | 共有壁のLDK側変更で洋室側が不変。洋室のvariant変更でLDKが不変。各室の点灯も独立し切替で消えない | **満たす** | 共有壁両側の独立編集（`ldk_now_reference`・`west_still_natural_after_ldk_edit`）に加え、**今回新たに照明の室別独立性を実UEで確認**：洋室の照明（elec-006）をONにした状態でLDKへ切替・LDKの照明（elec-008）をON→OFFしても、洋室に戻さず`current_state()`だけで洋室のelec-006が引き続きONのままであることを確認（`west_fixture_still_on_after_ldk_room_switch`） |
| 3 | 旧1.2のLDK案を読込→洋室設定が保持→新版案を保存→完全refresh1回で両室/太陽来歴/カメラを保持 | **満たす** | 実在の旧schemaVersion 1.0.0単室案（`build/scenarios/guest-a-v1`）読込による洋室保持をUEエディタで確認。さらに`scripts/refresh-visual-study.py --previous ... --scenario build/scenarios/guest-a-v1 --scope guest-pilot`による**完全refreshが終了コード0で最後まで成功**（`04-state-check`まで完走、`refresh.json`のstatus=complete）することを確認し、結果の`study-state.json`が`scopeId:'guest-pilot'`・両室`roomStates`・太陽来歴・カメラを正しく保持していることを確認した（v1で報告した終了コード非ゼロの事象はR1・R5関連の修正後、再現しなくなった） |
| 4 | 既存の仕上げ/照明/日時比較を新状態で接続。代表1比較で対象室だけが変わり終了で復元することを実UE確認 | **満たす** | R4修正後、`start_compare()`→`show_compare_a()`→`show_compare_b()`→`end_compare()`を実在の2案（`guest-a-v1`/`guest-b-v1`）でUEエディタ実行し、対象室（LDK）のfixturesが比較の開始・A表示・B表示・終了を通じて一切変化しないこと（`compare_a_ldk_fixtures_preserved_not_replaced`・`compare_b_ldk_fixtures_still_preserved`・`compare_ended_west_fixtures_still_intact`）、洋室のroomStateが終始無関係であることを確認した |
| 5 | 新版のLDK内覧でF5/F9を1往復し洋室状態も維持。不正な室/面参照1件を重い生成/適用前に拒否し現在状態を保持 | **満たす** | `-RyukaSmoke`ネイティブ自己診断（`PASS`）でF5/F9往復後も洋室のroomStateが不変であることを確認。`select_room('room-does-not-exist')`・対象室以外の面への`select_surface()`のいずれもRuntimeErrorで拒否されることを確認 |
| 6 | 対象scope・未開放機能・旧案の部分適用を文書化。関連テストと既存正本validatorが成功 | **満たす** | ARCHITECTURE.md/UNREAL_WALKTHROUGH.md/STATUS.mdを更新。`python -m pytest tests/`（170 passed, 55 subtests）、`node scripts/build-web-data.mjs --check`、`python tests/validate_house.py`・`validate_electrical.py`・`validate_furniture.py`・`validate_openings.py`すべて成功 |

## 実施した検証

### 単体・軽量確認

- `python -m pytest tests/`：170 passed, 55 subtests passed（v1の165 passedから、R2用の新規`tests/test_multi_room_state.py`3件・R3用の`tests/test_refresh_study.py`2件を追加）。
- `unreal`モジュールを最小スタブへ差し替えたR4の軽量確認（`build/W07-G1-v2-confirm/verify_r4_fixtures.py`、既存W06-v3レビューと同水準の手法）：`show_compare()`が候補のvariant/surfaceOverridesだけを採用しfixturesを保持することを、実コード（study_controls.pyそのもの）に対して確認。

### Blender（実行）

- 診断用の室別variant違いの`--state`でビルドし、家具の材質名を実際にBlenderへ問い合わせて確認：洋室の家具（`fur-041`、reference室）は`reference_cabinet`、LDKの家具（`fur-008`等、warm室）は`warm_wood`と、各アイテムが自室のvariantに対応する材質を参照していることを確認（R5）。

### Unreal Engine（実行）

- 実インポート（`--state`なし）：`unrealImportVerified: true`。
- C++ Walkthroughモジュールの実コンパイル、`-RyukaSmoke`ネイティブ自己診断：`PASS`。
- **完全refresh1回**（`scripts/refresh-visual-study.py --previous ... --scenario build/scenarios/guest-a-v1 --scope guest-pilot`、`--state`付き）：**終了コード0で完走**。`study-bindings.json` 441エントリ、`unrealImportVerified: true`、`study-state.json`の`scopeId`・両室`roomStates`・太陽来歴・カメラすべて期待通り（詳細は上記AC3参照）。
- UEエディタ実行検証スクリプト（上記の完全refresh結果に対して実行）：室切替・共有壁両側の独立編集・**照明の室別独立性（新規）**・仕上げA/Bのfixtures保持（新規、R4実UE確認）・実在の旧単室案の読込による洋室保持・不正な対象室/別室面選択の拒否。全18項目すべて成功。

## 変更ファイル一覧（v1からの追加分、主要なもの）

- `unreal/multi_room_state.py`：`partial_apply()`に`scope_id`引数追加、範囲外室の拒否（R2）
- `unreal/study_controls.py`：`_display_state()`新設・`register_menu()`/`_room_status_text()`/`_lighting_status_text()`等の統一（R1）、`show_compare()`のfixtures保持（R4）、`_compare_status_text()`のKeyError修正（追加発見分）、`load_scenario()`/`start_compare()`等の`partial_apply()`呼び出しへの`scope_id`引数追加（R2）
- `scripts/refresh_inputs.py`：`latest_state_path()`新設（R3）
- `scripts/refresh-visual-study.py`：全室カバー時に基準状態を読まないロジック、`latest_state_path()`利用（R3）、`partial_apply()`呼び出しへの`scope_id`引数追加（R2）
- `blender/build_interior.py`：`mats_by_variant`/`mats_by_room`/`build_palette_materials()`新設、`build_furniture()`/`build_decor()`の室別材質切替（R5）
- `unreal/import_study.py`：役割材質検出の室別variant prefix対応（R5関連の追加修正）
- `tests/test_multi_room_state.py`（新規）：R2の3件
- `tests/test_refresh_study.py`：R3の2件追加
- `docs/tasks/W07-G1-review.md`：v1レビュー（新規、GPT提出）

## 残件（次段階へ持ち越し）

1. **G2：室間移動**（内覧でLDK⇄洋室を実際に歩いて行き来する）は本ラウンドで未着手。内覧は今回もLDK単室のみ歩行可能（`walkthrough.json`の`walkableRoomId`固定）。
2. **G3：残り6室の登録**は未着手。`data/visual/study-scopes.json`・`surface-registry.json`・`room-render-settings.json`はLDK・洋室の2室分のみ。
3. `role-bindings.json`は今回`decoration.*`オブジェクトを一律LDK（`room-1f-06`）扱いにしている。洋室の装飾（ラグ・布・小物等）は本ラウンドで追加していないため。

## 検証コマンド（実行済み）

```
python -m pytest tests/ -q                         # 170 passed, 55 subtests passed
node scripts/build-web-data.mjs --check             # up to date
python tests/validate_house.py                      # Phase 1 checks passed
python tests/validate_electrical.py                 # checks passed
python tests/validate_furniture.py                  # checks passed
python tests/validate_openings.py                   # checks passed
```

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
