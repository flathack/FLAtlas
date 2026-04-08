from pathlib import Path

from fl_editor.path_utils import ci_find, ci_resolve, is_offmap_helper_object_data


def test_ci_find_matches_freelancer_filename_without_underscore(tmp_path: Path):
    data_dir = tmp_path / "DATA" / "SOLAR" / "DOCKABLE"
    data_dir.mkdir(parents=True)
    expected = data_dir / "jump_gatel.cmp"
    expected.write_text("cmp", encoding="utf-8")

    found = ci_find(data_dir, "jump_gateL.cmp")

    assert found == expected


def test_ci_resolve_matches_freelancer_filename_without_underscore(tmp_path: Path):
    data_dir = tmp_path / "DATA" / "SOLAR" / "DOCKABLE"
    data_dir.mkdir(parents=True)
    expected = data_dir / "jump_gatel.cmp"
    expected.write_text("cmp", encoding="utf-8")

    resolved = ci_resolve(tmp_path / "DATA", r"solar\dockable\jump_gateL.cmp")

    assert resolved == expected


def test_is_offmap_helper_object_data_detects_beam_target_helper():
    assert is_offmap_helper_object_data(
        {
            "nickname": "Li01_Beam_Target",
            "archetype": "jumphole",
            "base": "Li01_Beam_Target",
            "dock_with": "Li01_Beam_Target",
            "pos": "0, 0, 1000000",
        }
    )


def test_is_offmap_helper_object_data_keeps_regular_self_docking_base():
    assert not is_offmap_helper_object_data(
        {
            "nickname": "Bw02_02_Base",
            "archetype": "miningbase_small_ice",
            "base": "Bw02_02_Base",
            "dock_with": "Bw02_02_Base",
            "pos": "11560, 0, -4979",
        }
    )
