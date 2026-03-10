from __future__ import annotations

from pathlib import Path

from fl_editor.mod_manager_conflicts import (
    mod_manager_conflict_analysis,
    mod_manager_conflict_details,
    mod_manager_conflicting_active_ids,
    mod_manager_is_flmm_repo_profile,
    mod_manager_partial_conflict_details,
    mod_manager_profile_target_relpaths,
    mod_manager_profile_touch_signature,
)
from fl_editor.mod_manager_identity import mod_manager_normalized_path_key


def test_mod_manager_is_flmm_repo_profile_matches_flmm_mods_root():
    profile = {"mode": "repo", "repo_root": "/game/FLMM/mods"}

    assert mod_manager_is_flmm_repo_profile(profile, "/game/FLMM", mod_manager_normalized_path_key)
    assert not mod_manager_is_flmm_repo_profile(profile, "/other/install", mod_manager_normalized_path_key)


def test_mod_manager_profile_target_relpaths_handles_repo_and_flmm_sources(tmp_path: Path):
    source = tmp_path / "modA"
    source.mkdir()
    nested = source / "DATA" / "ships"
    nested.mkdir(parents=True)
    ini_file = nested / "test.ini"
    ini_file.write_text("[ship]\n", encoding="utf-8")

    repo_profile = {"mode": "repo"}
    repo_files = mod_manager_profile_target_relpaths(
        repo_profile,
        source,
        False,
        lambda path: [ini_file],
        lambda path: (False, {}, "unused"),
    )
    assert repo_files == {"data/ships/test.ini"}

    flmm_profile = {"mode": "repo"}
    flmm_files = mod_manager_profile_target_relpaths(
        flmm_profile,
        source,
        True,
        lambda path: [],
        lambda path: (
            True,
            {
                "operations": [
                    {"file": "DATA/ships/test.ini", "method": "append"},
                    {"file": "DATA/old.ini", "method": "renamefile", "newfilename": "DATA/new.ini"},
                ]
            },
            "",
        ),
    )
    assert flmm_files == {"data/ships/test.ini", "data/old.ini", "data/new.ini"}


def test_mod_manager_profile_touch_signature_distinguishes_hard_and_soft_flmm_ops(tmp_path: Path):
    source = tmp_path / "flmm_mod"
    source.mkdir()
    profile = {"id": "mod-a"}
    files = {"data/ships/test.ini", "data/equipment/goods.ini"}

    signature = mod_manager_profile_touch_signature(
        profile,
        files,
        True,
        source,
        lambda path: (
            True,
            {
                "operations": [
                    {
                        "method": "append",
                        "file": "DATA/ships/test.ini",
                        "sources": ["[Ship]\nnickname = my_ship\nids_name = 1"],
                    },
                    {
                        "method": "sectionreplace",
                        "file": "DATA/equipment/goods.ini",
                        "sections": ["[Good]\nnickname = good_a"],
                        "dests": ["price = 100"],
                    },
                ]
            },
            "",
        ),
        lambda text: [text] if text else [],
        lambda text: "good|good_a" if "good_a" in text.lower() else "ship|my_ship",
        lambda text: {"price"} if "price" in text.lower() else {"ids_name"},
    )

    assert "section:data/ships/test.ini:ship|my_ship" in signature["soft"]
    assert "key:data/equipment/goods.ini:good|good_a:price" in signature["hard"]


def test_mod_manager_conflict_analysis_separates_hard_and_partial_conflicts():
    profile = {"id": "base", "mode": "repo", "flmm": True}
    active_entries = [{"mod_id": "other-hard"}, {"mod_id": "other-soft"}, {"mod_id": "base"}]
    signatures = {
        "base": {
            "files": {"data/ships/test.ini", "data/equipment/goods.ini"},
            "hard": {"file:data/equipment/goods.ini"},
            "soft": {"section:data/ships/test.ini:ship|my_ship"},
        },
        "other-hard": {
            "files": {"data/equipment/goods.ini"},
            "hard": {"file:data/equipment/goods.ini"},
            "soft": set(),
        },
        "other-soft": {
            "files": {"data/ships/test.ini"},
            "hard": set(),
            "soft": {"section:data/ships/test.ini:ship|my_ship"},
        },
    }
    profiles = {
        "other-hard": {"id": "other-hard", "mode": "repo", "flmm": False},
        "other-soft": {"id": "other-soft", "mode": "repo", "flmm": True},
    }

    hard_ids, hard_details, partial_details = mod_manager_conflict_analysis(
        profile,
        active_entries,
        lambda mod_id: profiles.get(mod_id),
        lambda item: signatures.get(str(item.get("id", "")), {"files": set(), "hard": set(), "soft": set()}),
        lambda item: bool(item and item.get("flmm")),
    )

    assert mod_manager_conflicting_active_ids(hard_ids) == {"other-hard"}
    assert mod_manager_conflict_details(hard_details) == {"other-hard": {"data/equipment/goods.ini"}}
    assert mod_manager_partial_conflict_details(partial_details) == {"other-soft": {"data/ships/test.ini"}}
