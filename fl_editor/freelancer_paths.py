"""Helpers for locating core Freelancer configuration files."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Callable


def bundled_freelancer_ini_path(module_file: str) -> Path:
    module_path = str(module_file or "").strip()
    if module_path.startswith("/") and not module_path.startswith("//"):
        return Path(PurePosixPath(module_path).parent / "flvanilla" / "freelancer.ini")
    return Path(module_path).resolve().parent / "flvanilla" / "freelancer.ini"


def find_freelancer_ini_in_roots(
    roots: list[str | Path] | tuple[str | Path, ...],
    ci_resolve_func: Callable[[Path, str], Path | None],
) -> Path | None:
    seen: set[str] = set()
    for root in list(roots or []):
        txt = str(root or "").strip()
        if not txt:
            continue
        key = str(Path(txt)).replace("/", "\\").rstrip("\\").lower()
        if key in seen:
            continue
        seen.add(key)
        base = Path(txt)
        for rel in ("EXE/freelancer.ini", "freelancer.ini"):
            fp = ci_resolve_func(base, rel)
            if fp and fp.is_file():
                return fp
    return None


def find_freelancer_ini_read(
    primary_game_path: str | None,
    fallback_game_path: str | None,
    ci_resolve_func: Callable[[Path, str], Path | None],
) -> Path | None:
    roots: list[str] = []
    primary = str(primary_game_path or "").strip()
    fallback = str(fallback_game_path or "").strip()
    if primary:
        roots.append(primary)
    if fallback and fallback not in roots:
        roots.append(fallback)
    return find_freelancer_ini_in_roots(roots, ci_resolve_func)


def find_freelancer_ini_write(
    read_path: Path | None,
    ensure_writable_path: Callable[[Path], Path | None],
) -> Path | None:
    if read_path is None:
        return None
    return ensure_writable_path(read_path)
