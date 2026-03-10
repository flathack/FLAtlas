from __future__ import annotations

from pathlib import Path

import pytest

from fl_editor import config as config_module
from fl_editor.main_window import MainWindow


class _ProgressStub:
    def __init__(self, maximum: int):
        self._maximum = int(maximum)
        self.value = 0

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


def test_mod_manager_deactivate_restores_backups_and_removes_created_files(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    target_root = tmp_path / "clean"
    backup_dir = tmp_path / "backup"
    target_root.mkdir()
    backup_dir.mkdir()

    overwritten_rel = "DATA/test.ini"
    created_rel = "DATA/created.ini"

    overwritten_target = target_root / overwritten_rel
    overwritten_target.parent.mkdir(parents=True, exist_ok=True)
    overwritten_target.write_text("modded\n", encoding="utf-8")

    created_target = target_root / created_rel
    created_target.parent.mkdir(parents=True, exist_ok=True)
    created_target.write_text("new file\n", encoding="utf-8")

    overwritten_backup = backup_dir / overwritten_rel
    overwritten_backup.parent.mkdir(parents=True, exist_ok=True)
    overwritten_backup.write_text("original\n", encoding="utf-8")

    main_window._mm_active = [
        {
            "mod_id": "mod-a",
            "mod_name": "Mod A",
            "target_root": str(target_root),
            "backup_dir": str(backup_dir),
            "created_rel": [created_rel],
            "overwritten_rel": [overwritten_rel],
            "opensp_overwritten_rel": [],
            "temp_resource_dll_name": "",
        }
    ]

    monkeypatch.setattr(main_window, "_close_system_tabs_under_root", lambda _root: True)
    monkeypatch.setattr(main_window, "_mod_manager_store_savegames_for_deactivation", lambda _active: (True, ""))
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_mod_manager_append_active_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_make_mod_manager_progress", lambda _label, maximum: _ProgressStub(maximum))
    monkeypatch.setattr(main_window, "_update_mod_manager_progress", lambda *_args, **_kwargs: None)

    ok, msg = main_window._mod_manager_deactivate_active("mod-a", show_dialog=False)

    assert ok is True
    assert "removed=1" in msg.lower() or "removed = 1" in msg.lower() or "1" in msg
    assert not created_target.exists()
    assert overwritten_target.read_text(encoding="utf-8") == "original\n"
    assert main_window._mm_active == []
    assert not backup_dir.exists()
