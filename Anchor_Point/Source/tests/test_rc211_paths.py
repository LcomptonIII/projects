from pathlib import Path
from types import SimpleNamespace

from gui.paths import storage_data_dir
import src.main as main_mod


def test_storage_data_dir_follows_custom_absolute_storage_parent(tmp_path):
    custom = tmp_path / "custom-store" / "history.json"
    cfg = {"storage": {"path": str(custom)}}
    assert storage_data_dir(cfg, tmp_path / "install") == custom.parent


def test_storage_data_dir_resolves_relative_storage_from_app_root(tmp_path):
    cfg = {"storage": {"path": "custom/history.json"}}
    assert storage_data_dir(cfg, tmp_path) == tmp_path / "custom"


def test_export_xml_resolves_relative_path_against_config_dir(tmp_path, monkeypatch):
    config_dir = tmp_path / "config-home"
    config_dir.mkdir()
    cfg = {"exporters": {"mal_xml": {"path": "exports/animelist.xml"}}}
    ctx = SimpleNamespace(obj={"config": cfg, "config_path": str(config_dir / "config.yaml")})
    captured = {}

    class FakeExporter:
        def __init__(self, path):
            captured["path"] = Path(path)
        def export(self, summaries):
            return SimpleNamespace(updated=list(summaries))

    monkeypatch.setattr(main_mod, "MALXMLExporter", FakeExporter)
    main_mod._export_xml(ctx, ["one"])

    assert captured["path"] == (config_dir / "exports" / "animelist.xml").resolve()
