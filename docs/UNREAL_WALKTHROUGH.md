# Unreal内覧システム：第1段階

## 今回の範囲

ゲストLDK内を人の目線で移動し、仕上げ・太陽角度を切り替えて保存するネイティブC++モジュールを追加しました。Unrealの実行中はPythonを使いません。Pythonは生成・設定・検証を担当します。植物・布などの細部作成は中断し、この操作基盤を優先しています。

この版はUnrealをインストール済みのWindows PCで動かす開発用内覧です。配布用exeのパッケージ化、階段・他室移動、扉の開閉、日時ケースを選ぶ操作画面は後続です。

## 起動

専用ワークツリーをカレントディレクトリにして実行します。

```powershell
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/refresh-walk-v3/ue --cache '../../ddc'
```

編集画面の Tools → 内装比較 →「内覧を別ウィンドウで開始」からも起動できます。開始時に編集画面の比較条件を保存します。「内覧で保存した視点・条件を反映」で編集画面へ戻し、固定画像の比較に利用できます。複数の内覧ウィンドウから同時に保存しないでください。

| 操作 | 動作 |
|---|---|
| WASD / マウス | 歩行 / 視点方向 |
| Tab | マウスカーソルの解放・再取得 |
| 1 / 2 / 3 | natural / warm / reference の仕上げ |
| 4 / 5 | 手動太陽高度30° / 60°（実敷地・照度未校正） |
| F5 / F9 | 視点と条件の保存 / 復帰 |
| ウィンドウを閉じる | 内覧終了。必要な状態は先にF5で保存 |

移動速度1.2m/s、身体カプセル半径25cm・高さ176cm、目線は名目160cmです。Unrealの接地余裕による高さの微小差があります。家具や壁の当たり判定と、部屋ポリゴンから26cmの境界余裕を使います。ラグ・掛け布等の装飾は歩行を妨げる衝突体にしません。窓・ドアは閉じた形状のままです。衝突判定は通行可能性の参考であり、法令上の寸法判定ではありません。

## 保存と再生成の契約

- 生成データ：`SourcePackage`、`study-bindings.json`、`walkthrough.json`。
- 編集画面の保存：`study-state.json`。
- 施主の内覧保存：`Saved/walkthrough-state.json`。既存の比較状態スキーマ1.0.0を共用します。
- 編集画面と内覧の保存日時を比較して新しい方を使用します。再生成でも同じ選択を行い、入力をスナップショット化します。部屋IDや条件が不正なら再生成を停止します。
- 保存した位置が新しい家具・壁と重なる場合は、同じ部屋内の空いた候補を15cm間隔で探索し、元の位置に近い候補へ移します。候補がなければ内覧移動を開始しません。設置高さは対象階の床から再設定します。
- 窓や家具などの正本は今回変更していません。Three.js側で編集した場合は正本JSONへ反映してから更新します。

```powershell
python scripts/refresh-visual-study.py --previous build/ue-walk-v1 --output build/refresh-walk-next --cache '../../ddc'
```

前回プロジェクトに `walkthrough.json` がある場合、更新処理はBlender・Unreal生成後に内覧モジュールのビルド・衝突設定を追加します。C++/ヘッダー/Build.csもソース変更検出の対象です。

新規に生成した通常のUEプロジェクトへ追加する場合：

```powershell
python scripts/enable-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/ue-study --cache '../../ddc'
```

C++のビルドには対応するVisual Studio C++ツールチェーンとWindows SDKが必要です。この環境では日本語・長いパスがMSVC/UBAの応答ファイル処理を妨げたため、一時ディレクトリでC++をビルドし、バイナリを生成プロジェクトへ戻します。元のモデルやEngineの設定は変更しません。一時ビルドは診断用に残ります。

## 検証状況（2026-09-08）

44件のPythonテストと既存Three.js家具チェックが成功。`build/refresh-walk-v3/` で正本からの一括再生成・視点と条件の引継ぎ・内覧モジュール再構築が完了し、再生成後の描画なし実行も成功しました。C++のコンパイル、611メッシュの衝突設定、Unrealの描画なし実行での開始位置確保・カプセルの壁衝突・仕上げと太陽変更・保存復帰を確認しました。

```powershell
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/refresh-walk-v3/ue --cache '../../ddc' --smoke --logic-only
```

`--logic-only` を外すと描画付きの検証です。自動テストの状態と画像は `Saved/walkthrough-smoke*` に分離しており、施主の保存視点を上書きしません。`walkthrough-verification.json` の `runtimeVerified` と `renderVerified` を区別してください。スイープ衝突と状態操作の自動確認であり、手動のマウス操作感・歩きやすさは確認待ちです。

**描画付き内覧は未検証です。** 現環境でUnrealのGPU初期化が約60秒後に失敗しています。今回のモジュールを含まない `ue-textiles-v4` の既存固定カメラ描画でも再現しました。Direct3D 11への切り替えでも失敗。一方、Windows単体のDXGI生成・D3D12デバイス生成は成功しており、GPU全体の故障とは断定できません。Unrealの手動起動結果を確認して原因を絞る必要があります。`--rhi d3d11` は診断用であり、Lumenの画質確認には使用しません。

## 次の作業

1. Unrealの描画初期化問題を解決し、実際の内覧画面・入力・操作感を確認する。
2. 衝突時の移動・身体寸法・視野角の調整と、操作画面の日本語化。
3. 階段・部屋間移動・ドアを追加し、家全体へ展開する。
