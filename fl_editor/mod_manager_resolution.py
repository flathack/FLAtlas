"""Resolution and aspect-ratio helpers for the Mod Manager."""

from __future__ import annotations

import re


RATIO_DEFINITIONS: list[tuple[str, list[str]]] = [
    ("4:3", ["1024x768", "1280x960", "1600x1200"]),
    ("5:4", ["1280x1024"]),
    ("16:10", ["1280x800", "1440x900", "1680x1050", "1920x1200"]),
    ("16:9", ["1280x720", "1366x768", "1600x900", "1920x1080", "2560x1440", "3840x2160"]),
    ("21:9", ["2560x1080", "3440x1440"]),
]


def parse_resolution(text: str) -> tuple[int, int] | None:
    match = re.match(r"^\s*(\d+)\s*[xX]\s*(\d+)\s*$", str(text or ""))
    if not match:
        return None
    width = int(match.group(1))
    height = int(match.group(2))
    if width <= 0 or height <= 0:
        return None
    return width, height


def resolution_text(width: int, height: int) -> str:
    return f"{int(width)}x{int(height)}"


def default_resolution_text(screen_size: tuple[int, int] | None = None) -> str:
    if screen_size is None:
        return "1920x1080"
    width, height = int(screen_size[0]), int(screen_size[1])
    if width <= 0 or height <= 0:
        return "1920x1080"
    return resolution_text(width, height)


def ratio_definitions() -> list[tuple[str, list[str]]]:
    return [(label, list(values)) for label, values in RATIO_DEFINITIONS]


def ratio_options() -> list[str]:
    return [label for label, _ in ratio_definitions()]


def ratio_for_resolution_text(text: str) -> str | None:
    resolution = parse_resolution(text)
    if resolution is None:
        return None
    width, height = resolution
    aspect = float(width) / float(height)
    best_label = None
    best_delta = None
    for label, _ in ratio_definitions():
        parts = label.split(":")
        if len(parts) != 2:
            continue
        try:
            ratio_width = float(parts[0])
            ratio_height = float(parts[1])
        except Exception:
            continue
        if ratio_height <= 0.0:
            continue
        delta = abs(aspect - (ratio_width / ratio_height))
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_label = label
    return best_label


def resolution_options(
    ratio_label: str | None = None,
    selected_ratio: str | None = None,
    selected_resolution: str | None = None,
    current_resolution: str | None = None,
) -> list[str]:
    wanted = str(ratio_label or selected_ratio or "").strip()
    options: list[str] = []
    definitions = dict(ratio_definitions())
    if wanted in definitions:
        options = list(definitions[wanted])
    else:
        for _label, values in ratio_definitions():
            options.extend(values)
    current = str(current_resolution or default_resolution_text()).strip()
    current_ratio = ratio_for_resolution_text(current)
    if current and current not in options and (not wanted or wanted == current_ratio):
        options.append(current)
    selected = str(selected_resolution or "").strip()
    if selected and selected not in options:
        selected_ratio_guess = ratio_for_resolution_text(selected)
        if not wanted or selected_ratio_guess == wanted:
            options.append(selected)
    return options
