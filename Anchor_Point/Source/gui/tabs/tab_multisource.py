"""MultiSource AniList workflow GUI.

Thin front-end over the validated ``src/main.py sync-all`` pipeline.  The GUI
never reimplements resolver/sync rules; it launches the same CLI entrypoint so
backup, plan binding, drift detection, quarantine, logging and verification stay
identical to the production command-line workflow.
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys
import threading
from pathlib import Path
from gui.paths import storage_data_dir
from tkinter import filedialog, messagebox

import customtkinter as ctk

from gui.logbox import LogBox


class MultiSourceTab:
    def __init__(self, frame: ctk.CTkFrame, app) -> None:
        self.frame = frame
        self.app = app
        self._proc: subprocess.Popen | None = None
        self._build()
        self.refresh_summary()

    def _build(self) -> None:
        f = self.frame
        f.columnconfigure(0, weight=1)
        f.rowconfigure(3, weight=1)

        title = ctk.CTkFrame(f, fg_color="transparent")
        title.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        title.columnconfigure(0, weight=1)
        ctk.CTkLabel(title, text="Sync",
                     font=ctk.CTkFont(size=20, weight="bold"), anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(title,
                     text="Update your anime lists from enabled watch-history sources. Preview first, then apply safe changes to AniList or MAL.",
                     text_color=("gray45", "gray65"), anchor="w").grid(row=1, column=0, sticky="w", pady=(2, 0))

        # Source inclusion controls. These decide which stored provider datasets
        # participate in consolidation; unchecking never deletes provider history.
        sources = ctk.CTkFrame(f, corner_radius=8)
        sources.grid(row=1, column=0, sticky="ew", padx=14, pady=6)
        ctk.CTkLabel(sources, text="Include in Sync", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(12,16), pady=12)
        prefs=self.app.cfg.setdefault("multisource",{}).setdefault("include",{})
        self._include_vars={}
        for key,label in (("crunchyroll","Crunchyroll"),("hidive","HIDIVE"),("netflix","Netflix"),("manual","Manual Entry")):
            v=ctk.BooleanVar(value=bool(prefs.get(key,True))); self._include_vars[key]=v
            ctk.CTkCheckBox(sources,text=label,variable=v,command=self._save_source_prefs).pack(side="left",padx=8,pady=12)

        # Plan summary + actions
        actions = ctk.CTkFrame(f, corner_radius=8)
        actions.grid(row=2, column=0, sticky="ew", padx=14, pady=6)
        actions.columnconfigure(0, weight=1)
        self._summary = ctk.CTkLabel(actions, text="No sync plan generated yet. Click Preview Sync Changes to analyze your enabled sources.", anchor="w",
                                     font=ctk.CTkFont(size=13, weight="bold"))
        self._summary.grid(row=0, column=0, columnspan=4, sticky="ew", padx=12, pady=(10, 8))
        self._preview_btn = ctk.CTkButton(actions, text="Preview Sync Changes", width=155, command=self._preview)
        self._preview_btn.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))
        self._apply_btn = ctk.CTkButton(actions, text="Sync Safe Changes to AniList", width=190, command=self._apply)
        self._apply_btn.grid(row=1, column=1, sticky="w", padx=6, pady=(0, 10))
        self._mal_btn = ctk.CTkButton(actions, text="Sync Safe Changes to MAL", width=180, command=self._apply_mal)
        self._mal_btn.grid(row=1, column=2, sticky="w", padx=6, pady=(0, 10))
        self._cancel_btn = ctk.CTkButton(actions, text="Cancel Workflow", width=130, command=self._cancel,
                                         fg_color=("#a64b4b", "#8b3a3a"), state="disabled")
        self._cancel_btn.grid(row=1, column=3, sticky="w", padx=6, pady=(0, 10))
        tools=ctk.CTkFrame(actions,fg_color="transparent"); tools.grid(row=2,column=0,columnspan=4,sticky="w",padx=12,pady=(0,10))
        ctk.CTkButton(tools, text="Refresh Summary", width=120, command=self.refresh_summary,
                      fg_color=("gray60", "gray35")).pack(side="left",padx=(0,6))
        ctk.CTkButton(tools, text="Open Data Folder", width=120, command=self._open_data,
                      fg_color=("gray60", "gray35")).pack(side="left")
        self._first_run_note=ctk.CTkLabel(actions, text=("First sync may take longer: Anchor Point must identify and match existing titles/seasons on the initial analysis. "
            "Safe resolved data labels are saved locally, so future previews reuse known matches and should be substantially faster."),
            text_color=("gray45","gray65"), anchor="w", justify="left", wraplength=880)
        self._first_run_note.grid(row=3,column=0,columnspan=4,sticky="ew",padx=12,pady=(0,10))

        log_frame = ctk.CTkFrame(f, fg_color="transparent")
        log_frame.grid(row=3, column=0, sticky="nsew", padx=14, pady=(4, 10))
        log_frame.columnconfigure(0, weight=1); log_frame.rowconfigure(1, weight=1)
        ctk.CTkLabel(log_frame, text="Workflow log", anchor="w").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._log = LogBox(log_frame, height=230)
        self._log.grid(row=1, column=0, sticky="nsew")

    def _data_dir(self) -> Path:
        return storage_data_dir(self.app.cfg, self.app.data_root)

    def _browse_netflix(self) -> None:
        p = filedialog.askopenfilename(title="Select Netflix ViewingActivity CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if p:
            self._netflix_path.set(p)

    def _open_data(self) -> None:
        p = self._data_dir()
        p.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(p)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except Exception as e:
            messagebox.showerror("Open folder", str(e))

    @staticmethod
    def _read_rows(path: Path) -> list[dict]:
        if not path.exists():
            return []
        with open(path, newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def refresh_summary(self) -> None:
        r = self._data_dir() / "resolved"
        plan = self._read_rows(r / "sync_plan.csv")
        review = self._read_rows(r / "review.csv")
        held = self._read_rows(r / "sync_review.csv")
        rejected = self._read_rows(r / "sync_rejected.csv")
        blocked = self._read_rows(r / "sync_blockers.csv")
        if not plan and not (r / "sync_plan.csv").exists():
            self._summary.configure(text="No sync plan generated yet. Click Preview Sync Changes to analyze your enabled sources.")
            return
        adds = sum(x.get("action") == "ADD" for x in plan)
        updates = sum(x.get("action") == "UPDATE" for x in plan)
        skips = sum(x.get("action") == "SKIP" for x in plan)
        self._summary.configure(text=(f"Plan: {adds} ADD  •  {updates} UPDATE  •  {skips} SKIP  |  "
                                      f"{len(review)} resolver review  •  {len(held)} held  •  "
                                      f"{len(blocked)} blocked  •  {len(rejected)} rejected"))

    def _save_source_prefs(self) -> None:
        inc=self.app.cfg.setdefault("multisource",{}).setdefault("include",{})
        for k,v in self._include_vars.items(): inc[k]=bool(v.get())
        self.app.save_config()

    def _base_args(self) -> list[str]:
        enabled=[k for k,v in self._include_vars.items() if v.get()]
        args=["sync-all","--sources",",".join(enabled) if enabled else "none"]
        # On-demand live refresh is automatic for enabled authenticated sources.
        if "crunchyroll" in enabled and self.app.cfg.get("crunchyroll",{}).get("etp_rt",""):
            args.append("--fetch-crunchyroll")
        if "hidive" in enabled and self.app.cfg.get("hidive",{}).get("bearer_token",""):
            # The child CLI reads the locally saved HIDIVE credentials from config.yaml.
            # Do not place authentication material on the OS clipboard or command line.
            args.append("--fetch-hidive")
        return args

    def _preview(self) -> None:
        self._run(self._base_args())

    def _apply(self) -> None:
        r = self._data_dir() / "resolved"
        plan = self._read_rows(r / "sync_plan.csv")
        writable = [x for x in plan if x.get("action") in {"ADD", "UPDATE"}]
        if not writable:
            messagebox.showinfo("AniList sync", "There are no safe ADD/UPDATE changes in the current plan. Run Resolve & Preview first if history changed.")
            return
        adds = sum(x.get("action") == "ADD" for x in writable)
        updates = sum(x.get("action") == "UPDATE" for x in writable)
        blocked = len(self._read_rows(r / "sync_blockers.csv")) + len(self._read_rows(r / "sync_review.csv"))
        msg = (f"Apply {adds} ADD and {updates} UPDATE entries to AniList?\n\n"
               f"{blocked} review/blocker rows will remain quarantined.\n"
               "A timestamped AniList backup will be created before any write.")
        if not messagebox.askyesno("Confirm AniList sync", msg):
            return
        # Re-resolve/re-plan immediately before applying; the CLI then independently
        # validates account, plan hash, remote drift, backup and post-write state.
        args = self._base_args() + ["--apply", "--confirm", "APPLY", "--allow-partial"]
        self._run(args)

    def _cancel(self) -> None:
        proc=self._proc
        if proc is None:
            return
        self._log.append("Cancellation requested. Stopping further workflow processing...", "warn")
        try:
            proc.terminate()
            def ensure_stopped() -> None:
                try:
                    proc.wait(timeout=3)
                    self.frame.after(0, lambda: self._log.append("Workflow cancelled and process stopped.", "warn"))
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                        proc.wait(timeout=2)
                        self.frame.after(0, lambda: self._log.append("Workflow did not stop promptly; it was force-stopped.", "warn"))
                    except Exception as e:
                        self.frame.after(0, lambda e=e: self._log.append(f"Unable to confirm workflow stopped: {e}", "error"))
            threading.Thread(target=ensure_stopped, daemon=True).start()
        except Exception as e:
            self._log.append(f"Unable to request cancellation: {e}", "error")

    def _apply_mal(self) -> None:
        cfg=self.app.cfg.get("exporters",{}).get("mal",{})
        token=(cfg.get("access_token") or "").strip()
        if not token:
            messagebox.showinfo("MAL sync", "Configure MyAnimeList in Export & Sync Settings before syncing.")
            return
        mapping=self._read_rows(self._data_dir() / "resolved" / "mapping.csv")
        safe=[r for r in mapping if r.get("decision")=="AUTO" and str(r.get("mal_id") or "").strip()]
        if not safe:
            messagebox.showinfo("MAL sync", "No safely resolved MAL mappings are available. Run Preview Sync Changes first.")
            return
        if not messagebox.askyesno("Confirm MAL sync", f"Check {len(safe)} safely resolved mappings against MAL and apply only progress increases?\n\nExisting MAL progress will never be reduced."):
            return
        self._log.clear(); self._set_busy(True)
        def worker():
            ok=True; changed=skipped=failed=0
            try:
                from src.exporters.mal import MALExporter
                exp=MALExporter(token)
                consolidated={}
                for r in safe:
                    try: mid=int(float(r.get("mal_id") or 0)); progress=int(float(r.get("progress") or 0))
                    except Exception: continue
                    if not mid: continue
                    cur=consolidated.get(mid)
                    if cur is None or progress>cur["progress"]:
                        consolidated[mid]={"progress":progress,"title":r.get("anilist_title") or r.get("title") or str(mid),"episodes":int(float(r.get("anilist_episodes") or 0)) if r.get("anilist_episodes") else 0}
                total=len(consolidated)
                self.frame.after(0,lambda: self._log.append("== MyAnimeList ======================================", "info"))
                self.frame.after(0,lambda: self._log.append("Note: Syncing changes may take some time. Keep Anchor Point open until the sync is complete.", "warn"))
                for n,(mid,item) in enumerate(consolidated.items(),1):
                    try:
                        current=exp._current_status(mid) or {}
                        old=int(current.get("num_episodes_watched") or 0)
                        target=item["progress"]
                        if old>=target:
                            skipped+=1
                        else:
                            from src.crunchyroll.models import SeriesSummary
                            ss=SeriesSummary(series_id=f"mal::{mid}",series_title=item["title"],season_number=1,episodes_watched=list(range(1,target+1)),max_episode=target)
                            status="completed" if item["episodes"] and target>=item["episodes"] else "watching"
                            exp._update_list(mid,status,ss); changed+=1
                    except Exception:
                        failed+=1; ok=False
                    if n==1 or n%10==0 or n==total:
                        self.frame.after(0,lambda a=n,b=total:self._log.append(f"MAL progress: {a} / {b}","info"))
                self.frame.after(0,lambda:self._log.append(f"MAL sync complete. Updated: {changed}  •  Already current: {skipped}  •  Failed: {failed}","ok" if failed==0 else "warn"))
            except Exception as e:
                ok=False; self.frame.after(0,lambda:self._log.append(f"MAL workflow error: {e}","error"))
            finally:
                self.frame.after(0,lambda:self._set_busy(False))
        threading.Thread(target=worker,daemon=True).start()

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self._preview_btn.configure(state=state)
        self._apply_btn.configure(state=state)
        self._mal_btn.configure(state=state)
        self._cancel_btn.configure(state="normal" if busy else "disabled")

    def _command(self, cli_args: list[str]) -> list[str]:
        # main.py exposes --multisource-cli in both script and PyInstaller modes,
        # keeping config/data rooted next to the app while using the bundled core.
        if getattr(sys, "frozen", False):
            return [sys.executable, "--multisource-cli", *cli_args]
        return [sys.executable, str(self.app.project_root / "main.py"), "--multisource-cli", *cli_args]

    def _run(self, cli_args: list[str]) -> None:
        if self._proc is not None:
            return
        self._log.clear(); self._set_busy(True)

        def worker() -> None:
            ok = False
            try:
                cmd = self._command(cli_args)
                self._proc = subprocess.Popen(cmd, cwd=str(self.app.data_root), stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                              errors="replace", bufsize=1)
                assert self._proc.stdout is not None
                for line in self._proc.stdout:
                    msg = line.rstrip()
                    self.frame.after(0, lambda m=msg: self._log.append(m, "info"))
                rc = self._proc.wait()
                ok = rc == 0
                if rc != 0:
                    self.frame.after(0, lambda: self._log.append("Workflow stopped before completion. No new destination sync is started after cancellation.", "warn"))
            except Exception as e:
                self.frame.after(0, lambda: self._log.append(f"GUI workflow error: {e}", "error"))
            finally:
                self._proc = None
                def finish():
                    self._set_busy(False); self.refresh_summary(); self.app.refresh_status()
                    if ok: self._log.append("Workflow finished successfully.", "ok")
                self.frame.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()
