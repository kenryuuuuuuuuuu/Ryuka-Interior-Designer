# W04 レビュー v2

判定：CHANGES_REQUESTED
BASE：`37fb6a9543f1ad40da33185e4239ab704bd11463`
HEAD：`939cc52f2b28017d0140a68ca7c75f0a26cd05ce`
レビュー束：`build/reviews/W04-v2`

## 再確認結果

前回R1〜R5の修正差分を確認しました。関連unittestはsurface_finish_overrides 24件、study_scenarios 10件、refresh_study 8件の計42件成功。証拠12件と差分のSHA-256はmanifestと一致しました。実機再起動・再生成はレビューでは行っていません。

- R3：色/roughnessのマージ、面ラベル/比較表示、保存前の不整合検出、名前付き案の保存関数共通化を受け入れます。提出検証は主に関数呼出しによるもので、実ダイアログ操作一式を確認したとは扱いませんが、それだけを理由に再提出は求めません。
- R5：床上面・天井下面だけへのslot割当、riser除外、level照合を受け入れます。別階の網羅的実機テストは要求しません。
- R1/R2/R4：以下の具体的な取りこぼしを修正してください。前回要件の範囲内です。

## R1 継続必須：プリセット切替で模様が変わらない

対象：unreal/import_study.py:82付近、unreal/study_controls.py:100付近、Walkthrough.cppのSurfacePlan、blender/build_interior.pyのSurfaceBinder。

marker_materialへdetailを渡すことで「生成時の模様」は付くようになりました。しかし親材質はstudy.variantだけを使って生成した1種類であり、editor/内覧の切替では現在の親を再利用してColor/Roughnessだけを変えます。resolve_finishが返す変更後のdetailは適用されません。

具体例：naturalで生成した床をreferenceへ切替しても、板模様から60cmタイルへ変わりません。referenceで生成した床をnaturalへ戻すとタイルのままです。面別variantを持つ案の読込、A/B、基準variant切替も同じ問題です。resolve_finishの実データ確認ではnaturalはplanks、referenceはpattern.kind=tileとなりますが、適用先グラフを切り替える経路がありません。ノードにCustomが「ある」ことだけではこの動作を確認できません。

修正：kind×variantごとにパラメータ付き親材質を事前生成し、適用時にeffective variantに対応した親を選ぶ方式等で対応してください。C++も同じ親選択を使います。任意色/roughnessはその親からのinstanceに適用します。全体変更・面上書き・解除のすべてが同じ解決規則に従うこと。

Blender側もまだpatternがある場合だけapply_patternを呼ぶため、natural/warmの既存wood/fabricディテール等を登録面に引き継いでいません。対象kindの基準材質と同じディテールを維持することを前回通り確認してください。不要なディテール追加ではなく既存の保持です。

代表検証：同じUEプロジェクトで床をnatural→reference→解除、天井をreferenceへ変更し、模様自体の切替を確認します。再生成なしのeditor/内覧で同じ規則になることと、選んだ案からの再生成後も一致することを代表1回で確認すれば十分です。

## R2 継続必須：周辺条件なしの案を、周辺条件ありへ黙って読み替える

対象：unreal/study_controls.py:54付近、start_compare。

apply_stateはcontextが存在するとき、expectedがNoneなら現在のハッシュを自動設定しています。したがって「遮蔽物なしで保存した正常な旧案」を「遮蔽物ありの現在プロジェクト」で読込/比較すると、不一致を案内せず採用します。今回の実機証拠は逆方向（必要なcontextがプロジェクトにない）だけです。

またstart_compareは両案のパッケージ自己整合性を調べますが、現在モデルのcontext/面参照との適合は表示時まで調べません。Aは適合、Bは現在contextに不適合の場合、Aを適用した後でB切替に失敗します。

修正：保存済み案の適用では「contextなし」も条件として比較し、現在プロジェクトと両方向に一致することを要求します。新規インポートでcontextを初期状態へ記録する処理は、案の読込とは明示的に分けてください。シーンを変更しない共通の適用前検証を使い、A/B両案について現在モデルとの適合を確認してから_compareとシーンを更新します。

代表検証：Aが適合しBが「contextなし/不一致」の例を1件。比較開始が拒否され、開始前状態と_compareが維持されれば十分です。広範な異常系追加は不要です。

## R4 継続必須：C++の型判定がPythonとまだ一致しない

対象：Walkthrough.cpp:249〜290付近。

surfaceOverrides本体と対象IDの検証は改善しました。しかし次はまだ受け入れられます。

- schemaVersion=1.1.0でsurfaceOverrides自体が欠落：HasFieldがfalseなので検証を通過します。Pythonは拒否します。
- bound面にcolorHex=123、roughness="bad"、variant=123等を指定：TryGetStringField/TryGetNumberFieldがfalseになると、if内部の不正判定を行わず既定値へ進みます。Pythonは拒否します。

修正：必須フィールドの有無、任意フィールドが存在する場合の取得成功、取得値の制約をそれぞれ判定してください。「取得に成功したときだけ値を調べる」では型不正を拒否できません。既存の保存復旧方式や新しい障害注入機構は変更不要です。

代表検証：コピーしたテスト保存にroughnessの文字列など1件を入れ、内覧側が適用せず理由を案内することを確認してください。その他はコード対照とビルドで十分です。全分岐・多重障害は求めません。

## 次の提出

同じBASEからW04-v3として3点をまとめて提出してください。R3/R5の再検証、階段/全館の追加対応、過去の障害テスト一式は不要です。上記の通常の材質切替、単純なcontext不一致、C++型不正の確認と、修正後の代表生成で十分です。W05はDRAFTのままにし、W04受入後に計画を見直します。
