# W07-G1 再レビュー v2

判定：**ACCEPTED**。2026-09-10。

- BASE：`5d4d3cbb06f4436a3574c12dea44ade7a20fb3f3`
- HEAD：`60d8cd644d00e57f11708dbbb1a1aa263095b2bc`
- ブランチ：`feature/visual-twin-foundation`
- 提出：`build/reviews/W07-G1-v2`
- 前回：[v1レビュー](W07-G1-review.md)

## 判定理由

前回の通常利用を妨げる不具合は修正されています。v1→v2の12ファイルの差分、呼び出し先、累積変更一覧、提出証拠を確認しました。G1の2室基盤を受け入れます。G2の詳細仕様を現行実装に合わせて確定できる段階です。G2の室間歩行、G3の残り区画は未実装であり、今回の受入に含みません。push/mergeは実施していません。

| 指摘 | 再レビュー結果 |
|---|---|
| R1 起動例外 | メニュー表示が実シーンを要求しない_display_state()を使うことを確認。refreshは04-walkthrough・04-state-checkを含めcomplete。UEログ末尾もSuccess - 0 error(s), 2 warning(s)。終了コード判定の緩和はありません。 |
| R2 部分案のscope | 共通partial_applyへ対象scope_idを渡し、範囲外室を拒否します。提出のマージ結果はguest-pilotで2室を保持し、レビュー側のvalidate_state_own_scopeも成功しました。 |
| R3 基準保存 | 全室案では基準保存を読まず、部分案では共通latest_state_pathで新しい内覧保存を選びます。追加テストが両経路を確認しています。基準保存の証拠記録だけは下記の改善事項です。 |
| R4 仕上げA/B | 候補からvariant/surfaceOverridesだけを採用します。最終コードの関数を抽出し、実シーン適用のみ代替したレビュー側の確認でも対象室fixturesと他室の保持が成功しました。追加修正された比較表示関数もKeyErrorなく動作しました。 |
| R5 室別家具材質 | Blenderで室別の材質セットを家具・装飾へ渡し、UEは室variantの接頭辞を除去して役割を認識します。外皮のnaturalと固定色の追加材質を保持しています。材質名サニタイズへの対応も両側で一致しています。 |

## 証拠・検証

- manifest記載の8成果物は全てSHA-256一致。BASE/HEADも提出と一致しています。
- refresh.jsonの全7工程がcomplete、マージ状態とUE保存は同一ハッシュです。保存内容の自己検証もレビュー側で成功しました。
- refresh実行時のstudy_controls.pyのハッシュは最終HEADと異なります。比較表示関数_compare_status_textだけをv1版に戻した内容が実行時ハッシュと完全一致することを確認しました。つまり、完全refreshはこの表示修正の直前に実行されています。生成先Content/Python/study_controls.pyは最終コードと一致し、修正後の比較確認結果も提出されています。影響を限定できるため、完全refreshの追加実行は求めません。
- 実UEの18項目成功は提出JSONを確認しました。部屋切替、室別点灯、比較時のfixtures保持、旧案読込後の洋室とscopeの保持、未知室/別室面の拒否を含みます。レビュー側でUEを再起動して追試したものではありません。
- F5/F9はv1からの実行証拠を継続利用します。v2-refreshのwalkthrough-verificationはconfigured=true/runtimeVerified=falseであり、これを新しいruntime成功証拠とは扱いません。C++はv1以降変更されておらず、前回方針通り追加の全内覧再試験は要求しません。
- レビュー側：`python -m unittest discover -s tests -q`で170件成功。現在の既定Pythonにpytestがないため、unittestで実行しました。`node scripts/build-web-data.mjs --check`と`python tests/validate_house.py`も成功。報告のpytest実行そのものを再現したとは扱いません。
- AC1/2は生成・編集コードと提出実機証拠、AC3はrefresh完走と状態照合、AC4は代表比較の提出結果と実関数確認、AC5は既存内覧証拠と拒否確認、AC6は文書と関連検証により、G1の受入を妨げる問題はありません。

## 進行を止めない改善事項

1. R3で求めた「部分案の基準保存もスナップショットし、選択元とハッシュを記録する」は未対応です。現状はマージ結果を固定するので選択時点の他室状態を保持できますが、長い生成中の基準保存更新をunchanged()が検出できず、選択元を後から追えません。次にrefreshを触る際、基準ファイルの記録と変更検出を追加してください。今回の通常利用を止める残件とはしません。
2. 報告の「太陽来歴保持」は今回のrefresh証拠では手動角度（solarなし）です。日時由来solarを含むrefreshを新たに実機確認したという意味には扱いません。既存の来歴保持処理・関連テストは維持されています。
3. 実機確認スクリプト本体と、実行後に変更したコードの対応を次回からmanifestへまとめると、結果JSONだけより再現が容易です。今回の追加試験・再提出は不要です。

再起動後の再開時は、本レビューをG1の最新判定として参照してください。v1のCHANGES_REQUESTEDは本判定で更新されます。
