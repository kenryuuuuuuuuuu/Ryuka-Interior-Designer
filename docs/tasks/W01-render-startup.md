# W01 Unreal描画初期化の復旧

状態：READY。推奨モデル：**Opus 5**。UEとWindowsの境界で原因が未確定のためです。実装担当はClaude Code、契約変更と最終レビューはGPTです。

## 開始点

`build/worktrees/visual-twin` ワークツリーの `feature/visual-twin-foundation` が対象です（以後のパスはこのワークツリー相対）。親リポジトリのmainではありません。コード基準 `697f15c37a862932bb59d11c2915352b17365049` と本仕様を含むHEADから開始し、完全なBASE SHAを記録してください。他の変更が入っていれば差分を確認して対象を混ぜません。

## 目的・範囲

描画なしでは通るゲストLDK内覧を、DX12/SM6の実画面で起動できる状態にします。今回は描画初期化の切り分けと、根拠が得られた必要最小限の修正だけです。家具・布・植物、全館移動、状態スキーマ変更、操作UI拡張は対象外です。

## 読むもの

AGENTS.md、BACKGROUND.md（初回）、DEVELOPMENT_WORKFLOW.md、UNREAL_WALKTHROUGH.md。

入口：`scripts/launch-unreal-walkthrough.py`、`scripts/enable-unreal-walkthrough.py`、`unreal/configure_walkthrough.py`、`unreal/walkthrough/Source/RyukaInterior/Walkthrough.cpp`、`scripts/refresh-visual-study.py`。全コードを最初から読み直す必要はありません。

## 既知の証拠と未確定事項

- `build/refresh-walk-v3/` は一括再生成・状態引継ぎ・C++再構築とNullRHI検証に成功しています。`ue/walkthrough-verification.json` はruntimeVerified=true、renderVerified=falseです。これは入力操作の手動確認ではありません。
- C++を含まない旧 `build/ue-textiles-v4/RyukaInterior.uproject` でも約60秒でGPU初期化が失敗しました。旧版では以前に固定視点レンダーが成功しています。
- DX11、DX12、Editor/Editor-Cmd、SM6指定、アダプタ選択方式変更でも解決していません。Windows単体のDXGI/D3D12デバイス生成は成功しており、ドライバ故障・C++原因とは断定できません。
- 施主による旧プロジェクトの手動起動結果は未回答です。これを既知の成功/失敗にしないでください。必要なら実施を依頼し、それに依存しない調査を進めます。
- `build/` の成果物はローカルのみです。存在を最初に確認し、なければ勝手に存在を仮定せず必要な再生成を報告します。

## 実装方針

1. 既存ログと最終成功時/失敗時の起動条件を比較し、失敗する最終段階・終了コード・RHI・GPU・Engine版・実行方法を短い表にします。ログ内の住所/ユーザー名等を公開報告へ転記しません。
2. 最大4ケースの初期診断表を作ります。旧プロジェクトの手動Editor、旧プロジェクトの既知ランチャー、最新プロジェクトの描画、必要なら隔離した最小UEプロジェクトです。一度に変える条件は一つ。既存の同じ失敗を再実行する場合は、今回得る新しい証拠を先に記録してください。
3. 全て失敗なら環境/Engine側、旧版のみ成功ならプロジェクト差分、手動のみ成功ならランチャー条件へ焦点を移します。これは仮説分岐であり原因の断定ではありません。エンジンソース調査はログで段階が絞れた場合に行います。
4. 修正は原則ランチャー/設定生成器と関連テスト・文書に限定します。生成uprojectだけの手修正で終わらず、再生成で同じ修正が適用されるようにします。実装方法は任せますが、変更理由と修正前後の証拠を残してください。
5. 既存の状態・生成物を保全し、新しいbuild出力で確認します。描画成功後に下記smokeと実画面の目視確認までを行います。詳細な歩行体験の合格はW02です。

禁止する近道：DX11/NullRHIへの恒久変更を画質目標の達成扱いにする、描画フラグを強制的にtrueにする、古いPNGを新しい描画結果として使う、ユーザーのSaved/walkthrough-state.jsonをsmokeで書き換えること。

Engine/ドライバの入替、OS全体の設定変更、広範囲のキャッシュ消去が必要なら、診断結果と影響を先に施主へ提示してください。自動承認されない環境操作は黙って代替条件で合格扱いにしません。

## 受入条件

| ID | シナリオ・期待結果 | 証拠 |
|---|---|---|
| AC1 | 新旧/起動方法の比較で、観測事実と原因仮説が区別されている | 診断表、ログの相対パス、終了コード、各試行の仮説 |
| AC2 | 最新生成プロジェクトがDX12/SM6で描画される | 新しく生成したsmoke PNGを目視確認、対応ログ、renderVerified=true、実行コード版 |
| AC3 | 実際のウィンドウにLDKが表示される | 起動手順と確認結果、画面証拠。取得不能なら施主確認待ち。自動テストで代用しない |
| AC4 | 既存のロジック検証・保存保護・Web正本に回帰がない | 下記チェック、施主保存ファイルの実行前後ハッシュ（存在しない場合も記録） |
| AC5 | 修正が生成器に必要な場合、再生成後も描画できる | 新しい出力先でrefreshした記録とAC2の再確認。ソース変更不要なら理由付きN/A |

既存コマンド（専用ワークツリーで実行、成果物を上書きしない）：

```powershell
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/refresh-walk-v3/ue --cache '../../ddc' --smoke --logic-only
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/refresh-walk-v3/ue --cache '../../ddc' --smoke
python scripts/launch-unreal-walkthrough.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/refresh-walk-v3/ue --cache '../../ddc'
python -m unittest discover -s tests -p 'test_*.py'
python tests/validate_house.py
python tests/validate_furniture.py
python tests/validate_openings.py
python tests/validate_electrical.py
node scripts/build-web-data.mjs --check
node tests/test_furniture_web.mjs
```

smokeと手動起動は直列実行です。smokeは専用証拠を更新するので、既存証拠は診断開始前に別のbuildディレクトリへ保存してください。変更したコードを生成プロジェクトへ反映してから検証し、その更新コマンドも報告します。

## 停止と提出

異なる仮説を2回検証して新しい証拠が出なければ、盲目的なフラグ変更を止め、BLOCKED報告にします。描画が環境待ちの場合、AC2/3/5を未完了のまま、必要な情報・次に試す1手を明記します。これはW01合格ではありません。

`docs/tasks/W01-report.md` を報告テンプレートから作成し、コミット後に `build/reviews/W01-v1` へ差分束を作成します。ログ・PNG・検証JSONをそれぞれ `--artifact` に指定してください。次の機能へは自動着手しません。
