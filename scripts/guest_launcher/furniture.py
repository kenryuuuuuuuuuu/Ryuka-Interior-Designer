"""Three.js「furniture.jsonを書き出す」の出力を、検証してから正本へ反映する。

- 任意の house/電気/建具JSONの汎用一括上書きはしない。furniture.json だけ。
- 検証前に現行正本を上書きしない。
- 全館家具を含む書出しなので、ゲスト外の変更も隠さず全件を差分表示する。
- 削除件数を明示。note/status を落とす取込を黙って通さない。
- 反映時：直前正本を git 除外領域にコピー → 安全に置換 → Web生成データ再生成。
  失敗時は「正本反映済み／Web生成失敗」等の実状態を返す（途中を完了にしない）。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import paths

_TESTS = paths.ROOT / "tests"
if str(_TESTS) not in sys.path:
    sys.path.insert(0, str(_TESTS))
import validate_furniture as _vf  # noqa: E402  (repo validator, refactored to expose validate())

FURNITURE_JSON = paths.ROOT / "data" / "furniture.json"
CATALOG_JSON = paths.ROOT / "data" / "furniture-catalog.json"
HOUSE_JSON = paths.ROOT / "data" / "house.json"
ASSET_BINDINGS_JSON = paths.ROOT / "data" / "visual" / "asset-bindings.json"
GUEST_SCOPE_ROOMS = {
    "room-1f-01", "room-1f-02", "room-1f-03", "room-1f-04",
    "room-1f-05", "room-1f-06", "room-1f-23", "room-1f-24",
}
_TRACKED_FIELDS = ("type", "room", "label", "level", "x", "z", "rotation",
                   "widthOverride", "depthOverride", "heightOverride", "elevation", "status", "note")


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass
class ItemChange:
    id: str
    kind: str                 # "added" | "removed" | "modified"
    inGuestScope: bool
    label: Optional[str] = None
    room: Optional[str] = None
    fields: list = field(default_factory=list)   # for "modified": [{field, before, after}]
    provenanceLoss: list = field(default_factory=list)   # dropped note/status etc.


@dataclass
class CandidateReport:
    sourcePath: str
    ok: bool                          # candidate is structurally readable AND passes validation
    validationError: Optional[str]    # first blocking reason (Japanese), else None
    changes: list = field(default_factory=list)          # list[ItemChange]
    counts: dict = field(default_factory=dict)           # added/removed/modified, and guest/other splits
    assetBindingWarnings: list = field(default_factory=list)
    totalItems: int = 0
    # W08-G review R2: the exact bytes the operator saw the diff against. The
    # apply step refuses if data/furniture.json OR the candidate file changed
    # since this report was built, and sends the operator back to re-preview.
    sourceSha: Optional[str] = None
    candidateSha: Optional[str] = None

    @property
    def has_changes(self) -> bool:
        return bool(self.changes)


def read_candidate(path: Path) -> dict:
    """候補ファイルを読む。furniture.json の形（schemaVersion 1.0.0 / items 配列）で
    なければ ValueError。汎用取込を避けるため形を先に確認する。"""
    path = Path(path)
    try:
        doc = _read(path)
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"ファイルを読めません（{e}）。ブラウザの「furniture.jsonを書き出す」で保存したファイルを選んでください。")
    if not isinstance(doc, dict) or doc.get("schemaVersion") != "1.0.0" or doc.get("units") != "m" \
            or not isinstance(doc.get("items"), list):
        raise ValueError("furniture.json の形式ではありません（schemaVersion 1.0.0 / units m / items 配列）。"
                         "ブラウザの「furniture.jsonを書き出す」の出力を選んでください。house/電気/建具のJSONは取り込めません。")
    return doc


def _diff_item(before: dict, after: dict) -> list:
    rows = []
    for f in _TRACKED_FIELDS:
        b = before.get(f)
        a = after.get(f)
        if b != a:
            rows.append(dict(field=f, before=b, after=a))
    return rows


def build_report(candidate_path: Path, root: Path = paths.ROOT) -> CandidateReport:
    """候補と現行正本の差分＋検証結果をまとめる。正本は一切変更しない。"""
    candidate_path = Path(candidate_path)
    candidate = read_candidate(candidate_path)
    source_path = root / "data" / "furniture.json"
    current = _read(source_path)
    catalog = _read(root / "data" / "furniture-catalog.json")
    house = _read(root / "data" / "house.json")

    report = CandidateReport(sourcePath=str(candidate_path), ok=False, validationError=None,
                             totalItems=len(candidate["items"]),
                             sourceSha=_sha(source_path), candidateSha=_sha(candidate_path))

    cur_by_id = {i["id"]: i for i in current["items"]}
    new_by_id = {}
    for i in candidate["items"]:
        if i.get("id") in new_by_id:
            report.validationError = f"候補内で id「{i.get('id')}」が重複しています。"
            return report
        new_by_id[i["id"]] = i

    def scope_of(item):
        return item.get("room") in GUEST_SCOPE_ROOMS

    for id_ in sorted(set(new_by_id) - set(cur_by_id)):
        it = new_by_id[id_]
        report.changes.append(ItemChange(id=id_, kind="added", inGuestScope=scope_of(it),
                                         label=it.get("label"), room=it.get("room"),
                                         fields=[dict(field=f, before=None, after=it.get(f))
                                                 for f in _TRACKED_FIELDS if f in it]))
    for id_ in sorted(set(cur_by_id) - set(new_by_id)):
        it = cur_by_id[id_]
        report.changes.append(ItemChange(id=id_, kind="removed", inGuestScope=scope_of(it),
                                         label=it.get("label"), room=it.get("room")))
    for id_ in sorted(set(cur_by_id) & set(new_by_id)):
        rows = _diff_item(cur_by_id[id_], new_by_id[id_])
        if not rows:
            continue
        loss = []
        for f in ("status", "note"):
            if cur_by_id[id_].get(f) and not new_by_id[id_].get(f):
                loss.append(f)
        report.changes.append(ItemChange(id=id_, kind="modified", inGuestScope=scope_of(new_by_id[id_]),
                                         label=new_by_id[id_].get("label") or cur_by_id[id_].get("label"),
                                         room=new_by_id[id_].get("room"), fields=rows, provenanceLoss=loss))

    added = [c for c in report.changes if c.kind == "added"]
    removed = [c for c in report.changes if c.kind == "removed"]
    modified = [c for c in report.changes if c.kind == "modified"]
    report.counts = dict(
        added=len(added), removed=len(removed), modified=len(modified),
        guestScope=sum(1 for c in report.changes if c.inGuestScope),
        otherScope=sum(1 for c in report.changes if not c.inGuestScope),
        provenanceLoss=sum(1 for c in report.changes if c.provenanceLoss),
    )

    # 既存 validator を候補データへ適用（ID重複・未知型・不正寸法/室参照・階の食い違い）。
    try:
        _vf.validate(catalog, candidate, house)
    except AssertionError as e:
        report.validationError = str(e) or "検証に失敗しました。"
        return report
    except (KeyError, TypeError) as e:
        report.validationError = f"候補データの構造が不正です（{e}）。"
        return report

    # asset-binding との整合を確認可能な範囲で事前検出（更新成功前に未対応型を対応済みに見せない）。
    report.assetBindingWarnings = _asset_binding_warnings(candidate, root)

    report.ok = True
    return report


def _asset_binding_warnings(candidate: dict, root: Path) -> list:
    """asset-bindings.json が参照する家具が候補から消える／型が変わる場合の注意。
    候補検証の軽量チェックであり、正本変更前に提示する。"""
    warnings = []
    try:
        bindings = _read(root / "data" / "visual" / "asset-bindings.json").get("bindings", [])
    except (json.JSONDecodeError, OSError):
        return warnings
    by_id = {i["id"]: i for i in candidate["items"]}
    catalog = _read(root / "data" / "furniture-catalog.json")
    shape_by_type = {t["type"]: t["shape"] for t in catalog["types"]}
    # assetId -> expected catalog shape (from furniture_assets.validate_bindings' registry)
    expected_shape = {"sofa-timber-v1": "sofa", "round-table-v1": "roundTable", "chair-timber-v1": "timberChair",
                      "toilet-v1": "toilet", "vanity-v1": "vanity", "washer-v1": "boxAppliance", "bathtub-v1": "bathtub"}
    for b in bindings:
        fid = b.get("furnitureId")
        aid = b.get("assetId")
        if fid not in by_id:
            warnings.append(f"asset-bindings.json の {aid} が参照する家具 {fid} が候補にありません（取込後は不整合になります）。")
            continue
        want = expected_shape.get(aid)
        got = shape_by_type.get(by_id[fid].get("type"))
        if want and got and want != got:
            warnings.append(f"家具 {fid} の型が {by_id[fid].get('type')}（shape {got}）に変わり、"
                            f"asset-bindings.json の {aid}（shape {want} 想定）と合いません。")
    return warnings


@dataclass
class ApplyResult:
    applied: bool                 # data/furniture.json was replaced
    webDataRegenerated: bool
    backupPath: Optional[str]
    webLog: Optional[str]
    message: str                  # human-readable real state (Japanese)


def apply_candidate(candidate_path: Path, root: Path = paths.ROOT,
                    backup_dir: Path = paths.BACKUP_DIR,
                    expected_source_sha: Optional[str] = None,
                    expected_candidate_sha: Optional[str] = None) -> ApplyResult:
    """検証済み候補を正本へ反映する。build_report() が ok を返した候補だけに使う。

    `expected_source_sha` / `expected_candidate_sha` を渡すと、差分確認時から
    `data/furniture.json` か候補ファイルが変わっていないかを反映直前に照合する
    （review R2：見ていない内容を書き込まない）。どちらか変わっていれば ValueError で
    止め、再確認へ戻す。

    手順：sha照合 → 直前正本を backup_dir へコピー → data/furniture.json を置換 →
    `node scripts/build-web-data.mjs`（--write）で generated/ を再生成。
    どこで失敗しても、その時点までの実状態を ApplyResult に入れて返す。
    """
    candidate_path = Path(candidate_path)
    source_path = root / "data" / "furniture.json"

    if expected_source_sha is not None and _sha(source_path) != expected_source_sha:
        raise ValueError("差分を確認したあとで data/furniture.json が変わりました（別の取込や編集の可能性）。"
                         "もう一度「家具JSON取込」で差分を確認してください。反映は中止しました。")
    if expected_candidate_sha is not None and _sha(candidate_path) != expected_candidate_sha:
        raise ValueError("差分を確認したあとで候補ファイルが変わりました（同じ場所へ再書出しされた可能性）。"
                         "もう一度「家具JSON取込」で差分を確認してください。反映は中止しました。")

    report = build_report(candidate_path, root)
    if not report.ok:
        raise ValueError(report.validationError or "候補が検証を通っていません。")

    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = backup_dir / f"furniture-{stamp}.json"
    target = root / "data" / "furniture.json"
    shutil.copy2(target, backup)

    # 検証済み候補を正規化して書く（読んだ dict を indent=2 で。schemaVersion/units/note/items のみ）。
    doc = read_candidate(candidate_path)
    keep = {k: doc[k] for k in ("schemaVersion", "units", "note", "items") if k in doc}
    tmp = target.with_suffix(".json.launcher-tmp")
    tmp.write_text(json.dumps(keep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(target)

    web_log = paths.LOG_DIR / f"web-data-{stamp}.log"
    web_log.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(["node", str(root / "scripts/build-web-data.mjs")],
                              cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace")
        web_log.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
        if proc.returncode != 0:
            return ApplyResult(applied=True, webDataRegenerated=False, backupPath=str(backup),
                               webLog=str(web_log),
                               message="正本（data/furniture.json）は反映済みですが、Web生成データの再生成に失敗しました。"
                                       f"ログ: {web_log}。node の確認後、`node scripts/build-web-data.mjs` を手動実行してください。")
    except FileNotFoundError:
        return ApplyResult(applied=True, webDataRegenerated=False, backupPath=str(backup), webLog=None,
                           message="正本は反映済みですが、node が見つからず Web生成データを再生成できませんでした。"
                                   "node を導入後、`node scripts/build-web-data.mjs` を実行してください。")

    return ApplyResult(applied=True, webDataRegenerated=True, backupPath=str(backup), webLog=str(web_log),
                       message="正本（data/furniture.json）を反映し、Web生成データを再生成しました。"
                               "UEモデルへ反映するには「モデル更新」が必要です（取込＝更新ではありません）。")


def restore_backup(backup_path: Path, root: Path = paths.ROOT) -> None:
    """apply_candidate() が残した復元用コピーで data/furniture.json を戻す。"""
    shutil.copy2(Path(backup_path), root / "data" / "furniture.json")
