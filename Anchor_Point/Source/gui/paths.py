"""
Path helpers for frozen (PyInstaller) vs script execution.

  resource_root()  →  bundled files: locales/, src/, images
                       sys._MEIPASS when frozen, project root when script

  data_root()      →  user files: config.yaml, data/
                       directory next to the exe when frozen,
                       project root when script
"""

import sys
from pathlib import Path


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)           # type: ignore[attr-defined]
    return Path(__file__).parent.parent


def data_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent  # next to AnchorPoint.exe
    return Path(__file__).parent.parent


def storage_data_dir(cfg: dict, root: Path) -> Path:
    """Return the directory containing the configured history store and source artifacts."""
    store_path = Path(cfg.get("storage", {}).get("path", "data/history.json")).expanduser()
    if not store_path.is_absolute():
        store_path = root / store_path
    return store_path.parent
