"""ゲスト内覧ランチャーの入口。

  python -m guest_launcher            … GUI（既定）
  python scripts/guest_launcher/__main__.py  … 同じ（.cmd から）

補助サブコマンド（実装者の操作確認・CI用。施主の日常操作はGUI）:
  status                     現在の設定・モデル・依存の状態
  detect                     生成済み候補の検出結果
  furniture-report <path>    候補 furniture.json の差分・検証（正本不変）
  furniture-apply <path>     候補を反映（--backup-dir で控えの場所を指定可）
  furniture-restore <backup> 控えから data/furniture.json を戻す
  scenarios                  保存済み案の一覧
  scenario-save <proj> <name> [note]
  update <proj>              モデル更新を1回実行（重い。--output で出力先）
  update-plan <proj>         更新の要否・入力差分だけ
  record-ab <proj> <name> [note]     仕上げA/Bを撮影して記録（重い）
  shared-copy <record_dir> <out_dir> 記録から共有用コピーを作る
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# `python this_file.py` でも `import guest_launcher.x` が通るように scripts/ を追加。
_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from guest_launcher import comparison, config as _config, furniture, models, paths, scenarios, update, walkthrough  # noqa: E402


def _dump(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def _status():
    cfg = _config.load()
    model = cfg.current_model_path()
    info = models.inspect_project(model).__dict__ if model else None
    if info:
        info["path"] = str(info["path"])
    _dump(dict(config=dict(engine=cfg.enginePath, blender=cfg.blenderPath, cache=cfg.cachePath,
                           currentModel=cfg.currentModel, registered=[m["path"] for m in cfg.registeredModels],
                           lastUpdateOutput=cfg.lastUpdateOutput),
               missingDependencies=cfg.missing_dependencies(),
               currentModel=info))


def _detect():
    _dump([dict(path=str(i.path), valid=i.valid, scopeId=i.scopeId, importVerified=i.importVerified,
                walkthroughConfigured=i.walkthroughConfigured, updatedAt=i.updatedAt, reasons=i.reasons)
           for i in models.detect_candidates()])


def _furniture_report(path):
    r = furniture.build_report(Path(path))
    _dump(dict(sourcePath=r.sourcePath, ok=r.ok, validationError=r.validationError, counts=r.counts,
               totalItems=r.totalItems, assetBindingWarnings=r.assetBindingWarnings,
               sourceSha=r.sourceSha, candidateSha=r.candidateSha,
               changes=[dict(id=c.id, kind=c.kind, inGuestScope=c.inGuestScope, room=c.room,
                             fields=c.fields, provenanceLoss=c.provenanceLoss) for c in r.changes]))


def _furniture_apply(path, backup_dir=None, expect_source_sha=None, expect_candidate_sha=None):
    res = furniture.apply_candidate(Path(path), backup_dir=Path(backup_dir) if backup_dir else paths.BACKUP_DIR,
                                    expected_source_sha=expect_source_sha, expected_candidate_sha=expect_candidate_sha)
    _dump(dict(applied=res.applied, webDataRegenerated=res.webDataRegenerated,
               backupPath=res.backupPath, webLog=res.webLog, message=res.message))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        from guest_launcher import app
        return app.main()

    cmd, rest = argv[0], argv[1:]
    cfg = _config.load()
    if cmd == "status":
        _status()
    elif cmd == "detect":
        _detect()
    elif cmd == "furniture-report":
        _furniture_report(rest[0])
    elif cmd == "furniture-apply":
        opts = {}
        for flag, key in (("--backup-dir", "bd"), ("--expect-source-sha", "ss"), ("--expect-candidate-sha", "cs")):
            if flag in rest:
                i = rest.index(flag)
                opts[key] = rest[i + 1]
                rest = rest[:i] + rest[i + 2:]
        _furniture_apply(rest[0], opts.get("bd"), opts.get("ss"), opts.get("cs"))
    elif cmd == "furniture-restore":
        furniture.restore_backup(Path(rest[0]))
        print("restored data/furniture.json from", rest[0])
    elif cmd == "scenarios":
        _dump(scenarios.list_scenarios())
    elif cmd == "scenario-save":
        proj, name = rest[0], rest[1]
        note = rest[2] if len(rest) > 2 else ""
        _dump(scenarios.save_current_as_scenario(Path(proj), name, note))
    elif cmd == "update-plan":
        _dump(update.plan_update(Path(rest[0])))
    elif cmd == "update":
        proj = rest[0]
        out = None
        if "--output" in rest:
            out = Path(rest[rest.index("--output") + 1])
        out = out or update.update_output_dir()
        outcome = update.run_update(cfg, Path(proj), out, on_line=lambda t: print(t, flush=True))
        _dump(dict(ok=outcome.ok, status=outcome.status, failedStep=outcome.failedStep, reason=outcome.reason,
                   outputDir=outcome.outputDir, newModelDir=outcome.newModelDir, elapsedSec=outcome.elapsedSec))
        if outcome.ok:
            cfg.set_current_model(Path(outcome.newModelDir))
            cfg.lastUpdateOutput = paths.to_repo_relative(Path(outcome.outputDir))
            _config.save(cfg)
        return 0 if outcome.ok else 1
    elif cmd == "record-ab":
        proj, name = rest[0], rest[1]
        note = rest[2] if len(rest) > 2 else ""
        rec = comparison.record_finish_ab(cfg, Path(proj), name, note, on_line=lambda t: print(t, flush=True))
        _dump(dict(ok=rec.ok, recordDir=rec.recordDir, images=rec.images, reason=rec.reason))
        return 0 if rec.ok else 1
    elif cmd == "shared-copy":
        _dump(comparison.build_shared_copy(Path(rest[0]), Path(rest[1])))
    elif cmd in ("walkthrough-check",):
        _dump(dict(problem=walkthrough.can_launch(Path(rest[0]))))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
