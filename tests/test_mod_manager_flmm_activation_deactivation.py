from __future__ import annotations

from pathlib import Path

import pytest

from fl_editor import config as config_module
from fl_editor.main_window import MainWindow


class _ProgressStub:
    def __init__(self, maximum: int):
        self._maximum = int(maximum)
        self.value = 0

    def setMaximum(self, value: int):
        self._maximum = int(value)

    def setValue(self, value: int):
        self.value = int(value)

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


def test_flmm_activate_then_deactivate_tracks_copied_payload_files(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    source = tmp_path / "mods" / "sample_flmm_mod"
    source.mkdir(parents=True)
    (source / "script.xml").write_text("<mod></mod>", encoding="utf-8")
    payload = source / "DATA" / "EQUIPMENT" / "engine_good.ini"
    payload.parent.mkdir(parents=True)
    payload.write_text("[Good]\nnickname = ge_engine_01\n", encoding="utf-8")

    clean_root = tmp_path / "clean"
    clean_root.mkdir()

    profile = {"id": "mod-a", "name": "Sample FLMM", "mode": "repo"}

    monkeypatch.setattr(main_window, "_mod_manager_profile_source", lambda _profile: source)
    monkeypatch.setattr(main_window, "_mod_manager_clean_root_path", lambda: clean_root)
    monkeypatch.setattr(main_window, "_mod_manager_is_flmm_profile", lambda _profile: True)
    monkeypatch.setattr(main_window, "_mod_manager_active_entry_by_id", lambda _mod_id: None)
    monkeypatch.setattr(main_window, "_mod_manager_conflicting_active_ids", lambda _profile: set())
    monkeypatch.setattr(main_window, "_mod_manager_has_active_entries", lambda: False)
    monkeypatch.setattr(main_window, "_temporary_flmm_resource_dll_name", lambda _profile: "")
    monkeypatch.setattr(main_window, "_make_mod_manager_progress", lambda _label, maximum: _ProgressStub(maximum))
    monkeypatch.setattr(main_window, "_update_mod_manager_progress", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_pump_ui", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_mod_manager_append_profile_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_mod_manager_profile_savegame_risk", lambda _profile: {"level": "safe", "reasons": []})
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_convert_bini_in_folder_in_place", lambda *_args, **_kwargs: (True, 0, 0, ""))
    monkeypatch.setattr(main_window, "_mod_manager_apply_opensp_patch", lambda *_args, **_kwargs: (True, "", []))
    monkeypatch.setattr(
        main_window,
        "_flmm_collect_script_spec",
        lambda _source: (True, {"operations": [{"file": "DATA/EQUIPMENT/engine_good.ini", "method": "append"}]}, ""),
    )
    monkeypatch.setattr(
        main_window,
        "_flmm_apply_script_to_target",
        lambda *_args, **_kwargs: (True, 1, [], [], ""),
    )

    ok, _msg = main_window._mod_manager_activate_profile(profile, show_dialog=False)

    assert ok is True
    target_payload = clean_root / "DATA" / "EQUIPMENT" / "engine_good.ini"
    assert target_payload.exists()
    assert len(main_window._mm_active) == 1
    active = dict(main_window._mm_active[0])
    assert "DATA/EQUIPMENT/engine_good.ini" in active.get("created_rel", [])

    monkeypatch.setattr(main_window, "_close_system_tabs_under_root", lambda _root: True)
    monkeypatch.setattr(main_window, "_mod_manager_store_savegames_for_deactivation", lambda _active: (True, ""))
    monkeypatch.setattr(main_window, "_mod_manager_append_active_log", lambda *_args, **_kwargs: None)
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

    ok_deactivate, _msg = main_window._mod_manager_deactivate_active("mod-a", show_dialog=False)

    assert ok_deactivate is True
    assert not target_payload.exists()
    assert main_window._mm_active == []
