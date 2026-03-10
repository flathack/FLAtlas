from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fl_editor.mod_manager_identity import (
    mod_manager_active_entries,
    mod_manager_active_entry_by_id,
    mod_manager_active_ids,
    mod_manager_has_active_entries,
    mod_manager_is_target_installation,
    mod_manager_last_active_entry,
    mod_manager_make_id,
    mod_manager_normalized_path_key,
    mod_manager_profile_name_by_id,
    mod_manager_profile_source,
)


def test_mod_manager_make_id_is_stable_for_fixed_timestamp():
    now = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)
    assert mod_manager_make_id("test", now=now) == mod_manager_make_id("test", now=now)


def test_mod_manager_profile_source_handles_repo_and_direct_profiles():
    repo_profile = {"mode": "repo", "repo_folder": "modA"}
    direct_profile = {"mode": "direct", "direct_path": "/tmp/modB"}

    assert mod_manager_profile_source(repo_profile, repo_root_default="/mods") == Path("/mods") / "modA"
    assert mod_manager_profile_source(direct_profile) == Path("/tmp/modB")


def test_mod_manager_normalized_path_key_and_profile_name_lookup():
    profiles = [{"id": "a1", "name": "Alpha"}]

    assert mod_manager_normalized_path_key(Path("/tmp/test")) == "\\tmp\\test"
    assert mod_manager_profile_name_by_id(profiles, "a1") == "Alpha"
    assert mod_manager_profile_name_by_id(profiles, "missing") == ""


def test_mod_manager_active_entry_helpers_cover_common_cases():
    active = [{"mod_id": "a1", "name": "Alpha"}, "ignored", {"mod_id": "b2", "name": "Beta"}]

    assert mod_manager_active_entries(active) == [{"mod_id": "a1", "name": "Alpha"}, {"mod_id": "b2", "name": "Beta"}]
    assert mod_manager_active_ids(active) == {"a1", "b2"}
    assert mod_manager_active_entry_by_id(active, "b2") == {"mod_id": "b2", "name": "Beta"}
    assert mod_manager_has_active_entries(active)
    assert mod_manager_last_active_entry(active) == {"mod_id": "b2", "name": "Beta"}


def test_mod_manager_is_target_installation_compares_clean_profile_id():
    assert mod_manager_is_target_installation({"id": "abc"}, "abc")
    assert not mod_manager_is_target_installation({"id": "abc"}, "xyz")
