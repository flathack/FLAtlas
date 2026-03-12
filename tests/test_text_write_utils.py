from __future__ import annotations

from pathlib import Path

from fl_editor.text_write_utils import write_text_atomic, write_text_with_fallback


def test_write_text_with_fallback_uses_primary_encoding_when_possible(tmp_path: Path):
    target = tmp_path / "freelancer.ini"

    used_encoding = write_text_with_fallback(target, "plain ascii\n", ensure_parent=True)

    assert used_encoding == "cp1252"
    assert target.read_text(encoding="cp1252") == "plain ascii\n"


def test_write_text_with_fallback_uses_utf8_when_cp1252_cannot_encode(tmp_path: Path):
    target = tmp_path / "utf8.txt"

    used_encoding = write_text_with_fallback(target, "snowman: \u2603\n")

    assert used_encoding == "utf-8"
    assert target.read_text(encoding="utf-8") == "snowman: \u2603\n"


def test_write_text_with_fallback_creates_parent_directory_when_requested(tmp_path: Path):
    target = tmp_path / "nested" / "freelancer.ini"

    used_encoding = write_text_with_fallback(target, "ok\n", ensure_parent=True)

    assert used_encoding == "cp1252"
    assert target.read_text(encoding="cp1252") == "ok\n"


def test_write_text_atomic_replaces_target_via_tmp_file(tmp_path: Path):
    target = tmp_path / "universe.ini"
    target.write_text("old\n", encoding="utf-8")

    written = write_text_atomic(target, "new\n")

    assert written == target
    assert target.read_text(encoding="utf-8") == "new\n"
    assert not Path(str(target) + ".tmp").exists()
