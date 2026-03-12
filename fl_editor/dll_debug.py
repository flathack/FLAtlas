"""Helpers for building DLL fallback debug output."""

from __future__ import annotations

from pathlib import Path
from typing import Callable


def classify_dll_source(
    probe: Path,
    *,
    mod_root: Path | None,
    vanilla_root: Path | None,
) -> str:
    try:
        probe_resolved = probe.resolve()
    except Exception:
        probe_resolved = probe
    try:
        mod_resolved = mod_root.resolve() if mod_root is not None and str(mod_root) else None
    except Exception:
        mod_resolved = None
    try:
        vanilla_resolved = vanilla_root.resolve() if vanilla_root is not None and str(vanilla_root) else None
    except Exception:
        vanilla_resolved = None

    source = "mod"
    if vanilla_resolved is not None:
        try:
            probe_resolved.relative_to(vanilla_resolved)
            source = "vanilla"
        except Exception:
            source = "mod"
    if mod_resolved is not None:
        try:
            probe_resolved.relative_to(mod_resolved)
            source = "mod"
        except Exception:
            pass
    return source


def build_dll_debug_lines(
    pairs: list[tuple[str, str]],
    *,
    resolve_dll_path: Callable[[Path, str], Path | None],
    mod_root: Path | None,
    vanilla_root: Path | None,
    empty_text: str,
    mod_label: str,
    vanilla_label: str,
) -> list[str]:
    if not pairs:
        return [str(empty_text or "No DLL entries found.")]

    lines: list[str] = []
    for idx, (ini_path_text, dll_name) in enumerate(pairs, start=1):
        ini_path = Path(ini_path_text)
        resolved = resolve_dll_path(ini_path, dll_name)
        probe = resolved if resolved is not None else ini_path
        source = classify_dll_source(probe, mod_root=mod_root, vanilla_root=vanilla_root)
        source_label = mod_label if source == "mod" else vanilla_label
        resolved_text = str(resolved) if resolved else "-"
        lines.append(f"[{idx:02d}] {dll_name}")
        lines.append(f"     source: {source_label}")
        lines.append(f"     ini:    {ini_path}")
        lines.append(f"     file:   {resolved_text}")
    return lines
