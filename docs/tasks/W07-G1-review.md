# W07-G1 レビュー v1

判定：CHANGES_REQUESTED。2026-09-09。
BASE：5d4d3cbb06f4436a3574c12dea44ade7a20fb3f3
HEAD：673e4afe3b3eea2fd36ddb2e6a49e92abb6376ea
提出：build/reviews/W07-G1-v1

## 結論

2室の生成・室切替・共有壁両側の対応という基盤は進んでいます。ただし、通常の案保存/再生成/比較を止める不具合があり、G1は未完了です。下記を同じG1でまとめて修正してください。G2には進みません。終了コードの非ゼロを「実質成功」として受け入れることはできません。

## R1 高：起動時メニューの例外を解消し、完全refreshを最後まで通す

対象：unreal/study_controls.py:1459〜1462、_room_status_text()、scripts/build-unreal-study.pyのinit_unreal生成。

提出ログ `build/W07-G1-ac3-refresh3/ue/import.log` の127〜141行には、init_unreal.py→register_menu()→current_state()→scene()のRuntimeErrorが記録されています。末尾にも `Failure - 15 error(s), 2 warning(s)` とあります。「ログに例外はなく、ログに現れないシャットダウン処理が原因」とする報告は証拠と一致しません。

G1でメニュー登録に追加したcurrent_state()は未オープンのHouseレベルを要求します。新規インポート/エディタ起動時に実シーンを読む必要のないメニューは、メモリ/ディスクの検証済み状態から構築するか、レベル準備後へ登録を遅延してください。commandletで不要なUIを登録しない方式でも構いません。終了コードとの因果の最終確定は修正版実行で行いますが、まず目の前の起動例外を直すべきです。

`import-verification.json`があるだけで非ゼロ終了を成功へ読み替える変更はしないでください。現状refreshは03-unrealで停止し、後続の内覧構築/状態照合まで到達していません。修正後に代表1回だけ、--stateを含む完全refreshを最後まで成功させてください。ドライバ/Engine変更や追加の高度な診断ツールは現段階では不要です。

## R2 高：部分適用後のscopeIdが保存室と矛盾する

対象：unreal/multi_room_state.py:partial_apply、validate_state_own_scope、unreal/study_controls.py:load_scenario/scene_state、refreshのマージ。

partial_apply()はincomingのscopeIdを維持したまま他室を加えます。実際の提出 `build/W07-G1-ac3-refresh3/merged-study-state.json` はscopeId=guest-ldkなのにroomStatesがLDK＋洋室です。これを現行validate_state_own_scope()へ渡すと、レビュー側で `roomStates references room(s) outside the current scope: room-1f-05` を再現しました。

その場のapply_state()はプロジェクトのroomIdsで検証するため見た目上は成功しますが、再保存した案/次のrefreshはscopeIdから自己検証するため失敗します。「旧案を読み込んで洋室が残った」だけでは往復が成立していません。

マージ結果は現在プロジェクトのscopeIdを持たせ、旧案のscopeは必要なら来歴に残してください。共通マージへ対象scopeを渡し、保存・再読込・refreshの契約を揃えます。対象外室を含むincomingをマージ時に黙って落とすことも避け、適用前に拒否します。

最小確認：旧LDK案→2室へマージ→新版保存→scenario_inputs/retained_inputsで再読込が通ること。元の旧案ファイルは不変にします。

## R3 高：refreshが不足室の最新保存を使わず、全室案でも不要な前回保存を要求する

対象：scripts/refresh-visual-study.py:150〜175。

--scenarioの場合もprevious_fullを無条件に `previous/study-state.json` から読みます。これは生成時だけの原本コピーではなくエディタの保存ファイルです。内覧F5の `Saved/walkthrough-state.json` が新しくても採用されません。旧LDK案を重ねると、その案に含まれない洋室の最新F5設定を古いエディタ値へ戻す経路になります。

また、全対象室をカバーする正常な案でもprevious/study-state.jsonが壊れていると停止します。仕様の「全室案なら--previousの壊れた保存を読まない」に反します。案が部分集合の場合は基準状態を必要とする、という境界を実装してください。

既存retained_inputs等の最新有効保存選択/復旧待ち検出を共通利用し、部分案の不足室を保持します。全室案なら基準保存の内容を読みません。必要な基準が不正/復旧待ちなら不足室を案内して停止し、古い値/既定へ黙って落としません。マージに使う両入力をスナップショットし、何を基準にしたか記録します。

確認は、異なる洋室値を持つ旧エディタ保存と新しいF5保存で新しい値が残る1例、全室案と不正な前回保存の1例を小さなテストで十分です。UE再生成をケースごとに繰り返しません。

## R4 高：仕上げA/Bが照明まで切り替える

対象：unreal/study_controls.py:show_compare（850行付近）。

候補から返すroomStateにはfixturesも含まれますが、show_compare()は対象室のroomState全体を候補で置換しています。レビュー側で製品関数を抽出しapply_state等のみを代替して確認すると、比較開始前の `elec-008:on=true` が候補の空fixturesで消えました。仕上げの違いと照明の違いを混ぜて比較してしまいます。

開始前の対象室状態にcandidateのvariant/surfaceOverridesだけを重ね、fixturesは保持してください。他室/太陽/露出/視点を保持する現在の方針はそのままで構いません。コードコメントの「照明固定」と実装を合わせます。

AC4で求めた代表1比較の実UE確認も、修正版でR1の生成後の同じプロジェクトを使って開始→A/B→終了の1往復だけ実施してください。同時に2室の点灯を変え、室切替で隣室の設定/実光束が保持されることを確認すればAC2の未確認分もまとめられます。全比較の実機網羅は不要です。

## R5 中：Blenderの家具材質が各室variantを反映しない

対象：blender/build_interior.py:770〜804、build_furniture()。

外皮の基準材質naturalを維持するために作った単一matsを、そのまま2室すべての家具にも渡しています。室別variantはSurfaceBinderには渡りますが、家具/装飾はrole-bindingsを記録するだけで、Blender内での室別材質適用がありません。UEはroomIdから切り替えるので、同じ保存条件でBlenderとUEの家具仕上げが食い違います。

外皮の基準材質は固定したまま、対象室の役割材質は各室variantから生成/割当してください。固定色の金属等、元々variant対象外の材質まで変更する必要はありません。UEのrole対応が壊れないようにし、木目等も維持します。

確認は2室に異なるvariantを設定した1回の生成で、家具の代表材質がそれぞれの色/模様を参照することを検査すれば十分です。高精細化や新家具制作は要求しません。

## 確認した範囲・受入状況

- 提出の変更一覧33ファイル、主要差分と状態/生成/比較/保存の関係先を確認しました。証拠10件のSHA-256はすべて一致です。Blender成果物の読み取り制限は昇格した読み取りで解消し、証拠不備ではありません。
- test_refresh_study 11件・test_lighting 17件をレビュー側で実行し成功しました。保存形式の自己矛盾、仕上げ比較での点灯変更は別途軽量確認で再現しています。テスト件数の成功だけで未実施の操作を成功とは判断しません。
- AC1/共有壁生成/室切替は提出証拠あり。共有面の2スロット化を確認しました。AC3はrefresh停止とR2/R3のため未完、AC4は実機代表確認なしに加えR4の不具合あり。既存のC++コンパイル/論理smokeは提出証拠として扱い、今回は全内覧操作の再実行を追加要求しません。
- レビュー側ではBlender/UEを起動していません。根本原因の証明や全条件の実機再現は要求しませんが、通常更新が最後まで完了することは必須です。

## 提出方法

上記R1〜R5を同じG1内で修正し、元BASEを維持、W07-G1-report.mdを事実に合わせて更新、build/reviews/W07-G1-v2を作成してください。特に「既存の無害な例外」「ログに例外なし」「AC3実質満たす」の記述は修正します。

修正後の重い確認は、室別材質と旧案部分適用を含む完全refresh代表1回＋そのプロジェクトで比較/点灯の短い確認へまとめてください。原則Sonnetで継続可能です。原因不明という理由でG2へ持ち越さず、まず特定できたコード上の問題を修正します。
