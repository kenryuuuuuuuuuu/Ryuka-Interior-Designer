"""通常の「内覧」と「編集・比較」の起動。

- 通常の内覧は既存の描画付き walkthrough（launch-unreal-walkthrough.py、--smoke なし）。
- テスト用 smoke / verify / 初期状態復元スクリプトは通常起動に流用しない。
- 保存した F5 状態を基準状態で上書きしない（このモジュールは study-state.json を書かない）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Optional

from . import config as _config
from . import paths, runner, models

_SCRIPTS = paths.ROOT / "scripts"


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def can_launch(model_dir: Path) -> Optional[str]:
    """起動できない理由（日本語）。問題なければ None。"""
    model_dir = Path(model_dir)
    info = models.inspect_project(model_dir)
    if not info.valid:
        return "；".join(info.reasons)
    wv = model_dir / "walkthrough-verification.json"
    if not wv.is_file():
        return "内覧が構築されていません。モデルを更新するか、別のモデルを選んでください。"
    try:
        if not _read(wv).get("configured"):
            return "内覧が構築されていません（configured が真ではありません）。"
    except (OSError, json.JSONDecodeError):
        return "walkthrough-verification.json を読めません。"
    return None


def launch_walkthrough(cfg: _config.LauncherConfig, model_dir: Path,
                       on_line: Optional[Callable[[str], None]] = None) -> runner.subprocess.CompletedProcess:
    """描画付き内覧を起動する（ウィンドウが開く。閉じるまでブロックするのでスレッドから呼ぶ）。"""
    model_dir = Path(model_dir).resolve()
    problem = can_launch(model_dir)
    if problem:
        raise RuntimeError(problem)
    entry = getattr(cfg, "entryMode", "resume")
    if entry not in entry_options(model_dir):
        raise ValueError("この開始位置は使えません。モデルを更新するか前回の続きを選んでください。")
    argv = runner.python_argv(
        _SCRIPTS / "launch-unreal-walkthrough.py",
        "--project", model_dir, "--engine", cfg.engine, "--cache", cfg.cache,
        "--entry", entry,
    )  # --smoke なし＝通常の描画付き内覧
    log_path = paths.LOG_DIR / f"walkthrough-{model_dir.name}.log"
    return runner.run_logged(argv, log_path, cwd=paths.ROOT, on_line=on_line)


def open_editor(cfg: _config.LauncherConfig, model_dir: Path,
                on_line: Optional[Callable[[str], None]] = None) -> runner.subprocess.CompletedProcess:
    """UEエディタでプロジェクトを開く（面編集・詳細比較はエディタ側の『ツール → 内装比較』）。"""
    model_dir = Path(model_dir).resolve()
    uproject = model_dir / "RyukaInterior.uproject"
    if not uproject.is_file():
        raise RuntimeError("RyukaInterior.uproject が見つかりません。")
    editor = Path(cfg.engine) / "Engine/Binaries/Win64/UnrealEditor.exe"
    if not editor.is_file():
        raise RuntimeError(f"UnrealEditor.exe が見つかりません（{editor}）。「設定」でエンジンの場所を確認してください。")
    argv = [str(editor), str(uproject),
            "-DDC=InstalledNoZenLocalFallback", "-LocalDataCachePath=" + str(Path(cfg.cache).resolve())]
    log_path = paths.LOG_DIR / f"editor-{model_dir.name}.log"
    return runner.run_logged(argv, log_path, cwd=paths.ROOT, on_line=on_line)


WALKTHROUGH_KEYS = (
    "WASD：歩く／マウス：見回す／Tab：カーソル表示",
    "1・2・3：対象室の仕上げ切替（選択モデルの対象室に適用）",
    "4・5：太陽高度（手動角度・未校正）",
    "E：近くの扉の開閉",
    "F5：今の仕上げ・視点・扉・太陽条件をこのモデルに保存",
    "F9：最後に保存した状態へ復元",
    "保存してから終了・更新すること。更新は別のモデルを新しく作ります。",
)


ENTRY_LABELS = {"resume": "前回の続き", "home": "自宅入口", "guest": "ゲスト入口"}

def entry_options(model_dir):
    options=["resume"]
    try:
        doc=_read(Path(model_dir)/"walkthrough.json")
        rooms=set(doc['rooms'])
        if doc.get('launcherEntrySelection'):
            for mode,rid in [('home','room-1f-19'),('guest','room-1f-02')]:
                if rid in rooms:options.append(mode)
    except (OSError,ValueError,KeyError,TypeError):pass
    return options
