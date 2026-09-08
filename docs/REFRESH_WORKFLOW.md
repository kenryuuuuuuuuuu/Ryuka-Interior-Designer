# 保存した検討条件を引き継いで一括更新する

現在の正本からBlenderとUnrealを再生成し、前回の仕上げ・視点・太陽条件・周辺設定を引き継ぎます。比較ギャラリーまで任意で実行できます。元のプロジェクトを上書きしません。

## 操作

コマンドはこのスクリプトが存在するチェックアウトのルートで実行します。現在の分離作業環境は元リポジトリ内の`build/worktrees/visual-twin`です。main側のルートで実行する場合は、先にそのディレクトリへ移動してください。

1. Three.jsで編集した家具・窓・電気設備はJSONを書き出し、作業中のブランチの正本へ反映します。localStorage内の変更は自動では取り込まれません。
2. 必要な正本検証と`node scripts/build-web-data.mjs`を実行します。Claude Codeの更新が別ブランチにある場合は、先に通常のGit手順で統合してください。この機能はブランチの切替・マージを行いません。
3. 前回のUnrealで「ツール → 内装比較 → 比較条件とレベルを保存」を実行します。未保存の画面上の変更は引き継げません。
4. 以下を実行します。

```powershell
python scripts/refresh-visual-study.py --previous build/ue-context-v3 --output build/refresh-v1 --cache '../../ddc' --gallery --note '実敷地とは無関係のサンプル地点・周辺建物を使った検証です。'
```

`--previous`は前回のUEプロジェクトのディレクトリ、`--output`は新しい出力先です。出力はこのworktreeの`build/`内にします。`--gallery`を省くとBlender画像とUEプロジェクトまでを生成し、一括撮影の時間を省けます。どちらでも検証します。

アプリの既定位置はBlender 5.2とUE 5.8です。別の場所の場合は`--blender`と`--engine`を指定します。キャッシュは書き込み可能な119文字以内のディレクトリです。例の`../../ddc`は現在の分離worktree用です。

## 更新と保持

| 対象 | 扱い |
|---|---|
| 建物・家具・開口・設備 | 現在の作業ブランチの正本から読み直します |
| 仕上げ案名、視点、太陽角度・日時、光源強度、露出 | 前回の`study-state.json`をコピーして保持します |
| 日時メニュー | 前回の`sun-cases.json`があれば保持します |
| 隣棟・塀 | 前回の`site-context.json`を保持し、保存条件のハッシュと照合します |
| 床材などの生成設定 | 現在のソースから読み直します。UEで任意に編集した材質のコピーはしません |

周辺ファイルの欠落、保存後の書き換え、古い保存条件で周辺ハッシュがない場合は事前に停止します。周辺条件を意図的に更新する際は、まず`build-unreal-study.py --context ...`で明示的に取り込みます。古い周辺対応プロジェクトは現行コントロールで条件を保存し直します。

ギャラリーには1〜12件の撮影可能な太陽ケースが必要です。日時ケースがない手動角度のプロジェクトでも、`--gallery`なしなら更新できます。

## 出力

- `index.html`：更新結果と成果物へのリンク
- `refresh.json`：工程、入力ハッシュ、変更ファイル、引き継ぎの検証結果
- `retained/`：コピーした前回の保存条件・周辺設定
- `blender/`：検証済みモデル・GLB・Blender画像
- `ue/`：新しいUnrealプロジェクト
- `comparison/`：任意の日時×仕上げ比較
- `01-source-check.log`など：各工程のログ

処理中に正本・生成コード・前回の保存条件が変わると停止します。並行開発は別チェックアウトで行い、終了後に統合してください。失敗時は`status:failed`を記録してログと中間成果物を残し、完成ページは作りません。原因を直して新しい出力先で再実行します。自動再開は未実装です。

`changedSourceFiles`は前回のBlenderパッケージの入力ハッシュとの比較です。以前は記録対象でなかったUEコードなども表示されます。建物の変更だけを示す一覧ではありません。

## 名前付きの検討案を保存・一覧・再適用する（W03-A、2026-09-08追加）

内覧・編集画面で決めた比較条件（仕上げ・視点・太陽条件）を、名前を付けて`build/scenarios/`配下に保存し、後から選んで別の再生成に適用できます。家の形状・家具配置は常に現在の正本から生成するため、案作成時とソースが異なれば見た目は変わり得ます。家具配置案そのものの複数管理、壁面単位の仕上げは対象外です。

```powershell
# 保存：projectは既存UEプロジェクト、outputは未作成ディレクトリ。Blender/UEは起動しません。
python scripts/save-study-scenario.py --project build/W02-refresh-v5/ue --name 'ゲストLDK・木部案A' --note '午前の検討' --output build/scenarios/guest-a-v1

# 一覧
python scripts/list-study-scenarios.py --root build/scenarios

# 再適用：--scenarioを指定すると、状態・日時・周辺は案パッケージだけから読み、
# previous側の最新保存や周辺は混ぜません。--previousは前回projectのimport済み確認・
# 内覧モジュール有無・変更ファイル比較に引き続き使います。
python scripts/refresh-visual-study.py --previous build/W02-refresh-v5/ue --scenario build/scenarios/guest-a-v1 --output build/W03-A-refresh-v1 --cache '../../ddc'
```

保存時、編集画面(`study-state.json`)と内覧の保存(`Saved/walkthrough-state.json`)のうち新しい方（テスト/smoke保存は対象外）を使います。選ばれた状態が無効な場合や、内覧の保存が復旧待ち（バックアップのみ残り本体がない状態）の場合は、案を保存せず中止します。案は追記方式で、既存出力先を上書きしません。

`refresh.json`には選択した案（id/name、案パッケージのSHA-256、原本情報）が`selectedScenario`として記録されます。既存の`sourceHashes`（今回の入力）・`changedSourceFiles`（previousモデルとの比較）の意味は変わりません。

実敷地・真北、キッチンと冷蔵庫の正面方向、採用品番、夜間照明、専用の歩行UIは別の作業です。日時・角度・周辺条件を含む成果物はローカルで保管します。
