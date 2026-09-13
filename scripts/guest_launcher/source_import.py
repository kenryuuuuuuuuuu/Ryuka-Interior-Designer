"""Preview and safely import the three Three.js building/electrical exports."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import paths

if str(paths.ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(paths.ROOT / "tests"))
import validate_electrical  # noqa: E402
import validate_openings  # noqa: E402

KINDS = ("openings", "interior-doors", "electrical")
FIELDS = {
    "openings": ("type", "level", "face", "offset", "wallX", "widthOverride", "heightOverride", "sillOverride", "hingeSide", "swingDir", "slideDir", "label", "status", "note"),
    "interior-doors": ("type", "floor", "orientation", "wallAt", "center", "x0", "z0", "x1", "z1", "widthOverride", "heightOverride", "hingeSide", "swingDir", "slideDir", "label", "status", "note"),
    "electrical": ("type", "level", "room", "wallAt", "orientation", "center", "side", "face", "offset", "wallX", "x", "z", "widthOverride", "depthOverride", "heightOverride", "mountHeightOverride", "label", "status", "note"),
}


def _read(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _index(items: list, origin: str) -> dict:
    by_id = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError(f"{origin}: 各項目に文字列のidが必要です。")
        if item["id"] in by_id:
            raise ValueError(f"{origin}: id {item['id']} が重複しています。")
        by_id[item["id"]] = item
    return by_id


@dataclass
class Report:
    kind: str
    candidate: Path
    source_sha: str
    candidate_sha: str
    changes: list
    counts: dict
    warnings: list
    error: str | None = None

    @property
    def ok(self):
        return self.error is None


def _validate(kind: str, candidate: dict, root: Path) -> list:
    data = root / "data"
    generated = root / "generated"
    house = _read(data / "house.json")
    if kind in ("openings", "interior-doors"):
        validate_openings.validate(
            _read(data / "door-catalog.json"), _read(data / "window-catalog.json"),
            candidate if kind == "openings" else _read(data / "openings.json"),
            candidate if kind == "interior-doors" else _read(data / "interior-doors.json"),
            house, _read(generated / "interior-walls.json")["walls"])
        if kind == "openings":
            live_ids = {i["id"] for i in candidate["items"]}
            decor = _read(data / "visual/guest-decor.json")
            missing = [i["id"] for i in decor["items"]
                       if i.get("openingId") and i["openingId"] not in live_ids]
            if missing:
                raise ValueError("装飾が参照する開口を削除できません: " + ", ".join(missing))
        return ["外部ドアはUE内覧の開閉操作対象外です。"] if kind == "openings" else []

    catalog = _read(data / "electrical-catalog.json")
    validate_electrical.validate(catalog, candidate, _read(data / "electrical-estimate.json"),
        house, _read(generated / "interior-walls.json")["walls"],
        _read(generated / "exterior-walls.json")["walls"])
    by_type = {t["type"]: t for t in catalog["types"]}
    ids = {i["id"] for i in candidate["items"]}
    unassigned = [i["id"] for i in candidate["items"]
                  if by_type[i["type"]]["category"] == "lighting"
                  and by_type[i["type"]]["mount"] != "exterior" and not i.get("room")]
    if unassigned:
        raise ValueError("室内照明に設置室がありません: " + ", ".join(unassigned))
    lighting = _read(data / "visual/lighting-settings.json")
    missing = {fid for group in lighting.get("groups", [])
               for fid in group.get("fixtureIds", []) if fid not in ids}
    if missing:
        raise ValueError("照明グループが参照する器具を削除できません: " + ", ".join(sorted(missing)))
    unsupported = lighting.get("unsupportedTypes", {})
    unresolved = [i["id"] for i in candidate["items"]
                  if by_type[i["type"]]["category"] == "lighting"
                  and i.get("room") and (i["type"] in unsupported
                  or i["type"] not in lighting.get("profiles", {}))]
    if unresolved:
        raise ValueError("UE未対応の室内照明です: " + ", ".join(unresolved))
    indoor_lights=sum(by_type[i['type']]['category']=='lighting' and bool(i.get('room'))
                      for i in candidate['items'])
    housings=len(candidate['items'])-indoor_lights
    return [f"UE更新後: 室内照明{indoor_lights}件は仮器具と発光、その他{housings}件は仮形状です。",
            "屋外照明はUEの発光処理対象外です。スイッチと照明の配線連動は未実装です。"]


def build_report(kind: str, candidate_path: Path, root: Path = paths.ROOT) -> Report:
    if kind not in KINDS:
        raise ValueError("取込対象は openings / interior-doors / electrical の3種類です。")
    candidate_path = Path(candidate_path)
    source = root / "data" / (kind + ".json")
    try:
        doc = _read(candidate_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"JSONを読めません: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schemaVersion") != "1.0.0" or doc.get("units") != "m" or not isinstance(doc.get("items"), list):
        raise ValueError(f"{kind}.json の形式ではありません（schemaVersion 1.0.0 / units m / items配列）。")
    current = _read(source)
    new = _index(doc["items"], "候補")
    old = _index(current["items"], "正本")
    changes = []
    for item_id in sorted(set(new) | set(old)):
        if item_id not in old:
            change = "追加"
            fields = [(f, None, new[item_id].get(f)) for f in FIELDS[kind] if f in new[item_id]]
        elif item_id not in new:
            change = "削除"
            fields = []
        else:
            fields = [(f, old[item_id].get(f), new[item_id].get(f))
                      for f in sorted(set(old[item_id]) | set(new[item_id]))
                      if old[item_id].get(f) != new[item_id].get(f)]
            if not fields:
                continue
            change = "変更"
        loss = [f for f in ("note", "status")
                if item_id in old and old[item_id].get(f)
                and item_id in new and not new[item_id].get(f)]
        item = new.get(item_id, old.get(item_id))
        changes.append(dict(id=item_id, kind=change, label=item.get("label", ""),
            category=item.get("type", ""), fields=fields, provenanceLoss=loss))
    counts = {name: sum(c["kind"] == name for c in changes) for name in ("追加", "削除", "変更")}
    report = Report(kind, candidate_path, _sha(source), _sha(candidate_path), changes, counts, [])
    try:
        report.warnings = _validate(kind, doc, root)
    except (AssertionError, ValueError, KeyError, TypeError) as exc:
        report.error = str(exc) or "候補の検証に失敗しました。"
    return report


def apply(report: Report, root: Path = paths.ROOT) -> Path:
    """Recheck both SHA values, then replace one validated source and rebuild Web data."""
    source = root / "data" / (report.kind + ".json")
    if _sha(source) != report.source_sha or _sha(report.candidate) != report.candidate_sha:
        raise ValueError("差分確認後に正本または候補が変わりました。取込を開き直してください。")
    fresh = build_report(report.kind, report.candidate, root)
    if not fresh.ok:
        raise ValueError(fresh.error)
    paths.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = paths.BACKUP_DIR / f"{report.kind}-{datetime.now():%Y%m%d-%H%M%S-%f}.json"
    shutil.copy2(source, backup)
    tmp = source.with_suffix(".json.launcher-tmp")
    try:
        tmp.write_bytes(report.candidate.read_bytes())
        tmp.replace(source)
        result = subprocess.run(["node", str(root / "scripts/build-web-data.mjs")], cwd=root,
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode:
            raise RuntimeError("Webデータ再生成失敗: " + result.stdout + result.stderr)
    except Exception:
        shutil.copy2(backup, source)
        subprocess.run(["node", str(root / "scripts/build-web-data.mjs")], cwd=root,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
        raise
    finally:
        tmp.unlink(missing_ok=True)
    return backup
