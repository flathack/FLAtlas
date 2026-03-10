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


def test_mod_manager_repair_profile_restores_from_reference_and_removes_extra_files(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    profile = {"id": "mod-a", "name": "Repo Mod", "mode": "repo"}
    source = tmp_path / "repo_mod"
    source.mkdir()
    (source / "script.xml").write_text("<script></script>", encoding="utf-8")
    payload = source / "DATA" / "EQUIPMENT" / "engine_good.ini"
    payload.parent.mkdir(parents=True)
    payload.write_text("modded\n", encoding="utf-8")

    target_root = tmp_path / "target"
    target_root.mkdir()
    target_file = target_root / "DATA" / "EQUIPMENT" / "engine_good.ini"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("broken\n", encoding="utf-8")
    extra_file = target_root / "EXE" / "plugin.dll"
    extra_file.parent.mkdir(parents=True)
    extra_file.write_text("leftover\n", encoding="utf-8")

    reference_root = tmp_path / "reference"
    reference_root.mkdir()
    reference_file = reference_root / "DATA" / "EQUIPMENT" / "engine_good.ini"
    reference_file.parent.mkdir(parents=True)
    reference_file.write_text("original\n", encoding="utf-8")

    main_window._mm_profiles = [profile]
    monkeypatch.setattr(main_window, "_mod_manager_profile_source", lambda _profile: source)
    monkeypatch.setattr(main_window, "_mod_manager_clean_root_path", lambda: target_root)
    monkeypatch.setattr(main_window, "_mod_manager_is_flmm_profile", lambda _profile: True)
    monkeypatch.setattr(main_window, "_mod_manager_active_entry_by_id", lambda _mod_id: None)
    monkeypatch.setattr(main_window, "_close_system_tabs_under_root", lambda _root: True)
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_mod_manager_append_profile_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_make_mod_manager_progress", lambda _label, maximum: _ProgressStub(maximum))
    monkeypatch.setattr(main_window, "_update_mod_manager_progress", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        main_window,
        "_flmm_collect_script_spec",
        lambda _source: (
            True,
            {"operations": [{"file": "DATA/EQUIPMENT/engine_good.ini", "method": "append"}, {"file": "EXE/plugin.dll", "method": "renamefile", "newfilename": "EXE/plugin.dll"}]},
            "",
        ),
    )

    ok, _msg = main_window._mod_manager_repair_profile_against_reference(
        profile,
        reference_root=reference_root,
        show_dialog=False,
    )

    assert ok is True
    assert target_file.read_text(encoding="utf-8") == "original\n"
    assert not extra_file.exists()
