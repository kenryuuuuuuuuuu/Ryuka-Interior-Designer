"""tkinter GUI（既定の入口）。既存CLIとUE機能を薄くまとめる。

日常操作でUE/Blenderの実行パスや生成先を毎回入力させない。長時間処理は
スレッドで回し、ウィンドウは応答し続ける。工程名・実行中/成功/失敗・ログ・
経過時間を表示し、根拠のない進捗率は出さない。
"""
from __future__ import annotations

import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from . import comparison, config as _config, furniture, models, paths, runner, scenarios, update, walkthrough

GUIDE_PATH = paths.ROOT / "docs" / "GUEST_TRIAL_GUIDE.md"
APP_TITLE = "ゲスト内覧ランチャー"


class LauncherApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("880x680")
        self.cfg = _config.load()
        paths.ensure_dirs()
        self._ui_queue: "queue.Queue" = queue.Queue()
        self._build_ui()
        self._refresh_status()
        self.root.after(120, self._drain_queue)

    # ---------- UI construction ----------
    def _build_ui(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_app_close)
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")
        self.status_var = tk.StringVar(value="…")
        ttk.Label(top, textvariable=self.status_var, justify="left", font=("", 10)).pack(anchor="w")

        bar = ttk.Frame(self.root, padding=(12, 0))
        bar.pack(fill="x")
        buttons = [
            ("内覧を開く", self.on_open_walkthrough),
            ("編集・比較を開く", self.on_open_editor),
            ("家具JSON取込", self.on_import_furniture),
            ("モデル更新", self.on_update_model),
            ("案と比較記録", self.on_scenarios_window),
            ("モデルを選ぶ", self.on_choose_model),
            ("設定", self.on_settings),
            ("使い方", self.on_help),
        ]
        for i, (label, cmd) in enumerate(buttons):
            ttk.Button(bar, text=label, command=cmd, width=16).grid(row=i // 4, column=i % 4, padx=4, pady=4, sticky="ew")
        for c in range(4):
            bar.columnconfigure(c, weight=1)

        steps = ttk.LabelFrame(self.root, text="実行中の工程", padding=8)
        steps.pack(fill="x", padx=12, pady=(8, 0))
        self.steps_var = tk.StringVar(value="（待機中）")
        ttk.Label(steps, textvariable=self.steps_var, justify="left").pack(anchor="w")

        logf = ttk.LabelFrame(self.root, text="ログ", padding=6)
        logf.pack(fill="both", expand=True, padx=12, pady=8)
        self.log = scrolledtext.ScrolledText(logf, height=16, wrap="word", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

        foot = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        foot.pack(fill="x")
        ttk.Button(foot, text="ログフォルダを開く", command=lambda: _open_path(paths.LOG_DIR)).pack(side="left")
        ttk.Button(foot, text="設定ファイルの場所", command=lambda: _open_path(paths.LAUNCHER_DIR)).pack(side="left", padx=6)

    # ---------- helpers ----------
    def _log(self, text: str):
        self._ui_queue.put(("log", text))

    def _set_steps(self, text: str):
        self._ui_queue.put(("steps", text))

    def _drain_queue(self):
        # Each item is isolated: a TclError from one destroyed target (e.g. a
        # closed UpdateWindow's step box) must never stop the pump or skip the
        # job-completion callbacks queued behind it. The reschedule is in a
        # finally so the loop always keeps running.
        try:
            while True:
                try:
                    kind, payload = self._ui_queue.get_nowait()
                except queue.Empty:
                    break
                try:
                    if kind == "log":
                        self.log.configure(state="normal")
                        self.log.insert("end", payload + "\n")
                        self.log.see("end")
                        self.log.configure(state="disabled")
                    elif kind == "steps":
                        self.steps_var.set(payload)
                    elif kind == "call":
                        payload()
                except tk.TclError as e:
                    sys.stderr.write(f"[launcher] UI update skipped (widget gone): {e}\n")
                except Exception as e:  # noqa: BLE001 - a bad callback must not kill the pump
                    sys.stderr.write(f"[launcher] queued callback failed: {e!r}\n")
        finally:
            try:
                self.root.after(120, self._drain_queue)
            except tk.TclError:
                pass  # root itself is gone (app closing)

    def _on_main(self, fn):
        self._ui_queue.put(("call", fn))

    def _on_app_close(self):
        # A running model-update owns a UE subprocess; closing the app would
        # orphan it and lose the post-run model switch. Block until it ends
        # (or the user can keep working). Other short jobs are fine to leave.
        if runner.BackgroundJob.is_running("model-update"):
            messagebox.showwarning(APP_TITLE, "モデル更新の実行中です。完了までランチャーを閉じないでください。\n"
                                              "結果はメインのログと状態表示に出ます。")
            return
        self.root.destroy()

    def apply_update_success(self, new_model_dir: str, output_dir: str):
        """Switch the current model after a successful update. Deliberately on
        the app, not the UpdateWindow, so closing that window mid-run cannot
        prevent the switch (review R3)."""
        self.cfg = _config.load()
        self.cfg.set_current_model(Path(new_model_dir))
        self.cfg.lastUpdateOutput = paths.to_repo_relative(Path(output_dir))
        _config.save(self.cfg)
        self._log(f"更新に成功しました。現行モデルを {paths.to_repo_relative(Path(new_model_dir))} へ切り替えました。")
        self._on_main(self._refresh_status)

    def _refresh_status(self):
        self.cfg = _config.load()
        lines = []
        model = self.cfg.current_model_path()
        if model is None:
            lines.append("現在のモデル：未選択。「モデルを選ぶ」から登録してください。")
        else:
            info = models.inspect_project(model)
            mark = "有効" if info.valid else "要確認"
            lines.append(f"現在のモデル：{info.label}  [{mark}]")
            lines.append(f"　更新日時：{info.updatedAt or '不明'}　メッシュ：{info.meshCount or '?'}")
            if info.savedStateMtime:
                lines.append(f"　保存状態：schema {info.savedStateSchema or '?'} / {info.savedStateMtime}")
            else:
                lines.append("　保存状態：まだF5保存がありません（内覧でF5すると保存されます）")
            if not info.valid:
                lines.append("　注意：" + " / ".join(info.reasons))
        missing = self.cfg.missing_dependencies()
        if missing:
            lines.append("依存の不足：")
            lines.extend("　- " + m for m in missing)
        else:
            lines.append(f"エンジン：{self.cfg.enginePath}　Blender：{self.cfg.blenderPath}　cache：{self.cfg.cachePath}")
        self.status_var.set("\n".join(lines))

    def _require_model(self):
        model = self.cfg.current_model_path()
        if model is None:
            messagebox.showinfo(APP_TITLE, "先に「モデルを選ぶ」でゲストモデルを登録してください。")
            return None
        return model

    def _run_bg(self, key: str, target, on_done=None):
        if runner.BackgroundJob.is_running(key):
            messagebox.showinfo(APP_TITLE, "同じ処理が実行中です。完了までお待ちください。")
            return None
        job = runner.BackgroundJob(key, target, on_done=lambda j: self._on_main(lambda: self._job_done(j, on_done)))
        job.start()
        return job

    def _job_done(self, job, on_done):
        if job.error:
            self._log(f"！エラー：{job.error}")
        if on_done:
            try:
                on_done(job)
            except tk.TclError as e:
                sys.stderr.write(f"[launcher] job-done UI update skipped: {e}\n")
            except Exception as e:  # noqa: BLE001
                self._log(f"！完了処理でエラー：{e!r}")
        try:
            self._refresh_status()
        except tk.TclError:
            pass

    # ---------- actions ----------
    def on_open_walkthrough(self):
        model = self._require_model()
        if not model:
            return
        problem = walkthrough.can_launch(model)
        if problem:
            messagebox.showwarning(APP_TITLE, problem)
            return
        self._log("内覧を起動します。ウィンドウが開きます。操作キーは「使い方」を参照してください。")
        self._log("　" + " ／ ".join(walkthrough.WALKTHROUGH_KEYS[:5]))
        self._run_bg("walkthrough", lambda: walkthrough.launch_walkthrough(self.cfg, model, on_line=self._log),
                     on_done=lambda j: self._log("内覧を終了しました。" if not j.error else ""))

    def on_open_editor(self):
        model = self._require_model()
        if not model:
            return
        self._log("UEエディタを起動します。面編集・詳細比較は『ツール → 内装比較』から。保存してから閉じてください。")
        self._run_bg("editor", lambda: walkthrough.open_editor(self.cfg, model, on_line=self._log))

    def on_import_furniture(self):
        path = filedialog.askopenfilename(title="ブラウザで書き出した furniture.json を選択",
                                          filetypes=[("furniture.json", "*.json"), ("すべて", "*.*")])
        if not path:
            return
        try:
            report = furniture.build_report(Path(path))
        except ValueError as e:
            messagebox.showerror(APP_TITLE, str(e))
            return
        FurnitureImportWindow(self, Path(path), report)

    def on_update_model(self):
        model = self._require_model()
        if not model:
            return
        if self.cfg.missing_dependencies():
            messagebox.showwarning(APP_TITLE, "依存の不足を「設定」で解消してから更新してください。")
            return
        UpdateWindow(self, model)

    def on_scenarios_window(self):
        model = self._require_model()
        if not model:
            return
        ScenarioWindow(self, model)

    def on_choose_model(self):
        ChooseModelWindow(self)

    def on_settings(self):
        SettingsWindow(self)

    def on_help(self):
        if GUIDE_PATH.is_file():
            _open_path(GUIDE_PATH)
        else:
            messagebox.showinfo(APP_TITLE, "docs/GUEST_TRIAL_GUIDE.md を参照してください。")


# ============ sub-windows ============
class FurnitureImportWindow(tk.Toplevel):
    def __init__(self, app: LauncherApp, candidate_path: Path, report: furniture.CandidateReport):
        super().__init__(app.root)
        self.app = app
        self.candidate_path = candidate_path
        self.report = report
        self.title("家具JSONの取込（差分の確認）")
        self.geometry("760x560")

        head = ttk.Frame(self, padding=10)
        head.pack(fill="x")
        c = report.counts
        summary = (f"候補：{candidate_path.name}　全{report.totalItems}件\n"
                   f"追加 {c.get('added', 0)} ／ 削除 {c.get('removed', 0)} ／ 変更 {c.get('modified', 0)}"
                   f"（ゲスト対象 {c.get('guestScope', 0)} ／ ゲスト外 {c.get('otherScope', 0)}）")
        if c.get("provenanceLoss"):
            summary += f"\n注意：note/status が失われる項目が {c['provenanceLoss']} 件あります。"
        ttk.Label(head, text=summary, justify="left").pack(anchor="w")
        if not report.ok:
            ttk.Label(head, text="検証エラー：" + (report.validationError or ""), foreground="#b00",
                      wraplength=700, justify="left").pack(anchor="w", pady=(6, 0))
        for w in report.assetBindingWarnings:
            ttk.Label(head, text="⚠ " + w, foreground="#a60", wraplength=700, justify="left").pack(anchor="w")

        tree = ttk.Treeview(self, columns=("kind", "scope", "room", "detail"), show="headings", height=16)
        for col, txt, w in (("kind", "変更", 60), ("scope", "範囲", 70), ("room", "室", 90), ("detail", "内容", 460)):
            tree.heading(col, text=txt)
            tree.column(col, width=w, anchor="w")
        tree.pack(fill="both", expand=True, padx=10)
        for ch in report.changes:
            detail = {"added": "新規追加", "removed": "削除",
                      "modified": ", ".join(f"{f['field']}: {f['before']}→{f['after']}" for f in ch.fields)}[ch.kind]
            if ch.provenanceLoss:
                detail += f"　（{'/'.join(ch.provenanceLoss)} が消えます）"
            tree.insert("", "end", values=({"added": "追加", "removed": "削除", "modified": "変更"}[ch.kind],
                                           "ゲスト" if ch.inGuestScope else "ゲスト外",
                                           ch.room or "-", f"{ch.id} {detail}"))
        if not report.changes:
            tree.insert("", "end", values=("-", "-", "-", "現在の正本と差分はありません。"))

        foot = ttk.Frame(self, padding=10)
        foot.pack(fill="x")
        state = "normal" if (report.ok and report.changes) else "disabled"
        ttk.Button(foot, text="正本へ反映", command=self._apply, state=state).pack(side="right")
        ttk.Button(foot, text="閉じる", command=self.destroy).pack(side="right", padx=6)
        ttk.Label(foot, text="反映すると data/furniture.json を置換し Web生成データを再生成します。\n"
                             "反映前に直前の正本を build/launcher/backups/ に控えます。",
                  justify="left").pack(side="left")

    def _apply(self):
        if not messagebox.askyesno(self.title(), "この差分を data/furniture.json に反映します。よろしいですか？"):
            return
        self.app._log(f"家具JSONを反映します：{self.candidate_path}")
        # review R2: the diff was built against these exact bytes; apply refuses
        # if either the source or the candidate changed since.
        src_sha = self.report.sourceSha
        cand_sha = self.report.candidateSha

        def work():
            return furniture.apply_candidate(self.candidate_path,
                                             expected_source_sha=src_sha, expected_candidate_sha=cand_sha)

        def done(job):
            if job.error:
                messagebox.showerror(self.title(), str(job.error))
                if "もう一度" in str(job.error):
                    self.destroy()  # stale preview -- operator must re-open the import window
                return
            res: furniture.ApplyResult = job.result
            self.app._log(res.message)
            if res.backupPath:
                self.app._log(f"　復元用コピー：{res.backupPath}")
            messagebox.showinfo(self.title(), res.message)
            self.destroy()

        self.app._run_bg("furniture-apply", work, on_done=done)


class UpdateWindow(tk.Toplevel):
    def __init__(self, app: LauncherApp, model_dir: Path):
        super().__init__(app.root)
        self.app = app
        self.model_dir = model_dir
        self.title("モデル更新")
        self.geometry("720x520")
        self._start_ts = None

        ttk.Label(self, text="更新は選択モデルを元に、新しい出力ディレクトリでBlender・UEを再生成します。\n"
                             "前のモデルと保存済みの案は上書き・削除しません。成功を確認してから現行モデルを切り替えます。",
                  padding=10, justify="left").pack(fill="x")

        plan_box = scrolledtext.ScrolledText(self, height=8, wrap="word", font=("", 9))
        plan_box.pack(fill="both", expand=False, padx=10)
        plan = update.plan_update(model_dir)
        s = plan.get("summary") or {}
        text = "前回モデルからの入力差分：\n"
        if "error" in s:
            text += f"　（差分算出に失敗：{s['error']}）\n"
        else:
            for label, key in (("部屋", "rooms"), ("家具", "furniture"), ("家具カタログ", "catalog"),
                               ("照明プロファイル", "lightingProfiles"), ("照明グループ", "lightingGroups")):
                cc = s.get(key)
                if cc:
                    text += f"　{label}：追加{cc['added']}・削除{cc['removed']}・変更{cc['modified']}\n"
        text += f"変更された入力ファイル数：{len(plan['changedSourceFiles'])}\n"
        if plan["issues"]:
            text += "参照切れ・重複（更新は失敗します。先に修正）：\n"
            text += "\n".join("　- " + i["message"] for i in plan["issues"])
        elif not plan["changedSourceFiles"]:
            text += "\n入力に変更はありません。更新しても内容は同じになります。"
        plan_box.insert("end", text)
        plan_box.configure(state="disabled")

        self.steps_box = scrolledtext.ScrolledText(self, height=10, wrap="word", font=("Consolas", 9))
        self.steps_box.pack(fill="both", expand=True, padx=10, pady=6)
        self.steps_box.configure(state="disabled")

        foot = ttk.Frame(self, padding=10)
        foot.pack(fill="x")
        self.run_btn = ttk.Button(foot, text="更新開始", command=self._start,
                                  state="disabled" if plan["issues"] else "normal")
        self.run_btn.pack(side="right")
        ttk.Button(foot, text="閉じる", command=self.destroy).pack(side="right", padx=6)
        self.elapsed_var = tk.StringVar(value="")
        ttk.Label(foot, textvariable=self.elapsed_var).pack(side="left")
        ttk.Label(self, text="この画面を閉じても更新は続き、結果はメインのログと状態表示に出ます。",
                  padding=(10, 0, 10, 8)).pack(fill="x")

    def _safe(self, fn):
        """Run a widget update only if this window still exists (review R3:
        the job keeps running and writing even after the window is closed)."""
        try:
            if self.winfo_exists():
                fn()
        except tk.TclError:
            pass

    def _append(self, text: str):
        self.app._on_main(lambda: self._safe(lambda: self._do_append(text)))

    def _do_append(self, text: str):
        self.steps_box.configure(state="normal")
        self.steps_box.insert("end", text + "\n")
        self.steps_box.see("end")
        self.steps_box.configure(state="disabled")

    def _tick(self):
        if self._start_ts is None or not self.winfo_exists():
            return
        try:
            self.elapsed_var.set(f"経過 {int(time.monotonic() - self._start_ts)} 秒")
            self.after(1000, self._tick)
        except tk.TclError:
            pass

    def _start(self):
        if not messagebox.askyesno(self.title(), "内覧・エディタは保存して閉じてから更新してください。開始しますか？"):
            return
        self.run_btn.configure(state="disabled")
        out = update.update_output_dir()
        self._start_ts = time.monotonic()
        self._tick()
        self.app._log(f"モデル更新を開始：出力 {out}")

        def on_step(steps):
            names = " → ".join(f"{s['name']}[{ {'complete':'済','running':'実行中','failed':'失敗'}.get(s['status'], s['status']) }]"
                               for s in steps)
            self.app._set_steps(names)

        def on_line(t):
            self._append(t)
            self.app._log(t)

        def work():
            return update.run_update(self.app.cfg, self.model_dir, out, on_line=on_line, on_step=on_step)

        def done(job):
            self._start_ts = None
            if job.error:
                self.app._log(f"！モデル更新の実行エラー：{job.error}")
                self._safe(lambda: (self._do_append(f"！実行エラー：{job.error}"), self.run_btn.configure(state="normal")))
                return
            outcome: update.UpdateOutcome = job.result
            # The current-model switch is on the app, not this window -- it
            # happens whether or not the window is still open (review R3).
            if outcome.ok:
                self.app.apply_update_success(outcome.newModelDir, outcome.outputDir)
            else:
                self.app._log(f"モデル更新に失敗しました（工程：{outcome.failedStep or '不明'}）。前のモデルと案は維持されています。"
                              f" 理由：{outcome.reason}" + (f" 詳細：{outcome.refreshJson}" if outcome.refreshJson else ""))

            def refresh_window():
                self._do_append(f"\n結果：{outcome.status}（{int(outcome.elapsedSec)}秒）")
                if outcome.ok:
                    self._do_append(f"現行モデルを {paths.to_repo_relative(Path(outcome.newModelDir))} へ切り替えました。")
                    messagebox.showinfo(self.title(), "更新に成功し、現行モデルを新しいものへ切り替えました。")
                else:
                    self._do_append(f"失敗工程：{outcome.failedStep or '(不明)'} / 理由：{outcome.reason}")
                    if outcome.refreshJson:
                        self._do_append(f"詳細：{outcome.refreshJson}")
                    self._do_append("「モデルを選ぶ」で前のモデルへ戻せます。")
                    messagebox.showwarning(self.title(), f"更新に失敗しました（工程：{outcome.failedStep}）。前のモデルを維持しています。")
                    self.run_btn.configure(state="normal")

            self._safe(refresh_window)

        self.app._run_bg("model-update", work, on_done=done)


class ScenarioWindow(tk.Toplevel):
    def __init__(self, app: LauncherApp, model_dir: Path):
        super().__init__(app.root)
        self.app = app
        self.model_dir = model_dir
        self.title("案と比較記録")
        self.geometry("820x600")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self._build_scenarios(nb)
        self._build_comparisons(nb)

    def _build_scenarios(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="保存した案")
        self.sc_tree = ttk.Treeview(f, columns=("name", "scope", "rooms", "created", "note"), show="headings", height=12)
        for col, txt, w in (("name", "名前", 150), ("scope", "対象", 90), ("rooms", "室:仕上げ", 220),
                            ("created", "保存日時", 160), ("note", "メモ", 160)):
            self.sc_tree.heading(col, text=txt)
            self.sc_tree.column(col, width=w)
        self.sc_tree.pack(fill="both", expand=True)
        self._reload_scenarios()
        bar = ttk.Frame(f, padding=(0, 8))
        bar.pack(fill="x")
        ttk.Button(bar, text="現在の保存を案にする", command=self._save_scenario).pack(side="left")
        ttk.Button(bar, text="読込・比較の開き方", command=self._show_hint).pack(side="left", padx=6)
        ttk.Button(bar, text="案フォルダを開く", command=lambda: _open_path(paths.SCENARIOS_DIR)).pack(side="left")

    def _reload_scenarios(self):
        for i in self.sc_tree.get_children():
            self.sc_tree.delete(i)
        for row in scenarios.list_scenarios():
            if row.get("broken"):
                self.sc_tree.insert("", "end", values=("(壊れた案)", "", "", "", row.get("error", "")))
            else:
                self.sc_tree.insert("", "end", values=(row["name"], row["scope"], row["rooms"],
                                                       row["createdAt"], row.get("note", "")))

    def _save_scenario(self):
        name = _ask_text(self, "案の保存", "案の名前")
        if not name:
            return
        note = _ask_text(self, "案の保存", "メモ（任意）", allow_blank=True) or ""

        def work():
            return scenarios.save_current_as_scenario(self.model_dir, name, note)

        def done(job):
            if job.error:
                messagebox.showerror(self.title(), str(job.error))
                return
            r = job.result
            src = {"editor": "エディタの保存", "runtime": "内覧のF5保存"}.get(r.get("stateSource"), r.get("stateSource"))
            self.app._log(f"案を保存しました：{r['name']}（元：{src}）→ {r['path']}")
            messagebox.showinfo(self.title(), f"案「{r['name']}」を保存しました。\n保存元：{src}\n{r['path']}")
            self._reload_scenarios()

        self.app._run_bg("scenario-save", work, on_done=done)

    def _show_hint(self):
        messagebox.showinfo("読込・比較の開き方", scenarios.open_editor_hint())

    def _build_comparisons(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="比較記録（仕上げA/B）")
        self.cmp_tree = ttk.Treeview(f, columns=("name", "created", "images", "note"), show="headings", height=10)
        for col, txt, w in (("name", "名前", 180), ("created", "日時", 170), ("images", "画像", 60), ("note", "メモ", 260)):
            self.cmp_tree.heading(col, text=txt)
            self.cmp_tree.column(col, width=w)
        self.cmp_tree.pack(fill="both", expand=True)
        self._reload_comparisons()
        bar = ttk.Frame(f, padding=(0, 8))
        bar.pack(fill="x")
        ttk.Button(bar, text="仕上げA/Bを記録", command=self._record_ab).pack(side="left")
        ttk.Button(bar, text="選択を開く", command=self._open_selected).pack(side="left", padx=6)
        ttk.Button(bar, text="共有用コピーを作る", command=self._shared_copy).pack(side="left")

    def _reload_comparisons(self):
        for i in self.cmp_tree.get_children():
            self.cmp_tree.delete(i)
        self._records = comparison.list_records()
        for r in self._records:
            self.cmp_tree.insert("", "end", values=(r["name"], r["createdAt"], len(r.get("images", [])), r.get("note", "")))

    def _record_ab(self):
        name = _ask_text(self, "比較記録", "記録の名前")
        if not name:
            return
        note = _ask_text(self, "比較記録", "メモ（任意）", allow_blank=True) or ""
        if not messagebox.askyesno(self.title(), "対象室の仕上げ違い（natural/warm）を固定カメラで撮影します。数分かかります。"):
            return
        self.app._log(f"仕上げA/Bを記録します：{name}")

        def work():
            return comparison.record_finish_ab(self.app.cfg, self.model_dir, name, note, on_line=self.app._log)

        def done(job):
            if job.error:
                messagebox.showerror(self.title(), str(job.error))
                return
            rec: comparison.ComparisonRecord = job.result
            if not rec.ok:
                self.app._log("記録失敗：" + (rec.reason or ""))
                messagebox.showwarning(self.title(), rec.reason or "記録に失敗しました。")
                return
            self.app._log(f"比較記録を保存：{rec.recordDir}（画像 {len(rec.images)} 枚）")
            messagebox.showinfo(self.title(), f"記録しました：{rec.recordDir}")
            self._reload_comparisons()

        self.app._run_bg("comparison-record", work, on_done=done)

    def _selected_record(self):
        sel = self.cmp_tree.selection()
        if not sel:
            messagebox.showinfo(self.title(), "記録を選んでください。")
            return None
        return self._records[self.cmp_tree.index(sel[0])]

    def _open_selected(self):
        rec = self._selected_record()
        if rec:
            _open_path(Path(rec["path"]))

    def _shared_copy(self):
        rec = self._selected_record()
        if not rec:
            return
        out = filedialog.askdirectory(title="共有用コピーの作成先（この中に新しいフォルダを作ります）")
        if not out:
            return
        target = Path(out) / f"comparison-shared-{Path(rec['path']).name}"
        try:
            result = comparison.build_shared_copy(Path(rec["path"]), target)
        except ValueError as e:
            messagebox.showerror(self.title(), str(e))
            return
        self.app._log(f"共有用コピーを作成：{result['outDir']}（画像 {result['images']} 枚、絶対パス・座標・ログ・元JSONなし）")
        messagebox.showinfo(self.title(), f"共有用コピーを作成しました：\n{result['outDir']}\n"
                                          "自動公開・送信はしていません。")
        _open_path(target)


class ChooseModelWindow(tk.Toplevel):
    def __init__(self, app: LauncherApp):
        super().__init__(app.root)
        self.app = app
        self.title("モデルを選ぶ")
        self.geometry("820x480")
        ttk.Label(self, text="生成済みの guest プロジェクトを検出しました。scope・取込成功・内覧構築を確認しています。\n"
                             "日付やフォルダ名だけで最新版を決めません。",
                  padding=10, justify="left").pack(fill="x")
        self.tree = ttk.Treeview(self, columns=("valid", "path", "updated", "note"), show="headings", height=14)
        for col, txt, w in (("valid", "状態", 70), ("path", "場所", 300), ("updated", "更新日時", 170), ("note", "備考", 240)):
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w)
        self.tree.pack(fill="both", expand=True, padx=10)
        self._infos = models.detect_candidates()
        for info in self._infos:
            self.tree.insert("", "end", values=("有効" if info.valid else "要確認", info.label,
                                                info.updatedAt or "?", " / ".join(info.reasons) or "問題なし"))
        bar = ttk.Frame(self, padding=10)
        bar.pack(fill="x")
        ttk.Button(bar, text="別のフォルダを選ぶ…", command=self._browse).pack(side="left")
        ttk.Button(bar, text="選択を登録して現行にする", command=self._register).pack(side="right")

    def _register(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(self.title(), "モデルを選んでください。")
            return
        info = self._infos[self.tree.index(sel[0])]
        if not info.valid and not messagebox.askyesno(self.title(),
                                                      "このモデルは要確認です：\n" + "\n".join(info.reasons) +
                                                      "\n\nそれでも登録しますか？"):
            return
        self.app.cfg.set_current_model(info.path)
        _config.save(self.app.cfg)
        self.app._log(f"現行モデルを登録：{info.label}")
        self.app._refresh_status()
        self.destroy()

    def _browse(self):
        d = filedialog.askdirectory(title="UEプロジェクトのフォルダ（RyukaInterior.uproject がある場所）")
        if not d:
            return
        info = models.inspect_project(Path(d))
        if not info.valid and not messagebox.askyesno(self.title(),
                                                      "要確認：\n" + "\n".join(info.reasons) + "\n\n登録しますか？"):
            return
        self.app.cfg.set_current_model(info.path)
        _config.save(self.app.cfg)
        self.app._log(f"現行モデルを登録：{info.label}")
        self.app._refresh_status()
        self.destroy()


class SettingsWindow(tk.Toplevel):
    def __init__(self, app: LauncherApp):
        super().__init__(app.root)
        self.app = app
        self.title("設定（機械固有・git除外）")
        self.geometry("720x300")
        self.vars = {}
        rows = [("enginePath", "Unreal Engine フォルダ", app.cfg.enginePath),
                ("blenderPath", "blender.exe", app.cfg.blenderPath),
                ("cachePath", "DDC cache フォルダ（119文字以内）", app.cfg.cachePath)]
        for i, (key, label, val) in enumerate(rows):
            ttk.Label(self, text=label).grid(row=i, column=0, sticky="w", padx=10, pady=8)
            v = tk.StringVar(value=val)
            self.vars[key] = v
            ttk.Entry(self, textvariable=v, width=64).grid(row=i, column=1, padx=6)
            ttk.Button(self, text="選ぶ", command=lambda k=key: self._browse(k)).grid(row=i, column=2, padx=6)
        ttk.Label(self, text="この設定は build/launcher/config.json（git除外）に保存されます。",
                  padding=10).grid(row=len(rows), column=0, columnspan=3, sticky="w")
        ttk.Button(self, text="保存", command=self._save).grid(row=len(rows) + 1, column=1, sticky="e", pady=10)

    def _browse(self, key):
        if key == "blenderPath":
            p = filedialog.askopenfilename(title="blender.exe")
        else:
            p = filedialog.askdirectory(title="フォルダ")
        if p:
            self.vars[key].set(p)

    def _save(self):
        for k, v in self.vars.items():
            setattr(self.app.cfg, k, v.get())
        _config.save(self.app.cfg)
        self.app._refresh_status()
        problems = self.app.cfg.missing_dependencies()
        if problems:
            messagebox.showwarning(self.title(), "\n".join(problems))
        else:
            messagebox.showinfo(self.title(), "保存しました。")
        self.destroy()


# ---------- small helpers ----------
def _ask_text(parent, title, prompt, allow_blank=False):
    top = tk.Toplevel(parent)
    top.title(title)
    top.geometry("420x130")
    top.transient(parent)
    top.grab_set()
    ttk.Label(top, text=prompt, padding=10).pack(anchor="w")
    var = tk.StringVar()
    ent = ttk.Entry(top, textvariable=var, width=48)
    ent.pack(padx=10)
    ent.focus_set()
    result = {"value": None}

    def ok():
        v = var.get().strip()
        if not v and not allow_blank:
            return
        result["value"] = v
        top.destroy()

    bar = ttk.Frame(top, padding=10)
    bar.pack(fill="x")
    ttk.Button(bar, text="OK", command=ok).pack(side="right")
    ttk.Button(bar, text="取消", command=top.destroy).pack(side="right", padx=6)
    ent.bind("<Return>", lambda e: ok())
    parent.wait_window(top)
    return result["value"]


def _open_path(path: Path):
    path = Path(path)
    try:
        import os
        if path.is_dir():
            os.startfile(str(path))  # noqa: S606 - Windows explorer on a local dir
        else:
            webbrowser.open(path.as_uri())
    except Exception:  # noqa: BLE001
        messagebox.showinfo(APP_TITLE, str(path))


def main(argv=None):
    root = tk.Tk()
    try:
        root.call("tk", "scaling", 1.2)
    except tk.TclError:
        pass
    LauncherApp(root)
    root.mainloop()
    return 0
