# W03-B 家具・部屋の変更一覧と参照切れの事前案内

状態：READY。実装担当：Claude Code / Sonnet。仕様・レビュー：GPT。

## 今回できるようにすること

前回モデルから家具や部屋をどう変えたかを、ファイル名だけでなく「円卓の位置変更」「テレビ追加」などの単位で確認できるようにします。削除した家具に装飾設定が残っている等の参照切れを、Blender/UEの重い処理を始める前に、対象IDと設定ファイルを添えて案内します。

W03-Aの名前付き案を維持し、形状/配置は常に現在の正本から生成します。今回の変更は説明と事前検証です。家具配置案の複数管理、自動マージ、IDの自動再発行、消えた家具の自動復活、壁面ID、全館内覧、C++改修は含めません。

## 作業場所と読むもの

`build/worktrees/visual-twin`、`feature/visual-twin-foundation`。W03-A受入コードは157eed4aef14f64fa7767d6b8c25f7985867e2e7。本仕様を含む着手時HEADをBASEとして記録してください。未関連の変更は混ぜません。

AGENTS.md、初回BACKGROUND.md、DEVELOPMENT_WORKFLOW.mdの完成優先方針を守ります。参照は `scripts/refresh-visual-study.py`、`scripts/refresh_inputs.py`、`scripts/build-visual-twin.py`、`docs/REFRESH_WORKFLOW.md`、`tests/test_refresh_study.py`。

前回モデルの原本コピーは `<previous>/SourcePackage/inputs/data/`、ハッシュは `<previous>/SourcePackage/manifest.json` にあります。新たなスナップショット形式やDBは作りません。

## データ比較の契約

### 比較元と比較先

- 比較元：--previousのSourcePackageに実際に保存された入力JSON。
- 比較先：実行時のこのworktreeのdata/以下の正本。ブラウザのlocalStorageは含めません。
- --scenario指定時も比較元はpreviousです。案の作成時からの差分と呼ばないこと。画面には「前回モデルからの変更」と表示します。案のoriginはW03-Aの記録のまま維持します。
- 対象はhouse.jsonのrooms（キーid）、furniture.jsonのitems（キーid）、furniture-catalog.jsonのtypes（キーtype）。型カタログの変更は、配置JSONが不変でも家具に影響するので別途表示します。
- 配列の並び替えやJSONの整形だけでは変更扱いにしません。room.polygonの頂点順は形状契約の一部として配列比較のままで構いません。幾何学的な同値判定は実装しません。

### 追加・削除・変更

IDが新しい側だけならadded、古い側だけならremoved、両方にあって値が異なればmodified。名前や位置の類似度で同一物と推測しません。ID変更は削除＋追加です。id/typeの重複を見つけたら、dict化で上書きせず理由付きで拒否します。

modifiedには異なったトップレベルのフィールド名とbefore/after値を記録します。欠落とnullは区別し、例えば `{field:"elevation", beforePresent:false, afterPresent:true, after:1.0}` のように表現します。追加/削除には該当側の元レコードを保持します。note/status等の根拠・確度も落としません。

表示分類は次の範囲で十分です。

- 家具：x/z/rotation/elevation/room/level → 配置、typeや寸法関連 → 型・寸法、label/note/status → 名称・注記。複数なら複数表示可。未分類フィールドはその他。
- 部屋：polygon/level/ceiling → 形状・階・天井、label/note/status → 名称・注記、その他はその他。
- カタログ：型変更と、その型を現在参照する家具IDの一覧。各家具の外寸を独自に再計算する必要はありません。「型変更の影響候補」とし、個別上書きまで解析して確定影響とは断定しません。

## 現在の参照切れの確認

現データの下記の参照だけを明示的に検証します。汎用の参照グラフは不要です。

| 参照元 | 必要な参照先 |
|---|---|
| furniture.items[].room | house.rooms[].id |
| furniture.items[].type | furniture-catalog.types[].type |
| visual/guest-ldk-study.jsonのroomId | house.rooms[].id |
| 選択された案/保存状態のroomId | house.rooms[].id（既存state validatorも併用） |
| visual/asset-bindings.jsonのbindings[].furnitureId | furniture.items[].id |
| visual/guest-decor.jsonのroomId | house.rooms[].id |
| visual/guest-decor.jsonのitems[].furnitureId（存在する項目） | furniture.items[].id |
| visual/guest-decor.jsonのitems[].openingId（存在する項目） | openings.items[].id |

本タスクでは開口を変更一覧の対象にはしませんが、装飾の参照確認のためopenings.jsonを読みます。部屋所属や向き等の描画条件の詳細は既存のvalidator/Blender側へ任せ、ここでは参照先の存在を確認します。

未使用の家具型が残ることはエラーにしません。家具を削除して紐づくasset-binding/decorも削除した場合は通常の変更です。古いモデルにだけ残る参照を現在のエラーとしません。欠けた参照を自動で削除/付け替えしません。

## 出力とCLI

共通の純Pythonモジュール（例：scripts/source_changes.py）と軽いCLI `scripts/check-study-changes.py` を追加します。

```powershell
python scripts/check-study-changes.py --previous build/W03-A-refresh-v1/ue --output build/W03-B-check-v1
```

outputはこのworktreeのbuild内の新しいディレクトリ限定。Blender/UEを起動せず、`source-changes.json` と `index.html` を出力します。任意の--current-dataは試験で有用なら追加可能ですが、refreshの本番入力は常にROOT/dataです。

source-changes.jsonはschemaVersion=1.0.0として、少なくとも以下を記録します。

- baselineStatus：available / unavailable（一部だけ欠落なら全体unavailableで十分）。理由。
- comparisonBasis：previous-package-to-current-source。
- comparedFiles：対象とその前後ハッシュ（既存manifestのCRLF→LF正規化を尊重）。
- rooms/furniture/catalog：added/removed/modifiedの各配列。
- issues：code、sourceFile、sourceId、field、targetId、message。重複ID・現在の欠けた参照はerror。
- warnings：比較不能など。形状全体の差分ではなく対象限定であることを明記。

比較元の必須スナップショットがない、または対応ハッシュを検証できない旧形式の場合は「詳細比較できません」と表示し、現在の全件を追加扱いにしません。詳細比較ができなくても現在の参照確認は実施します。比較元の破損/欠落を現在の正本へコピーしません。

HTMLは追加/削除/変更の件数、対象ラベルとID、変更フィールドの前後、参照切れの修正案内を簡潔に表示します。例：「decor-rugが参照する家具fur-038がありません。guest-decor.jsonの設定を確認してください」。長いnote/ポリゴンは折りたたみdetails等で十分です。文字列はHTMLエスケープします。屋根・階段・設備・開口全体の変更検出が実装済みとは書きません。

終了コード：現在の参照切れ/重複など修正必須のissuesがあれば1、なければ0。比較元が古く比較不能なだけなら警告で0です。必須の現JSONが読めない/壊れている場合は非0とし、利用者にファイルを示します。広い例外を握りつぶして正常扱いにはしません。

## refreshへの接続

既存の入力ハッシュを取得した後、Blender起動前に共通処理を実行します。新出力の `source-changes.json` と `changes.html` を保存し、refresh.jsonに結果の要約と相対パスを追加します。既存changedSourceFilesの意味/形式は変えません。

現在の参照切れがあれば、refreshの既存failed扱いで停止し、ターミナルにchanges.htmlの場所を案内します。既存の未完成出力を完成ページにしません。元のUEプロジェクト・案・正本には書き込みません。--scenarioで選んだ部屋が消えた場合も、重い処理前の明確なエラーで十分です（既存入力検証より後へエラーを無理に統一しなくて構いません）。

成功時のindex.htmlに「前回モデルからの変更」の要約と詳細ページへのリンクを追加します。比較不能なら警告を短く表示します。Blender/UE処理や状態引継ぎを二重実装しません。実行中の正本変更は既存unchangedチェックを活用します。

## 検証と完了条件（軽量）

1. コピーした入力で家具1件の移動・追加・削除、カタログ寸法変更、部屋名変更をまとめて比較し、IDごとの差分が正しいこと。配列順だけの変更が出ないこと。
2. 家具を削除しdecor参照を残したケースで、対象IDとファイルを案内して止まること。参照も取り除けば通ること。比較元欠落は警告で、全件追加にならないこと。
3. 現在の実データから軽量CLIを1回実行し、HTMLを確認。既存refresh関連テストを実行し、参照エラー時にはBlender/UEを呼ばないことをモック等で確認します。
4. 通常refreshへの接続は代表1件で確認します。今回は幾何/描画を変更しないため、既存の生成成功を活かし、工程呼出しと出力リンクをPython統合テストで確認できれば、UEフル再生成の再実行を必須にしません。

コミット前のhouse検証、build-web-data --checkは維持します。多重障害・全分岐証明・C++障害注入の再実行は不要です。テストは上記の代表例に絞ります。

## 提出

docs/tasks/W03-B-report.mdに成果・代表コマンド・検証結果・残件を短くまとめ、着手BASEからbuild/reviews/W03-B-v1を作成してください。証拠は代表的なsource-changes.jsonとHTML/テスト結果程度で十分です。W03-Cの壁面ID設計やW04へは進みません。
