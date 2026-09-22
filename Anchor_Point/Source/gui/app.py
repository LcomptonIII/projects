import sys
import yaml
from pathlib import Path
import customtkinter as ctk

from gui import i18n
from gui.paths import resource_root, data_root

_PROJECT_ROOT = Path(__file__).parent.parent


class App(ctk.CTk):
    def __init__(self):
        # resource_root → locales/, src/, images  (sys._MEIPASS when frozen)
        # data_root     → config.yaml, data/      (next to exe when frozen)
        self.project_root: Path = resource_root()
        self.data_root:    Path = data_root()
        self.config_path:  Path = self.data_root / "config.yaml"
        self.cfg: dict          = self._load_config()

        # 1.0 exposes only the completed English localization.
        i18n.load("en")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        super().__init__()

        self.title(i18n.t("app_title"))
        self.geometry("980x700")
        self.minsize(820, 580)
        self._set_icon()
        self._build_ui()
        self._setup_tray()
        self._check_for_update()

    # ------------------------------------------------------------------ config

    def _load_config(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def save_config(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self.cfg, f, allow_unicode=True,
                      default_flow_style=False, sort_keys=False)
        # Always refresh the status bar after saving
        self.refresh_status()

    def refresh_status(self) -> None:
        if hasattr(self, "statusbar"):
            self.statusbar.refresh()

    # ------------------------------------------------------------------ tray

    def _setup_tray(self) -> None:
        self.tray = None
        self.apply_tray_setting()

    def apply_tray_setting(self) -> None:
        """Start or stop the tray icon based on the current config value.
        Safe to call at any time — handles transitions in both directions."""
        enabled = self.cfg.get("ui", {}).get("tray_enabled", False)

        if enabled:
            if self.tray is None:
                from gui.tray import TrayIcon
                self.tray = TrayIcon(self)
                self.tray.start()
            self.protocol("WM_DELETE_WINDOW", self._on_close_btn)
        else:
            if self.tray is not None:
                self.tray.stop()
                self.tray = None
            # Restore normal close behaviour
            self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _on_close_btn(self) -> None:
        """Hide window to tray. The app keeps running; Exit from tray to quit."""
        self.withdraw()
        if self.tray:
            self.tray.notify(i18n.t("tray_minimized_hint"))

    # ------------------------------------------------------------------ icon

    def _set_icon(self) -> None:
        icon_png = self.project_root / "anchorpointlogo.png"
        if not icon_png.exists():
            return
        try:
            from PIL import Image, ImageTk
            img = Image.open(icon_png).convert("RGBA")

            # The bundled ICO is authoritative and already contains the full
            # Windows multi-resolution set. Never regenerate it at runtime.
            ico_path = icon_png.with_suffix(".ico")
            if ico_path.exists():
                self.iconbitmap(str(ico_path))

            # On Windows, iconbitmap() lets the shell select the native frame
            # from the embedded multi-resolution ICO. Calling iconphoto() here
            # can replace that HICON with a Tk-generated raster and cause the
            # taskbar icon to be rescaled/blurred at non-100% DPI.
            if sys.platform != "win32":
                sizes = (16, 24, 32, 48, 64, 128, 256)
                self._icon_photos = [
                    ImageTk.PhotoImage(img.resize((size, size), Image.Resampling.LANCZOS))
                    for size in sizes
                ]
                self.iconphoto(True, *self._icon_photos)
        except Exception:
            pass

    # ------------------------------------------------------------------ update check

    def _check_for_update(self) -> None:
        import threading

        def worker():
            from gui.update_check import check_for_update
            tag = check_for_update()
            if tag:
                self.after(0, lambda: self.tab_config.set_update_available(tag))

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        from gui.tabs.tab_multisource import MultiSourceTab
        from gui.tabs.tab_sources import CrunchyrollTab, HidiveTab, NetflixTab, ManualEntryTab
        from gui.tabs.tab_status import StatusTab
        from gui.tabs.tab_export import ExportTab
        from gui.tabs.tab_config import ConfigTab
        from gui.tabs.tab_schedule import ScheduleTab
        from gui.statusbar import StatusBar

        nav_bg=ctk.CTkFrame(self,height=48,corner_radius=0,fg_color=("gray80","gray17")); nav_bg.pack(fill="x"); nav_bg.pack_propagate(False)
        nav_values=["Sync","Crunchyroll","HIDIVE","Netflix","Manual Entry","My Library","Schedule","Export","Export & Sync Settings"]
        self._nav_keys={v:k for v,k in zip(nav_values,["sync","crunchyroll","hidive","netflix","manual","library","schedule","export","settings"])}
        self._nav=ctk.CTkSegmentedButton(nav_bg,values=nav_values,command=self._on_nav,font=ctk.CTkFont(size=11)); self._nav.pack(fill="x",padx=8,pady=8); self._nav.set("Sync")
        self.statusbar=StatusBar(self,self); self.statusbar.pack(fill="x")
        content=ctk.CTkFrame(self,fg_color="transparent"); content.pack(fill="both",expand=True,padx=8,pady=(4,8)); content.columnconfigure(0,weight=1); content.rowconfigure(0,weight=1)
        self._frames={k:ctk.CTkFrame(content,fg_color="transparent") for k in self._nav_keys.values()}
        for f in self._frames.values(): f.grid(row=0,column=0,sticky="nsew")
        self.tab_fetch=MultiSourceTab(self._frames["sync"],self)
        self.tab_crunchyroll=CrunchyrollTab(self._frames["crunchyroll"],self)
        self.tab_hidive=HidiveTab(self._frames["hidive"],self)
        self.tab_netflix=NetflixTab(self._frames["netflix"],self)
        self.tab_manual=ManualEntryTab(self._frames["manual"],self)
        self.tab_status=StatusTab(self._frames["library"],self)
        self.tab_schedule=ScheduleTab(self._frames["schedule"],self)
        self.tab_export=ExportTab(self._frames["export"],self)
        self.tab_config=ConfigTab(self._frames["settings"],self)
        self._show("sync")

    # ------------------------------------------------------------------ nav

    def _on_nav(self, value: str) -> None:
        key = self._nav_keys.get(value, "sync")
        self._show(key)
        # Refresh export tab status indicators when the user opens it
        if key == "export":
            self.tab_export.refresh_status()

    def _show(self, key: str) -> None:
        self._frames[key].tkraise()
