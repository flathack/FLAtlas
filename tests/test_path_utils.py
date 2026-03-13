from pathlib import Path

from fl_editor.path_utils import ci_find, ci_resolve


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
