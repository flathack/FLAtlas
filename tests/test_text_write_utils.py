from __future__ import annotations

from pathlib import Path

from fl_editor.text_write_utils import write_text_with_fallback


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
