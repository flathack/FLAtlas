"""File-system and text helpers for the INI editor."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class IniTreeEntry:
    path: Path
    entry_type: str
    children: list["IniTreeEntry"] = field(default_factory=list)


def should_skip_ini_tree_entry(path: Path) -> bool:
    return path.name.startswith(".git")


def scan_ini_tree(root_path: Path) -> IniTreeEntry:
    def _scan(folder: Path) -> IniTreeEntry:
        children: list[IniTreeEntry] = []
        for child in sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if should_skip_ini_tree_entry(child):
                continue
            if child.is_dir():
                children.append(_scan(child))
            else:
                children.append(IniTreeEntry(path=child, entry_type="file"))
        return IniTreeEntry(path=folder, entry_type="dir", children=children)

    return _scan(root_path)


def parse_ini_sections(text: str) -> list[tuple[str, int]]:
    sections: list[tuple[str, int]] = []
    for block_number, raw_line in enumerate(str(text or "").splitlines()):
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            sections.append((line, block_number))
    return sections
