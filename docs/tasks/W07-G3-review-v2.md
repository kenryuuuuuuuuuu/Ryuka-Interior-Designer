# W07-G3 再レビュー v2

判定：**ACCEPTED**（2026-09-10）。前回R1〜R3は解消です。今回確認した範囲で、追加の受入阻害事項はありません。G1/G2/G3を受入済みとし、次はW08-Gの仕様・起動導線へ進めます。

- BASE: `e9113b94d03f6eaf5c83bede32fc9532bca470c0`（維持）
- 受入HEAD: `1d6a11bb4f035b4aabaf9209766f54c677f18cc3`
- 提出束: `build/reviews/W07-G3-v2`
- 既存ワークツリー・feature/visual-twin-foundationを継続。受入はmerge/push実施を意味しません。

## 指摘の確認

| 指摘 | 判定・根拠 |
|---|---|
| R1 旧scope取込 | 解消。SurfaceBinderがvariant_by_roomに含まれる室だけを登録します。全registry検証は維持。関連テスト成功、pilotの実取込記録はunrealImportVerified=true、16面すべてbound、所属は洋室/LDKのみ。guestは52面すべてboundです。 |
| R2 空室の基本variant | 解消。役割スロットのない室は管理状態から基本variantを取得し、上書き後のMIDから逆算しません。既存の実材質整合チェックも維持。玄関全面warm上書き後のnatural保持、保存/再読込、解除後のnatural実材質復帰の実UE成功記録を確認しました。 |
| R3 水回り形状 | 解消。キャビネットをボウル下の低い箱と外周パネルへ分割し、内部空間を確保。洗濯機のdiscは垂直面の円を奥行方向へ押し出し、ガラス前面を縁より前へ出します。関連テスト成功。洗面/トイレ/UBの更新画像を確認し、洗面の凹み、便器全体、浴槽内部が前回より確認しやすくなっています。洗濯機正面の目視には下記の配置制限があります。 |

## 検証と限界

- レビュー側でunittest discoverを実行し、**201件成功**。pytestによる再実行ではありません。
- manifestの証跡 **23点すべてSHA-256一致**。guestの実取込712メッシュ、verifyの20項目成功、smokeのPASS記録を確認しました。
- 完全refresh-v2はcomplete。sourceHashesは現在の対応ファイルとすべて一致（LF正規化）。転送検証のstatePreserved/geometryVerified/cameraRotationPreservedはtrueです。siteDaylightCalibrated=falseは既知の未校正事項です。
- UE/Blenderの重い生成・実機操作はレビュー側では再実行していません。コード、関連テスト、提出された実行結果と画像に基づく判定です。

## 残件と報告の訂正

1. **洗濯機の配置向き**：fur-002の正本rotationを維持した結果、前面が壁側で、室内代表画像から丸ドアは見えません。今回の円形生成コードの修正と、設置向きの妥当性は区別します。配置レビューの残件とし、採用方向を推測して変更することは求めません。正面の実描画を目視確認済みとは扱いません。
2. **refreshの実条件**：報告書AC5/6の「door-002 open、洗面内カメラ、新旧室で異なるvariant/点灯」はv2出力と一致しません。v2の保存状態は8室すべてnatural・面上書き/fixtures空、doorStates={}です。扉bindingもopenYawDeltaDeg=73ですがbakedOpen=falseです。カメラは非nullです。v2はこの基準状態でのrefresh成功として扱います。開扉・異なる室設定の転送はv1で確認済みであり、今回その転送ロジックに変更はないため、完成優先方針により重い再実行は不要です。次の文書更新で報告書を実条件へ訂正してください。
3. 報告書先頭のHEADはcf0f8ecのままですが、今回の受入対象はmanifestとgit HEADが一致する上記1d6a11bです。

上記はG3の再提出を求める事項ではありません。W08-Gへ進む際も、未確定の設備配置・仮仕上げ・狭所制限を引き継ぎます。
