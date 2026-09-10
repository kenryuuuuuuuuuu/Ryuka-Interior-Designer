# W07-G2 実装報告：ゲスト室間移動・扉の開閉

- **仕様書**：[W07-G2-guest-circulation.md](W07-G2-guest-circulation.md)
- **前段レビュー**：[W07-G1-review-v2.md](W07-G1-review-v2.md)（ACCEPTED）
- **今ラウンドのレビュー**：[W07-G2-review.md](W07-G2-review.md)（v1、`89d07af`、**CHANGES_REQUESTED**）。R1〜R4を同じG2ラウンドで一括修正した報告です。
- **BASE**：`60d8cd644d00e57f11708dbbb1a1aa263095b2bc`（W07-G2着手時HEAD、W07-G1-v2のHEADと同じ。**v1から変更していません**）
- **HEAD**：`d4dba49`（`W07-G2-v2: fix review R1-R4 (doorStates→real leaves, walkthrough attribution, double-swing + interference, verified route)`。本行を記録するdocsコミットがその上に1つ乗ります）
- **提出**：`build/reviews/W07-G2-v2`
- **作業場所**：`build/worktrees/visual-twin`、ブランチ：`feature/visual-twin-foundation`
- **範囲**：G2のみ。G3（残り6室の登録）には着手していません。

## レビューv1（R1〜R4）への対応

### R1（高）：doorStatesがエディタ・Blenderの葉へ適用されない

**対応：閉/開の基準transformを`bakedOpen`フラグで共有し、Blender生成・UE初期インポート・`apply_state()`/案読込の3経路すべてが「実際の葉のtransform」へ同じ状態を適用するようにしました。**

- `blender/build_interior.py`：`build_openings()`に`door_states`引数を追加し、`main()`が生成時の`--state`の`doorStates`（未指定なら`{}`＝全扉閉、`mrs.default_state_v2()`の契約と一致）をそのまま渡します。各葉は、常に閉で作った幾何の上に`is_open`なら開ポーズ（swing/両開き＝`rotation_euler[2]=radians(-delta_deg)`、slide＝沿い方向へ`dx`平行移動）を焼き込み、`bakedOpen`（bool）を葉ごとに`door-bindings.json`へ記録します。生成物`study.json`の`report`にも`doorStates`を記録します。
- `unreal/import_study.py`：`study.json`の`doorStates`を読み、インポート直後の各葉のtransformを独立して再設定します（回転は絶対値 `Delta` または `0`、位置は「閉基準」または「閉基準＋オフセット」の絶対セット）。GLB書き出し／Interchangeインポートで焼きポーズが崩れても、ここで期待値に戻ります。slide葉の閉基準は、いま見えている位置から`bakedOpen`ぶんを引いて復元します（「いま見えているポーズ＝閉」と決め打ちしません）。
- `unreal/study_controls.py:apply_state()`：doorStates検証だけで葉を動かさなかった箇所に、材質・面と同じ「候補を全部集めてからトランザクションで一括適用」規律で`door_plan`を追加しました。`openYawDeltaDeg`葉は絶対回転、`openOffsetCm`葉はエディタセッション内で一度だけ捕捉した閉基準（`_door_leaf_closed_location`、C++の`DoorLeafSpawnLocation`と同じ考え方、`bakedOpen`補正込み）＋オフセットです。
- **引き戸の基準の見直し（レビュー指摘）**：引き戸は**アウトセット引き戸**としてモデル化し、壁の片面へ寄せる分（`outset = 壁厚/2 + 0.035/2 + 0.01`）を**閉配置に焼き込み**ました。`openOffsetCm`は純粋な沿い方向の平行移動のみになり、「起動時位置＝閉位置」を各consumerが素直に捕捉できます。開いた生成物をさらにずらす問題は起きません（閉じても数cmだけ戸中心面からずれた位置で開口を塞ぐため、通行はブロックします）。
- エディタの専用トグルUIは新設していません（レビューで不要と明記。フォーム反映＝`apply_state()`での実葉反映は必須で、上記の通り実装済み）。
- **確認（辞書の一致と実シーンの一致を区別）**：`build/W07-G2-ue-v6/verify_w07_g2.py`（UEエディタ、`-run=pythonscript`）で、代表扉door-002（`openYawDeltaDeg=85`）について — `door_override_moved_real_leaf`（`apply_state`後に**実葉の回転**が85±1°）、`compare_a/b/end_real_leaf_still_open`（仕上げA/B比較の開始・A・B・終了を通じて**実葉が開いたまま固定**）、`real_leaf_open_before_legacy_load`→`legacy_load_closed_the_real_leaf`（旧schema 1.0.0単室案の**通常読込で実葉が実際に閉じる**＝回転0±1°）。`door_override_applied_json`/`compare_*_doors_json_unchanged`は辞書側の確認として別項目で持ち、両者を分けて記録しています。

### R2（高）：視点変更後も古いwalkthrough.roomIdが残り、復帰先を誤る

**対応：エディタの視点変更で`walkthrough`を解除し、C++復帰側は保存データの帰属を現在のモデルへ自己検証して、矛盾するものは拒否するようにしました。**

- `unreal/study_controls.py`：`select_room()`・`remember_view()`は、`apply_state()`前に`state['walkthrough']=None`を入れます。どちらのカメラも「エディタ自身の固定視点／室の初期視点」であって内覧が実際にいた位置ではないため、再解決ではなく解除です（この関数には解決に使う「内覧の現在室」概念がありません）。
- `unreal/walkthrough/.../Walkthrough.cpp:Restore()`：`walkthrough`が
  - 無い/nullなら、初回起動として`EntryRoomId`（玄関）から開始します。
  - 有るなら、`profileId==ProfileId` かつ `roomId`が現行モデルに実在 かつ `level`がその室のレベルと一致、を全て満たすときだけ、その室を復帰対象にします。1つでも満たさなければ `Message="保存データの内覧位置が現在のモデルと整合しません"` で `return false`（黙って玄関へ読み替えません）。
- 安全補正は、解決済みの同一室の内側に限定します（既存ロジック、変更なし）。既存の全室`roomStates`・`doorStates`・`solar`は保持します（F9は候補の扉状態を先に適用してから安全位置探索、という既存の順序も維持）。
- **確認**：ネイティブ`-RyukaSmoke`の連続経路で、洋室でF5→ホールへ移動→洋室へF9、が室・位置・扉・両室状態まで戻ること（`ac4RestoredRoomPositionDoorAndBothRoomStates`）。エディタ側は`verify_w07_g2.py`の`select_room_clears_stale_walkthrough`（`walkthrough`をLDK以外へ立てた状態で`select_room()`→`walkthrough is None`）。`remember_view()`の同等の1行はヘッドレスcommandletにビューポートが無く単体では実行できないため、`select_room()`と同一の`state['walkthrough']=None`である旨を記録し当該項目のみスキップ（`remember_view_clears_stale_walkthrough_skipped_no_viewport`）。矛盾帰属の拒否はC++`Restore()`の軽量チェックです。

### R3（高）：両開きの向きと開閉の干渉判定を修正する

**(a) 両葉が同じ室へ開く幾何へ修正：**

- `unreal/circulation.py:double_swing_hinges_and_deltas()`：右葉に渡していた`sign=-1.0`を削除しました。`_swing_delta_deg()`は葉自身の`hingeSide`で既に符号を反転しており（lo端の蝶番とhi端の蝶番は、同じ室へ入るのに逆符号のyawが要る）、素直に両葉を呼べば「逆符号ペア＝同一室へ開く」になります。二重反転していたのが原因で、door-024の両葉が同じ`openYawDeltaDeg=-85`（片方が収納側、片方が洋室側）になっていました。修正後は左`-85`／右`+85`。
- あわせて**開く向きをジオメトリから導出**する`swingToward`を`resolve_connections()`へ追加しました（`swingDir`/`hingeSide`は外部開口用の値で、複数の扉ラベルと同様に室内では信頼できないため）。共有壁からの各室の到達距離を比べ、遠くまで伸びる室（＝狭いホールでなく部屋の側）へ開きます。door-024は洋室側（大きい方の室）へ両葉が開きます。
- 確認：`tests/test_circulation.py:test_double_swing_leaves_open_toward_the_same_room`（`deltas['left'] == -deltas['right']`、絶対値一致、符号は不一致）。pytest 187→**190**。

**(b) 可動葉の移動領域と近距離遮蔽の検査：**

- `Walkthrough.cpp:LeafMotionClear()`（新規）：葉の`From`→`To`の経路を6ポーズ×葉幅方向4点の小球で離散サンプリングし、家具・内装・別の扉の葉・設置障害物がアーク/引き先に重なる動作を拒否します（始点・終点が個別に空いていても中間ポーズで拒否できます）。構造壁（`wall_`/`Ground_`プレフィックス）と扉自身の枠・兄弟葉は除外します（壁は「どこまで開くか」の固定制約であって「操作不能」ではなく、壁越し操作は`FindNearestDoor()`のライントレースが別途担当）。物理シミュレーション・アニメーションはありません。
- **開扉方向のみ検査**します。閉扉は生成時に検証済みの焼きポーズへ戻すだけなので、「閉じられない」は隣接枠を球がかすめる誤検出にしかならないためです。閉じる葉がプレイヤーのカプセルに当たる件は、これまで通り`InteractDoor()`が`ApplyConditions()`の後に`Safe(GetActorLocation())`で見ます。
- `ApplyConditions()`のトランザクション：`LeafMotionClear()`は候補検査フェーズ（読み取りのみ）で行い、失敗時は状態も葉も触らずに`return false`します。`InteractDoor()`は拒否時に扉状態・パネル位置を元へ戻し、HUDへ理由を表示します。
- `FindNearestDoor()`：正面判定を`Eye->GetForwardVector()`（1フレーム遅延する）から`Controller->GetControlRotation().Vector()`へ、加えて視点→扉のライントレースが扉のかなり手前で遮られたら候補から除外（壁越しの扉を操作対象にしない）。
- 引き戸の引き先：上記アウトセット化（R1）で、開いた葉がモデル化されていない壁ポケットへ埋め込まれる問題を解消済みです。
- **確認（実シーン、代表1件＋両開き1件）**：ネイティブ`-RyukaSmoke`で —
  - `doubleSwingBlockedWhenClosed`：閉じたdoor-024は通行をブロック。
  - `doubleSwingBlockedByFur007InRealScene`：door-024の開扉が、洋室のゲスト用冷蔵庫`fur-007`がアーク内にあるため`ApplyConditions()`で拒否される（ブロッカー＝`furniture_fur-007_body`、`t=1.00 along=0.35`。閉じた葉のポーズは個別に有効＝扉は生成できている）。
  - `doubleSwingOpensWithArcClear`/`doubleSwingReachableWithArcClear`：`fur-007`のコリジョンを一時的に無効化すると、両葉が動いて開口が通行可能になり、収納側へ抜けられる。
  - `doubleSwingCloses`：閉じられる。
  - door-001（引き戸）についても、閉時ブロック→開扉→通過が下記連続経路で通っています。

### R4（中）：指定した通常経路と洋室保存の実機確認

**対応：R1〜R3修正後の同一プロジェクト（`build/W07-G2-ue-v6`）で、指定経路を通常移動で往復し水回り入口へ到達することを、テレポートで各扉前へ配置する代替ではなく、前の脚が着地した位置から続く連続スイープで確認しました。**

`Walkthrough.cpp`の`-RyukaSmoke`を、扉ごとのテレポート分離ではなく1本の連続経路に置き換えました（`WalkTo`＝facing＋`SetActorLocation(bSweep=true)`、`SetDoor`＝`FaceDoor`＋`FindNearestDoor`の近接/正面判定経路。手動の`NearestDoorId=`代入はしません）。NullRHI（ロジックのみ）・DX12（実描画、`walkthrough-smoke.png`取得）の両方で**PASS**。全24脚が`true`（`walkthrough-smoke-route.json`、ディスク上はUTF-16）。

| 区間 | 脚（route.json のキー） | 結果 |
|---|---|---|
| 玄関→ホール（door-025、開放） | `genkanToHall` | true |
| ホール→door-002敷居→開扉→LDK | `hallToDoor002Threshold`・`openDoor002`・`hallToLdk` | true |
| LDK→ホール→door-002閉扉 | `ldkToHall`・`closeDoor002` | true |
| ホール→door-005敷居→開扉→洋室 | `hallToDoor005Threshold`・`openDoor005`・`hallToNishishitsu` | true |
| 洋室が編集scope（仕上げ変更可） | `nishishitsuIsEditScope` | true |
| **AC4**：洋室でF5（door-005開・`bReady`）→ホールへ→door-005閉→F9 | `ac4SavedWithDoorOpenAndReady`・`ac4BackToHall`・`ac4CloseDoor005AfterSave`・`ac4RestoredRoomPositionDoorAndBothRoomStates` | true |
| **両開き**：door-024の閉時ブロック／干渉拒否／アーク開放時の開通・到達・閉扉 | `doubleSwingBlockedWhenClosed`・`doubleSwingBlockedByFur007InRealScene`・`doubleSwingOpensWithArcClear`・`doubleSwingReachableWithArcClear`・`doubleSwingCloses` | true |
| 洋室→ホール→door-001敷居→開扉→トイレ（水回り入口）到達 | `nishishitsuBackToHall`・`hallToDoor001Threshold`・`openDoor001`・`hallToToilet`・`reachedWaterRoomEntry` | true |

`ac4RestoredRoomPositionDoorAndBothRoomStates`は、F9後に「現在室＝洋室」「door-005が開」「`roomStates[room-1f-05].variant=="warm"`（洋室で変更したもの）」「`roomStates[room-1f-06].variant=="natural"`（LDK、変更していない）」を同一実行内ですべて満たすことを確認しています。

**入れない狭所・正本矛盾**：AC2の必須経路（玄関→ホール→LDK→ホール→洋室＋水回り入口）は上記の通り通常移動で往復できました。収納（room-1f-23）は宿泊客の必須動線ではなく、door-024の開き角がゲスト用冷蔵庫`fur-007`（`data/furniture.json`、`status:"estimated"`、施主指示で270°へ回転・位置調整済み）の扉部分により制限されます。実寸は維持し、両葉が同一室へ開く機構（R3(a)）と干渉拒否（R3(b)）は代表確認済み、実通行は`fur-007`を除いた状態で確認、として記録します。door-002は開き角がLDK内側のL字壁で制限されますが（開ける範囲まで開く固定制約）、開扉・通過は上記の通り成立します。正本矛盾で成立しなかった経路はありません。

## 扉・室の接続解決結果（ジオメトリのみ、ラベル不使用）

`unreal/circulation.py`の`resolve_connections()`が、`house.json`の室ポリゴンと`interior-doors.json`の`(orientation, wallAt, center, width)`だけから解決した結果です（`interior-doors.json`自身の`label`テキストは参照していません）。開く向き（`swingToward`）も、`swingDir`/`hingeSide`ではなく共有壁からの各室の到達距離という幾何から導出します。

| 扉ID | 操作 | 接続室（実際） | ラベル上の記載 | 一致 |
|---|---|---|---|---|
| door-001 | 引き戸 | room-1f-01（トイレ）⟷room-1f-24（ホール） | トイレ⟷ホール相当 | 一致 |
| door-002 | 開き戸 | room-1f-06（LDK）⟷room-1f-24（ホール） | 「玄関⟷洗面脱衣室」（誤り） | **不一致（ラベルが古い）** |
| door-003 | 開き戸 | room-1f-03（洗面脱衣）⟷room-1f-04（UB） | 洗面脱衣⟷UB相当 | 一致 |
| door-004 | 開き戸 | room-1f-03（洗面脱衣）⟷room-1f-24（ホール） | 「玄関⟷LDK張り出し」（誤り） | **不一致（ラベルが古い）** |
| door-005 | 引き戸 | room-1f-05（洋室）⟷room-1f-24（ホール） | 洋室⟷ホール相当 | 一致 |
| door-024 | 両開き | room-1f-05（洋室）⟷room-1f-23（収納） | 洋室⟷収納相当 | 一致 |
| door-025 | 開放（扉本体なし） | room-1f-02（玄関）⟷room-1f-24（ホール） | 玄関⟷ホール相当 | 一致 |

`fold`・`double-fold`操作の扉は今回のゲスト8室に該当がなく一般化していません（`SUPPORTED_OPERATIONS`は`swing`/`double-swing`/`slide`/`open`）。

## 移動制限・前提

- LDK⟷洋室の直接接続は存在しません（両室ともホール経由）。捏造した直接開口はありません。
- 編集scope（`activeRoomId`、仕上げ編集対象）はLDK・洋室の2室のまま、内覧の歩行対象8室とは別概念です。非編集室（玄関・ホール等）を歩行中は仕上げキー（1/2/3）が「この部屋は編集対象外です」で無効化されます。
- 扉の蝶番位置は`interior-doors.json`の`hingeSide`を準用しますが、**開く向きはジオメトリ由来の`swingToward`**を採用します（`circulation.py`のモジュール冒頭・docstringに明記）。
- **door-024（洋室⟷収納の両開き）**：開き角はゲスト用冷蔵庫`fur-007`により制限されます。収納は宿泊客の必須動線ではなく、機構（両葉が同一方向へ開く＝R3(a)、干渉拒否＝R3(b)）は代表確認済みです。
- **door-002（LDK⟷ホールの開き戸）**：全開はLDK内側のL字壁で制限されます（開ける範囲まで開く固定制約。開扉・通過は成立）。
- エディタメニューに扉トグルの直接操作UIはありません（レビューで不要と明記、フォーム反映は実装済み）。
- 自宅で使用予定の`fold`／`double-fold`操作、残り6室（G3）は今回対象外です。

## 受入条件（AC）結果

「満たす」は**辞書（doorStates/walkthrough等のJSON）の一致**と**実シーン（実際の葉のtransform・実際の歩行）の一致**を区別して記載します。

| AC | 内容 | 結果 | 根拠（辞書／実シーン） |
|---|---|---|---|
| 1 | ゲストの接続・建具bindingsが正本から解決し、ラベル相違に引きずられない | **満たす** | 上表7接続すべてジオメトリのみで解決。`tests/test_circulation.py`（20件、うち新規3件：`bakedOpen`必須検証2件・両開き同一室3件）。 |
| 2 | 玄関→ホール→LDK→ホール→洋室を実際に歩いて往復、閉扉は遮り開扉で通過、水回り入口へ到達 | **満たす（実シーン）** | ネイティブ`-RyukaSmoke`の**1本の連続スイープ**で、玄関→ホール(door-025)→door-002開扉→LDK→ホール→door-002閉扉→door-005開扉→洋室、その後 洋室→ホール→door-001開扉→トイレ到達。全脚`true`（`walkthrough-smoke-route.json`）。NullRHI・DX12の両方でPASS、`walkthrough-smoke.png`取得。 |
| 3 | 開き戸・引き戸・両開きの葉/衝突がともに移動、壁/対象外を抜けない、閉動作中のカプセル干渉を拒否 | **満たす（実シーン）** | door-001（引き戸）・door-002（開き戸）：閉時ブロック→開扉→通過（上記連続経路）。door-024（両開き）：閉時ブロック／`fur-007`がアーク内にあるとき開扉拒否（`ApplyConditions()`の`LeafMotionClear()`。閉葉ポーズは個別に有効）／`fur-007`を除くと両葉が動いて通行可・収納側へ到達／閉扉可。引き戸はアウトセット化で開葉が壁へ埋め込まれない。カプセル干渉は`InteractDoor()`の`Safe()`で拒否（既存パス、維持）。 |
| 4 | 洋室相当の編集可能室で保存→別室で扉/仕上げ変更→F9で室・位置・扉・両室状態が戻る | **満たす（実シーン）** | 上記連続経路内で、洋室でFinish2（→warm）→F5（door-005開・`bReady`）→ホールへ移動しdoor-005を閉じ直す→F9。F9後に現在室＝洋室／door-005開／`room-1f-05.variant=="warm"`／`room-1f-06.variant=="natural"`をすべて確認（`ac4RestoredRoomPositionDoorAndBothRoomStates`）。 |
| 5 | 旧G1状態/旧LDK案を読込→新版保存。扉を開いた状態で代表比較A/B/終了を通して扉・他室が不変 | **満たす（辞書＋実シーン）** | `verify_w07_g2.py`（UEエディタ）：door-002を開いた状態から旧schema 1.0.0単室案（`guest-a-v1`/`guest-b-v1`）で仕上げA/B（開始→A→B→終了）を実行し、**辞書**（`compare_*_doors_json_unchanged`）と**実葉の回転**（`compare_a/b/end_real_leaf_still_open`＝85±1°で固定）がともに不変。旧1.0.0単室案の**通常読込**では`doorStates`が家全体項目として案の値（空）へ置き換わり、**実葉も実際に閉じる**（`legacy_load_closed_the_real_leaf`＝0±1°）。 |
| 6 | 保存案の開扉状態と位置を完全refresh1回で保持、内覧構築/転送検証まで終了コード0 | **満たす** | `scripts/refresh-visual-study.py --previous build/W07-G2-ue-v6 --scope guest-pilot`（前プロジェクトの`study-state.json`に`doorStates:{door-002:{open:true}}`・`walkthrough`を設定）。`refresh.json`の`status: complete`（全7工程）・終了コード0。生成後の`ue/study-state.json`＝`import-verification.json`の`comparisonState`が`doorStates`・`walkthrough`を保持（`unrealImportVerified: true`）。`tests/validate_study_transfer.py`の`doorStates`/`walkthrough`一致検証も成功（`state-transfer-verification.json`）。 |
| 7 | 既存検証成功、通行できない狭所/未仕上げ区画/仮定を明示 | **満たす** | `python -m pytest tests/`：**190 passed, 55 subtests passed**。`node scripts/build-web-data.mjs --check`・`validate_house.py`・`validate_electrical.py`・`validate_furniture.py`・`validate_openings.py`すべて成功。仮定・限界は本報告の「移動制限・前提」「残件」節。 |

## v1で発見・修正済みの実際の不具合（維持）

v1で報告した2件はそのまま有効です（今回の修正で退行していないことを上記実走行で確認）。

1. **内部扉の敷居（sill）帯が通行をブロック**：`blender/build_interior.py`が内部扉の敷居帯（`frameWidth`＝4.5cm、`MaxStepHeight` 2cm超）を生成していた。本物件の扉カタログは全種`sill=0`のため、内部扉の敷居帯生成を省略。
2. **扉プロンプトが古いラベルを表示**：`enable-unreal-walkthrough.py`が`interior-doors.json`の（ホール分離前の）古いラベルをHUDへ表示していた。解決済み接続が指す2室の現在の室名から組み立てるよう修正。

## 実施した検証

### 単体・軽量確認

- `python -m pytest tests/ -q`：**190 passed, 55 subtests passed**（`tests/test_circulation.py` 20件）。
- `node scripts/build-web-data.mjs --check`：最新。
- `python tests/validate_house.py` / `validate_electrical.py` / `validate_furniture.py` / `validate_openings.py`：すべて成功。

### Blender（実行）

- `scripts/build-visual-twin.py --interior --scope guest-pilot --output build/W07-G2-blender-v6`。`door-bindings.json`が7接続を正しい`operation`/`leaves`/`bakedOpen`で出力（door-024 左`-85`／右`+85`、全扉`bakedOpen:false`）。

### Unreal Engine（実行）

- 実インポート：`unrealImportVerified: true`（`build/W07-G2-ue-v6/import-verification.json`）。
- C++ Walkthroughモジュールの実コンパイル：`scripts/enable-unreal-walkthrough.py`（`error C`/`error LNK` ともに0）。
- ネイティブ`-RyukaSmoke`（NullRHI・DX12）：上記R4の連続経路24脚すべて`true`、`walkthrough-smoke.txt`＝PASS、`walkthrough-smoke.png`取得。
- UEエディタでの`study_controls.py`検証（`build/W07-G2-ue-v6/verify_w07_g2.py`、`-run=pythonscript`）：24項目すべて成功（＋ビューポート非依存の`remember_view`同等項目1件をヘッドレスのためスキップ、理由記録済み）。R1の実葉transform確認・R2の`select_room`解除確認・A/B比較中の実葉固定・旧案読込での実葉クローズを含みます。
- **完全refresh1回**（`refresh-visual-study.py --previous build/W07-G2-ue-v6 --scope guest-pilot`）：`status: complete`、終了コード0、`doorStates`/`walkthrough`が転送後も一致（`state-transfer-verification.json`）。

## 検証コマンド（実行済み）

```
python -m pytest tests/ -q
node scripts/build-web-data.mjs --check
python tests/validate_house.py
python tests/validate_electrical.py
python tests/validate_furniture.py
python tests/validate_openings.py

python scripts/build-visual-twin.py --blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --interior --scope guest-pilot --output build/W07-G2-blender-v6
python scripts/build-unreal-study.py --engine "C:/Program Files/Epic Games/UE_5.8" --package build/W07-G2-blender-v6 --output build/W07-G2-ue-v6 --cache C:/UE_DDC/w07g2f
python scripts/enable-unreal-walkthrough.py --project build/W07-G2-ue-v6 --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g2f
python scripts/launch-unreal-walkthrough.py --project build/W07-G2-ue-v6 --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g2f --smoke --logic-only
python scripts/launch-unreal-walkthrough.py --project build/W07-G2-ue-v6 --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g2f --smoke
# UEエディタ検証：UnrealEditor-Cmd.exe <v6>/RyukaInterior.uproject -run=pythonscript -script=<v6>/verify_w07_g2.py -unattended -NullRHI ...
python scripts/refresh-visual-study.py --previous build/W07-G2-ue-v6 --output build/W07-G2-refresh-v2 --blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --engine "C:/Program Files/Epic Games/UE_5.8" --cache C:/UE_DDC/w07g2refresh2 --scope guest-pilot
```

### 実行結果・証跡ファイル（実行したスクリプト自体も証跡として記載）

- `build/W07-G2-ue-v6/verify_w07_g2.py`（検証スクリプト本体）と`build/W07-G2-ue-v6/verify_w07_g2_result.json`（`_all_passed: true`、24項目）
- `build/W07-G2-ue-v6/Saved/walkthrough-smoke.txt`（PASS）、`build/W07-G2-ue-v6/Saved/walkthrough-smoke-route.json`（連続経路24脚、UTF-16）、`build/W07-G2-ue-v6/Saved/walkthrough-smoke.png`（DX12実描画スクリーンショット）
- `build/W07-G2-ue-v6/import-verification.json`（`unrealImportVerified: true`、`comparisonState`に`doorStates`/`walkthrough`）
- `build/W07-G2-refresh-v2/refresh.json`（`status: complete`）、`build/W07-G2-refresh-v2/ue/state-transfer-verification.json`
- `build/W07-G2-blender-v6/door-bindings.json`（7接続、`bakedOpen`込み）
- `tests/test_circulation.py`（20件）

## 変更ファイル一覧（v1差分に対する今ラウンドの追加・変更）

- `unreal/circulation.py`：`swingToward`（幾何由来の開き向き）を`resolve_connections()`へ追加、`_swing_delta_deg()`が`swingToward`を優先、`double_swing_hinges_and_deltas()`の`sign=-1.0`削除（R3a）、`validate_door_bindings()`が各葉の`bakedOpen`（bool）を必須化（R1）
- `blender/build_interior.py`：`build_openings()`に`door_states`引数、各葉の初期ポーズを`doorStates`から焼き込み＋`bakedOpen`記録、引き戸のアウトセット化、`study.json`へ`doorStates`記録、限界文言「All actual door leaves closed」削除（R1・R3）
- `unreal/import_study.py`：`study.json`の`doorStates`から各葉のtransformを独立再設定（R1）
- `unreal/study_controls.py`：`apply_state()`に実葉を動かす`door_plan`（トランザクション内一括適用）と`_door_leaf_closed_location`キャッシュ、`select_room()`/`remember_view()`が`walkthrough`を解除、`initial_state()`が`doorStates`を引き継ぎ（R1・R2）
- `unreal/walkthrough/Source/RyukaInterior/Walkthrough.h`・`.cpp`：`FLeafInfo::bBakedOpen`、`LeafMotionClear()`（開扉方向の移動領域干渉検査）、`FindNearestDoor()`の正面判定を`ControlRotation`化＋壁越しライントレース、`Restore()`の`walkthrough`帰属自己検証（不整合は拒否）、`ApplyConditions()`の`bBakedOpen`由来の閉基準復元、`-RyukaSmoke`を1本の連続経路＋両開き代表確認へ置換（R1・R2・R3・R4）
- `tests/test_circulation.py`：`bakedOpen`必須検証2件・両開き同一室検証1件を追加（187→190）
- `tests/validate_study_transfer.py`：保存視点が無い（`camera: null`）状態でも転送検証が通るよう分岐（`doorStates`/`walkthrough`一致検証はv1で追加済み）
- `docs/ARCHITECTURE.md`・`docs/UNREAL_WALKTHROUGH.md`・`docs/STATUS.md`：R1〜R4の内容と限界（door-024の`fur-007`制限、door-002のL字壁制限、扉トグルUI無し）を反映

## 残件（次段階へ持ち越し）

1. **G3：残り6室の登録**は未着手。
2. **自宅の`fold`／`double-fold`操作の扉**は今回一般化していない（ゲスト8室に該当する扉が無いため）。
3. エディタメニューに扉トグルの直接操作UIは無い（レビューで不要と明記。`doorStates`の往復・比較中の実葉固定・案読込での実葉反映は確認済み）。
4. door-024の開き角は`fur-007`により、door-002の開き角はLDK内側のL字壁により制限される（いずれも固定幾何。収納は必須動線外、door-002は開扉・通過は成立）。

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
