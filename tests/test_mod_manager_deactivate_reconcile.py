from __future__ import annotations

from pathlib import Path

import pytest

from fl_editor import config as config_module
from fl_editor.main_window import MainWindow


class _ProgressStub:
    def __init__(self, maximum: int):
        self._maximum = int(maximum)

    def setValue(self, _value: int):
        return None

    def maximum(self) -> int:
        return self._maximum

    def close(self):
        return None


@pytest.fixture
def main_window(monkeypatch, qapp, tmp_path):
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.json")
    window = MainWindow()
    yield window
    window.close()


def test_mod_manager_deactivate_reconciles_missing_relpaths_from_flmm_source(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    source = tmp_path / "mods" / "flmm_mod"
    source.mkdir(parents=True)
    (source / "script.xml").write_text("<script></script>", encoding="utf-8")
    payload = source / "DATA" / "EQUIPMENT" / "engine_good.ini"
    payload.parent.mkdir(parents=True)
    payload.write_text("[Good]\n", encoding="utf-8")

    target_root = tmp_path / "clean"
    target_root.mkdir()
    target_payload = target_root / "DATA" / "EQUIPMENT" / "engine_good.ini"
    target_payload.parent.mkdir(parents=True)
    target_payload.write_text("modded\n", encoding="utf-8")

    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()

    profile = {"id": "mod-a", "name": "FLMM Mod", "mode": "repo"}
    main_window._mm_profiles = [profile]
    main_window._mm_active = [
        {
            "mod_id": "mod-a",
            "mod_name": "FLMM Mod",
            "target_root": str(target_root),
            "backup_dir": str(backup_dir),
            "created_rel": [],
            "overwritten_rel": [],
            "opensp_overwritten_rel": [],
            "temp_resource_dll_name": "",
        }
    ]

    monkeypatch.setattr(main_window, "_mod_manager_profile_source", lambda _profile: source)
    monkeypatch.setattr(main_window, "_mod_manager_is_flmm_profile", lambda _profile: True)
    monkeypatch.setattr(
        main_window,
        "_mod_manager_active_entry_by_id",
        lambda mod_id: next(
            (
                entry
                for entry in main_window._mm_active
                if isinstance(entry, dict) and str(entry.get("mod_id", "")).strip() == str(mod_id or "").strip()
            ),
            None,
        ),
    )
    monkeypatch.setattr(main_window, "_close_system_tabs_under_root", lambda _root: True)
    monkeypatch.setattr(main_window, "_mod_manager_store_savegames_for_deactivation", lambda _active: (True, ""))
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_mod_manager_append_active_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_make_mod_manager_progress", lambda _label, maximum: _ProgressStub(maximum))
    monkeypatch.setattr(main_window, "_update_mod_manager_progress", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        main_window,
        "_flmm_collect_script_spec",
        lambda _source: (True, {"operations": [{"file": "DATA/EQUIPMENT/engine_good.ini", "method": "append"}]}, ""),
    )

    ok, _msg = main_window._mod_manager_deactivate_active("mod-a", show_dialog=False)

    assert ok is True
    assert not target_payload.exists()
    assert main_window._mm_active == []
