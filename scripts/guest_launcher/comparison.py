"""仕上げA/Bの記録と、共有用コピーの出力。

- 記録：撮影開始時に **F5/エディタ保存の最新の有効な保存** を案保存と同じ共通処理
  （refresh_inputs.retained_inputs）で1つ選び、その状態（部屋・視点・fixtures・扉・
  太陽/来歴）を A/B で固定して `capture-unreal-study.py --state` へ渡す。A と B の
  差は対象室（activeRoomId）の仕上げだけ。太陽高度は保存値のまま（無断で45度へ
  変えない）。元の保存ファイルは書き換えない。撮影失敗は登録しない。
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
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(paths.ROOT / "unreal") not in sys.path:
    sys.path.insert(0, str(paths.ROOT / "unreal"))
import multi_room_state as _mrs  # noqa: E402
from refresh_inputs import retained_inputs as _retained_inputs, read as _ri_read  # noqa: E402

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


def _select_latest_state(model_dir: Path):
    """案保存と同じ選択・検証（refresh_inputs.retained_inputs）で、エディタ保存と
    内覧のF5保存のうち新しい方を選び、移行済みの状態dict と由来を返す。"""
    retained = _retained_inputs(model_dir)          # raises ValueError on mid-recovery / invalid
    state_path = Path(retained["state"])
    legacy = _ri_read(paths.ROOT / "data/visual/guest-ldk-study.json")
    scopes = _mrs.validate_scopes(_ri_read(paths.ROOT / "data/visual/study-scopes.json"))
    state = _mrs.validate_state_own_scope(_ri_read(state_path), scopes, legacy, legacy["variants"])
    source = "内覧のF5保存" if state_path.parent.name == "Saved" else "エディタ保存"
    mtime = datetime.fromtimestamp(state_path.stat().st_mtime).astimezone().isoformat()
    return state, dict(source=source, path=paths.to_repo_relative(state_path), mtime=mtime)


def record_finish_ab(cfg: _config.LauncherConfig, model_dir: Path, name: str, note: str = "",
                     variants=("natural", "warm"),
                     on_line: Optional[Callable[[str], None]] = None) -> ComparisonRecord:
    """model_dir の対象室（選んだ保存の activeRoomId）の固定カメラで、仕上げ違いを撮る。

    撮影開始時に選んだ保存（F5/エディタの新しい方）を A/B で固定。太陽は保存値のまま。
    対象室 variant 以外は変更しない。元の保存ファイルは書き換えない。撮影失敗は記録しない。"""
    name = (name or "").strip()
    if not name:
        return ComparisonRecord(ok=False, recordDir=None, captureDir=None, name="", note=note,
                                reason="記録の名前を入力してください。")
    model_dir = Path(model_dir).resolve()
    info_iv = model_dir / "import-verification.json"
    if not info_iv.is_file() or not _read(info_iv).get("unrealImportVerified"):
        return ComparisonRecord(ok=False, recordDir=None, captureDir=None, name=name, note=note,
                                reason="検証済みのモデルではありません。先にモデルを更新・登録してください。")

    try:
        state, selected = _select_latest_state(model_dir)
    except ValueError as e:
        return ComparisonRecord(ok=False, recordDir=None, captureDir=None, name=name, note=note,
                                reason=f"撮影に使う保存状態を選べません（{e}）。内覧でF5保存してから記録してください。")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    record_dir = paths.RECORDS_DIR / stamp
    capture_dir = record_dir / "capture"
    capture_dir.mkdir(parents=True, exist_ok=True)
    saved_dir = model_dir / "Saved"

    # 撮影開始時に選んだ状態を1回だけ書き出し、両方の撮影で固定して使う。
    state_file = record_dir / "selected-state.json"
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if on_line:
        on_line(f"比較撮影に使う保存：{selected['source']}（{selected['path']}、{selected['mtime']}）")

    images = []
    for variant in variants:
        cap_name = f"gl-ab-{stamp}-{variant}"
        log_path = paths.LOG_DIR / f"{cap_name}.log"
        argv = runner.python_argv(
            _SCRIPTS / "capture-unreal-study.py",
            "--engine", cfg.engine, "--project", model_dir, "--cache", cfg.cache,
            "--name", cap_name, "--variant", variant, "--state", state_file,
        )
        try:
            proc = runner.run_logged(argv, log_path, cwd=paths.ROOT, on_line=on_line)
        except Exception as e:  # noqa: BLE001
            return ComparisonRecord(ok=False, recordDir=str(record_dir), captureDir=str(capture_dir),
                                    name=name, note=note, reason=f"撮影の実行に失敗しました（{e}）。ログ: {log_path}")
        png = saved_dir / f"{cap_name}.png"
        cond = saved_dir / f"{cap_name}-conditions.json"
        report_json = saved_dir / f"{cap_name}.json"
        if proc.returncode != 0 or not png.is_file() or not cond.is_file():
            return ComparisonRecord(ok=False, recordDir=str(record_dir), captureDir=str(capture_dir),
                                    name=name, note=note,
                                    reason=f"{variant} の撮影に失敗しました（終了コード {proc.returncode}）。"
                                           f"撮影失敗は記録しません。ログ: {log_path}")
        out_png = f"{variant}.png"
        out_cond = f"{variant}.json"
        shutil.copy2(png, capture_dir / out_png)
        shutil.copy2(cond, capture_dir / out_cond)
        if report_json.is_file():
            shutil.copy2(report_json, capture_dir / f"{variant}-report.json")
        images.append(dict(variant=variant, image=out_png, conditions=out_cond))

    if not images:
        return ComparisonRecord(ok=False, recordDir=str(record_dir), captureDir=str(capture_dir),
                                name=name, note=note, reason="完成した画像がありません。")

    # 撮影が対象室の仕上げだけを変えたか、選んだ保存と一致するかを確認する。
    mismatch = _verify_ab(capture_dir, state, images)
    if mismatch:
        return ComparisonRecord(ok=False, recordDir=str(record_dir), captureDir=str(capture_dir),
                                name=name, note=note, reason="撮影条件が選んだ保存と一致しません：" + mismatch)

    record = dict(schemaVersion="1.1.0", createdAt=datetime.now().astimezone().isoformat(),
                  name=name, note=note, model=paths.to_repo_relative(model_dir),
                  selectedSave=selected, activeRoomId=state.get("activeRoomId"), images=images)
    (record_dir / "record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ComparisonRecord(ok=True, recordDir=str(record_dir), captureDir=str(capture_dir),
                            name=name, note=note, images=images)


def _verify_ab(capture_dir: Path, selected_state: dict, images: list) -> Optional[str]:
    """撮影した条件が、選んだ保存に対して 対象室 variant 以外 一致するか確認する。"""
    active = selected_state.get("activeRoomId")
    fixed = {k: selected_state.get(k) for k in ("scopeId", "activeRoomId", "activeLevel", "solar", "sunLux", "camera", "azimuthDeg",
                                                "elevationDeg", "exposureEV100", "doorStates")}
    fixed["lightingMode"] = (selected_state.get("lighting") or {}).get("mode")
    for img in images:
        cond = _read(capture_dir / img["conditions"])
        for k, v in fixed.items():
            if k == "lightingMode":
                got = (cond.get("lighting") or {}).get("mode")
            else:
                got = cond.get(k)
            if got != v:
                return f"{img['variant']} の {k} が保存と違います（{got!r} ≠ {v!r}）"
        for room_id, rs in (selected_state.get("roomStates") or {}).items():
            got_rs = (cond.get("roomStates") or {}).get(room_id, {})
            expected = dict(rs)
            if room_id == active:expected["variant"] = img["variant"]
            if got_rs != expected:
                return f"{img['variant']} で {room_id} の仕上げ以外の条件が変わっています"
    return None


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
