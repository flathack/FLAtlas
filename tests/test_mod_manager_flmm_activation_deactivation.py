from __future__ import annotations

from pathlib import Path

import pytest

from fl_editor import config as config_module
from fl_editor.i18n import tr
from fl_editor.main_window import MainWindow


class _ProgressStub:
    def __init__(self, maximum: int):
        self._maximum = int(maximum)
        self.value = 0
        self.actions: list[tuple[str, bool]] = []

    def setMaximum(self, value: int):
        self._maximum = int(value)

    def setValue(self, value: int):
        self.value = int(value)

    def maximum(self) -> int:
        return self._maximum

    def close(self):
        return None


def _record_progress_action(progress: _ProgressStub, action: str, *, ok: bool = True):
    progress.actions.append((str(action), bool(ok)))


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
    monkeypatch.setattr(main_window, "_append_mod_manager_progress_action", _record_progress_action)
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

    def _apply_flmm(*_args, **_kwargs):
        target_payload = clean_root / "DATA" / "EQUIPMENT" / "engine_good.ini"
        target_payload.parent.mkdir(parents=True, exist_ok=True)
        target_payload.write_text(payload.read_text(encoding="utf-8"), encoding="utf-8")
        return True, 1, [], ["DATA/EQUIPMENT/engine_good.ini"], ""

    monkeypatch.setattr(
        main_window,
        "_flmm_apply_script_to_target",
        _apply_flmm,
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


def test_flmm_activation_applies_copyfile_and_replace_without_copying_source_variants(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    source = tmp_path / "mods" / "sample_flmm_mod"
    source.mkdir(parents=True)
    script_xml = "\n".join(
        [
            "<script>",
            '<data file="DATA\\EQUIPMENT\\engine_good.ini" method="copyfile" sourcefile="variants\\engine_good_alt.ini"></data>',
            '<data file="DATA\\UNIVERSE\\Systems\\Li05\\Li05.ini" method="replace">',
            "<dest>",
            "[Object]",
            "nickname = Li05_to_Li01",
            "ids_name = 260929",
            "</dest>",
            "<source>",
            "</source>",
            "</data>",
            "</script>",
        ]
    )
    (source / "script.xml").write_text(script_xml, encoding="utf-8")
    source_variant = source / "variants" / "engine_good_alt.ini"
    source_variant.parent.mkdir(parents=True)
    source_variant.write_text("[Good]\nnickname = ge_engine_alt\n", encoding="utf-8")

    clean_root = tmp_path / "clean"
    clean_root.mkdir()
    target_ini = clean_root / "DATA" / "UNIVERSE" / "Systems" / "Li05" / "Li05.ini"
    target_ini.parent.mkdir(parents=True, exist_ok=True)
    target_ini.write_text(
        "[Object]\nnickname = Li05_to_Li01\nids_name = 260929\n\n[Object]\nnickname = keep_me\n",
        encoding="utf-8",
    )

    profile = {"id": "mod-copy-replace", "name": "Sample FLMM", "mode": "repo"}

    monkeypatch.setattr(main_window, "_mod_manager_profile_source", lambda _profile: source)
    monkeypatch.setattr(main_window, "_mod_manager_clean_root_path", lambda: clean_root)
    monkeypatch.setattr(main_window, "_mod_manager_is_flmm_profile", lambda _profile: True)
    monkeypatch.setattr(main_window, "_mod_manager_active_entry_by_id", lambda _mod_id: None)
    monkeypatch.setattr(main_window, "_mod_manager_conflicting_active_ids", lambda _profile: set())
    monkeypatch.setattr(main_window, "_mod_manager_has_active_entries", lambda: False)
    monkeypatch.setattr(main_window, "_temporary_flmm_resource_dll_name", lambda _profile: "")
    monkeypatch.setattr(main_window, "_make_mod_manager_progress", lambda _label, maximum: _ProgressStub(maximum))
    monkeypatch.setattr(main_window, "_update_mod_manager_progress", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_append_mod_manager_progress_action", _record_progress_action)
    monkeypatch.setattr(main_window, "_pump_ui", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_mod_manager_append_profile_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_mod_manager_profile_savegame_risk", lambda _profile: {"level": "safe", "reasons": []})
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_convert_bini_in_folder_in_place", lambda *_args, **_kwargs: (True, 0, 0, ""))
    monkeypatch.setattr(main_window, "_mod_manager_apply_opensp_patch", lambda *_args, **_kwargs: (True, "", []))
    monkeypatch.setattr(main_window, "_flmm_prompt_option_selection", lambda *_args, **_kwargs: set())

    ok, _msg = main_window._mod_manager_activate_profile(profile, show_dialog=False)

    assert ok is True
    assert (clean_root / "DATA" / "EQUIPMENT" / "engine_good.ini").read_text(encoding="utf-8") == source_variant.read_text(encoding="utf-8")
    assert not (clean_root / "variants" / "engine_good_alt.ini").exists()
    li05_text = target_ini.read_text(encoding="utf-8")
    assert "nickname = Li05_to_Li01" not in li05_text
    assert "nickname = keep_me" in li05_text


def test_flmm_option_dialog_uses_xml_ids_for_option_matching(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    source = tmp_path / "mods" / "sample_flmm_mod"
    source.mkdir(parents=True)
    script_xml = "\n".join(
        [
            "<script>",
            "<options default=\"\">",
            '<option name="Engine trail" id="3">',
            '<item id="1" name="Yes"></item>',
            '<item id="0" name="No"></item>',
            "</option>",
            "</options>",
            '<data file="DATA\\FX\\effects.ini" method="copyfile" sourcefile="DATA\\FX\\effects_playtrail.ini" options="3:1"></data>',
            "</script>",
        ]
    )
    (source / "script.xml").write_text(script_xml, encoding="utf-8")
    source_file = source / "DATA" / "FX" / "effects_playtrail.ini"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("trail = yes\n", encoding="utf-8")

    clean_root = tmp_path / "clean"
    clean_root.mkdir()

    profile = {"id": "mod-options", "name": "Sample FLMM", "mode": "repo"}

    monkeypatch.setattr(main_window, "_mod_manager_profile_source", lambda _profile: source)
    monkeypatch.setattr(main_window, "_mod_manager_clean_root_path", lambda: clean_root)
    monkeypatch.setattr(main_window, "_mod_manager_is_flmm_profile", lambda _profile: True)
    monkeypatch.setattr(main_window, "_mod_manager_active_entry_by_id", lambda _mod_id: None)
    monkeypatch.setattr(main_window, "_mod_manager_conflicting_active_ids", lambda _profile: set())
    monkeypatch.setattr(main_window, "_mod_manager_has_active_entries", lambda: False)
    monkeypatch.setattr(main_window, "_temporary_flmm_resource_dll_name", lambda _profile: "")
    monkeypatch.setattr(main_window, "_make_mod_manager_progress", lambda _label, maximum: _ProgressStub(maximum))
    monkeypatch.setattr(main_window, "_update_mod_manager_progress", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_append_mod_manager_progress_action", _record_progress_action)
    monkeypatch.setattr(main_window, "_pump_ui", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_mod_manager_append_profile_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_mod_manager_profile_savegame_risk", lambda _profile: {"level": "safe", "reasons": []})
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_convert_bini_in_folder_in_place", lambda *_args, **_kwargs: (True, 0, 0, ""))
    monkeypatch.setattr(main_window, "_mod_manager_apply_opensp_patch", lambda *_args, **_kwargs: (True, "", []))
    monkeypatch.setattr(main_window, "_flmm_prompt_option_selection", lambda *_args, **_kwargs: {"3:1"})

    ok, _msg = main_window._mod_manager_activate_profile(profile, show_dialog=False)

    assert ok is True
    assert (clean_root / "DATA" / "FX" / "effects.ini").read_text(encoding="utf-8") == "trail = yes\n"


def test_flmm_activation_records_copy_script_and_bini_actions(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    source = tmp_path / "mods" / "sample_mod"
    source.mkdir(parents=True)
    payload = source / "DATA" / "EQUIPMENT" / "engine_good.ini"
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_text("[Good]\nnickname = ge_engine_01\n", encoding="utf-8")

    clean_root = tmp_path / "clean"
    clean_root.mkdir()
    profile = {"id": "mod-progress", "name": "Sample Mod", "mode": "repo"}
    progress = _ProgressStub(3)

    monkeypatch.setattr(main_window, "_mod_manager_profile_source", lambda _profile: source)
    monkeypatch.setattr(main_window, "_mod_manager_clean_root_path", lambda: clean_root)
    monkeypatch.setattr(main_window, "_mod_manager_is_flmm_profile", lambda _profile: True)
    monkeypatch.setattr(main_window, "_mod_manager_active_entry_by_id", lambda _mod_id: None)
    monkeypatch.setattr(main_window, "_mod_manager_conflicting_active_ids", lambda _profile: set())
    monkeypatch.setattr(main_window, "_mod_manager_has_active_entries", lambda: False)
    monkeypatch.setattr(main_window, "_temporary_flmm_resource_dll_name", lambda _profile: "")
    monkeypatch.setattr(main_window, "_make_mod_manager_progress", lambda _label, maximum: progress)
    monkeypatch.setattr(main_window, "_update_mod_manager_progress", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_append_mod_manager_progress_action", _record_progress_action)
    monkeypatch.setattr(main_window, "_pump_ui", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_mod_manager_append_profile_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_mod_manager_profile_savegame_risk", lambda _profile: {"level": "safe", "reasons": []})
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_mod_manager_apply_opensp_patch", lambda *_args, **_kwargs: (True, "", []))
    monkeypatch.setattr(main_window, "_convert_bini_in_folder_in_place", lambda *_args, **_kwargs: (True, 1, 1, ""))
    monkeypatch.setattr(main_window, "_flmm_collect_script_spec", lambda _source: (True, {"operations": [{"file": "DATA/SHIPS/shiparch.ini", "method": "append"}]}, ""))

    def _apply_flmm(*_args, **kwargs):
        kwargs["action_result_cb"]("append: DATA/SHIPS/shiparch.ini", True)
        return True, 1, [], ["DATA/SHIPS/shiparch.ini"], ""

    monkeypatch.setattr(main_window, "_flmm_apply_script_to_target", _apply_flmm)

    ok, _msg = main_window._mod_manager_activate_profile(profile, show_dialog=False)

    assert ok is True
    assert progress.actions == [
        (tr("mod_manager.progress.copying_action").format(path="DATA/EQUIPMENT/engine_good.ini"), True),
        ("append: DATA/SHIPS/shiparch.ini", True),
        (tr("mod_manager.progress.bini_action"), True),
    ]


def test_flmm_sectionreplace_matches_headerless_section_selector(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    source = tmp_path / "mods" / "sample_flmm_mod"
    source.mkdir(parents=True)
    (source / "script.xml").write_text(
        "\n".join(
            [
                "<script>",
                '<data file="DATA\\SHIPS\\shiparch.ini" method="sectionreplace">',
                "<section>",
                "nickname = or_elite_msn01",
                "</section>",
                "<dest>",
                "mass = 100.000000",
                "</dest>",
                "<source>",
                "mass = 150.000000",
                "</source>",
                "</data>",
                "</script>",
            ]
        ),
        encoding="utf-8",
    )

    clean_root = tmp_path / "clean"
    clean_root.mkdir()
    target_ini = clean_root / "DATA" / "SHIPS" / "shiparch.ini"
    target_ini.parent.mkdir(parents=True, exist_ok=True)
    target_ini.write_text(
        "[Ship]\nnickname = or_elite_msn01\nmass = 100.000000\n", encoding="utf-8"
    )

    profile = {"id": "mod-headerless", "name": "Sample FLMM", "mode": "repo"}

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
    monkeypatch.setattr(main_window, "_flmm_prompt_option_selection", lambda *_args, **_kwargs: set())

    ok, _msg = main_window._mod_manager_activate_profile(profile, show_dialog=False)

    assert ok is True
    assert "mass = 150.000000" in target_ini.read_text(encoding="utf-8")


def test_flmm_sectionreplace_seeds_missing_target_from_mod_source_file(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    source = tmp_path / "mods" / "sample_flmm_mod"
    source.mkdir(parents=True)
    (source / "script.xml").write_text(
        "\n".join(
            [
                "<script>",
                '<data file="EXE\\hc_client.ini" method="sectionreplace">',
                "<section>",
                "[Settings]",
                "</section>",
                "<dest>",
                "LogChat=no",
                "</dest>",
                "<source>",
                "LogChat=yes",
                "</source>",
                "</data>",
                "</script>",
            ]
        ),
        encoding="utf-8",
    )
    source_ini = source / "EXE" / "hc_client.ini"
    source_ini.parent.mkdir(parents=True, exist_ok=True)
    source_ini.write_text("[Settings]\nLogChat=no\n", encoding="utf-8")

    clean_root = tmp_path / "clean"
    clean_root.mkdir()
    profile = {"id": "mod-seed-target", "name": "Sample FLMM", "mode": "repo"}

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
    monkeypatch.setattr(main_window, "_flmm_prompt_option_selection", lambda *_args, **_kwargs: set())

    ok, _msg = main_window._mod_manager_activate_profile(profile, show_dialog=False)

    assert ok is True
    hc_client_text = (clean_root / "EXE" / "hc_client.ini").read_text(encoding="utf-8")
    assert "[Settings]" in hc_client_text
    assert "LogChat=yes" in hc_client_text


def test_flmm_sectionreplace_uses_mod_source_when_target_lacks_section(
    main_window: MainWindow,
    monkeypatch,
    tmp_path: Path,
):
    source = tmp_path / "mods" / "sample_flmm_mod"
    source.mkdir(parents=True)
    (source / "script.xml").write_text(
        "\n".join(
            [
                "<script>",
                '<data file="DATA\\SHIPS\\loadouts_special.ini" method="sectionreplace">',
                "<section>",
                "nickname = Nomad_Battleship_Loadout",
                "</section>",
                "<dest>",
                "equip = ge_gf1_engine_01",
                "</dest>",
                "<source>",
                "equip = ge_ng_engine_01",
                "</source>",
                "</data>",
                "</script>",
            ]
        ),
        encoding="utf-8",
    )
    source_ini = source / "DATA" / "SHIPS" / "loadouts_special.ini"
    source_ini.parent.mkdir(parents=True, exist_ok=True)
    source_ini.write_text(
        "\n".join(
            [
                "[Loadout]",
                "nickname = Nomad_Battleship_Loadout",
                "equip = ge_gf1_engine_01",
                "",
            ]
        ),
        encoding="utf-8",
    )

    clean_root = tmp_path / "clean"
    clean_root.mkdir()
    target_ini = clean_root / "DATA" / "SHIPS" / "loadouts_special.ini"
    target_ini.parent.mkdir(parents=True, exist_ok=True)
    target_ini.write_text(
        "\n".join(
            [
                "[Loadout]",
                "nickname = something_else",
                "equip = ge_gf1_engine_01",
                "",
            ]
        ),
        encoding="utf-8",
    )

    profile = {"id": "mod-loadout-fallback", "name": "Sample FLMM", "mode": "repo"}

    monkeypatch.setattr(main_window, "_mod_manager_profile_source", lambda _profile: source)
    monkeypatch.setattr(main_window, "_mod_manager_clean_root_path", lambda: clean_root)
    monkeypatch.setattr(main_window, "_mod_manager_is_flmm_profile", lambda _profile: True)
    monkeypatch.setattr(main_window, "_mod_manager_active_entry_by_id", lambda _mod_id: None)
    monkeypatch.setattr(main_window, "_mod_manager_conflicting_active_ids", lambda _profile: set())
    monkeypatch.setattr(main_window, "_mod_manager_has_active_entries", lambda: False)
    monkeypatch.setattr(main_window, "_temporary_flmm_resource_dll_name", lambda _profile: "")
    monkeypatch.setattr(main_window, "_make_mod_manager_progress", lambda _label, maximum: _ProgressStub(maximum))
    monkeypatch.setattr(main_window, "_update_mod_manager_progress", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_append_mod_manager_progress_action", _record_progress_action)
    monkeypatch.setattr(main_window, "_pump_ui", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_mod_manager_append_profile_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_window, "_mod_manager_profile_savegame_risk", lambda _profile: {"level": "safe", "reasons": []})
    monkeypatch.setattr(main_window, "_mod_manager_save_state", lambda: None)
    monkeypatch.setattr(main_window, "_convert_bini_in_folder_in_place", lambda *_args, **_kwargs: (True, 0, 0, ""))
    monkeypatch.setattr(main_window, "_mod_manager_apply_opensp_patch", lambda *_args, **_kwargs: (True, "", []))
    monkeypatch.setattr(main_window, "_flmm_prompt_option_selection", lambda *_args, **_kwargs: set())

    ok, _msg = main_window._mod_manager_activate_profile(profile, show_dialog=False)

    assert ok is True
    text = target_ini.read_text(encoding="utf-8")
    assert "nickname = Nomad_Battleship_Loadout" in text
    assert "equip = ge_ng_engine_01" in text
