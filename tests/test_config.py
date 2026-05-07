from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_config_merges_missing_keys_from_legacy_appdata(monkeypatch, tmp_path: Path):
    home_dir = tmp_path / "home"
    appdata_dir = tmp_path / "appdata"
    home_dir.mkdir(parents=True)
    appdata_dir.mkdir(parents=True)

    primary = home_dir / ".config" / "fl_editor" / "config.json"
    primary.parent.mkdir(parents=True)
    primary.write_text('{"theme":"dark"}', encoding="utf-8")

    legacy = appdata_dir / "fl_editor" / "config.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"storage.single_path":"C:/LegacyMod","theme":"light"}', encoding="utf-8")

    monkeypatch.setenv("APPDATA", str(appdata_dir))
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    import fl_editor.config as config_module

    config_module = importlib.reload(config_module)
    cfg = config_module.Config()

    assert cfg.get("theme") == "dark"
    assert cfg.get("storage.single_path") == "C:/LegacyMod"
    saved = primary.read_text(encoding="utf-8")
    assert '"storage.single_path": "C:/LegacyMod"' in saved


def test_config_move_to_sets_storage_pointer_and_keeps_current_data(monkeypatch, tmp_path: Path):
    home_dir = tmp_path / "home"
    appdata_dir = tmp_path / "appdata"
    home_dir.mkdir(parents=True)
    appdata_dir.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata_dir))
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    import fl_editor.config as config_module

    config_module = importlib.reload(config_module)
    cfg = config_module.Config()
    cfg.set("theme", "dark")

    moved_path = tmp_path / "custom" / "flatlas.json"
    cfg.move_to(moved_path)

    pointer = home_dir / ".config" / "fl_editor" / "config-location.json"
    assert json.loads(pointer.read_text(encoding="utf-8"))["config_path"] == str(moved_path)
    assert json.loads(moved_path.read_text(encoding="utf-8"))["theme"] == "dark"

    reloaded = config_module.Config()
    assert reloaded.path == moved_path
    assert reloaded.get("theme") == "dark"


def test_config_save_creates_backup_before_overwriting(monkeypatch, tmp_path: Path):
    home_dir = tmp_path / "home"
    appdata_dir = tmp_path / "appdata"
    home_dir.mkdir(parents=True)
    appdata_dir.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata_dir))
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    import fl_editor.config as config_module

    config_module = importlib.reload(config_module)
    cfg = config_module.Config()
    cfg.set("theme", "dark")
    cfg.set("theme", "light")

    backups = list((home_dir / ".config" / "fl_editor" / "backups").glob("config-*.json"))
    assert backups
    assert any(json.loads(path.read_text(encoding="utf-8")).get("theme") == "dark" for path in backups)

