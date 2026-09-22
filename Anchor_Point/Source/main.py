import sys
import ctypes
from pathlib import Path

_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Declare DPI awareness before Tk creates any windows.  Without this, Windows
# may bitmap-scale the application (including its taskbar/title-bar icons) on
# displays using 125%/150%/200% scaling.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()   # older Windows fallback
    except Exception:
        pass

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "AnchorPoint"
    )
except Exception:
    pass


def _headless_sync(target: str = "all") -> None:
    """
    Silent fetch + export for scheduled tasks and tray sync when running
    as a frozen exe  (AnchorPoint.exe --headless-sync [--target all]).

    When running as a plain script, schedule and tray call
    src/main.py sync directly — this function is never reached.
    """
    import yaml
    from gui.paths import data_root

    dr = data_root()
    config_path = dr / "config.yaml"
    if not config_path.exists():
        print("config.yaml not found")
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    etp_rt = cfg.get("crunchyroll", {}).get("etp_rt", "").strip()
    if not etp_rt:
        print("No etp_rt cookie in config.yaml")
        sys.exit(1)

    from src.crunchyroll.auth import CRAuth, DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET
    from src.crunchyroll.history import CRHistory
    from src.storage.history_store import HistoryStore
    from src.exporters.anilist import AniListExporter
    from src.exporters.mal import MALExporter
    from src.exporters.mal_xml import MALXMLExporter

    cr_cfg     = cfg.get("crunchyroll", {})
    store_path = cfg.get("storage", {}).get("path", "data/history.json")
    store_p    = Path(store_path) if Path(store_path).is_absolute() else dr / store_path

    print("Logging in to Crunchyroll...")
    auth  = CRAuth(
        client_id=cr_cfg.get("client_id") or DEFAULT_CLIENT_ID,
        client_secret=cr_cfg.get("client_secret") or DEFAULT_CLIENT_SECRET,
    )
    token = auth.login_with_etp_rt(etp_rt)
    print(f"Logged in: {token.account_id}")

    episodes = CRHistory(token).fetch_all(cfg.get("locale", "en-US"))
    store    = HistoryStore(store_p)
    added    = store.update(episodes)
    print(f"Sync: {added} new episodes (total {len(store)})")

    summaries = store.series_summaries()
    exp_cfg   = cfg.get("exporters", {})

    if target in ("anilist", "all"):
        tok = exp_cfg.get("anilist", {}).get("access_token", "").strip()
        if tok:
            r = AniListExporter(tok).export(summaries)
            print(f"AniList: {len(r.updated)} updated, {len(r.failed)} failed")

    if target in ("mal", "all"):
        tok = exp_cfg.get("mal", {}).get("access_token", "").strip()
        if tok:
            r = MALExporter(tok).export(summaries)
            print(f"MAL: {len(r.updated)} updated, {len(r.failed)} failed")

    if target in ("xml", "all"):
        xml_path = exp_cfg.get("mal_xml", {}).get("path", "data/animelist.xml")
        xml_p = Path(xml_path) if Path(xml_path).is_absolute() else dr / xml_path
        MALXMLExporter(str(xml_p)).export(summaries)
        print(f"XML: {xml_p}")


if __name__ == "__main__":
    if "--multisource-cli" in sys.argv:
        # Forward directly into the validated MultiSource Click CLI.  This path
        # also works from a frozen executable, allowing the GUI to use exactly
        # the same resolver/sync engine as command-line users.
        idx = sys.argv.index("--multisource-cli")
        forwarded = sys.argv[idx + 1:]
        from src.main import cli
        cli.main(args=forwarded, prog_name="AnchorPoint", standalone_mode=True)
    elif "--headless-sync" in sys.argv:
        target = "all"
        for i, arg in enumerate(sys.argv):
            if arg == "--target" and i + 1 < len(sys.argv):
                target = sys.argv[i + 1]
        _headless_sync(target)
    else:
        from gui.paths import data_root
        log_path = data_root() / "startup_error.log"
        try:
            from gui.app import App
            App().mainloop()
        except Exception:
            import traceback
            try:
                log_path.write_text(traceback.format_exc(), encoding="utf-8")
            except Exception:
                pass
            raise
