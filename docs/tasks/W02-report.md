# W02 実装報告（第5版・レビューv4のテスト隔離対応）

状態：READY_FOR_REVIEW
開始BASE（完全SHA）：`0ebb9f616930fa06436fddaed652e00a3334746c`（第1〜4版と同じBASEからの累積差分）
使用モデル：Claude Sonnet 5（`claude-sonnet-5`）
環境：第4版から変更なし（Windows 11 25H2 / UE 5.8.2 / Blender 5.2.0 LTS）。

## 結果

`docs/tasks/W02-review-v4.md`の必須修正（障害注入テストの保存先分離・削除範囲の制限）に対応しました。前回A・Bの製品ロジックは再設計していません。新機能は追加していません。

1. **保存先の分離**：`SavedViewName()`に、`-RyukaFaultSave`/`-RyukaVerifyRecovery`/`-RyukaBoundaryFaultTest`のいずれかが指定されているときだけ`Saved/walkthrough-test-state.json`（テスト専用名）を返す分岐を追加しました。`SaveView()`/`RestoreView()`は元のまま、保存先の決定箇所1か所を変えただけです。通常起動・`-RyukaSmoke`の保存先は変更していません。
2. **Shippingガード**：3つのテストブロック全体を`#if !UE_BUILD_SHIPPING`で囲みました（従来は障害注入行のみ）。
3. **削除範囲の制限**：`-RyukaFaultSave`起動時の後始末で使う`DeleteDirectory`を非再帰（`Tree=false`）に変更しました。想定外の中身があるディレクトリは削除されず残ります。

## 確認

`build/W02-refresh-v5`（同じBASEから一括再生成、NullRHI/DX12両smoke成功、`changedSourceFiles`に`Walkthrough.cpp`含む、`stateVerification`全項目true）の`Saved/`に、実際の保存とバックアップを想定した識別用データ（`REAL-PLAYER-SAVE-DO-NOT-TOUCH`等の目印付きJSON）を投入したうえで、`-RyukaFaultSave`→`-RyukaVerifyRecovery`（障害物残存時）→`-RyukaVerifyRecovery`（障害物除去後）→`-RyukaBoundaryFaultTest`を順に実行し、以下を確認しました。

| 確認項目 | 結果 |
|---|---|
| `Saved/walkthrough-state.json`のSHA-256 | テスト前後で完全一致（`62124bc7...`） |
| `Saved/walkthrough-state.json.bak`のSHA-256 | テスト前後で完全一致（`fb2e45a8...`） |
| テスト自体の結果（各`passed`） | `-RyukaFaultSave`・`-RyukaBoundaryFaultTest`とも`PASS`、`-RyukaVerifyRecovery`も期待通り（障害物残存時`ready:false`、除去後`ready:true`） |
| テスト専用ファイルの往復 | `Saved/walkthrough-test-state.json`/`.bak`のみで完結。`walkthrough-test-state.json.bak`のハッシュは復旧後の内容と完全一致 |

前回A・B（`RecoverSaveIfNeeded`の復旧判定、境界補正の停止/F9復帰）は今回のコード変更対象外で、上記テストが今回もPASSしていることで機能自体に回帰がないことも併せて確認しています。

回帰：`validate_house.py`（33室・35壁）、`python -m pytest tests/`（48 passed）とも成功。

## 変更ファイル

`unreal/walkthrough/Source/RyukaInterior/Walkthrough.cpp`のみ（`SavedViewName()`・`-RyukaFaultSave`ブロックの削除処理・3テストブロックの`#if`範囲）。`Walkthrough.h`の変更なし。

証拠は`build/W02-diag/v5-final-*`（生ログ）と`v5-final-*-decoded.json`（UTF-16→UTF-8変換、変換元は同名の`.log`実行で生成された`Saved/walkthrough-*.json`）にあります。`build/W02-refresh-v5/`が最新の一括生成先です。

## 残ること

家具・部屋境界が極端に近接する狭所での斜め移動の速度面の制限、実機での操作感確認は、これまでと同様に未着手・未検証のままです（今回のレビュー範囲外）。
