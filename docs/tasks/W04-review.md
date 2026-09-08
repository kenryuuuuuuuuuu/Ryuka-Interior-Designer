# W04 レビュー v1

判定：CHANGES_REQUESTED
BASE：`37fb6a9543f1ad40da33185e4239ab704bd11463`
HEAD：`c234fddadfa592db7a4d804384dab5b2b1335602`
レビュー束：`build/reviews/W04-v1`

## 確認した成果

面の識別からBlender/UEへの対応、面別色指定、比較状態への保存、refreshへの状態入力は接続されています。関連unittest（surface_finish_overrides 15件、surface_bindings_geometry 11件、refresh_study 8件）は計34件成功。差分と証拠15件のSHA-256はmanifestと一致しました。提出DX12画像で窓周りの赤壁・青床も確認しました。W03-Cの残件2点は修正済みです。

ただし以下は通常の仕上げ検討と仕様の中心に関わるため修正が必要です。既存テストの成功だけでは覆えていません。今回のレビューではUE/Blenderを再起動していません。コードで確認した不具合と、実機未確認の操作を区別して記載します。

## R1 必須：登録しただけで既存の質感を失う

対象：unreal/material_builder.py:121、unreal/import_study.py:80付近、unreal/study_controls.py:80付近、Walkthrough.cppのSurfacePlan、blender/build_interior.py:153。

UEは上書きの有無にかかわらず全bound面をColor/Roughnessだけのmarker_materialへ置き換えます。referenceの床タイル・天井板目も再現されず、解除しても元の質感へ戻りません。「上書きした面だけが単色になる」という報告より影響が広く、登録面は上書きなしでも退行します。仕様は既存模様とスケールの再利用を明示しており、制限として受け入れられません。

既存floor/surface shader・ノイズをパラメータ化または種別/variant別の親材質として再利用し、面別操作では模様を保持して指定値だけ変えてください。Blenderでもnatural/warmの既存ディテールを保持し、apply_patternへ上書き後のcolorHexを渡してください（現状は元paletteを渡し、pattern時の色指定が打ち消されます）。

代表確認：referenceの床/天井について、上書きなし→色変更→解除で模様・寸法が維持されること。Blender/UEの画素一致は不要です。

## R2 必須：案読込・比較が既存の整合性確認を迂回する

対象：unreal/study_controls.py:54、325、332。

load_scenario/start_compareはstudy-state.jsonを直接読み、scenario.jsonのfilesハッシュや周辺遮蔽との対応を確認しません。apply_stateは現在のsite-context.jsonが存在すると、保存側ハッシュを比較せず現在値へ上書きします。異なる遮蔽条件の案でも読込・同条件比較ができたと扱われます。

W03-Aのscenario_inputs相当の共通検証をUI経路でも利用してください。現在プロジェクトのcontextとの不一致は再生成が必要と案内し、状態を変更しないこと。A/Bは両案を先に検証してから開始します。壊れた案を一覧から黙って消す必要はありません。

代表確認：正常な2案の比較と、ハッシュ不一致またはcontext不一致の1案が適用前に拒否され元の状態が保たれること。

## R3 必須：面編集・保存の通常操作を完成させる

対象：unreal/study_controls.py:158、272、296、422付近。

- apply_color_to_selectedは色だけの辞書で既存overrideを丸ごと置換します。referenceを選んでから色を変えるとvariantを失い、roughness空欄も「変更なし」と異なり以前の指定が消えます。対象の既存辞書へ入力されたプロパティだけをマージしてください。roughnessだけの変更も可能にしてください。関数本体を抽出した軽量確認で、空欄roughness時の出力がcolorHexだけになることを確認しました。
- 面一覧はlabelを落としてkindとIDだけを表示し、比較中の案名/条件・選択中の面もログ頼みです。日本語の面label、選択中の対象、比較中の案と固定条件を通常画面で確認できるようにしてください。簡単なメニュー/パネル表示で十分です。Actor選択では壁の裏側まで輪郭が付くため、変更対象が部屋側の主面であることも分かる表示にします。
- scene_stateは面別状態を_stateから信頼しており、ScopedEditorTransactionによるUndoでシーン材質が戻っても辞書は戻りません。実際の表示と保存内容の不一致を検出するか、管理状態もUndoへ追従させてください。未管理変更は理由付き保存拒否でも構いません。
- 実機確認スクリプトは色入力ダイアログとsave_scenarioを呼んでいません。後者はUE内のsys.executableで外部Python CLIを起動するため、通常Pythonの実行ファイルであると仮定しないでください。この実行可否はレビューで実機確認していません。生成時に明示した利用可能なPythonか共通関数呼出しを使う等で成立させ、メニューから名前付き保存が実際に成功することを確認してください。

代表確認：面選択→reference→色変更（roughness空欄）→名前付き保存→読込を実UIで1往復。Undo後の保存整合性は簡単な1例で十分です。操作全体の自動化は要求しません。

## R4 必須：保存状態の検証をPython/内覧/事前確認で揃える

対象：unreal/study_state.py:43、Walkthrough.cpp:244付近、scripts/build-visual-twin.py、scripts/refresh-visual-study.py。

Pythonの `state.get('surfaceOverrides') or {}` は1.1.0のnull/[]/falseを空辞書として受け入れます。実データのコピーで3例とも確認しました。旧1.0.0の欠落だけを空へ正規化し、新形式の欠落・型不正を拒否してください。

C++は存在するbound面だけを走査するため、保存にある未知ID/no-surfaceのキーを黙って無視します。override内の未知フィールド・不正色・roughness範囲もPythonと同等に検証していません。適用前に保存側の辞書全体を検証し、無効時は既存の理由付き復帰処理へ渡してください。別部屋のsurface IDも適用先roomIdと照合します。

また未知override IDの確認はbuild_interior.main内であり、報告の「Blender起動前」は事実と異なります。登録ID・roomの存在を純Pythonで確認できる部分はBlender前へ移してください。no-surfaceの幾何判定は仕様通りBlender後・UE前で構いません。

代表確認：新形式の型不正1件、内覧保存の未知ID1件、未知IDの事前停止を軽いモックで確認。多重障害・復旧再設計は不要です。

## R5 必須：床・天井の対象を主面へ限定する

対象：blender/build_interior.py:286〜355。

壁はcapへ限定していますが、床はblock全体、天井はprism全体へ専用材質を付けており、下面/上面や厚み端面まで同時に変わります。さらにceiling.riserも天井IDへ登録され、仕様で除外した段差立ち上がりまで対象です。床上面・天井下面だけにslotを割り当て、他面・riserは既存材質を維持してください。対応時にroomと生成部材のlevelも照合してください（現状は平面位置だけ）。

代表確認：生成meshのpolygon/material対応で床上面・天井下面だけが専用slotであること。1つの簡単な確認で十分です。

## 非阻害の将来注意

共有壁を両室とも登録した場合、壁ループが最初の登録区間をremainingから除くため、同区間の反対側登録は処理されません。現在はゲストのみなので、この一般化だけを理由にW04の工程を増やしません。他室登録へ広げる際は区間を一度分割して両capの所有を付与する必要があります。純helperのcap判定テストは生成ループの両面対応を証明しません。

## 修正後の提出・検証範囲

上記を同じW04内でまとめて修正し、元BASEから `build/reviews/W04-v2` と更新報告を提出してください。新しいタスクへの分割・途中承認は不要です。通常UIの1往復、質感と主面分離の代表確認、必要な単純異常系、最終変更後の完全refresh 1回を組み合わせれば十分です。既存W02の全テストや大量の証拠の追加は要求しません。

報告は、直接関数を呼んだ検証とUI操作、同一プロセスの保存復帰と別起動の復元を区別してください。現証拠のA/B固定条件チェックは太陽・露出だけで、cameraを比較していません。再起動復元の記述もsmoke内の保存復帰だけで裏付けたとしないこと。修正後の代表操作で画角と起動後の状態を一緒に確認すれば十分です。
