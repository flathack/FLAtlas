from __future__ import annotations

from pathlib import Path

from fl_editor.freelancer_paths import (
    bundled_freelancer_ini_path,
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
