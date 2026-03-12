"""Helpers for BINI conversion settings workflow."""

from __future__ import annotations

from pathlib import Path


def validate_bini_target_folder(target: str) -> tuple[bool, Path | None, str]:
    value = str(target or "").strip()
    if not value:
        return False, None, "no_folder"
    path = Path(value)
    if not path.exists() or not path.is_dir():
        return False, None, "invalid_folder"
    return True, path, ""


def build_bini_result_message(
    *,
    scanned: int,
    converted: int,
    errors: list[str],
    result_template: str,
    errors_template: str,
) -> str:
    message = str(result_template).format(scanned=int(scanned), converted=int(converted))
    if errors:
        message += "\n\n" + str(errors_template).format(count=len(errors)) + "\n" + "\n".join(errors)
    return message
