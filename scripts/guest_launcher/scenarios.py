"""保存済み案の一覧と「現在の保存を名前付き案にする」。

保存元は F5／エディタの最新の有効な保存を既存の共通処理
（refresh_inputs.retained_inputs 経由の save_scenario_package）が選ぶ。
未保存の画面状態は案にできない。既存案を黙って上書きしない
（名前から slug を作り、衝突したら -2, -3 …）。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import paths

_SCRIPTS = paths.ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from refresh_inputs import save_scenario_package  # noqa: E402

# list-study-scenarios.py はハイフン名なので importlib で読む。
_spec = importlib.util.spec_from_file_location("list_study_scenarios", _SCRIPTS / "list-study-scenarios.py")
_lss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lss)


def list_scenarios(root: Path = paths.SCENARIOS_DIR) -> list:
    """[{id,name,createdAt,scope,rooms,note,path}] を新しい順で返す。壊れた案は errors に。"""
    root = Path(root)
    rows, errors = [], []
    if not root.is_dir():
        return []
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and (p / "scenario.json").is_file()):
        try:
            desc = _lss.describe(folder)
            scenario = json.loads((folder / "scenario.json").read_text(encoding="utf-8-sig"))
            desc["note"] = scenario.get("note", "")
            desc["path"] = str(folder)
            desc["stateSource"] = (scenario.get("origin") or {}).get("stateSource")
            rows.append(desc)
        except Exception as e:  # noqa: BLE001
            errors.append(dict(path=str(folder), error=str(e)))
    rows.sort(key=lambda r: r.get("createdAt") or "", reverse=True)
    for e in errors:
        e["broken"] = True
    return rows + errors


def _slug(name: str) -> str:
    s = "".join(c if c.isalnum() else "-" for c in name).strip("-")
    return s or "scenario"


def save_current_as_scenario(project_dir: Path, name: str, note: str = "",
                             root: Path = paths.SCENARIOS_DIR) -> dict:
    """project_dir の最新の有効な保存を、name の案として build/scenarios/ に残す。

    save_scenario_package() が全ての失敗理由（未保存・mid-recovery・schema不一致 …）を
    ValueError で返す。ここでは握りつぶさず、そのまま呼び出し側へ渡す。"""
    name = (name or "").strip()
    if not name:
        raise ValueError("案の名前を入力してください。")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    slug = _slug(name)
    output = root / slug
    n = 1
    while output.exists():
        n += 1
        output = root / f"{slug}-{n}"
    scenario, out_path = save_scenario_package(Path(project_dir), name, note, output)
    return dict(id=scenario["id"], name=scenario["name"], note=scenario.get("note", ""),
               path=str(out_path), createdAt=scenario["createdAt"],
               scopeId=scenario.get("scopeId"), roomIds=scenario.get("roomIds", []),
               stateSource=(scenario.get("origin") or {}).get("stateSource"))


def open_editor_hint() -> str:
    """案の読込／比較は既存のUEメニュー（ツール → 内装比較 → 案の読込／比較A・B）または
    refresh --scenario で行う、という導線文言。GUIから開く先を一覧表示だけで終わらせない。"""
    return ("案の読込・比較：内覧を「編集・比較」で開き、UEの『ツール → 内装比較』から\n"
            "「案の読込」「比較A」「比較B」を選びます。CLIなら\n"
            "  python scripts/refresh-visual-study.py --previous <モデル> --scenario <案フォルダ> --output <新規> ...\n"
            "で案の比較条件を現在の建物へ適用できます。")
