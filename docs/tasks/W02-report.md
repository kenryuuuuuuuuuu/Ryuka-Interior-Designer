# W02 実装報告（第3版・レビューv2の必須修正A/B対応）

状態：READY_FOR_REVIEW
開始BASE（完全SHA）：`0ebb9f616930fa06436fddaed652e00a3334746c`（第1版・第2版と同じBASEからの累積差分）
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境（OS/UE/ツール版、変更した設定）：Windows 11 25H2 [10.0.26200.9278] / UE 5.8.2（CL-56702186）/ NVIDIA GeForce RTX 5060 Ti ドライバ 32.0.16.1656 / Blender 5.2.0 LTS / Avast Antivirus稼働中。環境設定の変更は行っていません。実キー・マウス入力の検証には`build/W02-diag/InputSim.cs`（Win32 `SendInput`、`EnumWindows`+`GetWindowText`でフォーカス確認）を、修正Aの障害注入には`build/W02-diag/FaultInjector.cs`（`FileSystemWatcher`でtempファイル作成を検知し即時削除、実際のネイティブ保存関数の内部で発生する2段階目のリネーム失敗を再現）を使用しました。

## 結果

`docs/tasks/W02-review-v2.md`の必須修正A・Bに対応しました。狭い場所の操作感の磨き込みや新機能は追加していません。

**修正A**：保存の置換処理が「旧ファイル削除→新ファイルへリネーム」の2段階（`FFileManagerGeneric::Move`の内部実装）になっており、1段階目成功後に2段階目が失敗すると旧データが失われる欠陥がありました。既存ファイルを削除せず退避（リネーム）してから置換し、失敗時は退避先から復元する設計に変更しました。**実際にネイティブ保存関数を通した障害注入テスト**（`FileSystemWatcher`でtempファイルの作成を検知し、UEプロセスの2段階目のリネームより先に削除して確実に失敗させる）で、旧データのSHA-256ハッシュが完全一致すること、Messageが正しく「保存に失敗しました」となること、その後のF9復元・UEプロセス完全終了後の再起動でも保護されたデータから正しく復元されることを確認しました。

**修正B**：境界補正の最終フォールバック（候補地点がSafeでない場合の`LastSafeLocation`への復帰）がスイープなしのテレポートだったため、経路上の貫通を防げていませんでした。フォールバックもスイープに変更し、さらに通常分岐（`Current`を`LastSafeLocation`として記録する条件）を`InsideRoom()`から`Safe()`に変更しました。Tick順序の説明も、実際のUEソース（`UMovementComponent`の`bTickBeforeOwner`と`RegisterComponentTickFunctions`）に基づく正確な記述に修正しました。

| 条件ID | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| AC2（B関連） | 部分PASS（安全性さらに向上、速度は変更なし） | 境界＋家具の複合ケース（冷蔵庫付近）を再テストし、貫通なし・クラッシュなしを確認（`build/W02-diag/v3-state-04〜06-*.json`、`v3-07-no-clip-check.png`）。レビューが要求した「1回目のスイープが障害物で止まり着地点が部屋外のまま」という経路を確実に再現するため、境界が常に近い細長い部屋（一時的な`walkthrough.json`、生成専用プロジェクトのみ）で持続的な斜め圧力（3秒間）をかけて検証し、`is stuck`警告・クラッシュとも発生せず位置は常に部屋の範囲内に留まることを確認しました（`v3-narrow-*.json`、`v3-08〜09-*.png`）。**未確認事項**：2回目のフォールバックスイープが特定のフレームで実際に発動したことを直接示すログ計装は、コードに新しい分岐/ログを追加しないというレビューの制約に従い、追加していません |
| AC4（A関連） | PASS（最も厳格な失敗経路を実証） | `FaultInjector.cs`で`Saved/walkthrough-state.json.tmp`作成を監視し、UEログで確認できる実際の`MoveFile`失敗（Error Code 2、10回リトライ全滅、最終的に"Error moving file"）を発生させた上で：(1)保存前後のSHA-256ハッシュが完全一致（`ac6769c7...`）、(2)Message「保存に失敗しました」表示、(3)その状態からF9復元が正常動作（「視点を復元しました」）、(4)UEプロセス完全終了→再起動でも保護データから復元（ハッシュ再確認）、をすべて確認しました。証拠：UEログの`LogFileManager`該当行、`v3-01〜03-*.png` |
| AC6 | PASS（最新コード反映版で再実行） | `refresh-visual-study.py --previous build/W02-refresh-v2/ue --output build/W02-refresh-v3 ...` → 終了コード0、`status:"complete"`、`changedSourceFiles`に`Walkthrough.cpp`含む、`stateVerification`全項目true。新出力先でNullRHI/DX12両smoke実行、終了コード0。`walkthrough-verification.json`・smoke PNGを証拠として保存（`v3-walkthrough-verification.json`、`v3-smoke-render.png`）。同じv3プロジェクトで35mm→35.000002mm、18mm→18mmの往復も再確認し、数値結果をJSONで保存（`v3-lens-35mm-result.json`、`v3-lens-18mm-result.json`） |

回帰：`python -m unittest discover -s tests -p 'test_*.py'`→48 tests OK。`validate_house.py`→33室・35壁。`validate_furniture.py`→30型・45件。`build-web-data.mjs --check`→最新。`test_furniture_web.mjs`→合格。すべて終了コード0（v2・v3両方の出力先で確認）。

## 必須修正A・Bへの個別回答

**必須修正A（高：置換途中の失敗で旧保存が失われる）**：ご指摘の通り、`FFileManagerGeneric::Move(Path,Tmp,Replace=true,...)`は内部で「既存Destを`DeleteFile`→`MoveFile(Dest,Src)`」の2段階処理であり、前回の修正（bool判定の訂正）だけでは、1段階目成功後に2段階目が失敗するケースへの保護になっていませんでした。既存ファイルを事前に削除せず、まず`.bak`へリネームで退避し、新データへの置換が成功して初めて`.bak`を削除、失敗時は`.bak`から復元する設計に変更しました。初回保存（旧ファイルなし）・通常上書き・temp書込み失敗・置換処理失敗（退避段階／最終段階の両方）を区別しています。同じ`Move()`を別の場所で呼ぶラッパーではなく、`Path`を先に削除しない構造そのものを変更しています。

検証は、レビューが要求した「temp完成後、置換が失敗する」経路を、実際のSaveView()関数を通して再現しました。`FileSystemWatcher`でtempファイルの`Created`イベントを監視し、検知後即座に削除することで、UE側の2段階目のリネーム（`.tmp`→本番ファイル名）を実際にファイルが見つからない状態で失敗させています。これはモックではなく、実際のネイティブファイル操作APIが本当に失敗した記録（UEログの`LogFileManager: Error: Error moving file ...`）を伴う再現です。停電耐性（両方の書き込みが同時に失われるような障害）は今回の対象に含めていません。

**必須修正B（高：境界補正の失敗時だけ衝突検査を迂回する）**：ご指摘の2点を修正しました。(1) 最終フォールバック（`Landed`が`Safe()`でない場合の`LastSafeLocation`への復帰）を、スイープなしのテレポートからスイープ移動に変更しました。「以前の点が安全」であることは「現在地点からそこまでの経路が安全」を意味しないというご指摘の通りで、2回目のスイープでも障害物があればそこで止まり、その着地点を改めて`Safe()`で確認してから採用します。(2) 通常分岐（`Current`を`LastSafeLocation`として記録する条件）を`InsideRoom(Current)`から`Safe(Current)`に変更し、コメントと実装を一致させました。(3) Tick順序の説明を、実際にローカルのUEソース（`Engine/Source/Runtime/Engine/Private/Components/MovementComponent.cpp`の35行目`bTickBeforeOwner=true`、186〜188行目`RegisterComponentTickFunctions`での`AddPrerequisite`）で確認した内容に基づく記述に修正し、「このプロジェクトで観測された順序」という不正確な表現を削除しました。不要な独自Tick機構は追加していません。

検証について正直に申し上げます。境界＋家具の複合ケース（冷蔵庫付近）と、境界が常に近い一時的な細長い部屋の両方で、持続的な圧力をかけて`is stuck`警告・クラッシュ・部屋外逸脱がいずれも発生しないことを確認しました。しかし、レビューが具体的に求めた「1回目のスイープが障害物で止まり、着地点がまだ部屋外となるケース」において、**2回目のフォールバックスイープが実際にそのフレームで発動したことを直接示すログは取得できていません**。コードに新しい条件分岐やログ計装を追加しないというレビューの指示（「実現が難しければ新しい条件分岐を積む前にGPTへ方式の相談をしてください」）を踏まえ、これ以上のコード変更は行わず、実機での安全側の挙動確認（貫通なし・クラッシュなし・境界維持）までを本報告の証拠とし、内部パスの直接的な発動確認は未実施として正直に報告します。

## 変更と判断

### コード変更（第3版で追加した差分、`Walkthrough.cpp`のみ）

1. `SaveView()`：`Path`を先に削除しない退避（`.bak`）方式に変更（修正A）。
2. `Tick()`：境界補正の通常分岐を`Safe(Current)`に変更、最終フォールバックをスイープに変更、Tick順序コメントを実際のエンジンソースに基づく記述に修正（修正B）。

`Walkthrough.h`の変更はありません。設計からの差異：なし。追加依存：なし。環境変更：なし。

未追跡/ignored成果物：`build/W02-diag/FaultInjector.cs`（新規、障害注入ヘルパー）、`v3-*.png`・`v3-*.json`（第3版の追加証拠）、`build/W02-refresh-v3/`（最新コード反映版の一括再生成出力）。前回の`build/W02-refresh-v1/`・`v2/`も検証環境として維持しています。いずれも`.gitignore`対象で未コミットです。

## 残ること

**未確認（AC2/修正B）**：2回目のフォールバックスイープが具体的なフレームで発動したことを直接示すログは取得していません。安全側の挙動（貫通なし・境界維持）は実機で確認済みですが、内部パスの発動自体を確実に証明する手段は、コード計装なしでは今回見つけられませんでした。

**未解決の既知の制限（AC2、変更なし）**：家具と部屋境界が極端に近接する狭い箇所で、斜め移動が完全な壁沿いスライドにならない場合があります（速度面）。これは修正A・Bの対象外（安全性のみ）として、今回追加の作業は行っていません。

**未検証**：施主自身の実機での操作感は引き続き未確認です。

## 再現・復旧

```powershell
# コンパイル・反映
python scripts/enable-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v3/ue --cache '../../ddc'

# NullRHI / DX12 両smoke
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v3/ue --cache '../../ddc' --smoke --logic-only
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v3/ue --cache '../../ddc' --smoke

# 正本からの一括再生成（新しい出力先を使用）
python scripts/refresh-visual-study.py --previous build/W02-refresh-v3/ue --output build/<new-name> --blender 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --engine 'C:/Program Files/Epic Games/UE_5.8' --cache '../../ddc'
```

修正Aの障害注入再現手順（PowerShell、`build/W02-diag/FaultInjector.cs`を使用。このworktreeの生成専用プロジェクトに対してのみ実施）：
```powershell
Add-Type -Path "build\W02-diag\FaultInjector.cs"
$job = Start-Job -ScriptBlock {
  param($diagPath, $dir)
  Add-Type -Path "$diagPath\FaultInjector.cs"
  [FaultInjector]::WatchAndDeleteOnCreate($dir, "walkthrough-state.json.tmp", 3000)
} -ArgumentList "build\W02-diag", "build\W02-refresh-v3\ue\Saved"
# この後、ゲーム内でF5を押す（既存のwalkthrough-state.jsonがある状態で）
```

異常系の他の再現手順（前版から変更なし）：
- schemaVersion不正：`Saved/walkthrough-state.json`の`schemaVersion`を書き換えて起動
- 太陽変更失敗：`study-bindings.json`を無効なJSONに置き換えてから太陽高度キーを押す
- 安全候補なし：`walkthrough.json`の`polygonCm`を極小の矩形に置き換えて起動

全ログ・スクリーンショット・状態JSONは`build/W02-diag/`配下、一括再生成の成果物は`build/W02-refresh-v3/`配下にあります。
