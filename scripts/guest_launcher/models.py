"""生成済みguestプロジェクトの検出・検証・現行選択。

「最新完成版」を日付やディレクトリ名だけで決めない。候補は
`import-verification.json` の scope と取込成功、`walkthrough-verification.json`
の構築結果を実際に確認する。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import paths


@dataclass
class ModelInfo:
    path: Path
    valid: bool
    scopeId: Optional[str] = None
    importVerified: bool = False
    walkthroughConfigured: bool = False
    walkthroughRuntimeVerified: bool = False
    meshCount: Optional[int] = None
    savedStateSchema: Optional[str] = None
    savedStateMtime: Optional[str] = None
    updatedAt: Optional[str] = None          # newest of the project's own generated files
    reasons: list = None                     # why not valid / caveats (Japanese)

    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []

    @property
    def label(self) -> str:
        return paths.to_repo_relative(self.path)


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def inspect_project(project_dir: Path) -> ModelInfo:
    """1つの候補ディレクトリを検証する。GUIのモデル選択・現行モデル表示に使う。"""
    project_dir = Path(project_dir).resolve()
    info = ModelInfo(path=project_dir, valid=False)
    reasons = info.reasons

    uproject = project_dir / "RyukaInterior.uproject"
    if not uproject.is_file():
        reasons.append("RyukaInterior.uproject がありません。")
        return info

    iv_path = project_dir / "import-verification.json"
    if not iv_path.is_file():
        reasons.append("import-verification.json がありません（取込が完了していません）。")
        return info
    try:
        iv = _read(iv_path)
    except (json.JSONDecodeError, OSError) as e:
        reasons.append(f"import-verification.json を読めません（{e}）。")
        return info

    info.scopeId = iv.get("scopeId")
    info.importVerified = bool(iv.get("unrealImportVerified"))
    info.meshCount = iv.get("meshes")
    if not info.importVerified:
        reasons.append("取込が成功として記録されていません（unrealImportVerified が真ではありません）。")
    if info.scopeId != "guest":
        reasons.append(f"scope が guest ではありません（{info.scopeId}）。ゲスト試用版の対象は guest です。")

    wv_path = project_dir / "walkthrough-verification.json"
    if wv_path.is_file():
        try:
            wv = _read(wv_path)
            info.walkthroughConfigured = bool(wv.get("configured"))
            info.walkthroughRuntimeVerified = bool(wv.get("runtimeVerified"))
        except (json.JSONDecodeError, OSError):
            reasons.append("walkthrough-verification.json を読めません。")
    if not info.walkthroughConfigured:
        reasons.append("内覧（walkthrough）が構築されていません。enable-unreal-walkthrough.py が未実行です。")

    saved = _latest_saved_state(project_dir)
    if saved is not None:
        info.savedStateMtime = datetime.fromtimestamp(saved.stat().st_mtime).astimezone().isoformat()
        try:
            info.savedStateSchema = _read(saved).get("schemaVersion")
        except (json.JSONDecodeError, OSError):
            info.savedStateSchema = None

    newest = _newest_generated_mtime(project_dir)
    if newest:
        info.updatedAt = datetime.fromtimestamp(newest).astimezone().isoformat()

    info.valid = (info.importVerified and info.scopeId == "guest" and info.walkthroughConfigured)
    return info


def _latest_saved_state(project_dir: Path) -> Optional[Path]:
    """編集側 study-state.json と内覧のF5保存 walkthrough-state.json の新しい方。
    mid-recovery（.bak あり・現行保存なし）は None を返す（案内は呼び出し側）。"""
    editor = project_dir / "study-state.json"
    runtime = project_dir / "Saved/walkthrough-state.json"
    if not runtime.exists() and (project_dir / "Saved/walkthrough-state.json.bak").exists():
        return None
    candidates = [p for p in (editor, runtime) if p.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _newest_generated_mtime(project_dir: Path) -> Optional[float]:
    times = []
    for name in ("import-verification.json", "walkthrough-verification.json", "study-state.json",
                 "Content/Generated/House.umap"):
        p = project_dir / name
        if p.is_file():
            times.append(p.stat().st_mtime)
    return max(times) if times else None


def detect_candidates(extra_dirs: Optional[list] = None) -> list:
    """初回セットアップ用：build/ 直下の候補を検証して返す（新しい順）。
    有効なものだけでなく理由付きで無効なものも返し、GUIが選ばせる。"""
    seen = set()
    out = []
    search = []
    build = paths.ROOT / "build"
    if build.is_dir():
        for child in build.iterdir():
            if not child.is_dir():
                continue
            if (child / "RyukaInterior.uproject").is_file():
                search.append(child)
            ue_sub = child / "ue"
            if (ue_sub / "RyukaInterior.uproject").is_file():
                search.append(ue_sub)
    for d in (extra_dirs or []):
        search.append(Path(d))
    for d in search:
        key = str(Path(d).resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(inspect_project(d))
    out.sort(key=lambda m: (m.valid, m.updatedAt or ""), reverse=True)
    return out
