from __future__ import annotations

import importlib
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

