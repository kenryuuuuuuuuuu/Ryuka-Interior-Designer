# W05 レビュー v1

判定：CHANGES_REQUESTED
BASE：`b478a9f4bf85cd309ea1e446a9d9cbae6b91cb39`
HEAD：`a27b62a7b3d824b11585bf52dd5756da188fa7ab`
レビュー束：`build/reviews/W05-v1`

## 確認結果

日時UI、固定条件の日時比較、比較画像出力、Blenderへの太陽角度反映、siteの案/refreshへのコピーは実装されています。仮の合成敷地による機能確認であり実敷地未確認という報告は適切です。実資料不足そのものを不合格理由にはしません。

関連unittestを再実行し、solar_position 8件、refresh_study 9件、study_scenarios 11件、計28件成功しました。証拠16件と差分のSHA-256はmanifestと一致。提出比較画像の代表1枚も確認しました。UE/Blenderの追加実行はレビューでは行っていません。

以下2点は通常の敷地変更・案読込で起こるため修正が必要です。細部の品質調整や過去の障害テストは追加要求しません。

## R1 必須：現在の敷地と実際の太陽状態の一致を確認する

対象：unreal/solar_position.pyのcases_match_site、study_controls.pyのset_sun_case/start_daylight_compare/load_site/recompute_sun_cases、scripts/refresh_inputs.py、build-unreal-study.py、比較撮影経路。

現状の照合は主に「日時一覧に付いたsiteSHA256」と入力の一致だけです。以下が抜けています。

- 敷地Bを読み込んでも、set_sun_case/start_daylight_compareは古い敷地Aのケースを適用できます。不一致のステータス表示だけで、適用は止まりません。撮影CLIも現在siteとの照合がありません。
- 再計算で一覧がBになっても、現在state.solarがAのまま保存/refreshを通ります。コピーした入力で「state.solar=A、site=B、sun-cases=B」のretained_inputsが成功することを確認しました。
- cases_match_siteはハッシュだけなので、同じハッシュを持った角度不整合を検出しません。正しいケースの高度を10度変更してもTrueでした。仕様は日時/入力から計算した角度との対応も要求しています。

修正：siteが存在する場合の共通照合を作り、選択ケースとstate.solarの双方について、siteSHA256・日時から再計算した角度を許容差付きで確認します。既存make_caseを再利用し、第二の計算アルゴリズムは不要です。UI適用、日時比較、保存/案検証、直接build、撮影で同じ契約を使います。site原本のない旧案は従来の角度検証で利用可とし、同一siteの日時比較であることはケースのsiteSHA256でも確認してください。

敷地変更/再計算後、現在状態が古いときは再適用を案内するか、現在日時を新siteから再計算して明示的に適用します。古いsolar来歴のまま保存成功にしません。手動角度状態を日時計算済みに変える必要はありません。

代表検証：site A→Bへ変更し、旧ケースの適用/比較が止まること。Bで再計算した後もAのstateを保存できないこと、Bの日時を適用すれば保存/refresh可能なことを1つの流れで確認。角度不一致は純Pythonの1例で十分です。

## R2 必須：名前付き案の読込でsiteと日時一覧も一緒に採用する

対象：unreal/study_controls.pyの_load_scenario_state/load_scenarioと、対応する入力選択処理。

scenario_inputsはsite/sunCasesのパスを返しますが、_load_scenario_stateはstateだけを取り出します。load_scenarioもstateだけを適用するため、別siteで保存した案を読んでも現在プロジェクトのsite.local.json/sun-cases.jsonが残ります。その後に日時変更や名前付き保存をすると、案とは別の敷地/一覧が混ざります。CLIの--scenarioが同梱ファイルを使うことだけでは、通常UIの読込は完成していません。

修正：通常の案読込では検証済みのstate/site/sun-casesを一つの入力組として採用してください。contextは実幾何なので、従来通り不一致なら再生成が必要です。旧案にsiteや一覧がない場合も現在の別siteを黙って補完せず、「原本なし」の扱いへ戻します。検証に失敗した場合は現在の正常な入力/状態を維持してください。仕上げだけのA/Bでは敷地を切り替える必要はなく、モード間の意味を維持します。

代表検証：異なるsiteと日時一覧を持つ2案を同じcontext条件で用意し、Bの読込後はUIの敷地・ケース・solarがBで揃い、保存し直した案にもBが入ること。実敷地を使う必要はありません。

## 再提出

同じBASEからbuild/reviews/W05-v2と更新報告を提出してください。2点をまとめて修正し、上記の代表操作・関連テスト・修正後の保存案からの完全refresh 1回で十分です。多数の季節画像やW04の再検証一式は不要です。

報告のAC3で「内覧F5/F9の確認」の根拠に挙げているsave()/current_state()はエディタ保存確認です。修正後の代表成果物で内覧保存復帰を1回確認するか、未実施と正しく記載してください。大掛かりなOS入力自動化は不要です。

W06へはまだ進みません。実敷地の緯度経度・真北・周辺寸法は引き続き未確認として保持します。
