from __future__ import annotations

from pathlib import Path

import pytest

from fl_editor import config as config_module
from fl_editor.main_window import MainWindow


@pytest.fixture
def main_window(monkeypatch, qapp, tmp_path):
    monkeypatch.setattr(config_module, "CONFIG_PATH", tmp_path / "config.json")
    window = MainWindow()
    yield window
    window.close()


def test_create_installation_from_selected_mod_copies_source_and_adds_direct_profile(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    repo_profile = {"id": "repo-mod", "name": "Hamburg City", "mode": "repo"}
    source_install = tmp_path / "source-install"
    source_install.mkdir()
    source_marker = source_install / "EXE" / "freelancer.ini"
    source_marker.parent.mkdir(parents=True)
    source_marker.write_text("[Resources]\n", encoding="utf-8")

    direct_profile = {
        "id": "direct-source",
        "name": "Vanilla Base",
        "mode": "direct",
        "direct_path": str(source_install),
    }
    main_window._mm_profiles = [repo_profile, direct_profile]
    main_window._mm_clean_profile_id = "direct-source"

    info_calls: list[tuple[str, str]] = []
    warning_calls: list[tuple[str, str]] = []
    loading_calls: list[tuple[bool, str]] = []
    refresh_calls: list[str] = []
    log_messages: list[str] = []
    activated_targets: list[Path] = []
    backup_dirs: list[Path] = []

    monkeypatch.setattr(main_window, "_mod_manager_selected_profile", lambda: repo_profile)
    monkeypatch.setattr(main_window, "_mod_manager_has_active_entries", lambda: False)
    monkeypatch.setattr(main_window, "_mod_manager_direct_profiles", lambda: [direct_profile])
    monkeypatch.setattr(main_window, "_mod_manager_profile_source", lambda profile: source_install if profile is direct_profile else None)
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_mod_manager_refresh_table", lambda preferred_pid="": refresh_calls.append(preferred_pid))
    monkeypatch.setattr(main_window, "_update_active_mod_indicator", lambda: None)
    monkeypatch.setattr(main_window, "_mod_manager_log", lambda message: log_messages.append(str(message)))
    monkeypatch.setattr(main_window, "_set_loading_visible", lambda visible, message="": loading_calls.append((bool(visible), str(message))))

    def _activate(_profile, *, show_dialog=True):
        assert _profile is repo_profile
        assert show_dialog is False
        active_profile = next(
            profile
            for profile in main_window._mm_profiles
            if isinstance(profile, dict) and str(profile.get("id", "")) == str(main_window._mm_clean_profile_id)
        )
        target_root = Path(str(active_profile.get("direct_path", "")))
        activated_targets.append(target_root)
        marker = target_root / "mod-applied.txt"
        marker.write_text("ok\n", encoding="utf-8")
        backup_dir = tmp_path / "backup-created"
        backup_dir.mkdir(exist_ok=True)
        backup_dirs.append(backup_dir)
        main_window._mm_active.append(
            {
                "mod_id": str(repo_profile.get("id", "")),
                "target_root": str(target_root),
                "backup_dir": str(backup_dir),
            }
        )
        return True, "Activation ok"

    monkeypatch.setattr(main_window, "_mod_manager_activate_profile", _activate)
    monkeypatch.setattr("fl_editor.main_window.QInputDialog.getItem", lambda *args, **kwargs: ("Vanilla Base", True))
    monkeypatch.setattr("fl_editor.main_window.QInputDialog.getText", lambda *args, **kwargs: ("Hamburg City Ready", True))
    monkeypatch.setattr("fl_editor.main_window.QFileDialog.getExistingDirectory", lambda *args, **kwargs: str(tmp_path / "dest"))
    monkeypatch.setattr("fl_editor.main_window.QMessageBox.information", lambda _parent, title, text: info_calls.append((str(title), str(text))))
    monkeypatch.setattr("fl_editor.main_window.QMessageBox.warning", lambda _parent, title, text: warning_calls.append((str(title), str(text))))

    main_window._mod_manager_create_installation_from_selected_mod()

    target_root = tmp_path / "dest" / "Hamburg_City_Ready"
    assert target_root in activated_targets
    assert target_root.exists()
    assert (target_root / "EXE" / "freelancer.ini").read_text(encoding="utf-8") == "[Resources]\n"
    assert (target_root / "mod-applied.txt").read_text(encoding="utf-8") == "ok\n"
    assert any(str(profile.get("direct_path", "")) == str(target_root) for profile in main_window._mm_profiles)
    assert main_window._mm_clean_profile_id == "direct-source"
    assert main_window._mm_active == []
    assert backup_dirs and not backup_dirs[0].exists()
    assert refresh_calls
    assert any("Hamburg City Ready" in message for message in log_messages)
    assert loading_calls[0][0] is True
    assert loading_calls[-1][0] is False
    assert not warning_calls
    assert info_calls


def test_create_repo_mod_auto_switches_to_edit_context_when_target_is_set(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    repo_root = tmp_path / "mods"
    repo_root.mkdir()
    log_messages: list[str] = []
    refresh_calls: list[str] = []
    status_messages: list[str] = []
    switched_profiles: list[dict] = []

    monkeypatch.setattr(main_window, "_mod_manager_repo_root_path", lambda: repo_root)
    monkeypatch.setattr(main_window, "_mod_manager_repo_setup_complete", lambda: True)
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_mod_manager_refresh_table", lambda preferred_pid="": refresh_calls.append(preferred_pid))
    monkeypatch.setattr(main_window, "_mod_manager_log", lambda message: log_messages.append(str(message)))
    monkeypatch.setattr(main_window, "_mod_manager_clean_target_profile", lambda: {"id": "target", "mode": "direct"})
    monkeypatch.setattr(main_window, "_mod_manager_has_active_entries", lambda: False)
    monkeypatch.setattr(main_window.statusBar(), "showMessage", lambda text: status_messages.append(str(text)))

    def _switch(profile: dict):
        switched_profiles.append(profile)
        return True, "Editing context set."

    monkeypatch.setattr(main_window, "_mod_manager_switch_edit_context", _switch)
    monkeypatch.setattr("fl_editor.main_window.QInputDialog.getText", lambda *args, **kwargs: ("My Fresh Mod", True))

    main_window._mod_manager_create_repo_mod()

    created_path = repo_root / "My Fresh Mod"
    assert created_path.exists()
    assert len(main_window._mm_profiles) == 1
    created_profile = main_window._mm_profiles[0]
    assert switched_profiles == [created_profile]
    assert refresh_calls == [str(created_profile.get("id", "")), str(created_profile.get("id", ""))]
    assert status_messages == ["Editing context set."]
    assert any("My Fresh Mod" in message for message in log_messages)
    assert "Editing context set." in log_messages


def test_create_repo_mod_does_not_switch_edit_context_without_target_installation(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    repo_root = tmp_path / "mods"
    repo_root.mkdir()
    switched_profiles: list[dict] = []

    monkeypatch.setattr(main_window, "_mod_manager_repo_root_path", lambda: repo_root)
    monkeypatch.setattr(main_window, "_mod_manager_repo_setup_complete", lambda: True)
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_mod_manager_refresh_table", lambda preferred_pid="": None)
    monkeypatch.setattr(main_window, "_mod_manager_log", lambda message: None)
    monkeypatch.setattr(main_window, "_mod_manager_clean_target_profile", lambda: None)
    monkeypatch.setattr(main_window, "_mod_manager_has_active_entries", lambda: False)
    monkeypatch.setattr(main_window, "_mod_manager_switch_edit_context", lambda profile: switched_profiles.append(profile))
    monkeypatch.setattr("fl_editor.main_window.QInputDialog.getText", lambda *args, **kwargs: ("Repo Only", True))

    main_window._mod_manager_create_repo_mod()

    assert not switched_profiles