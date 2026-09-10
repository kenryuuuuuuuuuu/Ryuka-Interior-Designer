"""モデル更新（既存 refresh-visual-study.py を工程表示付きで実行）。

- 正本取込 ≠ UE反映。取込後は「モデル更新が必要」と区別する。
- 更新は 選択モデルを previous、scope=guest、新しい出力ディレクトリで実行。
- 既定で重い全案ギャラリー（--gallery）は付けない。前モデル・案を上書き/削除しない。
- 工程名・実行中/成功/失敗・ログ・経過時間を表示。根拠のない進捗率は出さない。
- 終了コード0 かつ refresh の status: complete かつ 取込/転送/内覧構築の成功を
  確認してから、現行モデルを新モデルへ切り替える。失敗時は前モデルを維持。
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from . import config as _config
from . import models, paths, runner

_SCRIPTS = paths.ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import source_changes  # noqa: E402


def plan_update(model_dir: Path, root: Path = paths.ROOT) -> dict:
    """選択モデルの生成入力と現在の正本の差分。更新が必要かの判定に使う。

    `source_changes.compare` はゲスト向け refresh が使うのと同じ仕組み
    （rooms/furniture/catalog/照明設定の追加・削除・変更＋参照切れ）。"""
    model_dir = Path(model_dir)
    result = dict(updateNeeded=False, changedSourceFiles=[], summary=None, issues=[], baselineStatus=None)
    manifest_path = model_dir / "SourcePackage/manifest.json"
    try:
        old_hashes = json.loads(manifest_path.read_text(encoding="utf-8-sig")).get("sourceHashes", {})
    except (OSError, json.JSONDecodeError):
        old_hashes = {}
    now_hashes = _current_source_hashes(root)
    changed = sorted(k for k in set(old_hashes) | set(now_hashes) if old_hashes.get(k) != now_hashes.get(k))
    result["changedSourceFiles"] = changed
    try:
        changes = source_changes.compare(model_dir, root)
        result["summary"] = source_changes.summarize(changes)
        result["issues"] = changes["issues"]
        result["baselineStatus"] = changes["baselineStatus"]
    except Exception as e:  # noqa: BLE001
        result["summary"] = dict(error=str(e))
    result["updateNeeded"] = bool(changed)
    return result


def _current_source_hashes(root: Path) -> dict:
    import hashlib
    out = {}
    for folder in ("data", "blender", "unreal", "scripts", "generated", "tests"):
        base = root / folder
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in (".json", ".py", ".mjs", ".js", ".hlsl", ".ini", ".uproject", ".cpp", ".h", ".cs"):
                out[path.relative_to(root).as_posix()] = hashlib.sha256(
                    path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return out


@dataclass
class UpdateOutcome:
    ok: bool
    outputDir: Optional[str]
    newModelDir: Optional[str]       # <output>/ue when the run fully succeeded
    status: str                      # refresh.json status, or "failed"/"error"
    failedStep: Optional[str]
    reason: Optional[str]
    refreshJson: Optional[str]
    elapsedSec: float = 0.0
    steps: list = field(default_factory=list)


def update_output_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return paths.ROOT / "build" / f"W08-G-update-{stamp}"


def run_update(cfg: _config.LauncherConfig, model_dir: Path, output_dir: Path,
               on_line: Optional[Callable[[str], None]] = None,
               on_step: Optional[Callable[[list], None]] = None) -> UpdateOutcome:
    """1回の更新を最後まで実行する（スレッドから呼ぶ。ここではブロックする）。"""
    model_dir = Path(model_dir).resolve()
    output_dir = Path(output_dir).resolve()
    started = time.monotonic()
    log_path = paths.LOG_DIR / f"{output_dir.name}.log"

    argv = runner.python_argv(
        _SCRIPTS / "refresh-visual-study.py",
        "--previous", model_dir,
        "--output", output_dir,
        "--scope", "guest",
        "--blender", cfg.blender,
        "--engine", cfg.engine,
        "--cache", cfg.cache,
    )

    def _emit_steps():
        if on_step:
            on_step(_read_steps(output_dir))

    def _line(text: str):
        if on_line:
            on_line(text)
        if text.strip() in {"01-source-check", "01b-source-changes", "01c-surface-registry",
                            "02-blender", "03-unreal", "04-walkthrough", "04-state-check", "05-comparison"}:
            _emit_steps()

    try:
        proc = runner.run_logged(argv, log_path, cwd=paths.ROOT, on_line=_line)
    except Exception as e:  # noqa: BLE001
        return UpdateOutcome(ok=False, outputDir=str(output_dir), newModelDir=None, status="error",
                             failedStep=None, reason=str(e), refreshJson=None,
                             elapsedSec=time.monotonic() - started, steps=_read_steps(output_dir))

    elapsed = time.monotonic() - started
    refresh_json = output_dir / "refresh.json"
    report = {}
    if refresh_json.is_file():
        try:
            report = json.loads(refresh_json.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            report = {}
    steps = report.get("steps", [])
    _emit_steps()
    failed_step = next((s["name"] for s in steps if s.get("status") == "failed"), None)

    if proc.returncode != 0 or report.get("status") != "complete":
        return UpdateOutcome(ok=False, outputDir=str(output_dir), newModelDir=None,
                             status=report.get("status", "failed"), failedStep=failed_step,
                             reason=report.get("error") or f"refresh 終了コード {proc.returncode}",
                             refreshJson=str(refresh_json) if refresh_json.is_file() else None,
                             elapsedSec=elapsed, steps=steps)

    # status: complete でも、切替の前に実機の成功記録を独立に確認する。
    new_model = output_dir / "ue"
    info = models.inspect_project(new_model)
    if not info.valid:
        return UpdateOutcome(ok=False, outputDir=str(output_dir), newModelDir=None, status="incomplete",
                             failedStep="post-check", reason="；".join(info.reasons) or "更新後モデルの検証に失敗しました。",
                             refreshJson=str(refresh_json), elapsedSec=elapsed, steps=steps)
    transfer = output_dir / "ue" / "state-transfer-verification.json"
    try:
        t = json.loads(transfer.read_text(encoding="utf-8-sig"))
        if not (t.get("statePreserved") and t.get("geometryVerified")):
            raise ValueError("状態/幾何の転送検証が真ではありません。")
    except (OSError, json.JSONDecodeError, ValueError) as e:
        return UpdateOutcome(ok=False, outputDir=str(output_dir), newModelDir=None, status="incomplete",
                             failedStep="post-check", reason=f"転送検証を確認できません（{e}）。",
                             refreshJson=str(refresh_json), elapsedSec=elapsed, steps=steps)

    return UpdateOutcome(ok=True, outputDir=str(output_dir), newModelDir=str(new_model), status="complete",
                         failedStep=None, reason=None, refreshJson=str(refresh_json),
                         elapsedSec=elapsed, steps=steps)


def _read_steps(output_dir: Path) -> list:
    p = Path(output_dir) / "refresh.json"
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8-sig")).get("steps", [])
    except json.JSONDecodeError:
        return []
