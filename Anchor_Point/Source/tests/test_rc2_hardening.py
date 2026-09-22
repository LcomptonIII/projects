from pathlib import Path
from click.testing import CliRunner
import src.main as main


def test_relative_storage_path_resolves_against_config_dir(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("storage:\n  path: data/history.json\n", encoding="utf-8")
    ctx = type("C", (), {"obj": {"config": {"storage": {"path": "data/history.json"}}, "config_path": str(cfg)}})()
    assert main._history_path(ctx) == tmp_path / "data" / "history.json"


def test_custom_storage_path_defines_multisource_data_dir(tmp_path):
    cfg = tmp_path / "config.yaml"
    custom = tmp_path / "AnimeData" / "history.json"
    cfg.write_text(f"storage:\n  path: '{custom.as_posix()}'\n", encoding="utf-8")
    ctx = type("C", (), {"obj": {"config": {"storage": {"path": str(custom)}}, "config_path": str(cfg)}})()
    assert main._history_path(ctx) == custom
    assert main._data_dir(ctx) == custom.parent
    assert main._resolved_dir(ctx) == custom.parent / "resolved"


def test_cache_schema_constant_is_versioned():
    assert main.RESOLUTION_CACHE_SCHEMA.startswith("anchorpoint-resolver-cache-v")
