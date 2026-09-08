# W02 実装報告

状態：READY_FOR_REVIEW
開始BASE（完全SHA）：`0ebb9f616930fa06436fddaed652e00a3334746c`
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境（OS/UE/ツール版、変更した設定）：Windows 11 25H2 [10.0.26200.9278] / UE 5.8.2（CL-56702186）/ NVIDIA GeForce RTX 5060 Ti ドライバ 32.0.16.1656 / Blender 5.2.0 LTS / Avast Antivirus稼働中。環境設定の変更は行っていません。実キー・マウス入力の検証には、テスト専用のC#ヘルパー（`build/W02-diag/InputSim.cs`、Win32 `SendInput`を使いOSレベルの入力イベントを注入。関数の直接呼び出しではない）を使用しました。

## 結果

ゲストLDK内覧を実際のキーボード・マウス入力（`SendInput`によるOS入力）で操作確認し、3件の不具合（壁際の斜め歩行固まり、視点上下角度の上限なし、保存画角の復帰未反映）を修正しました。保存/復帰の正常系・異常系（JSON破損、必須フィールド欠落、別部屋、両保存無効、保存位置の重なり）をすべて実機で確認し、いずれもクラッシュせず安全に処理されることを確認しました。HUDは日本語表示です。正本から新しい出力先への一括再生成後もDX12描画・状態引継ぎが成功することを確認しました。一般的な壁際での斜め歩行は大きく改善しましたが、家具と部屋境界が極端に近接する一部の狭い箇所では、なお改善の余地があります（AC2は部分達成として報告します）。

| 条件ID | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| AC1 | PASS | 実入力（`InputSim.cs`経由の`SendInput`、ウィンドウタイトル検索でフォーカスを確認してから送信）で確認。前後左右移動（W/S/A/D、各方向の実測移動距離）、停止（キーを離すと位置不変）、斜め移動の速度不正規化なし（D単独0.6秒=72.4cm、W+D斜め0.6秒=68.6cm。理論上の√2倍=102.4cmには程遠く、正しく正規化）、マウスによる視点操作（yaw/pitch変化を確認）、Tab解放中はマウス移動が視点に無反応（yaw差0.0）、再取得で反応再開（yaw差39.9）。証拠：`build/W02-diag/ac-state-*.json`（位置・向きのログ）、`build/W02-diag/50-*.png`〜`51-*.png`（Tab確認のスクリーンショット） |
| AC2 | 部分PASS | 家具から離れた壁際：斜め移動で大幅改善（直進1秒=44.6cm→斜め1.5秒=113.6cm、修正前は壁際で移動入力自体がブロックされ0cm固着）。低fps（`t.MaxFPS 30`起動）でも床抜け・部屋外逸脱なし（Z座標232.85で不変、XY座標はポリゴン範囲内）を確認。**既知の制限**：家具（冷蔵庫等）と部屋境界（26cm）が極端に近接する狭い箇所では、斜め移動が完全な壁沿いスライドにならず進みが遅い場合がある（同条件で2〜25cm、複数回の改善を試みたが完全解消には至らず）。証拠：`build/W02-diag/ac-state-38〜49-*.json`、`build/W02-diag/52〜56-*.json`（低fps）、UEログの`is stuck and failed to move`警告（改善前） |
| AC3 | PASS | 1/2/3で仕上げ切替（`natural`/`warm`/`reference`）、4/5で太陽高度切替を実入力で確認。F5保存→別状態へ変更→F9復帰で保存内容と完全一致（variant一致、位置X/Y差0.1cm未満）を確認（`build/W02-diag/62〜64-*.json`）。lensMmは保存時21.4516mm、復帰後も同値で往復（float32丸め内）。UEプロセス完全終了→再起動でも保存内容から自動復元（`build/W02-diag/70-restart-restored.png`、「視点を復元しました」表示）。画角80度以外の基準（reference仕上げ・21.45mm）からの復帰も確認済み |
| AC4 | PASS | 実際にファイルを破損させて検証。(1)JSON構文エラー→クラッシュせず`study-state.json`へ安全にフォールバック（`build/W02-diag/71-corrupt-json-result.png`）。(2)`camera`フィールド欠落→クラッシュせず（ログにcritical/fatal/assertなし）。(3)別部屋roomId→クラッシュせず正本にフォールバック（`72-wrongroom-result.png`）。(4)両保存とも無効（構文エラー）→移動開始せず「有効な視点を復元できません」表示、ファイル未上書き（`73-both-invalid-result.png`）。(5)保存位置が家具（冷蔵庫）の中心と重なる→安全候補探索が機能し「空いている最も近い位置へ移動しました」と表示（`74-collision-result.png`）。すべて既存ファイルは書き換わらず、施主の実データには一切触れていません（このworktreeの生成専用プロジェクトのみを操作） |
| AC5 | PASS | 実画面で日本語HUDの表示を確認、文字化けなし（`build/W02-diag/50-tab-before.png`ほか多数）。追加のフォントアセットは使用せず、UE標準フォントで日本語グリフが正しく描画されることを確認しました |
| AC6 | PASS | `python scripts/refresh-visual-study.py --previous build/refresh-walk-v3/ue --output build/W02-refresh-v1 --blender <Blender5.2> --engine <UE5.8> --cache '../../ddc'` → 終了コード0、`refresh.json`の`status:"complete"`、`stateVerification`（statePreserved/geometryVerified/cameraRotationPreserved すべてtrue）。新出力先`build/W02-refresh-v1/ue`でNullRHI・DX12両smoke実行、ともに終了コード0・`renderVerified`はlogic-onlyでfalse／通常実行でtrue。コード反映版：本報告のHEAD（`unreal/walkthrough/Source/RyukaInterior/Walkthrough.cpp`・`.h`の全修正を含む） |
| AC7 | PASS | 下記回帰コマンドすべて成功。`docs/STATUS.md`・`docs/UNREAL_WALKTHROUGH.md`を現況（ドライバ更新後に描画復旧、W02で操作確認、残る既知制限）に更新 |

回帰：`python -m unittest discover -s tests -p 'test_*.py'`→48 tests OK。`python tests/validate_house.py`→33室・35壁 checks passed。`python tests/validate_furniture.py`→30型・45件 checks passed。`node scripts/build-web-data.mjs --check`→最新。`node tests/test_furniture_web.mjs`→合格。いずれも終了コード0。

## 変更と判断

### コード変更（`unreal/walkthrough/Source/RyukaInterior/Walkthrough.cpp`・`.h`）

1. **壁際の斜め移動固まり**：`Tick()`が移動前に`Safe(Next)`で移動先全体をチェックし、境界26cm以内なら移動入力自体を拒否していました（家具・壁の衝突とポリゴン境界の判定が同じ関数`Safe()`に混在）。`Safe()`を`InsideRoom()`（ポリゴン境界のみ）と`Safe()`（境界+衝突、開始位置探索用に維持）に分離し、`Tick()`では家具・壁の衝突をCharacterMovementの標準スイープ・スライドに委ね（常に`AddMovementInput`を呼ぶ）、部屋ポリゴンの境界（開口部など物理壁がない場所）だけを移動後に検出して補正する設計に変更しました。
   - 初回実装（直前の安全位置へ完全ロールバック）は、境界にほぼ接した状態で家具に沿ってスライドしようとするとCharacterMovementの押し出し処理と競合し「stuck」状態（UE標準ログの`is stuck and failed to move!`警告）を再現してしまいました。二分探索で「境界内の最遠点」まで部分的な前進を許す方式に変更し、さらに軸独立（X/Yそれぞれ単独ならポリゴン内かを先に試す）に変更して改善しました。ただし完全解消には至っていません（AC2参照）。
2. **視点上下角度の上限なし**：`AddControllerPitchInput`後に`GetControlRotation()`を読んで手動クランプする実装を最初に試しましたが、この入力が実際に`ControlRotation`へ反映されるのはPlayerControllerの内部更新（本Tickの後）のため、常に1フレーム遅れた値を読んでしまい機能しませんでした。UE標準の`PlayerCameraManager::ViewPitchMin/Max`（内覧開始時に-80/80を設定）に変更し、正しく機能することを確認しました。
3. **保存画角の復帰未反映**：`Restore()`が`camera.lensMm`を読み込まず、`Eye->FieldOfView`はコンストラクタの80度のまま固定されていました。`SaveView()`と同じ36mm換算センサー幅の契約（`lensMm=18/tan(FOV/2)`）の逆変換（`FOV=2*atan(18/lensMm)`）を追加し、Python側`study_state.py`と同じ許容範囲（12〜120mm）で検証してから適用します。
4. HUD・状態メッセージ（`Message`）をすべて日本語化。仕上げ名のラベルはEditor側`study_controls.py`の`register_menu()`と表記を一致させました。

設計からの差異：仕様書は「WASDは視点の水平向きに沿い、斜め歩きで速くならないこと」「Safe(Next)の書き換え」を明確に指示しており、これに沿って実装しました。二分探索・軸独立判定は仕様書に明記されていない実装判断ですが、「床と衝突を扱うCharacterMovementのスイープ/滑りを活かして修正」「ポリゴン外への移動防止は維持」という制約の範囲内での対応です。

追加依存：なし。環境変更：なし。

未追跡/ignored成果物：`build/W02-diag/`（診断スクリプト`InputSim.cs`・`dump_stacks.py`は今回未使用、実測ログ・スクリーンショット多数）、`build/W02-refresh-v1/`（一括再生成の出力一式）、`build/W02-baseline/`（作業開始前の`walkthrough-verification.json`退避）。いずれも`.gitignore`対象で未コミットです。

## 残ること

**未解決の既知の制限**：家具と部屋境界（26cm）が極端に近接する狭い箇所で、斜め移動が完全な壁沿いスライドにならない場合があります（AC2）。二分探索・軸独立クランプの2段階の改善を試みましたが、根本解消には至っていません。この位置は`fur-007`（冷蔵庫、guest LDK北壁際）付近で再現します。次段階での追加調査候補：家具の`CollisionTraceFlag`（現状`CTF_UseComplexAsSimple`）をシンプルコリジョンに変更する、または境界判定のヒステリシス（一度安全と判定した範囲を数フレーム保持する）を追加する、などが考えられますが、いずれも未検証です。

**テスト手法上の教訓**（今回の調査で判明、次回の参考に記録）：
- Windowsの`Process.MainWindowHandle`は`UnrealEditor-Cmd.exe`に対して不安定（フォーカスが実際には奪われていてもtrueを返す場合がある）で、ウィンドウタイトルの直接検索（`EnumWindows`+`GetWindowText`）に切り替える必要がありました。フォーカス確認を怠った一部の初期テストで「完全固着」と誤診断した箇所がありましたが、本報告の数値はすべてフォーカス確認済みの再テストによるものです。
- F5保存直後にF9やF5を連続で呼ぶテスト方法は、直前の呼び出しのMessageを次の呼び出しが上書きしてしまい、実際の成否を誤認する原因になりました（F9は実際には成功していたのに、直後のF5が高負荷で偶発的に失敗し「F9が失敗した」ように見えました）。個々の操作の結果はスクリーンショットで直接確認する必要があります。

**未検証**：施主自身の実機での操作感（マウス感度、歩きやすさの主観評価）は未確認です。実ゲームパッド入力は対象外（仕様書にも記載なし）。

## 再現・復旧

```powershell
# コンパイル・反映（既存の検証済みプロジェクトへ）
python scripts/enable-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v1/ue --cache '../../ddc'

# NullRHI / DX12 両smoke
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v1/ue --cache '../../ddc' --smoke --logic-only
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v1/ue --cache '../../ddc' --smoke

# 実ウィンドウでの内覧
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v1/ue --cache '../../ddc'

# 正本からの一括再生成（新しい出力先を使用）
python scripts/refresh-visual-study.py --previous build/W02-refresh-v1/ue --output build/<new-name> --blender 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --engine 'C:/Program Files/Epic Games/UE_5.8' --cache '../../ddc'
```

異常系の再現には`build/<project>/ue/Saved/walkthrough-state.json`または`study-state.json`を手動で破損・改変してから起動します（このworktreeの生成専用プロジェクトに対してのみ実施し、施主の実データには行いません）。

全ログ・スクリーンショット・状態JSONは`build/W02-diag/`配下、一括再生成の成果物は`build/W02-refresh-v1/`配下にあります。
