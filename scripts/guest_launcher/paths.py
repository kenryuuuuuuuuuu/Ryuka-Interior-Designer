"""ワークツリー基準のパス解決。起動時のcwdに依存しない。

このファイルは `<worktree>/scripts/guest_launcher/paths.py` なので、
`parents[2]` が常にワークツリのルート。GUIをどこから起動しても同じ。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# git除外領域（.gitignore の `build/`）にランチャーのローカル状態を置く。
LAUNCHER_DIR = ROOT / "build" / "launcher"
CONFIG_PATH = LAUNCHER_DIR / "config.json"
BACKUP_DIR = LAUNCHER_DIR / "backups"          # 正本反映前の復元用コピー
UPDATE_DIR = ROOT / "build"                    # refresh の出力先の親（新規ディレクトリを都度作る）
SCENARIOS_DIR = ROOT / "build" / "scenarios"   # 既存の save_scenario_package と同じ場所
RECORDS_DIR = LAUNCHER_DIR / "comparisons"     # 仕上げA/Bのローカル記録
LOG_DIR = LAUNCHER_DIR / "logs"

# 依存実行ファイルの既定の場所（この環境で確認済み）。config.json で上書き可能。
DEFAULT_ENGINE = Path("C:/Program Files/Epic Games/UE_5.8")
DEFAULT_BLENDER = Path("C:/Program Files/Blender Foundation/Blender 5.2/blender.exe")
DEFAULT_CACHE = Path("C:/UE_DDC/guest")


def ensure_dirs() -> None:
    for d in (LAUNCHER_DIR, BACKUP_DIR, SCENARIOS_DIR, RECORDS_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


def to_repo_relative(path: Path) -> str:
    """ROOT配下なら相対（POSIX）文字列、そうでなければ絶対文字列。
    設定ファイルに書くモデル参照を、可能な限りワークツリー相対にする。"""
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def from_repo_relative(text: str) -> Path:
    """to_repo_relative() の逆。相対文字列は ROOT 起点で解決する。"""
    p = Path(text)
    return p if p.is_absolute() else (ROOT / p).resolve()


def unreal_cmd(engine: Path) -> Path:
    return Path(engine) / "Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
