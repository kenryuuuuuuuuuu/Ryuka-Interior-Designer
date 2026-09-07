# W01 実装報告（第3版・解決）

状態：READY_FOR_REVIEW（**描画復旧を確認**。GPUドライバ更新により解消）
開始BASE（完全SHA）：`9882f564587d4f40ec9721c82c095aa1458c7596`
使用モデル：Claude Opus 5（`claude-opus-5`）
環境（OS/UE/ツール版）：Windows 11 25H2 [10.0.26200.9278] / UE 5.8.2（CL-56702186）/ Agility SDK `D3D12Core.dll 1.618.5.0`（UE同梱）/ AMD Ryzen 7 5700X / Blender 5.2.0 LTS / Avast Antivirus 26.8.11125（稼働中、未変更）。

**GPUドライバ（施主が実施）**：NVIDIA GeForce RTX 5060 Ti を `32.0.15.9186`（616.56より前の591.86）から **`32.0.16.1656`（616.56、2026-08-20）** へクリーンインストールで更新。NVIDIA App は導入せず、グラフィックスドライバ・HDオーディオ・PhysXのみ。

第2版で導入した診断ツール（Microsoft ProcDump 12.01を`build/W01-diag/tools/`へ展開、WinDbg 1.2606.22001.0）はそのままです。常駐登録（`-i`）は未実施。**Engine・Agility SDK・OS設定・アンチウイルス設定は最後まで変更していません。**

## 結果

第2版で特定した「NVIDIAドライバのDLLロード中に発生する例外」という診断に基づき、施主がGPUドライバを更新しました。**その結果、描画初期化が復旧し、AC1〜AC4がすべてPASSしました。** 診断の裏付けとして、問題のDLLは実際に置き換わっています（`nvppex.dll`：1,824,864 → 7,624,352 bytes、ドライバストアも`nv_dispig.inf_...`→`nv_dispsi.inf_...`）。

失敗箇所の所要時間が決定的に変化しました。

| ログ位置 | 更新前 | 更新後 |
|---|---|---|
| `Checking if RHI D3D12 with Feature Level SM6 ...` から次の出力まで | **60.19秒 → Critical error（本文空）** | **0.356秒 → 成功** |
| `Found D3D12 adapter 0` | 出力されず | `NVIDIA GeForce RTX 5060 Ti (VendorId: 10de, DeviceId: 2d04)` |
| `DirectX Agility SDK runtime` | 到達せず | `found.` |
| 判定行 | なし | `RHI D3D12 with Feature Level SM6 is supported and will be used.` |

| 条件ID | 判定 | 証拠・コマンド・終了コード |
|---|---|---|
| AC1 | PASS | 下記「診断表」「スタック解析」。証拠：`build/W01-diag/windbg-t12.log`、`windbg-t22.log`、`last-modules-t12.log`、`last-modules-t22.log`、`build/W01-diag/dumps/*.dmp`。ドライバ更新後の成功ログ：`build/refresh-walk-v3/ue/Saved/Logs/RyukaInterior.log` |
| AC2 | **PASS** | `python scripts/launch-unreal-walkthrough.py --engine <UE5.8> --project build/refresh-walk-v3/ue --cache '../../ddc' --smoke` → 終了コード0。`renderVerified: true`／`renderRHI: "d3d12"`／`runtimeVerified: true`、4項目（safe spawn／blocking capsule sweep／finish and sun switch／state save and restore）合格。新規生成した`build/refresh-walk-v3/ue/Saved/walkthrough-smoke.png`（483,923 bytes）を目視確認し、窓からの採光・家具・HUDが正しく描画されていることを確認 |
| AC3 | **PASS** | `--smoke`なしで内覧を実起動。ウィンドウタイトル`RyukaInterior (64-bit Development PCD3D_SM6)`、CPU 809.1秒・メモリ4,193MB（更新前は2.4秒で待機のまま）。画面証拠`build/W01-diag/ac3-window.png`にデスクトップ上のウィンドウとLDK表示を記録。キー操作はしていないため施主保存ファイルは未書換 |
| AC4 | PASS | ドライバ更新後に再実行。`python -m unittest discover -s tests -p 'test_*.py'` → 48 tests OK。`validate_house.py`（33室・35壁）／`validate_furniture.py`（30型・45件）／`validate_openings.py`（15型・19+31件）／`validate_electrical.py`（23型・143件）／`node scripts/build-web-data.mjs --check`（最新）／`node tests/test_furniture_web.mjs`（合格）。すべて終了コード0。施主保存ファイル`build/ue-walk-v1/Saved/walkthrough-state.json`のSHA-256は一連の作業を通じて`35e81125087dc3c72d5fb65befa27594964460a8c0763d064819c31ff369ad10`で不変、`build/refresh-walk-v3/ue/Saved/walkthrough-state.json`は不在のまま維持 |
| AC5 | N/A | **ソース変更が不要**でした（原因はGPUドライバ側にあり、生成器・ランチャーの修正では回避できない箇所のため）。ただし復旧後に正本から新規パッケージを再生成し、描画まで通ることを確認しています（下記「再生成の確認」） |

### 再生成の確認（AC5の補足・Blender OptiX回帰）

`python scripts/build-visual-twin.py --blender <Blender5.2> --interior --variant natural --output build/W01-postdriver-natural` を新しい出力先で実行し、終了コード0。データ検証（33室・45家具・19+31開口・143電気設備）、内部テスト（3件・5件）、形状検証とGLB往復検証がすべて合格し、`interior.png`（1,711,972 bytes）を目視確認しました。

**Blender OptiXに回帰はありません。** レンダー所要は更新前15.250秒に対し更新後14.844秒。OptiXキャッシュは更新前「`AppData\Local\NVIDIA\OptixCache`を作成できず出力先へ退避」という警告つきでしたが、更新後は正規の場所に`optix7cache.db`（1,638,400 bytes、実行時刻に更新）が作成されており、**むしろ正常化しています**。ログの`HIPEW initialization failed`はAMD GPU用ライブラリ不在の警告で、NVIDIA環境では無害です。

## スタック解析（第2版の中核）

ProcDumpで**ハング中**のフルダンプを2点採取しました（`-ma`、常駐登録なし）。採取はプロセスを一時停止させるため、タイミングへの影響がありうることを記録します。3点目は採取前にUEが終了したため取得できていません。

| ダンプ | 採取時刻 | 対象PID | 採取時CPU | サイズ | SHA-256 |
|---|---|---|---|---|---|
| `hang-t12.dmp` | 07:26:54 | 26628 | 2.4秒 | 1,577,378,704 | `A8EF211D69EB93C41C6ED744AB6904482E86FF81442A107D151EED793F3F421C` |
| `hang-t22.dmp` | 07:27:17 | 26628 | 2.4秒 | 1,577,289,376 | `1AF0463C3F1E98A75BE70531CD4F4F2B7A5EC9142B463546988D3FFC8434F311` |

両ダンプの主スレッドのスタックは**フレーム構成もスタックアドレスも完全に一致**（先頭 `00000063af974138`）し、23秒間まったく進行していません。同一の待機が継続していることを確認しました。

シンボル読込状況：Microsoft公開シンボル（`ntdll`/`KERNELBASE`/`kernel32`）は解決済み。**UEモジュールとNVIDIAドライバはPDBが無くエクスポート記号のみ**のため、`UnrealEditor_Core!MemoryTrace_GetActiveTag+0x7d5` のような表示は「最も近いエクスポート関数からのオフセット」であり、**その関数自体を指すとは限りません**。関数名レベルの断定はできず、モジュール単位の帰属が確実な情報です。

主スレッドの呼び出し順（下＝古い、上＝新しい。抜粋、パスは匿名化不要な範囲）：

```
2d UnrealEditor_Cmd!LaunchWindowsStartup
2c UnrealEditor_RHI!RHIInit+0x101
29 UnrealEditor_D3D12RHI!ThisIsAnUnrealEngineModule+0xc1efd
27 UnrealEditor_WindowsD3D!FWindowsD3D::ChooseD3D12Adapter+0x2b6
26 D3D12!D3D12CreateDevice+0x3b
24-21 D3D12Core (Agility SDK 1.618)
19 nvwgf2umx!OpenAdapter10+0x1c182b            ← NVIDIA ユーザーモードドライバ
18-12 nvwgf2umx 内部
11 KERNELBASE!LoadLibraryExW+0xff              ← ドライバがDLLを読み込もうとする
10 ntdll!LdrLoadDll+0x170
0f-0a ntdll ローダー内部（DLLロード通知の配送）
09 UnrealEditor_Core!(MemoryTrace_GetActiveTag+0x7d5 付近)
08 UnrealEditor_Core!(FResourceSizeEx::AddDedicatedVideoMemoryBytes+0x383 付近)
07 ntdll!KiUserExceptionDispatcher+0x2e        ← ここで例外が発生
04 VCRUNTIME140!_C_specific_handler
02 UnrealEditor_Core!ReportCrash+0x14d         ← UEのクラッシュ報告処理
01 KERNELBASE!WaitForSingleObjectEx+0xaf
00 ntdll!NtWaitForSingleObject+0x14            ← 60秒待機の実体
```

### 読み取れること（観測）と推定の区別

**観測（スタックから直接読める）**：

1. 60秒の待機は`ReportCrash`配下の`WaitForSingleObject`であり、**デバイス生成そのものの待ちではありません**。待機に入る前に既に例外が発生しています。第1版で「タイムアウト打ち切り」と書いた解釈は、より正確には「例外発生 → クラッシュ報告処理が待機」です。
2. 例外は`ntdll!KiUserExceptionDispatcher`の直下、**`UnrealEditor_Core`内のコード**で発生しています。
3. その呼び出し元は`ntdll!LdrLoadDll`（DLLロード）であり、さらに遡ると`nvwgf2umx`（NVIDIAユーザーモードドライバ）が`LoadLibraryExW`を呼んでいます。
4. 起点は`FWindowsD3D::ChooseD3D12Adapter` → `D3D12CreateDevice` → Agility SDK → NVIDIAドライバです。第1版で「`IsSupported()`内」と推定した範囲は、実スタックにより`ChooseD3D12Adapter`と確認されました（推定が結果的に当たっていましたが、第1版時点では推定にすぎませんでした）。

**推定（ソース読解との突き合わせ。断定ではありません）**：

`Engine/Source/Runtime/Core/Private/ProfilingDebugging/Microsoft/WindowsModuleDiagnostics.cpp`の`FModuleTrace`は、`LdrRegisterDllNotification`でDLLロード通知を登録し（105行）、`OnDllLoaded()`でロードされたDLLの**PEヘッダとデバッグディレクトリを直接読み取ります**（161〜179行）。フレーム08〜09が`UnrealEditor_Core`であり、呼び出し元がローダーであることは、この通知コールバックが実行中に例外を起こした像と整合します。ただしPDBが無いため、**例外を起こした関数がこの`OnDllLoaded`であるという確証はありません**。

なお`FModuleTrace::Initialize()`のうち、トレースチャネル（`ModuleChannel`）で制御されるのはログ出力のみで、**`LdrRegisterDllNotification`の登録自体は無条件**です。したがってコマンドライン引数でこの監視を止めることはできません（AC5をN/Aとした理由）。

### 引き金となったDLLの候補

ダンプのモジュール一覧を**ダンプ内の並び順**（ローダーの一覧順を反映し、新しくロードされたものほど後ろに来ます）で読むと、末尾はD3D12デバイス生成の流れそのものでした。両ダンプで完全に同一です（`build/W01-diag/last-modules-t12.log`、`last-modules-t22.log`）。

```
D3D12.dll → D3D12Core.dll（Agility SDK）→ nvldumdx.dll
→ cryptnet / wldp / drvstore / devobj / imagehlp / cryptsp / rsaenh（コード署名検証まわり）
→ nvgpucomp64.dll（約77MB）→ NvMemMapStoragex.dll
→ nvwgf2umx.dll（約81MB）→ nvppex.dll（最後）
```

最後に現れるのは`nvppex.dll`（NVIDIA Corporation、`32.0.15.9186`＝現行ドライバと同版、`C:\Windows\System32\DriverStore\FileRepository\nv_dispig.inf_amd64_...\`）です。DLLロード通知はイメージがマップされた後に配送されるため、**通知処理中に例外が起きたDLLは一覧に載っている**はずで、`nvppex.dll`が引き金である可能性が最も高いと考えます。

**ただし断定はしません。** ミニダンプのモジュール一覧の並びがロード順である保証はなく、`LdrLoadDll`へ渡された文字列そのものは読み出せていません（`dps`によるスタック走査では該当文字列を取得できませんでした）。確定するには引数文字列の直接読み出しが要ります。

## 診断表（AC1、第1版から修正）

すべて同一プロジェクト・同一コマンド系統で、一度に変えた条件は1つです。

| # | ケース（変えた条件） | 結果 | 停止直前の最後のログ | 得られた証拠 |
|---|---|---|---|---|
| 1 | 実行コンテキストを非対話サンドボックス→対話セッション1・通常ユーザーへ | 同一失敗 60.185秒 | `Checking if RHI D3D12 ...` | 実行コンテキストは原因ではない |
| 2 | UEを介さないD3D12（`d3d12_probe.py`） | 成功 | — | DXGIファクトリ0.01秒、アダプタ列挙即時、`D3D12CreateDevice`の**サポート確認**がFL11_0〜12_2で各0.08秒 |
| 3 | UEを介さない**実デバイス生成**（`d3d12_device_probe.py`、ABI修正後） | 成功・完走 | — | default 0.18秒／NVIDIA RTX 5060 Ti 0.12秒／Microsoft Basic Render Driver 0.00秒、いずれも`GetNodeCount=1`。終了コード0 |
| 4 | `-nohmd`（HMD検出の無効化） | 同一失敗 60.185秒 | `Checking if RHI D3D12 ...` | HMD検出は原因ではない。OpenXR ActiveRuntimeは未登録、VRプロセスも皆無 |
| 5 | 最小UEプロジェクト（プラグイン・C++・Content無し） | 失敗 60.218秒 | **`Running DelayedAutoRegister Phase PreRHIInit`** | **停止直前のログが実プロジェクトと異なります**（下記R2参照） |
| 6 | GUI版`UnrealEditor.exe`（起動方法） | 同一失敗 60.195秒 | `Checking if RHI D3D12 ...` | 起動方法には依存しない |
| 7 | Agility SDK経由のプローブ（`agility_probe.py`） | **検証不成立** | — | `SetSDKVersion`は成功するが`D3D12CreateDevice`が`hr=0x887e0003`（SDK_COMPONENT_MISSING）で即時失敗。UEと同条件を再現できておらず、裏付けにも反証にもなりません |
| 8 | Avastフックの影響範囲確認 | 反証 | — | `aswhook.dll`はUEだけでなく**通常のPowerShellプロセスにも注入**されており、正常動作した`d3d12_device_probe.py`も同条件です。注入の有無だけでは原因になりません |

## レビュー指摘への対応

- **R1（プローブの例外終了と過大な結論）**：`d3d12_device_probe.py`の`GetNodeCount`呼び出しでvtableスロットを10と誤指定していたのが原因のアクセス違反でした。`ID3D12Device::GetNodeCount`は**スロット7**（IUnknown 0-2、ID3D12Object 3-6）です。修正して再実行し、全アダプタで完走・終了コード0を確認しました（`build/W01-diag/d3d12_device_probe_fixed.log`）。**プローブ内の例外はGPU障害ではなく私のABI誤りでした。** 記述も「UE外では完全に正常」から「UE外からのデバイス生成とノード数取得は0.2秒未満で成功する。ただしUEが続けて行う各種`CheckFeatureSupport`は未検証」に限定しました。ドライバ全般の否定という表現も撤回します。
- **R2（最小プロジェクトの停止位置）**：ご指摘のとおりです。最小プロジェクトのログは`PreRHIInit`の直後に約60秒で終了しており、`Using Forced RHI: D3D12`も`Checking if RHI D3D12 ...`も出力されていません。実プロジェクトとは**停止直前のログが異なり、同じ停止APIとは断定できません**。「複数プロジェクトで起動に失敗する」という事実に記述を弱め、「プロジェクト固有ではない」という結論も「少なくとも本プロジェクト固有の設定・プラグイン・C++モジュールだけが原因ではない」に留めます。なお今回スタックを取得したのは**実プロジェクト**であり、最小プロジェクト側のスタックは未取得です。
- **R3（スタックで必ず確定できるとは限らない）**：そのとおりでした。実際にUEとNVIDIAドライバのPDBが無く、**関数名レベルでは断定できていません**。本版では「モジュール単位の帰属＝観測」「関数名・原因＝推定」を明示的に分けて記載しています。
- **R4（復旧手順のパス）**：修正しました。下記「再現・復旧」に元パスと復元先の対応を明記しています。

## 変更と判断

- **アプリケーションのコード変更はありません。** 変更は本報告書と、`build/`配下（Git管理外）の診断スクリプト・ログ・ダンプのみです。
- 追加した環境変更は診断ツール2件のみ（ProcDump展開、WinDbgインストール）。Engine・ドライバ・Agility SDK・OS設定・Avast設定は未変更です。
- ダンプ（各約1.5GB）は`build/W01-diag/dumps/`に置き、**Gitへ追加していません**（プロセスメモリを含むため）。
- 診断スクリプト：`d3d12_probe.py`／`d3d12_device_probe.py`（ABI修正済）／`agility_probe.py`（検証不成立）／`dump_stacks.py`（PDB無しでモジュール帰属を見るための自作パーサ。フルダンプではスタックメモリが`Memory64ListStream`に入るため簡易スキャンは機能せず、最終的な解析はWinDbgで実施しました）。

## 残ること

**W01の受入条件は満たしました**（AC1〜AC4がPASS、AC5は理由付きN/A）。以下は解決後も残る事項です。

**根本原因の確定には至っていません。** ドライバ更新で事象は解消しましたが、これは「ドライバ側の何かが変わった」ことを示すもので、旧ドライバのどの処理が例外を起こしたかを証明したわけではありません。具体的には次が未確定のままです。

- 引き金DLLが`nvppex.dll`であるという特定は、**モジュール一覧の並び順に基づく推定**です。`LdrLoadDll`へ渡された引数文字列は読み出せていません（確定させるなら採取済みダンプから追加解析が可能ですが、事象が解消した今は優先度が低いと判断します）。
- 例外を起こした関数がUEの`FModuleTrace::OnDllLoaded`であることも、UEのPDB不在のため**推定**です。
- 最小プロジェクト（`build/W01-diag/minimal-project/`）は停止直前のログが実プロジェクトと異なり、スタックも未取得のため、**同一原因かは未確認**です。ドライバ更新後に再試行していません。
- 旧ドライバへ戻した場合に再現するかの逆検証は行っていません（実施の必要性は低いと考えます）。

**否定・限定した仮説**：実行コンテキスト、HMD検出、起動方法、Avastフックの注入有無（いずれも反証あり）。プロジェクト固有性は「本プロジェクト固有ではない」に限定。`aswhook.dll`（Avast）はUE以外の通常プロセスにも注入されており、**Avastは無関係と判断**しました（設定変更は一切していません）。

### 次に検討できること（W01の範囲外・任意）

1. **UNREAL_WALKTHROUGH.mdとSTATUS.mdの更新**。「描画付き内覧は未検証」「GPU初期化が約60秒後に失敗」という記述が現状と合わなくなりました。ドライバ要件（`32.0.16.1656`以降で確認）を追記すべきです。**本報告では未実施です**（文書更新の範囲をW02以降のどこに含めるかはGPTの判断に委ねます）。
2. **Epicへの不具合報告**。DLLロード通知コールバック内でのPEヘッダ・デバッグディレクトリ解析は、外部DLLの構造次第で例外を起こしうる箇所です。報告するなら引き金DLLの確定を先に行うべきです。
3. **W02（歩行体験の合格）への移行**。実ウィンドウでの起動が可能になったため、マウス操作感・歩きやすさの手動確認が実施できる状態になりました。

Agility SDKのリネームは、ケース7が不成立で仮説の裏付けが無いまま影響の大きい改変になるため、現時点では提案しません。

## 再現・復旧

再実行コマンド（専用ワークツリーをカレントディレクトリに。`<UE5.8>`は実インストールパスへ置換）：

```powershell
# 描画なし（基準線）
python scripts/launch-unreal-walkthrough.py --engine '<UE5.8>' --project build/refresh-walk-v3/ue --cache '../../ddc' --smoke --logic-only

# 描画付き（ドライバ 32.0.16.1656 以降で成功する）
python scripts/launch-unreal-walkthrough.py --engine '<UE5.8>' --project build/refresh-walk-v3/ue --cache '../../ddc' --smoke

# 実ウィンドウでの内覧（F5を押さない限り施主保存ファイルは書き換わりません）
python scripts/launch-unreal-walkthrough.py --engine '<UE5.8>' --project build/refresh-walk-v3/ue --cache '../../ddc'

# Blenderからの再生成（OptiX回帰確認を兼ねる。出力先は毎回新しい名前に）
python scripts/build-visual-twin.py --blender '<Blender5.2>' --interior --variant natural --output build/<new-name>

# UE外のD3D12計測（環境を変更しません）
python build/W01-diag/d3d12_probe.py
python build/W01-diag/d3d12_device_probe.py

# ハング中のダンプ採取（常駐登録はしません）
build\W01-diag\tools\procdump64.exe -accepteula -ma <PID> build\W01-diag\dumps\hang.dmp

# ダンプ解析
& "$env:LOCALAPPDATA\Microsoft\WindowsApps\WinDbgX.exe" -z build\W01-diag\dumps\hang-t12.dmp -c ".symfix C:\symbols; .reload /f ntdll.dll; ~0 k 40; q" -logo build\W01-diag\windbg.log
```

**開始時点への復元（元パスと復元先の対応）**：診断開始前の証拠は`build/W01-baseline/refresh-walk-v3-ue/`に退避してあります。復元先はファイルごとに異なります。

| 退避先のファイル | 復元先 |
|---|---|
| `walkthrough-verification.json` | `build/refresh-walk-v3/ue/walkthrough-verification.json`（プロジェクト直下） |
| `walkthrough-smoke.log` | `build/refresh-walk-v3/ue/walkthrough-smoke.log`（プロジェクト直下） |
| `walkthrough-smoke-state.json` | `build/refresh-walk-v3/ue/Saved/walkthrough-smoke-state.json` |
| `walkthrough-smoke.txt` | `build/refresh-walk-v3/ue/Saved/walkthrough-smoke.txt` |
| `RyukaInterior-nullrhi.log` | 参照用のNullRHI成功時ログ（復元不要） |
| `textiles-v4-render-fail.log` | 参照用の旧プロジェクト失敗ログ（復元不要） |

本報告時点で`Saved/`配下の2件は復元済みで、`walkthrough-verification.json`は退避物とSHA-256が一致（`819559f1...`）し`renderVerified=false`のまま維持されています。

正本（`data/`）・生成物（`generated/`）・Three.js側（`interior-white-model.html`）には一切変更を加えていません。全ログは`build/W01-diag/`と`build/W01-baseline/`配下にあります。
