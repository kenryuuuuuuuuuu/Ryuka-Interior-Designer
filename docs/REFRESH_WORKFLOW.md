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
| 仕上げ案名、視点、太陽角度・日時、光源強度、露出、面ごとの仕上げ上書き（`surfaceOverrides`） | 前回の`study-state.json`をコピーして保持します |
| 日時メニュー | 前回の`sun-cases.json`があれば保持します |
| 隣棟・塀 | 前回の`site-context.json`を保持し、保存条件のハッシュと照合します |
| 床材などの生成設定 | 現在のソースから読み直します。UEで任意に編集した材質のコピーはしません |

周辺ファイルの欠落、保存後の書き換え、古い保存条件で周辺ハッシュがない場合は事前に停止します。周辺条件を意図的に更新する際は、まず`build-unreal-study.py --context ...`で明示的に取り込みます。古い周辺対応プロジェクトは現行コントロールで条件を保存し直します。

ギャラリーには1〜12件の撮影可能な太陽ケースが必要です。日時ケースがない手動角度のプロジェクトでも、`--gallery`なしなら更新できます。

## 出力

- `index.html`：更新結果と成果物へのリンク
- `refresh.json`：工程、入力ハッシュ、変更ファイル、引き継ぎの検証結果
- `source-changes.json`・`changes.html`：前回モデルからの家具・部屋の変更一覧と参照切れの確認結果
- `retained/`：コピーした前回の保存条件・周辺設定
- `blender/`：検証済みモデル・GLB・Blender画像
- `ue/`：新しいUnrealプロジェクト
- `comparison/`：任意の日時×仕上げ比較
- `01-source-check.log`など：各工程のログ

処理中に正本・生成コード・前回の保存条件が変わると停止します。並行開発は別チェックアウトで行い、終了後に統合してください。失敗時は`status:failed`を記録してログと中間成果物を残し、完成ページは作りません。原因を直して新しい出力先で再実行します。自動再開は未実装です。

`changedSourceFiles`は前回のBlenderパッケージの入力ハッシュとの比較です。以前は記録対象でなかったUEコードなども表示されます。建物の変更だけを示す一覧ではありません。

## 名前付きの検討案を保存・一覧・再適用する（W03-A、2026-09-08追加）

内覧・編集画面で決めた比較条件（仕上げ・視点・太陽条件・面ごとの仕上げ上書き）を、名前を付けて`build/scenarios/`配下に保存し、後から選んで別の再生成に適用できます。家の形状・家具配置は常に現在の正本から生成するため、案作成時とソースが異なれば見た目は変わり得ます。家具配置案そのものの複数管理は対象外です。

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

## 前回モデルからの変更・参照切れの事前確認（W03-B、2026-09-08追加）

`refresh-visual-study.py`はBlender起動前に、`--previous`のSourcePackageに保存された入力（rooms/家具/家具カタログ）と現在の正本を比較し、あわせて現在の正本内の参照（家具→部屋・型、装飾設定→家具・開口など）を確認します。現在の参照切れ（削除した家具に装飾設定が残っている等）があれば、重い生成の前に停止し`changes.html`の場所を案内します。Blender/UEには一切書き込みません。

```powershell
# Blender/UEを起動せず、変更一覧と参照確認だけを単独で行う場合
python scripts/check-study-changes.py --previous build/W02-refresh-v5/ue --output build/W03-B-check-v1
```

`source-changes.json`（schemaVersion 1.0.0）は`baselineStatus`（`available`/`unavailable`）・比較したファイルのハッシュ・rooms/furniture/catalogそれぞれのadded/removed/modified・`issues`（参照切れ・重複ID、修正必須）・`warnings`（比較範囲の限定を含む）を記録します。前回パッケージの原本コピーが無い/ハッシュが一致しない場合は`unavailable`となり、「詳細比較できません」と案内します。この場合も現在の全件を追加扱いにはせず、参照確認自体は実施します。終了コードは、現在の参照切れ・重複があれば1、なければ0です（比較元が古いだけなら警告のみで0）。

通常の`refresh-visual-study.py`実行では、この確認結果が`refresh.json`の`sourceChanges`、完了後の`index.html`の「前回モデルからの変更」欄、`changes.html`（詳細）に反映されます。対象はrooms/furniture/furniture-catalogの追加・削除・変更（IDごと、配列の並び替えは変更扱いにしません）と、限定した参照先の有無だけです。屋根・階段・設備・開口全体の変更検出は含みません。

## 面の永続ID・登録の確認（W03-C、2026-09-08追加）

`refresh-visual-study.py`は上記の参照確認に続けて、`data/visual/surface-registry.json`（部屋境界の壁・床・天井の識別設定）を現在の`house.json`と照合します。未解決（壁の移動・分割で登録した辺が見つからない、登録した部屋が無くなった等）があれば、同様にBlender起動前で停止し`surface-resolution.json`を案内します。単独確認・詳細はARCHITECTURE.md「面の永続ID」を参照してください。

```powershell
python scripts/check-study-surfaces.py --output build/W03-C-check-v1
```

## 面ごとの仕上げ変更（W04、2026-09-08追加）

前回の保存状態（`--previous`の`Saved/walkthrough-state.json`または編集画面の`study-state.json`）・選んだ名前付き案（`--scenario`）に含まれる`surfaceOverrides`（面ごとの色・粗さ・バリアント上書き）は、上記の面の永続ID確認の直後、Blender起動時に`--state`引数（内部的に`build-visual-twin.py --interior --state <一時ファイル>`として渡す）で自動的に引き継がれます。ユーザーが個別に指定する操作はありません。

対象IDが未解決（登録が見つからない）・面に紐付いていない（`no-surface`）場合は、前者はBlender起動前に停止（面の永続ID確認と同様）、後者は上書きだけ無視して残りの生成・保存条件は継続します（案自体は壊しません）。UEエディタでの面ごとの色・プリセット編集、案の保存・A/B比較の操作はARCHITECTURE.md「面ごとの仕上げ変更」を参照してください。
