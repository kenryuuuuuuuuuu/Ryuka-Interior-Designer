"""仕上げA/Bの記録と、共有用コピーの出力。

- 記録：既存 compare-unreal-studies.py で対象室の仕上げ違い（既定 natural/warm）を
  固定カメラで撮り、画像とその画像を生成した条件（案名・対象室・視点・日時または
  手動太陽・露出・昼夜/点灯・仮仕様）を対応付けてローカルに残す。
  撮影失敗は完成画像として登録しない。比較元の案・モデル状態は変更しない。
- 共有用コピー：画像と必要な比較条件の許可リストだけで構成する。
  絶対パス・敷地座標・site.local.json・生ログ・元JSON一式はコピーしない。
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from . import config as _config
from . import paths, runner

_SCRIPTS = paths.ROOT / "scripts"

# 共有用に出してよい撮影条件のキー（許可リスト）。これ以外は共有コピーに含めない。
_SHARED_STATE_KEYS = ("schemaVersion", "scopeId", "activeRoomId", "activeLevel",
                      "camera", "azimuthDeg", "elevationDeg", "exposureEV100", "lighting", "roomStates")
# ネットへ出してはいけない語（共有コピーの最終チェックで文字列走査する）。
_FORBIDDEN_SUBSTRINGS = ("site.local.json", "site-context.json", "latitudeDeg", "longitudeDeg",
                         "C:\\", "C:/", "/Users/", "sourceHashes", "projectFingerprint",
                         "imageSHA256", "sha256", "SHA256")


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@dataclass
class ComparisonRecord:
    ok: bool
    recordDir: Optional[str]
    captureDir: Optional[str]
    name: str
    note: str
    images: list = field(default_factory=list)      # [{variant, image, conditions}]
    reason: Optional[str] = None


def records_root() -> Path:
    return paths.RECORDS_DIR


def record_finish_ab(cfg: _config.LauncherConfig, model_dir: Path, name: str, note: str = "",
                     variants=("natural", "warm"),
                     on_line: Optional[Callable[[str], None]] = None) -> ComparisonRecord:
    """model_dir の固定カメラで variants の仕上げ違いを撮り、条件付きで記録する。"""
    name = (name or "").strip()
    if not name:
        return ComparisonRecord(ok=False, recordDir=None, captureDir=None, name="", note=note,
                                reason="記録の名前を入力してください。")
    model_dir = Path(model_dir).resolve()
    info_iv = model_dir / "import-verification.json"
    if not info_iv.is_file() or not _read(info_iv).get("unrealImportVerified"):
        return ComparisonRecord(ok=False, recordDir=None, captureDir=None, name=name, note=note,
                                reason="検証済みのモデルではありません。先にモデルを更新・登録してください。")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    record_dir = paths.RECORDS_DIR / stamp
    capture_dir = record_dir / "capture"
    record_dir.mkdir(parents=True, exist_ok=True)
    log_path = paths.LOG_DIR / f"compare-{stamp}.log"

    argv = runner.python_argv(
        _SCRIPTS / "compare-unreal-studies.py",
        "--engine", cfg.engine, "--project", model_dir, "--cache", cfg.cache,
        "--output", capture_dir, "--variants", *variants,
        "--note", "実敷地・採用品番は確認待ちの仮条件です。",
    )
    try:
        proc = runner.run_logged(argv, log_path, cwd=paths.ROOT, on_line=on_line)
    except Exception as e:  # noqa: BLE001
        return ComparisonRecord(ok=False, recordDir=str(record_dir), captureDir=None, name=name, note=note,
                                reason=f"撮影の実行に失敗しました（{e}）。ログ: {log_path}")

    manifest = capture_dir / "manifest.json"
    if proc.returncode != 0 or not manifest.is_file():
        return ComparisonRecord(ok=False, recordDir=str(record_dir), captureDir=str(capture_dir), name=name, note=note,
                                reason=f"撮影に失敗しました（終了コード {proc.returncode}）。ログ: {log_path}")
    doc = _read(manifest)
    if doc.get("status") != "complete":
        return ComparisonRecord(ok=False, recordDir=str(record_dir), captureDir=str(capture_dir), name=name, note=note,
                                reason=f"撮影が完了しませんでした（{doc.get('error') or doc.get('status')}）。撮影失敗は記録しません。")

    images = []
    for cap in doc["captures"]:
        if cap.get("status") != "complete":
            continue
        images.append(dict(variant=cap["variant"], caseIndex=cap["caseIndex"],
                           image=cap["image"], conditions=cap["conditions"]))
    if not images:
        return ComparisonRecord(ok=False, recordDir=str(record_dir), captureDir=str(capture_dir), name=name, note=note,
                                reason="完成した画像がありません。")

    record = dict(schemaVersion="1.0.0", createdAt=datetime.now().astimezone().isoformat(),
                  name=name, note=note, model=paths.to_repo_relative(model_dir),
                  captureManifest="capture/manifest.json", images=images)
    (record_dir / "record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ComparisonRecord(ok=True, recordDir=str(record_dir), captureDir=str(capture_dir),
                            name=name, note=note, images=images)


def list_records() -> list:
    root = paths.RECORDS_DIR
    if not root.is_dir():
        return []
    out = []
    for folder in sorted((p for p in root.iterdir() if p.is_dir() and (p / "record.json").is_file()), reverse=True):
        try:
            out.append(dict(_read(folder / "record.json"), path=str(folder)))
        except json.JSONDecodeError:
            pass
    return out


def _shared_conditions(state: dict, room_labels: dict) -> dict:
    """撮影条件から共有してよいものだけを取り出し、絶対パス・座標・ハッシュは含めない。"""
    out = {k: state[k] for k in _SHARED_STATE_KEYS if k in state}
    solar = state.get("solar")
    if solar and solar.get("localTimestamp"):
        out["datetime"] = solar["localTimestamp"]
        out["solarPrecision"] = ("概算の位置・方位" if "estimated" in (solar.get("locationStatus"), solar.get("northStatus"))
                                 else "位置・方位の入力確認済み（座標は非公開）")
    else:
        out["solar"] = "手動太陽角度（未校正）"
    active = state.get("activeRoomId")
    out["targetRoom"] = dict(id=active, label=room_labels.get(active, active))
    out["provisionalNote"] = "仕上げ・照明・採光は仮条件（未校正）。実敷地・採用品番は確認待ち。"
    return out


def build_shared_copy(record_dir: Path, out_dir: Path, root: Path = paths.ROOT) -> dict:
    """record_dir（record_finish_ab の出力）から、共有してよい画像＋条件だけの
    ディレクトリを作る。生成前に文字列を走査し、禁止語が残っていたら失敗させる。"""
    record_dir = Path(record_dir)
    out_dir = Path(out_dir)
    record = _read(record_dir / "record.json")
    capture_dir = record_dir / "capture"

    house = _read(root / "data" / "house.json")
    room_labels = {r["id"]: r.get("label", r["id"]) for r in house.get("rooms", [])}

    if out_dir.exists():
        raise ValueError(f"出力先が既にあります: {out_dir}")
    out_dir.mkdir(parents=True)

    shared_images = []
    for img in record["images"]:
        src_png = capture_dir / img["image"]
        src_cond = capture_dir / img["conditions"]
        if not src_png.is_file() or not src_cond.is_file():
            raise ValueError(f"撮影ファイルが見つかりません: {img['image']}")
        shutil.copy2(src_png, out_dir / img["image"])
        state = _read(src_cond)
        cond = _shared_conditions(state, room_labels)
        (out_dir / img["conditions"]).write_text(json.dumps(cond, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        shared_images.append(dict(variant=img["variant"], image=img["image"], conditions=img["conditions"]))

    shared = dict(schemaVersion="1.0.0", kind="comparison-shared-copy",
                  name=record["name"], note=record["note"], createdAt=record["createdAt"],
                  images=shared_images,
                  disclaimer="仕上げ・照明・採光は仮条件（未校正）。実敷地の位置・真北・採用品番は確認待ちです。")
    (out_dir / "shared.json").write_text(json.dumps(shared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # 公開できない語が画像以外のどこかに残っていないか（案名・メモ由来を含む）を先に確認する。
    _assert_no_forbidden(out_dir)

    (out_dir / "README.txt").write_text(
        f"共有用コピー：{record['name']}\n\n"
        f"メモ：{record['note'] or '(なし)'}\n\n"
        "この中には画像と、その画像を生成した比較条件のみが入っています。\n"
        "機械のパス、敷地の位置情報、ローカル設定、生成ログ、元データは含まれません。\n"
        "自動公開・送信はしていません。共有先はご自身で選んでください。\n",
        encoding="utf-8")
    return dict(outDir=str(out_dir), images=len(shared_images))


def _assert_no_forbidden(out_dir: Path) -> None:
    """出力ディレクトリの JSON を走査し、公開できない語が残っていたら全体を消して中止する。"""
    for path in sorted(out_dir.rglob("*.json")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for needle in _FORBIDDEN_SUBSTRINGS:
            if needle in text:
                shutil.rmtree(out_dir, ignore_errors=True)
                raise ValueError(f"共有コピーに公開できない語「{needle}」が {path.name} に含まれています。中止しました。")
