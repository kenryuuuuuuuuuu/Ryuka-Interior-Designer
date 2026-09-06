# ゲストLDKの床材・周辺遮蔽物

2026-09-06追加。日時比較の手順は[VISUAL_TWIN_PLAN.md 10章](VISUAL_TWIN_PLAN.md#10-日時地域真北による太陽位置)を参照してください。ここでは仮フローリングの表現と、ローカル資料に基づく隣棟・塀の概形を扱います。実敷地の位置・真北・周辺寸法、採用する床材・壁紙・ガラスの品番は未確定です。

## 床専用の材質

`data/visual/unreal-finishes.json`の`roles.floor`に、床板幅・長さ・目地幅（cm）、張り方向（度）、粗さを設定します。現在は幅15cm、長さ180cm、目地0.08cm、長手は図面東西方向という仮設定です。0°が東西、90°が南北です。確度と根拠も同じ設定に残します。

UEの床スラブ7個にだけ専用材質を割り当て、家具の木目と分離しています。床板の継ぎ目、ずらした端部、一枚ごとの色差をワールド座標cmから生成します。床を求積区画で分割していても模様の位置は連続します。輪郭形状を変えず、UVにも依存しません。目地は色で表現しており、実際の溝・面取り・凹凸は未実装です。実製品のテクスチャではありません。

案の色は従来の`wood`色を参照するため、既存のBlenderパッケージと保存済みの案名を使えます。新しい材質役割`floor`はUE生成時に割り当てます。Blenderの材質やThree.jsの正本データは変更しません。HLSLと仕上げ設定をプロジェクトへコピーし、画像の検証記録にハッシュを残します。

## 隣棟・塀の入力

敷地周辺の値は公開Gitへ入れず、作業中のworktreeの`build/context.local.json`に保存します。以下は**実際の隣棟とは無関係の動作確認用サンプル**です。

```json
{
  "schemaVersion": "1.0.0",
  "boxes": [{
    "id": "demo-south-building",
    "centerMetres": [4.5, 10.5, 3],
    "sizeMetres": [8, 3, 6],
    "rotationDeg": 0,
    "status": "estimated",
    "note": "遮蔽確認用の架空形状。実際の隣棟ではありません。"
  }]
}
```

- `centerMetres`は立体の**中心**を、建物と同じ座標の[東向きx、南向きz、GLからの高さ]で指定します。底面位置ではありません。高さ6mで底面GL0なら中心高さは3mです。
- `sizeMetres`は回転前の[東西幅、南北奥行、高さ]です。`rotationDeg`は平面上で時計回り、中心回転です。
- `id`は住所等を含まない識別子にします。`status`と`note`で測定・資料・概算の根拠を残します。
- 平らな不透明直方体の概形です。屋根勾配、樹木の透過、地形、窓などは再現しません。確認できない隣棟を実在するものとして追加しません。

```powershell
python scripts/build-unreal-study.py --engine 'C:/Program Files/Epic Games/UE_5.8' --package build/guest-natural-v2 --output build/ue-local-study --cache '../../ddc' --sun-cases build/sun-cases.json --context build/context.local.json
python scripts/capture-unreal-study.py --engine 'C:/Program Files/Epic Games/UE_5.8' --project build/ue-local-study --cache '../../ddc' --name winter-context --sun-case 1
```

出力先は新しいディレクトリを指定します。`--context`を使う場合は入力・出力ともworktree内の`build/`が必須です。周辺形状は建物正本と分離し、UEでは`Local/SiteContext`フォルダに入ります。生成時に回転後の外形を1mm以内で検証します。建物の545メッシュの検証に周辺物を混ぜません。

既存の比較条件を引き継ぐ場合は`--state`と`--context`を併せて指定します。周辺物を使用した比較条件には`siteContextSHA256`が保存され、再生成時に`--context`が抜けていれば停止します。更新した周辺設定を明示的に渡した場合は、新しいハッシュを記録します。周辺形状そのものは比較条件に埋め込まないため、ローカル設定も保管してください。

撮影前には周辺設定ファイルのハッシュと実シーンの外形・非表示・影設定を確認します。周辺物を手動で動かした場合はローカル設定へ反映して再生成します。画像ごとのJSONにも周辺入力のハッシュと検証結果が記録されます。材質を任意に編集した場合や複雑な外部メッシュを追加した場合まで保証する仕組みではありません。

## 検証と残りの作業

`tests/test_site_context.py`で回転と座標変換、不正寸法、根拠欠落、床板寸法の範囲を検証します。`tests/validate_unreal_context.py`はUE commandlet内で床と家具の材質分離、案の切り替え、周辺物の外形と手動移動の拒否を確認します。従来の太陽位置・条件引き継ぎ・正本の検証も継続します。

これで実敷地の設定が完了したわけではありません。実位置・真北と周辺寸法を確認して入力し、床材・壁紙・ガラスの採用品番を反映する作業が残っています。天候・材料反射率・ガラス透過率・室内照度は引き続き未校正です。
