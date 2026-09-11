# W08-G 再レビュー v2

判定：**ACCEPTED**（2026-09-11）。R1〜R3は解消です。今回確認した範囲で追加の受入阻害事項はありません。ゲスト試用版の実装を受け入れ、施主による操作・画質確認へ進みます。自宅H1以降には自動着手しません。

- BASE: `1d6a11bb4f035b4aabaf9209766f54c677f18cc3`（維持）
- 受入HEAD: `02a4f0704109f0d2bde6480c5f412e5252235b80`
- 提出束: `build/reviews/W08-G-v2`
- 対象: 既存worktree `build/worktrees/visual-twin` / `feature/visual-twin-foundation`

## 指摘の確認

| 指摘 | 判定・根拠 |
|---|---|
| R1 最新F5と比較条件 | 解消。共通retained_inputsで保存を選び、selected-state.jsonへ固定して両撮影へ--stateで渡します。無断の高度45度指定は撤去。提出比較は内覧F5保存・対象室room-1f-03・太陽55度・door-002 openを選択しています。レビュー側で両conditionsを選択保存と全キー比較し、対象室variantのnatural/warm以外に差がないことを確認しました。 |
| R2 プレビュー後の変更 | 解消。CandidateReportの正本/候補SHAをGUIから反映処理へ渡し、不一致なら書込み前に拒否して再確認へ戻します。正本の別note変更、候補の同一パス再書出し、SHA一致時の反映のテストが成功しました。 |
| R3 更新画面の破棄 | 解消。キューの各項目を分離し、再登録をfinallyへ移動。更新成功時の設定切替はウィジェット操作より先にアプリ側で行い、破棄済み画面への操作をガードします。死んだwidgetコールバック後の継続、窓なしのモデル切替、更新中のアプリ終了抑止のGUI関連テストが成功しました。 |

## 確認結果と範囲

- レビュー側でunittest discoverを実行し、**221件成功、スキップなし**。pytestによる再実行ではありません。Tk関連3件もこの実行に含まれます。
- 提出manifestの成果物は **16点**で、すべてSHA-256一致です（提出説明の「17点」とは差があります）。
- `build/W08-G-update-v3/refresh.json` はcomplete。sourceHashesは現在の対応ファイルとすべて一致（LF正規化）。statePreserved/geometryVerified/cameraRotationPreservedはtrueです。
- 更新後はLDK warm、洗面reference＋elec-004 on、UB warm、8室状態、非nullカメラ、door-002 openを保持。Blenderの扉bindingもbakedOpen=true、openYawDeltaDeg=73です。前回未確認だったAC4の条件を満たす提出結果を確認しました。
- 洗面のnatural/warm画像を目視し、同じ画角で仕上げ差が出ていることを確認しました。生成コード上も元の保存ファイルを書き換えず、一時的に指定状態を適用して撮影する経路です。
- レビュー側ではUE/Blenderの重い生成や通常GUIの手操作一巡を再実行していません。GUI関連自動テスト・コード・提出された実行証拠に基づく受入です。施主の使い勝手・画質評価は未実施として扱います。

## 試用への引継ぎ

起動入口はワークツリー直下の `guest-launcher.cmd`、手順は [GUEST_TRIAL_GUIDE.md](../GUEST_TRIAL_GUIDE.md) です。まず内覧を開き、移動・扉・室の仕上げを試し、F5保存後に終了して再起動する短い操作から確認します。

洗濯機の設置向き、狭所、仮材質・未校正の照明/採光は既知の残件です。試用結果を見てゲスト調整を先に行うか、自宅H1へ進むかを決めます。受入は写真同等品質の認定やmerge/push実施を意味しません。

報告書の先頭HEADは361f74fのままですが、今回の受入HEADはmanifestとgit HEADが一致する上記02a4f07です。証跡件数と併せ、次の文書更新で訂正すればよく、再提出は不要です。
