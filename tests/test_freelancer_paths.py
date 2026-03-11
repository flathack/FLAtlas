from __future__ import annotations

from pathlib import Path

from fl_editor.freelancer_paths import (
    bundled_freelancer_ini_path,
    find_freelancer_ini_in_roots,
    find_freelancer_ini_read,
    find_freelancer_ini_write,
)


def test_bundled_freelancer_ini_path_uses_module_directory():
    result = bundled_freelancer_ini_path("/tmp/project/fl_editor/main_window.py")

    assert result == Path("/tmp/project/fl_editor/flvanilla/freelancer.ini")


def test_find_freelancer_ini_read_prefers_primary_and_deduplicates(tmp_path: Path):
    primary = tmp_path / "primary"
    fallback = tmp_path / "fallback"
    (primary / "EXE").mkdir(parents=True)
    fallback.mkdir()
    ini_path = primary / "EXE" / "freelancer.ini"
    ini_path.write_text("", encoding="utf-8")

    result = find_freelancer_ini_read(
        str(primary),
        str(primary),
        lambda root, rel: root / rel if (root / rel).exists() else None,
    )

    assert result == ini_path


def test_find_freelancer_ini_write_uses_writable_wrapper(tmp_path: Path):
    read_path = tmp_path / "freelancer.ini"
    read_path.write_text("", encoding="utf-8")

    result = find_freelancer_ini_write(read_path, lambda path: path.with_suffix(".writable.ini"))

    assert result == tmp_path / "freelancer.writable.ini"


def test_find_freelancer_ini_in_roots_uses_first_match_order(tmp_path: Path):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    (root_a / "EXE").mkdir(parents=True)
    (root_b / "EXE").mkdir(parents=True)
    ini_b = root_b / "EXE" / "freelancer.ini"
    ini_b.write_text("", encoding="utf-8")
    ini_a = root_a / "EXE" / "freelancer.ini"
    ini_a.write_text("", encoding="utf-8")

    result = find_freelancer_ini_in_roots(
        [str(root_a), str(root_b)],
        lambda root, rel: root / rel if (root / rel).exists() else None,
    )

    assert result == ini_a


def test_find_freelancer_ini_in_roots_deduplicates_equivalent_roots(tmp_path: Path):
    root = tmp_path / "root"
    (root / "EXE").mkdir(parents=True)
    ini = root / "EXE" / "freelancer.ini"
    ini.write_text("", encoding="utf-8")

    result = find_freelancer_ini_in_roots(
        [str(root), str(root)],
        lambda p, rel: p / rel if (p / rel).exists() else None,
    )

    assert result == ini
