# W07-G1 複数室の共通基盤

状態：READY。2026-09-09。仕様/レビュー：GPT、実装：Claude Code。

## 到達点と範囲

施主は「ゲスト3単位→W08-Gで試用→自宅4単位→W08-F」を承認済みです。今回はG1だけを一括実装します。対象はゲストLDK `room-1f-06` と洋室 `room-1f-05` の2室です。同じUEプロジェクトで室を切替表示し、各室の仕上げ・照明を別々に編集/比較/保存し、旧LDK案の読込と完全refreshまで通します。単にデータ構造だけを作って完了にはしません。

作業場所：`build/worktrees/visual-twin`、ブランチ：`feature/visual-twin-foundation`を継続。着手HEADの完全SHAをBASEとして固定します。AGENTS.md、BACKGROUND.md、DEVELOPMENT_WORKFLOW.md、ARCHITECTURE.md、W06-review-v3.md、W07-staged-design.mdを参照してください。W06は追加修正3ceda9bまで受入済みです。

G2の部屋間歩行・建具開閉・接続グラフ、G3のゲスト全8区画の仕上げ、自宅/階段/2階は今回実装しません。扉は現在の閉状態を維持します。モデル選択の瞬間移動は「部屋を切り替える」と表示し、通行確認済みと呼びません。

## 1. scopeと生成入力

新規 `data/visual/study-scopes.json` にschemaVersion、scopes（scopeId、label、roomIds、defaultRoomId）を定義します。今回の `guest-pilot` は上記2室を持ちます。旧LDKだけのscope `guest-ldk` も定義して旧CLI利用を維持します。roomIdsは空/重複/未知IDを拒否。部屋・寸法・家具をここへ複製しません。ゲスト全8室と自宅scopeの有効化は後続です。

build-visual-twin --interior、build-unreal-study、refreshへ対象scopeを伝え、scope未指定の既存呼出しは従来の単室範囲として動作させます。refreshは明示scopeがあれば優先、なければ前回プロジェクトのscope、旧プロジェクトならguest-ldkを使用します。案の読込だけでプロジェクトの生成範囲を勝手に変えません。

study.json、入力収集・ハッシュ、UEのimport-verificationへ実際のscopeId/roomIdsを記録します。比較対象の部屋と、採光の遮蔽に必要な外皮/隣室形状は別です。対象外の家を切り落として光漏れを発生させないでください。

既存guest-ldk-studyの共通レンダー設定/variantパレットは再利用できます。部屋の初期カメラ・初期variantはroomIdで参照する新しい設定表へ分離し、二重の正本にしません。旧単室設定は読込アダプターを通して利用可能にします。

## 2. 状態データ契約

新保存はstudy-state schemaVersion `2.0.0` とします。以下の意味を固定し、同じ意味の旧トップレベルvariant/roomId/surfaceOverridesを新版へ二重保存しません。

```json
{
  "schemaVersion": "2.0.0",
  "scopeId": "guest-pilot",
  "activeRoomId": "room-1f-06",
  "activeLevel": 1,
  "camera": null,
  "azimuthDeg": 155,
  "elevationDeg": 30,
  "sunLux": 50000,
  "exposureEV100": 7.5,
  "lighting": {"mode": "day"},
  "roomStates": {
    "room-1f-06": {"variant": "natural", "surfaceOverrides": {}, "fixtures": {}},
    "room-1f-05": {"variant": "natural", "surfaceOverrides": {}, "fixtures": {}}
  }
}
```

cameraの形式（locationCm/rotationDeg/lensMm）は既存を維持。位置はUE絶対座標です。solar/siteContextSHA256などの既存来歴フィールドは引き継ぎ、site.local.json/sun-cases.jsonと状態の整合性をW05通り検証します。modeは家全体の昼夜、器具の点灯/調光/色温度は所属室のfixturesです。夜へ切り替えてsolarを消しません。

activeRoomIdは現在の操作/視点対象であり、保存範囲ではありません。activeLevelはhouseから検証し、自己申告を信じません。roomStatesのキーが案の適用対象室です。新しい通常保存はプロジェクト対象室の全状態を保持します。scopeIdは由来と生成範囲確認に利用しますが、異なるscopeIdでも保存室が現在scopeの部分集合なら適用可能です。未知室/対象外室を無言で捨てず案内して拒否します。

室内surfaceOverrides/fixturesの型と数値範囲はW04/W06のままです。参照対象のroom/levelがそのキーの室と一致する必要があります。新規器具への既定off、欠落上書きの既定値、型不正の拒否は維持します。activeRoomIdはroomStates内に存在しなければなりません。

### 旧案移行と通常読込

1.0/1.1/1.2は既存検証後、roomIdの1室だけのroomStatesへ移行します。1.0/1.1のlightingはday/off。1.2のmodeとfixturesをそのまま移します。surface ID・器具ID・来歴・カメラを維持します。読込時に元ファイルを書き換えません。

移行・検証・部分適用を共通Pythonモジュールに集め、案保存/読込/CLI/Blender/UEエディタで使います。ネイティブ内覧の検証も同じ契約に合わせます。新形式を旧版と誤認したり、不正値を既定へ落としたりしないでください。

旧LDK案を2室モデルへ通常読込する場合：全体条件とその案の敷地/日時一覧を一組で採用し、LDKのroomStateを置換、洋室のroomStateは保持します。案のカメラがnullならそのactiveRoomの初期視点を使用。カメラの室を無言で別室へ読み替えません。先に両方の整合確認を済ませ、不正なら元シーン/保存/敷地ファイルを維持します。

完全refreshの場合も、前回状態を基準に案の対象室だけを重ねます。従来の「--scenario時は--previousの壊れた保存を読まない」は、案が対象scopeの全室をカバーする場合に維持します。部分案では不足室の基準状態が必要です。前回の有効状態が得られなければ、不足室を明示して停止し、黙って初期化しません。新規モデルを作る明示操作に限り、不足室の初期状態を使えます。

## 3. 複数室の形状・仕上げ・照明

LDKの既存面IDは維持し、洋室の壁/床/天井へ安定したIDを追加します。壁の両側はそれぞれの室が所有します。現行の先行処理が共有壁の裏側まで消費する箇所を修正し、同じ壁を二重に重ねて解決しません。開口や側面を塞がず、室ごとの面を正しく材質スロットへ対応させます。

variantは室ごとに有効になります。LDKをwarmにしても洋室の壁/床/天井や家具までwarmへ変わらないよう、グローバルなroleマテリアル一括置換を室所有へ変更します。対象外室/外皮は既存の基準材質を維持。面ごとのvariant親材質・模様・粗さの契約を維持します。床/天井はlevelとroomを照合し、同じ室の複数ピースを1面IDで扱える状態にします。

家具は対象roomIdsに属する既存配置を生成します。room参照と実座標に矛盾があればIDを案内し、座標だけで別室へ無断移動/二重生成しません。洋室は既存家具の寸法と簡易材質が分かれば十分です。新しい小物・画像相当の装飾は不要です。

lighting-bindingsへ器具のroomId/levelを持たせ、対象scope全体で1回解決します。室を切り替えても隣室光源を消しません。グループは全正本上の参照整合を確認した後、今回scope内の操作対象を選びます。scope内外をまたぐグループは部分点灯を黙って行わず、このscopeでは対象外と案内します。対象外室だけの正常なグループを理由に生成全体を止めないでください。未知器具とscope外の実在器具は区別します。状態上書きが空でも設定/グループの検証を省略しません。

家具・照明・面の生成物をroomIdで検索できるbindingsへ整理し、生成Actor名を永続IDにしません。外観上の器具と実光源を二重生成しません。

## 4. 操作・比較

UEメニューに「対象室」を追加し、選択中の室名を常設表示します。切替は指定室の安全な初期カメラへ移動し、他室の状態を保持します。G1では室ごとのカメラ履歴編集UIまでは不要です。現在カメラ1つを保存し、再読込で復帰できれば十分です。

室別variant、面選択、器具/グループ一覧はactiveRoomを基準に表示します。室への切替だけでmodeや太陽/露出/他室の材質・光束を変えません。

| 比較 | 変更する条件 | 固定する条件 |
|---|---|---|
| 仕上げA/B | 選択中の室のvariant/surfaceOverrides | 他室全部、照明、太陽/敷地、視点/露出 |
| 照明A/B | 選択中の室のfixtures（両案night必須） | 他室のfixtures/仕上げ、選択室の仕上げ、太陽来歴、視点/露出、周辺条件 |
| 日時A/B | 全体の日時/太陽（dayのみ） | 全室の仕上げ/fixtures、視点/露出、周辺条件 |

案に選択室が無ければ比較を拒否します。他室まで同じ案へ切り替えるUIはG1では不要です。W06の排他制御を維持し、比較中の室切替・案読込・通常編集は終了を促します。比較終了は開始前の全状態を戻します。案の通常読込は前述の部分適用契約です。

## 5. 内覧・既存連携の維持

G1は室間歩行を実装しませんが、既存LDKのネイティブ内覧は壊さず、新2.0状態の全室条件で描画しF5/F9できるようにします。F5でカメラだけを変更しても洋室の状態を捨てないでください。現段階の内覧開始がLDK限定であることをメニュー/案内に明示します。洋室のカメラからLDK内覧を開始する際は明示的にLDK開始点へ移し、通常案読込のカメラ検証を緩めて代用しません。

単室polygon/固定床による移動そのものはG2で置換する予定です。今回はC++の状態所有/材質・光源適用と保存互換を更新します。保存バックアップや境界補正の再設計はしません。

refresh/案一覧/比較画像/検証レポートも新形式の室情報を扱い、variantやroomIdがトップレベルにある前提を残さないでください。validate_study_transferは入力/出力を同じ移行関数で正規化し、全体条件と各室の意味上の値を確認します。schemaVersionの一致だけや新版という理由だけで保存成功としません。

重点確認先：scripts/refresh_inputs.py、build-visual-twin.py、build-unreal-study.py、refresh-visual-study.py、compare-unreal-daylight.py、enable-unreal-walkthrough.py、unreal/study_state.py、study_controls.py、import_study.py、内覧C++、BlenderのSurfaceBinder/家具/照明生成、入力収集リスト。変更先一覧は実装者が検索で補完します。

## 受入条件・検証の上限

| AC | 必須成果と代表確認 |
|---|---|
| 1 | guest-pilotで2室の家具/面/照明を同じプロジェクトへ生成し、メニューで切替表示できる |
| 2 | 共有壁のLDK側を変更して洋室側が不変。洋室のvariant変更でLDKが不変。各室の点灯も独立し切替で消えない |
| 3 | 旧1.2のLDK案を読込→洋室設定が保持→新版案を保存→完全refresh1回で両室/太陽来歴/カメラを保持 |
| 4 | 既存の仕上げ/照明/日時比較を新状態で接続。代表1比較で対象室だけが変わり終了で復元することを実UE確認。他比較は共通処理の単体確認でもよい |
| 5 | 新版のLDK内覧でF5/F9を1往復し洋室状態も維持。不正な室/面参照1件を重い生成/適用前に拒否し現在状態を保持 |
| 6 | 対象scope・未開放機能・旧案の部分適用を文書化。関連テストと既存正本validatorが成功 |

実UEの2室画像各1枚と代表操作結果、完全refresh1回を基本にします。旧1.0/1.1の移行は小さな単体テストで十分。全室/全器具/全比較の全組合せ、多重障害注入、性能チューニングは求めません。Three.jsの挙動を変更しない場合はブラウザの全操作再確認は不要です。実入力を改変するテストは隔離コピーを使います。

## 自律判断と提出

通常の関数分割・実装順・内部コミットはClaudeが決め、工程ごとの承認待ちは不要です。scope/状態移行・旧案の他室保持という契約を変更する必要が出た場合だけ、影響と代案を報告して保留してください。実装量が多いだけでG1を勝手に細分化しません。

ARCHITECTURE、UNREAL_WALKTHROUGH、STATUSを更新し、W07-G1-report.mdへBASE/HEAD、変更契約、AC結果、操作手順、残件を簡潔に記録します。prepare-review.pyで `build/reviews/W07-G1-v1` を作成。正常系の代表画像/結果・refresh結果をmanifestへ登録し、重複証拠は増やしません。モデルはSonnetで開始可能です。G2以降は未着手を維持します。
