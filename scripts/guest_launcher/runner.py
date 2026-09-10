"""サブプロセス実行の共通処理。

- 外部CLIは必ず引数配列で起動する（パスや案名をシェルコードへ連結しない）。
- 標準出力/標準エラーはログファイルへ、行単位で `on_line` へも渡す。
- 長時間処理はスレッドで回し、GUIを止めない。
"""
from __future__ import annotations

import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Sequence

from . import paths


def python_argv(script: Path, *args) -> list:
    """`python <repo script> ...` の引数配列。sys.executable を使う。"""
    return [sys.executable, str(Path(script))] + [str(a) for a in args]


def run_logged(argv: Sequence, log_path: Path, cwd: Optional[Path] = None,
               on_line: Optional[Callable[[str], None]] = None,
               timeout: Optional[float] = None, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """argv をそのまま起動（shell=False）。出力を log_path とコールバックへ流す。"""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    argv = [str(a) for a in argv]
    started = datetime.now()
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write(f"# {started.isoformat()}\n# {' '.join(argv)}\n\n")
        log.flush()
        proc = subprocess.Popen(argv, cwd=str(cwd or paths.ROOT), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                errors="replace", bufsize=1, env=env)
        try:
            for line in proc.stdout:
                log.write(line)
                log.flush()
                if on_line:
                    on_line(line.rstrip("\n"))
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise
    return subprocess.CompletedProcess(argv, proc.returncode)


class BackgroundJob:
    """1つの長時間処理をスレッドで回す。同じ `key` の二重起動を防ぐ。"""

    _active_keys: set = set()
    _lock = threading.Lock()

    def __init__(self, key: str, target: Callable, on_done: Optional[Callable] = None):
        self.key = key
        self._target = target
        self._on_done = on_done
        self.thread: Optional[threading.Thread] = None
        self.result = None
        self.error: Optional[BaseException] = None

    @classmethod
    def is_running(cls, key: str) -> bool:
        with cls._lock:
            return key in cls._active_keys

    def start(self) -> bool:
        with BackgroundJob._lock:
            if self.key in BackgroundJob._active_keys:
                return False
            BackgroundJob._active_keys.add(self.key)
        self.thread = threading.Thread(target=self._run, name=f"job:{self.key}", daemon=True)
        self.thread.start()
        return True

    def _run(self):
        try:
            self.result = self._target()
        except BaseException as e:  # noqa: BLE001 - surfaced to on_done
            self.error = e
        finally:
            with BackgroundJob._lock:
                BackgroundJob._active_keys.discard(self.key)
            if self._on_done:
                self._on_done(self)
