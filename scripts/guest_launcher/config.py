"""git除外のローカル設定（機械固有パス・選択中モデル・登録モデル）。

`build/launcher/config.json`（`.gitignore` の `build/` 配下）に保存する。
モデル参照は可能ならワークツリー相対（paths.to_repo_relative）で持ち、
再起動後に選択と登録を復元できるようにする。
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from . import paths

SCHEMA_VERSION = "1.0.0"


@dataclass
class LauncherConfig:
    schemaVersion: str = SCHEMA_VERSION
    enginePath: str = str(paths.DEFAULT_ENGINE)
    blenderPath: str = str(paths.DEFAULT_BLENDER)
    cachePath: str = str(paths.DEFAULT_CACHE)
    entryMode: str = "resume"
    currentModel: Optional[str] = None          # repo-relative or absolute path to a UE project dir
    registeredModels: list = field(default_factory=list)   # list[{"path": str, "label": str, "registeredAt": str}]
    lastUpdateOutput: Optional[str] = None       # repo-relative path of the newest refresh output dir

    # --- machine paths as Path objects ---
    @property
    def engine(self) -> Path:
        return Path(self.enginePath)

    @property
    def blender(self) -> Path:
        return Path(self.blenderPath)

    @property
    def cache(self) -> Path:
        return Path(self.cachePath)

    def current_model_path(self) -> Optional[Path]:
        return paths.from_repo_relative(self.currentModel) if self.currentModel else None

    def registered_model_paths(self) -> list:
        return [paths.from_repo_relative(m["path"]) for m in self.registeredModels]

    def set_current_model(self, project_dir: Path) -> None:
        rel = paths.to_repo_relative(project_dir)
        self.currentModel = rel
        if not any(m["path"] == rel for m in self.registeredModels):
            self.register_model(project_dir)

    def register_model(self, project_dir: Path, label: str = "") -> None:
        from datetime import datetime
        rel = paths.to_repo_relative(project_dir)
        self.registeredModels = [m for m in self.registeredModels if m["path"] != rel]
        self.registeredModels.append(dict(path=rel, label=label or Path(rel).name,
                                          registeredAt=datetime.now().astimezone().isoformat()))

    def unregister_model(self, project_dir: Path) -> None:
        rel = paths.to_repo_relative(project_dir)
        self.registeredModels = [m for m in self.registeredModels if m["path"] != rel]
        if self.currentModel == rel:
            self.currentModel = None

    # --- dependency presence ---
    def missing_dependencies(self) -> list:
        """人間可読の日本語で、足りない依存実行ファイルと次の操作を返す。"""
        problems = []
        if not paths.unreal_cmd(self.engine).is_file():
            problems.append(f"Unreal Engine が見つかりません（{self.enginePath}）。「設定」でエンジンの場所を指定してください。")
        if not self.blender.is_file():
            problems.append(f"Blender が見つかりません（{self.blenderPath}）。「設定」でBlenderの場所を指定してください。")
        if len(str(self.cache.resolve())) > 119:
            problems.append(f"cache のパスが長すぎます（{self.cachePath}）。119文字以内の場所を「設定」で指定してください。")
        return problems


def load() -> LauncherConfig:
    if paths.CONFIG_PATH.is_file():
        try:
            raw = json.loads(paths.CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raw = {}
    else:
        raw = {}
    known = {f for f in LauncherConfig().__dict__}
    return LauncherConfig(**{k: v for k, v in raw.items() if k in known})


def save(config: LauncherConfig) -> None:
    paths.ensure_dirs()
    config.schemaVersion = SCHEMA_VERSION
    tmp = paths.CONFIG_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(paths.CONFIG_PATH)
