# W01 実装報告

状態：BLOCKED
開始BASE（完全SHA）：`9882f564587d4f40ec9721c82c095aa1458c7596`
使用モデル：Claude Opus 5（`claude-opus-5`。セッションで実際に選択されたモデルを確認）
環境（OS/UE/ツール版、変更した設定）：Windows 11 25H2 [10.0.26200.9278] / UE 5.8.2（CL-56702186、Launcher外の直接インストール）/ DirectX Agility SDK `D3D12Core.dll 1.618.5.0`（UE同梱）/ NVIDIA GeForce RTX 5060 Ti ドライバ 32.0.15.9186 / AMD Ryzen 7 5700X / Python 3.14 / Node。**環境設定の変更は行っていません**（ドライバ・Engine・OS設定・キャッシュ削除はいずれも未実施）。

## 結果

描画初期化の失敗箇所を`FD3D12DynamicRHIModule::IsSupported()`内まで特定し、有力仮説を4つ検証して全て否定しました。UEの外ではD3D12が完全に正常動作することを実証済みです。**根本原因の特定と描画復旧には環境変更（ドライバ更新／Engine改変／デバッガ導入）が必要な段階に達したため、仕様書の停止条件に従いBLOCKEDとします。** AC2/AC3/AC5は未完了です。既存の状態・生成物・施主保存ファイルは保全し、回帰がないことを確認しました。

| 条件ID | 判定 | 証拠パス・コマンド・終了コード・実行したコード版 |
|---|---|---|
| AC1 | PASS | 下記「診断表」。観測事実と仮説を分離して記載。ログ：`build/W01-baseline/textiles-v4-render-fail.log`、`build/refresh-walk-v3/ue/Saved/Logs/RyukaInterior.log`、`build/W01-diag/minimal-project/Saved/Logs/Minimal.log`、`build/W01-diag/*.log`。コード版はBASE（`9882f56`）から未変更 |
| AC2 | FAIL | `python scripts/launch-unreal-walkthrough.py --engine <UE5.8> --project build/refresh-walk-v3/ue --cache '../../ddc' --smoke` → 終了コード1（UE側は終了コード3）。60.185秒のハング後に致命的エラー。smoke PNGは生成されず、`renderVerified`は`false`のまま |
| AC3 | BLOCKED | GUI版`UnrealEditor.exe`で実プロジェクトを起動 → ウィンドウは生成されるが同一箇所で60.195秒後に致命的エラー。実画面でのLDK表示は未達。自動テストでの代用はしていません |
| AC4 | PASS | `python -m unittest discover -s tests -p 'test_*.py'` → 48 tests OK / `validate_house.py`（33室・35壁）/ `validate_furniture.py`（30型・45件）/ `validate_openings.py`（15型・19+31件）/ `validate_electrical.py`（23型・143件）/ `node scripts/build-web-data.mjs --check`（最新）/ `node tests/test_furniture_web.mjs`（合格）。いずれも終了コード0。施主保存ファイル`build/ue-walk-v1/Saved/walkthrough-state.json`のSHA-256は実行前後とも`35e81125087dc3c72d5fb65befa27594964460a8c0763d064819c31ff369ad10`で不変。`build/refresh-walk-v3/ue/Saved/walkthrough-state.json`は実行前後とも不在（記録） |
| AC5 | N/A | 根本原因が未特定のため生成器・ランチャーへの修正を行っていません。仕様書の「盲目的なフラグ変更をしない」に従い、裏付けのない回避フラグの恒久化は見送りました |

## 診断表（AC1）

すべて同一プロジェクト・同一コマンド系統で、**一度に変えた条件は1つ**です。所要時間は「Checking if RHI ...」ログから致命的エラーまでの実測値です。

| # | ケース（変えた条件） | 結果 | ハング時間 | 得られた新しい証拠 |
|---|---|---|---|---|
| 1 | 描画付きsmoke（実行コンテキストを非対話サンドボックス→**対話セッション1・通常ユーザー**へ変更） | 同一失敗 | 60.185秒 | 実行コンテキストは原因ではない |
| 2 | **UEを介さないD3D12プローブ**（`build/W01-diag/d3d12_probe.py`） | 全て成功 | — | DXGIファクトリ0.01秒、アダプタ列挙即時、`D3D12CreateDevice`サポート確認がFL11_0〜**12_2**まで各0.08秒 |
| 3 | 同上＋**実デバイス生成**（`d3d12_device_probe.py`） | 成功 | — | 実際の`ID3D12Device`生成が**0.18秒**で成功（`hr=0x00000000`） |
| 4 | `-nohmd`（**HMD検出を無効化**） | 同一失敗 | 60.185秒 | HMD/VRランタイム検出は原因ではない。OpenXR ActiveRuntimeは未登録・VRプロセスも皆無 |
| 5 | **最小UEプロジェクト**（プラグイン・C++モジュール・Contentすべて無し、`build/W01-diag/minimal-project/`） | 同一失敗 | 65.6秒（終了コード3） | **プロジェクト固有ではない**。生成物・Config・C++内覧モジュールは無関係 |
| 6 | **GUI版`UnrealEditor.exe`**（起動方法の変更） | 同一失敗 | 60.195秒 | 起動方法にも依存しない。ウィンドウは生成されるがCPUを消費せず待機し、同一箇所で落ちる |
| 7 | **Agility SDK経由のプローブ**（`agility_probe.py`） | **検証不成立** | — | `SetSDKVersion`は成功するが`D3D12CreateDevice`が`hr=0x887e0003`（SDK_COMPONENT_MISSING）で即時失敗。UEと同条件を再現できておらず、**仮説の裏付けにも反証にもならない** |

### 観測事実（すべて再現性あり、計4回の描画付き実行で一致）

1. 失敗箇所は常に `LogRHI: Checking if RHI D3D12 with Feature Level SM6 is supported by your system.` の直後で、そこから **60.17〜60.20秒** 後に `LogWindows: Error: === Critical error: ===`。**エラー本文は空**。終了コードは3（ランチャー経由では1）。
2. ハング中のプロセスは**CPUをほとんど消費しない**（60秒間でCPU約2.5〜2.8秒、メモリ726MBで不変）。通常のクラッシュではなく待機・タイムアウト打ち切りの挙動です。
3. ハング中に NVIDIA ユーザーモードドライバ（`nvwgf2umx.dll`、`nvldumdx.dll`、`nvgpucomp64.dll` 等）と `d3d12.dll`／`D3D12Core.dll`／`UnrealEditor-WindowsD3D.dll` はロード済み。
4. WMI（`Win32_VideoController`）0.15秒、レガシーWMI 0.05秒、GPUドライバのレジストリ照会0.02秒でいずれも正常。GPU情報照会は原因ではありません。
5. DXGIアダプタは2つ：`NVIDIA GeForce RTX 5060 Ti`（16051MB）と`Microsoft Basic Render Driver`（WARP）。
6. 描画なし（`-NullRHI` / `--logic-only`）の実行は成功し続けており、`runtimeVerified=true`は維持されています。

### エンジンソースの読解で絞り込んだ範囲（仮説であり断定ではありません）

`Engine/Source/Runtime/RHI/Private/Windows/WindowsDynamicRHI.cpp:1374` のログ出力直後に `DynamicRHIModule->IsSupported()` が呼ばれます。`IsSupported()` が false を返した場合は `HandleUnsupportedFeatureLevel` / `HandleUnsupportedRHI` が **専用のログを必ず出力**しますが、それが一切出ていません。また `SafeTestD3D12CreateDevice()` が成功した場合に必ず出る `Found D3D12 adapter 0: ...`（`WindowsD3D12Device.cpp:872`）も、`DirectX Agility SDK runtime found/not found`（同937行）も出力されていません。

したがって停止位置は **`FD3D12DynamicRHIModule::IsSupported()` に入った後、最初のアダプタに対する`SafeTestD3D12CreateDevice()`の完了前**（その手前の`FWindowsD3D::ChooseD3D12Adapter()`を含む区間）と絞れます。この区間はログを出力しないため、これ以上はログのみでは切り分けられません。なお`CheckDeviceForEmulatedAtomic64Support()`はIntel GPU専用で、本環境では該当しません。

**未確定**：この区間のどのAPI呼び出しがブロックしているかは特定できていません。UE外では同等の処理（アダプタ列挙・デバイス生成・機能レベル確認）がいずれも0.2秒未満で完了するため、「UEが使うDirectX Agility SDK 1.618経由の経路と、このNVIDIAドライバの組み合わせ」を有力な仮説としていますが、ケース7の検証が不成立のため**裏付けは取れていません**。

## 変更と判断

- **コード変更はありません。** 原因が未特定の段階でランチャーや生成器へ回避フラグを入れることは、仕様書が禁止する「盲目的なフラグ変更」に当たるため見送りました。本報告書の追加のみです。
- 設計からの差異：なし。追加依存：なし。環境変更：なし。
- 診断用の未追跡成果物（すべて`build/`配下、`.gitignore`対象）：
  - `build/W01-baseline/` — 診断開始前に退避した既存証拠（仕様書の指示による）
  - `build/W01-diag/d3d12_probe.py` / `d3d12_device_probe.py` / `agility_probe.py` と各`.log` — UE外D3D12の計測。いずれも**環境を変更しない読み取り専用のプローブ**
  - `build/W01-diag/minimal-project/` — 最小UEプロジェクト（診断ケース5）
  - `build/W01-diag/verbose-*.log`、`run3-*.log`、`nohmd-*.log`、`minimal-*.log` — 各試行の出力
- 実行手順上の誤りとその扱い：詳細ログ取得の初回試行で、uprojectを相対パスで渡したこと、およびGit Bashのパス自動変換で`/Game/Generated/House`が別パスへ変換されたことにより、UEがプロジェクトを読めず早期終了しました（`build/W01-diag/verbose-d3d12.log`）。**この試行は無効**として扱い、PowerShellで絶対パス指定に修正して再実行しています。
- 保全と復旧：smoke実行はスクリプト仕様上、既存の`walkthrough-smoke*`を削除します。開始前に`build/W01-baseline/`へ退避し、検証後に復元しました。`walkthrough-verification.json`は退避物とSHA-256が一致（`819559f1...`）し、`renderVerified=false`のまま維持されています。施主保存ファイルは上表AC4のとおり不変です。

## 残ること

**未完了**：AC2（DX12/SM6での描画）、AC3（実ウィンドウでのLDK表示）、AC5（生成器修正後の再確認）。W01は合格していません。

**否定した仮説**：実行コンテキスト（対話/非対話・権限）、D3D12およびGPUドライバ全般の不具合、HMD/VRランタイム検出、プロジェクト固有の設定・プラグイン・C++モジュール、起動方法（Cmd版/GUI版）。

**検証不成立**：Agility SDK経由の再現（ケース7）。Pythonプロセスからのopt-inが機能せず、UEと同条件を作れませんでした。

**未確認事項**：施主による手動起動の結果は、今回私が代理でGUI版を起動して同一失敗を確認しましたが、施主自身の操作環境での結果は依然として未回答です。

### 次に試す1手（いずれも環境変更を伴うため施主の承認が必要です）

優先度順に、影響と得られるものを併記します。

1. **デバッガ導入によるハング中のスタック取得**（推奨）。`procdump`または Windows SDK の`cdb`を導入し、ハング中の60秒間にダンプを取得すれば、停止しているAPI呼び出しを**確定的に**特定できます。影響：開発ツールの追加インストールのみで、Engine・ドライバ・プロジェクトには変更を加えません。最も情報量が多く、副作用が最も小さい選択肢です。
2. **NVIDIAドライバの更新またはクリーンインストール**。現在32.0.15.9186。RTX 5060 Ti（Blackwell世代）とUE 5.8.2同梱のAgility SDK 1.618の組み合わせを変える検証です。影響：GPUドライバの入替のためBlender側のOptiXレンダリングにも影響しうるので、実施前に既存の生成物を確定させておく必要があります。
3. **UE同梱Agility SDKの一時無効化**（`Engine/Binaries/Win64/D3D12`のリネーム）。ケース7で確認できなかった仮説を直接検証できます。影響：**Engineインストールの改変**にあたり、他プロジェクトにも影響し、UEの再インストールで復旧が必要になる可能性があります。実施するなら復旧手順を用意した上で。
4. 参考：`-d3d11`（DX11）での起動可否の再確認。ただし仕様書のとおりDX11は画質目標の達成扱いにできず、切り分け情報としてのみ使えます。

## 再現・復旧

再実行コマンド（専用ワークツリーをカレントディレクトリにします。`<UE5.8>`は実際のインストールパスに置換）：

```powershell
# 描画なし（現在も成功する基準線）
python scripts/launch-unreal-walkthrough.py --engine '<UE5.8>' --project build/refresh-walk-v3/ue --cache '../../ddc' --smoke --logic-only

# 描画付き（現在60秒で失敗する）
python scripts/launch-unreal-walkthrough.py --engine '<UE5.8>' --project build/refresh-walk-v3/ue --cache '../../ddc' --smoke

# UE外のD3D12計測（環境を変更しません）
python build/W01-diag/d3d12_probe.py
python build/W01-diag/d3d12_device_probe.py

# 最小プロジェクトでの再現（プロジェクト非依存の確認）
& '<UE5.8>/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'build/W01-diag/minimal-project/Minimal.uproject' -game -d3d12 -sm6 -RenderOffscreen -unattended -nosplash -NoSound -NoSourceControl
```

以前の生成物へ戻す方法：`build/W01-baseline/refresh-walk-v3-ue/`に診断開始前の`walkthrough-verification.json`・`walkthrough-smoke-state.json`・`walkthrough-smoke.txt`・`walkthrough-smoke.log`とNullRHI成功時のログを保存してあります。`Saved/`配下へコピーすれば開始時点に戻ります（本報告時点で復元済み）。全ログは`build/W01-diag/`および`build/W01-baseline/`配下にあります。

正本（`data/`）・生成物（`generated/`）・Three.js側（`interior-white-model.html`）には一切変更を加えていません。
