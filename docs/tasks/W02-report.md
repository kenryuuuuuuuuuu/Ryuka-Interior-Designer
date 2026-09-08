# W02 実装報告（第4版・レビューv3の必須修正A/B対応）

状態：READY_FOR_REVIEW
開始BASE（完全SHA）：`0ebb9f616930fa06436fddaed652e00a3334746c`（第1〜3版と同じBASEからの累積差分）
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境（OS/UE/ツール版、変更した設定）：Windows 11 25H2 [10.0.26200.9278] / UE 5.8.2（CL-56702186）/ NVIDIA GeForce RTX 5060 Ti ドライバ 32.0.16.1656 / Blender 5.2.0 LTS / Avast Antivirus稼働中。環境設定の変更は行っていません。

**今回はレビューv3で「検証用ログ・決定的な障害注入・ネイティブテストの追加」が明示的に許可されたため、外部プロセスからの当て推量的な操作（キー入力シミュレーション、FileSystemWatcherの競合待ち）ではなく、コード内に決定論的なテスト経路を追加しました**（`-RyukaFaultSave`、`-RyukaVerifyRecovery`、`-RyukaBoundaryFaultTest`のコマンドライン引数で有効化。通常起動では一切分岐せず、施主の起動には影響しません）。これらは`Walkthrough.cpp`に恒久的に残るテストコードで、`build/`配下の生成専用プロジェクトに対してのみ実行し、施主の実データ（`build/ue-walk-v1`等）には一切触れていません。

## 結果

`docs/tasks/W02-review-v3.md`の必須修正A・Bに対応しました。狭い場所の操作感の磨き込みや新機能は追加していません。

**修正A（バックアップ復元失敗の未処理）**：`SaveView()`内で、置換失敗後にバックアップを復元する`Move()`の戻り値を無視していました。これを確認するように変更し、復元も失敗した場合はバックアップを一切触らずに具体的なメッセージを表示して即座にreturnするようにしました。さらに、`Path`が存在せず`Backup`が存在する（＝前回の置換とその復元の両方が失敗した）状態を純粋にディスク上のファイルの有無だけで検出する`RecoverSaveIfNeeded()`を追加し、`SaveView()`（保存を拒否し、Backupを一切上書きしない）と`RestoreView()`（`bReady=false`にして操作を止める）の両方の先頭で呼ぶようにしました。可能な場合は自動復旧（`Backup`を`Path`へ戻す）を試み、それ自体が失敗する場合のみ人間の確認を求めるメッセージを出します。

**修正B（2回とも補正失敗時に操作が継続してしまう）**：境界補正が2回とも`Safe()`失敗だった場合、`LastSafeLocation`を更新しないだけで`bReady`はtrueのまま残り、後続の`AddMovementInput`・`SaveView()`が安全でない位置から継続できてしまっていました。両方失敗した場合は`StopMovementImmediately()`・`DisableMovement()`・`bReady=false`とし、「安全な位置へ戻れません。F9で復元してください」を表示するようにしました。無条件テレポートは追加していません。F9（`RestoreView()`→`Restore()`）が改めてSafeな開始点を確保できた場合のみ`MOVE_Walking`が復元され、操作が再開します。

## 必須修正A・Bへの個別回答

**必須修正A**：ご指摘の通り、`Move(Path,Backup,...)`（復元）の戻り値を無視していたため、復元も失敗した場合に「Pathなし・Backupあり」という状態が検出されないまま残り、次のF9/起動が黙って基準状態へフォールバックし、次のF5が「Pathなし＝初回保存」として扱ってBackupを保護対象から外してしまう経路がありました。今回、この状態をディスク上のファイル存在だけで判定する`RecoverSaveIfNeeded()`を`SaveView()`と`RestoreView()`の両方の先頭に置き、(1) 保存は拒否してBackupを一切変更しない、(2) 起動/F9も同じ状態を検出して`bReady=false`にする、(3) 可能なら自動復旧（`Move(Path,Backup)`が実際に成功する場合のみ）、を実装しました。停電耐性や汎用の履歴管理は追加していません（ご指示通り単純な復旧待ち状態のみ）。

検証は、レビューが許可したネイティブの障害注入点を`SaveView()`自体に追加しました（`#if !UE_BUILD_SHIPPING`かつ`-RyukaFaultSave`起動時のみ有効）。バックアップへの退避（`Move(Backup,Path)`）が成功した直後、退避で空いた`Path`という名前に**実際にディレクトリを作成**します。これにより後続2つの`Move()`呼び出し（最終置換・復元）は、Windowsの本物のリネーム意味論（ファイルを既存ディレクトリへ上書きリネームできない）によって、シミュレーションではなく実際に失敗します。FileSystemWatcherによる競合待ちと異なり、常に同じ段階で確実に失敗するため回帰として固定できます。

この障害注入を使い、単一プロセス内で決定論的に：(1) 初回保存でBackupなしの状態を作る、(2) 2回目の保存で二重失敗を発生させる、(3) Backupの内容が保存前と完全一致することを確認、(4) その状態でもう一度F5を押してもBackupが変化しないことを確認、(5) その状態でF9を押すと`bReady=false`かつ復旧待ちメッセージになることを確認、をすべて`SaveView()`/`RestoreView()`の実コードを通して検証し、結果を`Saved/walkthrough-fault-save.json`に記録するテスト（`-RyukaFaultSave`）を追加しました。障害物（ディレクトリ）はこの時点であえてディスクに残し、**別プロセスとしてUEを2回追加起動**することで、(6) 再起動しても同じ状態が認識されること、(7) 障害物を実際に削除してから再起動すると自動復旧すること、を確認しました。この2回の追加起動は`-RyukaVerifyRecovery`という読み取り専用の観測スイッチを使っており、これは起動時に無条件で呼ばれる既存の`RestoreView()`の判断には一切手を加えず、その結果（`bReady`・`Message`・実ファイルの状態）をJSONに書き出して終了するだけなので、動作としては施主の普通の起動と同一です。

**検証中に副次的な不具合を発見・修正しました**：復旧待ちメッセージに`FPaths::ProjectDir()`由来の絶対パスをそのまま埋め込んでいたところ、このリポジトリの実際の作業ディレクトリ名（日本語を含む）を通ると、このHUDメッセージだけが文字化けすることが判明しました（実ファイルI/O自体は正しいディレクトリに対して一貫して成功しており、破損は表示用文字列に限られることを確認済みです）。絶対パスではなく、非ASCII文字を含まないプロジェクト相対名（`Saved/walkthrough-state.json.bak`）に変更し、この環境で再現・解消を確認しました。表示のみの問題で保存/復旧のロジック自体に影響はありませんが、実際にこの日本語パス環境で動かす以上、見過ごさず修正しています。

実測結果（`build/W02-diag/v4-final-*.log`、デコード済みJSON `build/W02-diag/v4-final-*-decoded.json`）：

| 手順 | プロセス | 結果 |
|---|---|---|
| (1)(2)(3) 二重失敗発生・Backup保護 | `-RyukaFaultSave`（1プロセス目） | `createdInitialSave: true`, `backupPreservedAfterFault: true`, メッセージに「復旧」を含む |
| (4) 再F5でもBackup保持 | 同上（同一プロセス内） | `backupPreservedAfterRepeatSave: true` |
| (5) F9も復旧待ちを検出 | 同上（同一プロセス内） | `blockedOnF9WhileFaulted: true` |
| (6) 再起動でも認識 | `-RyukaVerifyRecovery`（2プロセス目、障害物残存） | `ready: false`, `pathIsFile: false`, `backupExists: true` |
| (7) 障害解除後に自動復旧 | 障害物を実際に削除→`-RyukaVerifyRecovery`（3プロセス目） | `ready: true`, `pathIsFile: true`, `backupExists: false`。復元後の`walkthrough-state.json`のSHA-256（`ac6769c7...`）は元のBackupのハッシュと完全一致 |

**必須修正B**：Walkthrough.cpp:391-397（旧325-330相当）を、両方のSafe()判定が失敗した場合に`StopMovementImmediately()`・`DisableMovement()`・`bReady=false`・専用メッセージを設定するよう変更しました。検証は、レビューが許可した実スポーンのブロッキング形状（`/Engine/BasicShapes/Cube.Cube`、`BlockAll`コリジョン）を使い、`Tick()`本体の補正ロジックには一切手を加えずに3段階を連続して直接通しました（`-RyukaBoundaryFaultTest`）：

1. 既知のSafeな地点から実際の`Safe()`判定を使って境界（または家具）の外にわずかに出る地点まで実際に歩かせ（5cmずつプローブ）、そこへテレポートして通常の1回で回復するケースを再現（新しい停止分岐が誤って発動しないことの回帰確認）。
2. 直前の到達地点と直前の`LastSafeLocation`の両方を広く覆う実ブロッカー（900×900×300cm）をスポーンし、候補地点・2軸独立候補・二分探索区間・フォールバック先のいずれからも安全な逃げ場がない状態を作って二重失敗を強制。
3. ブロッカーを削除してからF9相当の`RestoreView()`を呼び、Safeな地点へ復帰することを確認。

実測結果（`build/W02-diag/v4-boundary-run2-decoded.json`）：`recoveredWithinTwoAttempts: true`（メッセージは変化なし＝通常続行）、`stoppedAfterBothAttemptsFailed: true`（`MovementMode==MOVE_None`かつ`Velocity`ほぼゼロも確認、メッセージ「安全な位置へ戻れません。F9で復元してください」）、`resumedAfterF9: true`（メッセージ「視点を復元しました」）。`passed: true`。

## 変更と判断

### コード変更（第4版で追加した差分、`Walkthrough.cpp`のみ）

1. `SavedViewPaths()`・`RecoverSaveIfNeeded()`を追加（修正A）。
2. `SaveView()`：先頭で`RecoverSaveIfNeeded()`を確認、復元`Move()`の戻り値を確認して失敗時に専用メッセージでreturn、`-RyukaFaultSave`時のみ有効な障害注入行を追加（修正A）。
3. `RestoreView()`：先頭で`RecoverSaveIfNeeded()`を確認（修正A）。
4. `Tick()`：境界補正が2回とも失敗した場合の停止処理を追加（修正B）。
5. `Tick()`：`-RyukaFaultSave`・`-RyukaVerifyRecovery`・`-RyukaBoundaryFaultTest`の3つのネイティブテストブロックを追加（いずれも該当スイッチがコマンドラインにない限り完全に不活性）。
6. 復旧待ちメッセージの参照先を、絶対パスからプロジェクト相対名（ASCII）に変更（検証中に発見した文字化け対策）。

`Walkthrough.h`の変更はありません。設計からの差異：なし。追加依存：なし。環境変更：なし。

未追跡/ignored成果物：`build/W02-diag/v4-*`（第4版の追加ログ・デコード済みJSON）、`build/W02-refresh-v4/`（最新コード反映版の一括再生成出力）。前回の`build/W02-refresh-v1〜v3/`も検証環境として維持しています。いずれも`.gitignore`対象で未コミットです。

## 残ること

**未解決の既知の制限（変更なし）**：家具と部屋境界が極端に近接する狭い箇所で、斜め移動が完全な壁沿いスライドにならない場合があります（速度面）。今回もA・B（安全性）の対象外として作業していません。

**未検証**：施主自身の実機での操作感は引き続き未確認です。

## 再現・復旧

```powershell
# コンパイル・反映
python scripts/enable-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v4/ue --cache '../../ddc'

# NullRHI / DX12 両smoke
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v4/ue --cache '../../ddc' --smoke --logic-only
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v4/ue --cache '../../ddc' --smoke

# 正本からの一括再生成（新しい出力先を使用）
python scripts/refresh-visual-study.py --previous build/W02-refresh-v4/ue --output build/<new-name> --blender 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --engine 'C:/Program Files/Epic Games/UE_5.8' --cache '../../ddc'
```

修正Aのネイティブ回帰テスト（`UnrealEditor-Cmd.exe`を直接起動。このworktreeの生成専用プロジェクトに対してのみ実施）：
```powershell
# 1) 二重失敗を発生させ、Backup保護・再F5・F9拒否まで単一プロセスで確認
& "$Engine\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "$Project\RyukaInterior.uproject" /Game/Generated/House -game -NullRHI -windowed -NoSourceControl -NoSound -nosplash -unattended -RyukaFaultSave
# → Saved/walkthrough-fault-save.json / .txt を確認

# 2) 障害物（Saved/walkthrough-state.json がディレクトリ化）を残したまま再起動し、認識を確認
& "$Engine\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "$Project\RyukaInterior.uproject" /Game/Generated/House -game -NullRHI -windowed -NoSourceControl -NoSound -nosplash -unattended -RyukaVerifyRecovery
# → Saved/walkthrough-recovery-check.json: ready=false, pathIsFile=false, backupExists=true

# 3) 障害物を削除してから再起動し、自動復旧を確認
Remove-Item -Recurse -Force "$Project\Saved\walkthrough-state.json"
& "$Engine\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "$Project\RyukaInterior.uproject" /Game/Generated/House -game -NullRHI -windowed -NoSourceControl -NoSound -nosplash -unattended -RyukaVerifyRecovery
# → Saved/walkthrough-recovery-check.json: ready=true, pathIsFile=true, backupExists=false
```

修正Bのネイティブ回帰テスト：
```powershell
& "$Engine\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "$Project\RyukaInterior.uproject" /Game/Generated/House -game -NullRHI -windowed -NoSourceControl -NoSound -nosplash -unattended -RyukaBoundaryFaultTest
# → Saved/walkthrough-boundary-fault.json / .txt を確認
```

異常系の他の再現手順（前版から変更なし）：
- schemaVersion不正：`Saved/walkthrough-state.json`の`schemaVersion`を書き換えて起動
- 太陽変更失敗：`study-bindings.json`を無効なJSONに置き換えてから太陽高度キーを押す
- 安全候補なし：`walkthrough.json`の`polygonCm`を極小の矩形に置き換えて起動

全ログ・状態JSONは`build/W02-diag/`配下、一括再生成の成果物は`build/W02-refresh-v4/`配下にあります。
