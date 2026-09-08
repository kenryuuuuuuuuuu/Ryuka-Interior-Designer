# W02 実装報告（第2版・レビューR1〜R4対応）

状態：READY_FOR_REVIEW
開始BASE（完全SHA）：`0ebb9f616930fa06436fddaed652e00a3334746c`（第1版と同じBASEからの累積差分）
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境（OS/UE/ツール版、変更した設定）：Windows 11 25H2 [10.0.26200.9278] / UE 5.8.2（CL-56702186）/ NVIDIA GeForce RTX 5060 Ti ドライバ 32.0.16.1656 / Blender 5.2.0 LTS / Avast Antivirus稼働中。環境設定の変更は行っていません。実キー・マウス入力の検証には、テスト専用のC#ヘルパー（`build/W02-diag/InputSim.cs`、Win32 `SendInput`でOS入力を注入し、`EnumWindows`+`GetWindowText`でフォーカスを確認してから送信。関数の直接呼び出しではない）を使用しました。

## 結果

`docs/tasks/W02-review.md`のR1〜R4すべてに対応しました。安全性の欠落（R1）を修正し、太陽変更失敗時のロールバック（R2）、schemaVersion検証と失敗理由の保持・常時仕上げ表示（R4）を追加し、未実施だった検証（R3：異なる画角での往復、安全候補なし、保存失敗のファイルハッシュ確認）を実際にファイルを壊して実施しました。**この過程で、レビュー未指摘の重大なバグを新たに1件発見・修正しました**：`SaveView()`の保存成否判定が`IFileManager::Move()`（`bool`を返す）を`ECopyResult::COPY_OK`（enumの0）と比較しており、C++の通常の算術変換規則により判定が反転していました（実際に失敗した保存が「成功」と表示され、成功した保存が理論上「失敗」と表示され得る状態）。読み取り専用ファイルでの実地テストで、`DeleteFile`が実際に失敗したログが残っているにもかかわらず「視点と条件を保存しました」と表示されたことから発見しました。

| 条件ID | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| AC1 | PASS（第1版から維持） | 実入力で確認済み。レビューの「採用可能な部分は維持」に従い変更なし |
| AC2 | 部分PASS（安全性の欠落を修正、速度改善は据え置き） | **R1修正を反映**：境界補正の候補点判定を`InsideRoom()`のみから`Safe()`（境界＋家具/壁の重なりなし）に変更し、候補点への移動もテレポートからスイープ移動（`SetActorLocation(...,true,&Hit,...)`）に変更、着地点を再度`Safe()`で確認してから採用する設計にしました。これにより経路上の家具貫通を防ぎます。冷蔵庫付近での再測定は前回と同じ数値（斜め移動2.0cm→24.8cm、二分探索・軸独立化の効果は維持）で、速度自体はまだ完全なスライドに至っていません。家具のない壁際は引き続き大幅改善（44.6cm→113.6cm）。証拠：`build/W02-diag/v2-state-*.json`、`v2-05-refrigerator-position.png` |
| AC3 | PASS（R3の画角実測を追加） | 第1版の保存/復帰・再起動復帰に加え、**R3で指摘された「80度以外の画角」を実際にJSONへ設定して検証**：lensMm=35mm（FOV≈54.43度）を復帰後に保存し直すと35.000002mmで往復、lensMm=18mm（FOV=90度）は18mmちょうどで往復。いずれもfloat精度の範囲内で契約通り機能することを確認しました |
| AC4 | PASS（R2・R4修正、および未実施2ケースを追加実施） | **R2**：`study-bindings.json`を実際に破損させた状態で太陽高度変更（4キー）を実行し、`ApplyConditions()`失敗時にelevationDegが変更前の値のまま保持される（60→60、変更されない）こと、Message「太陽角度を変更できません」を確認（`build/W02-diag/v2-07-setsun-rollback.png`）。**R4**：schemaVersion="2.0.0"（未知バージョン）を実際に保存ファイルに設定して起動し、拒否されて基準状態にフォールバックすること、かつ具体的な理由（「保存データの形式（バージョン）が無効です」）が汎用メッセージで消されずに複合メッセージとして表示されることを確認（`v2-08-schema-version-reject.png`）。**未実施だった2ケースを追加**：(a) 部屋ポリゴンを10cm四方に一時的に縮小し「安全候補なし」を実際に再現、具体的理由が正しく表示されること確認（`v2-10-no-safe-candidate-fixed.png`、これも当初R4の実装漏れで上書きされていたバグを発見・修正）。(b) 保存ファイルを読み取り専用にして保存失敗を発生させ、前後のSHA-256ハッシュが完全一致することを確認（既存ファイル保護）、かつ上記のMove()比較バグ修正後は正しく「保存に失敗しました」と表示されることを確認（`v2-13-readonly-save-fixed.png`） |
| AC5 | PASS（R4の常時仕上げ表示を追加） | HUDに「現在の仕上げ：〇〇」を常時表示するよう追加（`CurrentVariantLabel()`）。日本語グリフは通常のLit表示で確認済み（`v2-01-hud-variant.png`）。復帰失敗時は「現在の仕上げ：－」を表示 |
| AC6 | PASS（最新コード反映版で再実行） | `python scripts/refresh-visual-study.py --previous build/W02-refresh-v1/ue --output build/W02-refresh-v2 ...` → 終了コード0、`status:"complete"`、`stateVerification`全項目true。`changedSourceFiles`に`Walkthrough.cpp`が含まれることを確認（＝本報告の全修正が反映された状態で再生成）。新出力先`build/W02-refresh-v2/ue`でNullRHI/DX12両smoke実行、ともに終了コード0、`renderVerified`はlogic-onlyでfalse・通常実行でtrue |
| AC7 | PASS（記述を訂正） | 48テスト成功は維持。**レビュー指摘どおり訂正**：`UNREAL_WALKTHROUGH.md`の「NullRHIの描画検証」という記述を「描画なしのロジック検証」に修正しました（下記参照）。既存Pythonテストは家屋データの検証であり、今回のC++歩行ロジックの検証ではない旨も明記します |

回帰：`python -m unittest discover -s tests -p 'test_*.py'`→48 tests OK。`validate_house.py`→33室・35壁。`validate_furniture.py`→30型・45件。`build-web-data.mjs --check`→最新。`test_furniture_web.mjs`→合格。すべて終了コード0。

## R1〜R4への個別回答

**R1（高：境界補正が家具へのめり込みを防いでいない）**：ご指摘の通りでした。修正前は`KeepX`/`KeepY`/二分探索点を`InsideRoom()`のみで採否判定し、`SetActorLocation`もスイープなしで実行していたため、候補点自体が別の家具と重なる可能性、および経路上の家具を貫通する可能性の両方を防げていませんでした。`Safe()`（境界＋オーバーラップ判定）で候補を選び、候補への移動をスイープ（`SetActorLocation(Candidate,true,&Hit,ETeleportType::TeleportPhysics)`）に変更し、着地点を再度`Safe()`で確認してから`LastSafeLocation`に採用する設計に修正しました。安全でなければ前フレームの位置へ戻します（そこは前フレームで`Safe()`確認済みのためスイープ不要と判断）。「Super::Tickだけで移動完了を保証した」という根拠不明のコメントは、実際に確認できる範囲（このプロジェクトでの観測順序であり、UEの一般的なtick-group保証ではないこと）に修正しました。ヒステリシスの追加や全家具のコリジョン一律変更は行っていません。速度面の改善（AC2）は完全解消しておらず、部分PASSのまま報告します。

**R2（中：太陽変更失敗時の状態不一致）**：`SetSun()`に、`ApplyConditions()`失敗時のロールバックを追加しました。`TSharedPtr`の単純なコピーは同じ`FJsonObject`を指すため、その場での`SetNumberField`/`RemoveField`はロールバック用のコピーも変更してしまう点を踏まえ、`MakeShared<FJsonObject>(*State)`でオブジェクト自体（`Values`マップ）を複製してから変更し、失敗時はこのバックアップに戻す実装にしました。`SetSun()`はトップレベルの`elevationDeg`/`solar`のみを扱うため、この方式で十分ロールバックできます。実際に`study-bindings.json`を破損させて検証済みです。

**R3（中：画角・異常系の合格根拠が不足）**：ご指摘の通り、第1版の「80度以外の基準＝21.45mm」という記述は誤りでした（18/tan(40°)≈21.4516mmは実際にはFOV=80度そのものです）。35mm・18mmという実際に異なる画角で往復精度を検証し直しました（上表AC3参照）。安全候補なしと保存失敗も、専用プロジェクトのファイルを実際に壊して検証しました（上表AC4参照）。保存失敗はメッセージだけでなくSHA-256ハッシュの前後一致で確認し、その過程で「一時ファイルだから常に保護される」という前提が実際には保存成否判定バグにより無関係に成立していた（表示は誤っていたが、Move失敗時にファイルは実際に上書きされていなかった）ことも確認しました。

**R4（中：復帰状態の版検証と利用者表示が不足）**：`Restore()`の先頭で`schemaVersion`を検証し、`"1.0.0"`以外は拒否するようにしました（既存契約を維持し、新スキーマは作っていません）。各失敗パス（バージョン不正・部屋不一致・カメラ情報不正・画角不正・安全候補なし・条件適用失敗）にそれぞれ具体的な`Message`を設定しました。`RestoreView()`は、保存側の復元が失敗して基準状態にフォールバックした場合、その理由を保持して複合メッセージ（「保存データが無効なため基準状態に戻しました（理由）」）を表示するようにしました。**この実装の過程で、両方とも失敗した場合に正本（study-state.json）側の具体的理由がSaved側の理由で上書きされてしまう別のバグを実装中に発見し、その場で修正しました**（`Message=Reason;`という上書き行を削除）。現在の仕上げはHUDに常時表示するようにしました（`CurrentVariantLabel()`）。

## 変更と判断

### コード変更（`unreal/walkthrough/Source/RyukaInterior/Walkthrough.cpp`・`.h`、第2版で追加した差分）

1. `InsideRoom()`ベースだった境界補正の候補判定を`Safe()`ベースに変更し、候補への移動をスイープに変更（R1）。
2. `SetSun()`にJSON差し替えによるロールバックを追加（R2）。
3. `Restore()`にschemaVersion検証と型検証を追加、各失敗パスに具体的なMessageを設定（R4前半）。
4. `RestoreView()`のフォールバックメッセージ処理を、具体的な失敗理由を保持するよう修正（R4後半、実装中に発見した二次バグも含む）。
5. `CurrentVariantLabel()`を追加し、`DrawHUD()`で現在の仕上げを常時表示（R4）。
6. **`SaveView()`の保存成否判定バグを修正**：`IFileManager::Move()`は`bool`を返すが`ECopyResult::COPY_OK`（enumの0）と比較しており、`(int)bool==(int)enum`という通常の算術変換により判定が反転する状態でした。`==COPY_OK`を削除し、`bool`の戻り値をそのまま使うよう修正しました。これはレビューのR1〜R4のいずれにも直接指摘されていませんが、R3の「保存失敗のハッシュ確認」を実施する過程で発見したものです。

設計からの差異：なし（前回報告の設計方針を踏襲）。追加依存：なし。環境変更：なし。

未追跡/ignored成果物：`build/W02-diag/`（第2版の追加証拠：`v2-*.png`、`v2-state-*.json`、破損テスト用のバックアップファイル）、`build/W02-refresh-v2/`（最新コード反映版の一括再生成出力）。前回の`build/W02-refresh-v1/`も検証環境として維持しています。いずれも`.gitignore`対象で未コミットです。

## 残ること

**未解決の既知の制限（AC2、変更なし）**：家具と部屋境界が極端に近接する狭い箇所で、斜め移動が完全な壁沿いスライドにならない場合があります。R1の安全性修正（貫通防止）は完了しましたが、速度・滑らかさの改善は達成できていません。次段階の候補（家具コリジョンのシンプル化、境界判定のヒステリシス）は未検証のまま残っています。

**新たに判明した事実**：`Walkthrough.cpp`には`==COPY_OK`の比較バグがあり、これは今回R3の追加検証（保存失敗のハッシュ確認）で偶然発見しました。この経験から、成否判定ロジックはメッセージ表示だけでなく、実際のファイル状態（ハッシュ等）で裏付けることの重要性を再確認しました。同種の型不一致が他の判定ロジックに潜んでいないか、次段階で一度確認する価値があるかもしれませんが、今回の修正範囲（R1〜R4に限定）を超えるため、本報告では実施していません。

**未検証**：施主自身の実機での操作感（マウス感度、歩きやすさの主観評価）は引き続き未確認です。

## 再現・復旧

```powershell
# コンパイル・反映
python scripts/enable-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v2/ue --cache '../../ddc'

# NullRHI / DX12 両smoke
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v2/ue --cache '../../ddc' --smoke --logic-only
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v2/ue --cache '../../ddc' --smoke

# 実ウィンドウでの内覧
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/W02-refresh-v2/ue --cache '../../ddc'

# 正本からの一括再生成（新しい出力先を使用）
python scripts/refresh-visual-study.py --previous build/W02-refresh-v2/ue --output build/<new-name> --blender 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --engine 'C:/Program Files/Epic Games/UE_5.8' --cache '../../ddc'
```

異常系の再現手順（このworktreeの生成専用プロジェクトに対してのみ実施し、施主の実データには行いません）：
- schemaVersion不正：`Saved/walkthrough-state.json`の`schemaVersion`を`"1.0.0"`以外に書き換えて起動
- 太陽変更失敗：`study-bindings.json`を無効なJSONに置き換えてから太陽高度キー（4/5）を押す
- 安全候補なし：`walkthrough.json`の`polygonCm`を身体が入らない極小の矩形に置き換えて起動
- 保存失敗：`Saved/walkthrough-state.json`を読み取り専用属性にしてからF5を押す（前後のSHA-256を比較）

全ログ・スクリーンショット・状態JSONは`build/W02-diag/`配下、一括再生成の成果物は`build/W02-refresh-v2/`配下にあります。
