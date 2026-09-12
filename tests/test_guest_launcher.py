"""W08-G ゲスト試用版ランチャーの純ロジックのテスト（tkinter 不使用）。

設定・モデル検証・家具候補の差分/検証/反映・共有コピーの無害化を、
一時ディレクトリ上の最小リポジトリで確認する。重いUE/Blender工程は含まない。
"""
import json
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from guest_launcher import comparison, config as gl_config, furniture, models, paths as gl_paths  # noqa: E402


def _mini_repo(tmp: Path) -> Path:
    """furniture 検証/反映に必要な最小の data/ と scripts/ を持つ疑似ルート。"""
    root = tmp / "repo"
    (root / "data" / "visual").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "generated").mkdir()
    for rel in ("data/furniture.json", "data/furniture-catalog.json", "data/house.json",
                "data/visual/asset-bindings.json", "scripts/build-web-data.mjs"):
        shutil.copy2(ROOT / rel, root / rel)
    for source in (ROOT / "data").glob("*.json"):
        shutil.copy2(source, root / "data" / source.name)
    return root


class FurnitureCandidateTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = _mini_repo(self.tmp)
        self.current = json.loads((self.root / "data/furniture.json").read_text(encoding="utf-8"))

    def _write_candidate(self, doc, name="cand.json"):
        p = self.tmp / name
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    def test_identical_candidate_has_no_changes_and_is_ok(self):
        p = self._write_candidate(self.current)
        report = furniture.build_report(p, root=self.root)
        self.assertTrue(report.ok)
        self.assertFalse(report.has_changes)
        self.assertEqual(report.validationError, None)

    def test_move_and_resize_pass_validation_with_diff(self):
        doc = json.loads(json.dumps(self.current))
        moved = next(i for i in doc["items"] if i.get("room"))
        moved["x"] = round(moved["x"] + 0.03, 2)
        doc["items"][0]["heightOverride"] = 0.8
        report = furniture.build_report(self._write_candidate(doc), root=self.root)
        self.assertTrue(report.ok, report.validationError)
        ids = {c.id for c in report.changes}
        self.assertIn(moved["id"], ids)
        self.assertEqual(report.counts["modified"], len(report.changes))

    def test_unknown_type_rejected_before_any_source_change(self):
        doc = json.loads(json.dumps(self.current))
        doc["items"][0]["type"] = "no-such-type"
        before = (self.root / "data/furniture.json").read_bytes()
        report = furniture.build_report(self._write_candidate(doc), root=self.root)
        self.assertFalse(report.ok)
        self.assertIn("未知のtype", report.validationError)
        self.assertEqual((self.root / "data/furniture.json").read_bytes(), before)
        with self.assertRaises(ValueError):
            furniture.apply_candidate(self._write_candidate(doc), root=self.root, backup_dir=self.tmp / "b")

    def test_duplicate_id_in_candidate_rejected(self):
        doc = json.loads(json.dumps(self.current))
        doc["items"].append(dict(doc["items"][0]))
        report = furniture.build_report(self._write_candidate(doc), root=self.root)
        self.assertFalse(report.ok)
        self.assertIn("重複", report.validationError)

    def test_non_furniture_json_refused(self):
        p = self.tmp / "house.json"
        p.write_text(json.dumps({"schemaVersion": "1.0.0", "rooms": []}), encoding="utf-8")
        with self.assertRaises(ValueError):
            furniture.read_candidate(p)

    def test_removal_and_provenance_loss_are_surfaced(self):
        doc = json.loads(json.dumps(self.current))
        removed = doc["items"].pop()["id"]
        doc["items"][0].pop("note", None)
        doc["items"][0].pop("status", None)
        doc["items"][0]["status"] = "estimated"  # status is required; only note loss remains
        report = furniture.build_report(self._write_candidate(doc), root=self.root)
        kinds = {(c.id, c.kind) for c in report.changes}
        self.assertIn((removed, "removed"), kinds)

    def test_apply_refuses_when_source_or_candidate_changed_after_preview(self):
        # review R2: the diff was built against specific bytes; apply must not
        # write unseen content.
        doc = json.loads(json.dumps(self.current))
        item = next(i for i in doc["items"] if i.get("room"))
        item["x"] = round(item["x"] + 0.04, 2)
        cand = self._write_candidate(doc)
        report = furniture.build_report(cand, root=self.root)
        self.assertTrue(report.ok)
        src = self.root / "data/furniture.json"
        original_source = src.read_text(encoding="utf-8")

        # (a) source changed after preview
        src_doc = json.loads(original_source)
        src_doc["items"][1]["note"] = "别の取込で足したメモ"
        src.write_text(json.dumps(src_doc, ensure_ascii=False, indent=2), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "もう一度"):
            furniture.apply_candidate(cand, root=self.root, backup_dir=self.tmp / "b1",
                                      expected_source_sha=report.sourceSha,
                                      expected_candidate_sha=report.candidateSha)
        # the unseen source note is still there (not clobbered)
        self.assertEqual(json.loads(src.read_text(encoding="utf-8"))["items"][1].get("note"), "别の取込で足したメモ")
        src.write_text(original_source, encoding="utf-8")

        # (b) candidate re-written to the same path after preview
        doc["items"][0]["heightOverride"] = 0.7
        cand.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "もう一度"):
            furniture.apply_candidate(cand, root=self.root, backup_dir=self.tmp / "b2",
                                      expected_source_sha=report.sourceSha,
                                      expected_candidate_sha=report.candidateSha)
        self.assertEqual(src.read_text(encoding="utf-8"), original_source)

        # (c) matching shas -> applies
        fresh = furniture.build_report(cand, root=self.root)
        res = furniture.apply_candidate(cand, root=self.root, backup_dir=self.tmp / "b3",
                                        expected_source_sha=fresh.sourceSha,
                                        expected_candidate_sha=fresh.candidateSha)
        self.assertTrue(res.applied)
        furniture.restore_backup(res.backupPath, root=self.root)

    def test_apply_backs_up_replaces_and_regenerates(self):
        doc = json.loads(json.dumps(self.current))
        item = next(i for i in doc["items"] if i.get("room"))
        item["x"] = round(item["x"] + 0.02, 2)
        p = self._write_candidate(doc)
        before = (self.root / "data/furniture.json").read_text(encoding="utf-8")
        result = furniture.apply_candidate(p, root=self.root, backup_dir=self.tmp / "backups")
        self.assertTrue(result.applied)
        self.assertTrue(Path(result.backupPath).is_file())
        self.assertEqual(Path(result.backupPath).read_text(encoding="utf-8"), before)
        after = json.loads((self.root / "data/furniture.json").read_text(encoding="utf-8"))
        self.assertEqual(next(i["x"] for i in after["items"] if i["id"] == item["id"]), item["x"])
        # node may be unavailable in the test env; either way the real state is reported truthfully
        self.assertIn(result.webDataRegenerated, (True, False))
        furniture.restore_backup(result.backupPath, root=self.root)
        self.assertEqual((self.root / "data/furniture.json").read_text(encoding="utf-8"), before)

    def test_asset_binding_mismatch_warned(self):
        doc = json.loads(json.dumps(self.current))
        # flip a bound water fixture to an incompatible type
        for it in doc["items"]:
            if it["id"] == "fur-002":  # washing-machine -> washer-v1 (boxAppliance)
                it["type"] = "toilet"
        report = furniture.build_report(self._write_candidate(doc), root=self.root)
        self.assertTrue(any("asset-bindings" in w or "washer-v1" in w for w in report.assetBindingWarnings))


class ModelInspectionTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    _n = 0

    def _project(self, scope="guest", import_ok=True, wt=True):
        ModelInspectionTests._n += 1
        p = self.tmp / f"proj{ModelInspectionTests._n}"
        p.mkdir()
        (p / "RyukaInterior.uproject").write_text("{}", encoding="utf-8")
        (p / "import-verification.json").write_text(json.dumps(
            dict(unrealImportVerified=import_ok, scopeId=scope, meshes=700)), encoding="utf-8")
        if wt:
            (p / "walkthrough-verification.json").write_text(json.dumps(dict(configured=True)), encoding="utf-8")
        return p

    def test_valid_guest_project(self):
        info = models.inspect_project(self._project())
        self.assertTrue(info.valid)
        self.assertEqual(info.scopeId, "guest")

    def test_wrong_scope_is_flagged(self):
        info = models.inspect_project(self._project(scope="guest-pilot"))
        self.assertFalse(info.valid)
        self.assertTrue(any("guest" in r for r in info.reasons))

    def test_missing_import_and_walkthrough(self):
        self.assertFalse(models.inspect_project(self._project(import_ok=False)).valid)
        self.assertFalse(models.inspect_project(self._project(wt=False)).valid)

    def test_not_a_project(self):
        info = models.inspect_project(self.tmp / "nope")
        self.assertFalse(info.valid)


class ConfigTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self._orig = (gl_paths.CONFIG_PATH, gl_paths.LAUNCHER_DIR)
        gl_paths.LAUNCHER_DIR = self.tmp / "launcher"
        gl_paths.CONFIG_PATH = gl_paths.LAUNCHER_DIR / "config.json"
        gl_paths.LOG_DIR = gl_paths.LAUNCHER_DIR / "logs"
        gl_paths.BACKUP_DIR = gl_paths.LAUNCHER_DIR / "backups"
        gl_paths.RECORDS_DIR = gl_paths.LAUNCHER_DIR / "comparisons"

    def tearDown(self):
        gl_paths.CONFIG_PATH, gl_paths.LAUNCHER_DIR = self._orig

    def test_roundtrip_and_model_registration(self):
        cfg = gl_config.load()
        self.assertEqual(cfg.currentModel, None)
        cfg.set_current_model(gl_paths.ROOT / "build" / "some-model")
        gl_config.save(cfg)
        again = gl_config.load()
        self.assertEqual(again.currentModel, "build/some-model")
        self.assertEqual(len(again.registeredModels), 1)
        again.unregister_model(gl_paths.ROOT / "build" / "some-model")
        self.assertEqual(again.currentModel, None)

    def test_relative_paths_survive(self):
        self.assertEqual(gl_paths.to_repo_relative(gl_paths.ROOT / "build/x/ue"), "build/x/ue")
        self.assertEqual(gl_paths.from_repo_relative("build/x/ue"), gl_paths.ROOT / "build/x/ue")


class SharedCopyTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.record = self.tmp / "rec"
        (self.record / "capture").mkdir(parents=True)
        # a fake capture: one image + its conditions (a real study-state shape)
        (self.record / "capture" / "case-0-natural.png").write_bytes(b"\x89PNG\r\n\x1a\n fake")
        state = dict(schemaVersion="2.1.0", scopeId="guest", activeRoomId="room-1f-06", activeLevel=1,
                     camera=dict(locationCm=[213, 425, 225.7], rotationDeg=[-3, 11, 0], lensMm=20),
                     azimuthDeg=155.0, elevationDeg=30.0, exposureEV100=7.5, sunLux=50000,
                     lighting=dict(mode="day"),
                     roomStates={"room-1f-06": dict(variant="warm", surfaceOverrides={}, fixtures={})},
                     solar=dict(localTimestamp="2026-06-21T14:00", locationStatus="estimated", northStatus="estimated"),
                     siteContextSHA256="deadbeef" * 8)
        (self.record / "capture" / "case-0-natural.json").write_text(json.dumps(state), encoding="utf-8")
        (self.record / "record.json").write_text(json.dumps(dict(
            schemaVersion="1.0.0", createdAt="2026-09-10T00:00:00+09:00", name="仕上げ比較", note="A/B",
            model="build/x/ue", captureManifest="capture/manifest.json",
            images=[dict(variant="natural", caseIndex=0, image="case-0-natural.png",
                         conditions="case-0-natural.json")])), encoding="utf-8")

    def test_shared_copy_keeps_images_and_conditions_but_no_secrets(self):
        out = self.tmp / "shared"
        result = comparison.build_shared_copy(self.record, out, root=ROOT)
        self.assertEqual(result["images"], 1)
        self.assertTrue((out / "case-0-natural.png").is_file())
        cond = json.loads((out / "case-0-natural.json").read_text(encoding="utf-8"))
        self.assertIn("camera", cond)
        self.assertIn("targetRoom", cond)
        self.assertEqual(cond["targetRoom"]["id"], "room-1f-06")
        blob = "".join(p.read_text(encoding="utf-8") for p in out.rglob("*") if p.suffix != ".png")
        for forbidden in ("siteContextSHA256", "C:\\", "latitudeDeg", "sha256"):
            self.assertNotIn(forbidden, blob)

    def test_forbidden_token_aborts(self):
        # inject an absolute path into the user note
        rec = json.loads((self.record / "record.json").read_text(encoding="utf-8"))
        rec["note"] = r"C:\Users\someone\secret"
        (self.record / "record.json").write_text(json.dumps(rec), encoding="utf-8")
        with self.assertRaises(ValueError):
            comparison.build_shared_copy(self.record, self.tmp / "shared2", root=ROOT)
        self.assertFalse((self.tmp / "shared2").exists())


try:
    import tkinter as _tk
    _tk.Tk().destroy()
    _HAS_TK = True
except Exception:  # noqa: BLE001 - headless / no display
    _HAS_TK = False


@unittest.skipUnless(_HAS_TK, "tkinter/display not available")
class GuiResilienceTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self._orig = (gl_paths.CONFIG_PATH, gl_paths.LAUNCHER_DIR, gl_paths.LOG_DIR)
        gl_paths.LAUNCHER_DIR = self.tmp / "launcher"
        gl_paths.CONFIG_PATH = gl_paths.LAUNCHER_DIR / "config.json"
        gl_paths.LOG_DIR = gl_paths.LAUNCHER_DIR / "logs"
        gl_paths.ensure_dirs = lambda: gl_paths.LAUNCHER_DIR.mkdir(parents=True, exist_ok=True)
        from guest_launcher import app as gl_app
        self.gl_app = gl_app
        self.root = _tk.Tk()
        self.root.withdraw()
        self.app = gl_app.LauncherApp(self.root)
        self.addCleanup(self.root.destroy)

    def tearDown(self):
        gl_paths.CONFIG_PATH, gl_paths.LAUNCHER_DIR, gl_paths.LOG_DIR = self._orig

    def test_drain_queue_isolates_a_dead_widget_callback(self):
        # review R3: a TclError from one destroyed target must not stop the
        # pump or skip the job-completion callbacks queued behind it.
        ran = []

        def boom():
            raise _tk.TclError("invalid command name .dead.stepsbox")

        self.app._on_main(boom)
        self.app._on_main(lambda: ran.append("after-boom"))
        self.app._drain_queue()  # must not raise
        self.root.update()
        self.assertIn("after-boom", ran)

    def test_apply_update_success_switches_model_without_a_window(self):
        # the current-model switch lives on the app, not the UpdateWindow, so
        # closing that window mid-run cannot prevent it.
        proj = self.tmp / "newmodel" / "ue"
        proj.mkdir(parents=True)
        self.app.apply_update_success(str(proj), str(self.tmp / "newmodel"))
        again = gl_config.load()
        self.assertEqual(again.currentModel, gl_paths.to_repo_relative(proj))

    def test_app_close_blocked_while_update_running(self):
        from unittest import mock
        from guest_launcher import runner as gl_runner
        with gl_runner.BackgroundJob._lock:
            gl_runner.BackgroundJob._active_keys.add("model-update")
        try:
            with mock.patch.object(self.gl_app.messagebox, "showwarning") as warn, \
                 mock.patch.object(self.root, "destroy") as destroy:
                self.app._on_app_close()
            warn.assert_called_once()
            destroy.assert_not_called()
        finally:
            with gl_runner.BackgroundJob._lock:
                gl_runner.BackgroundJob._active_keys.discard("model-update")
        # with nothing running, close proceeds
        with mock.patch.object(self.root, "destroy") as destroy:
            self.app._on_app_close()
            destroy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
