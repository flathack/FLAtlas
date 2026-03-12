from __future__ import annotations

from pathlib import Path

from fl_editor.bini_settings import build_bini_result_message, validate_bini_target_folder


def test_validate_bini_target_folder_handles_missing_and_invalid_targets(tmp_path: Path):
    ok_empty, path_empty, error_empty = validate_bini_target_folder("")
    ok_missing, path_missing, error_missing = validate_bini_target_folder(str(tmp_path / "missing"))

    assert (ok_empty, path_empty, error_empty) == (False, None, "no_folder")
    assert (ok_missing, path_missing, error_missing) == (False, None, "invalid_folder")


def test_validate_bini_target_folder_accepts_existing_directory(tmp_path: Path):
    ok, path, error = validate_bini_target_folder(str(tmp_path))

    assert ok
    assert path == tmp_path
    assert error == ""


def test_build_bini_result_message_appends_error_block_only_when_needed():
    clean_message = build_bini_result_message(
        scanned=10,
        converted=3,
        errors=[],
        result_template="Done: {scanned}/{converted}",
        errors_template="Errors: {count}",
    )
    error_message = build_bini_result_message(
        scanned=10,
        converted=3,
        errors=["first", "second"],
        result_template="Done: {scanned}/{converted}",
        errors_template="Errors: {count}",
    )

    assert clean_message == "Done: 10/3"
    assert error_message == "Done: 10/3\n\nErrors: 2\nfirst\nsecond"
