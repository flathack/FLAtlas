"""File-system and text helpers for the INI editor."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class IniTreeEntry:
    path: Path
    entry_type: str
    children: list["IniTreeEntry"] = field(default_factory=list)
    source: str = "primary"


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


def scan_ini_tree_with_fallback(root_path: Path, fallback_root: Path | None) -> IniTreeEntry:
    fallback = fallback_root if isinstance(fallback_root, Path) else None
    if fallback is None:
        return scan_ini_tree(root_path)
    try:
        if root_path.resolve() == fallback.resolve():
            return scan_ini_tree(root_path)
    except Exception:
        if root_path == fallback:
            return scan_ini_tree(root_path)

    def _existing_dir(path: Path | None) -> Path | None:
        if path is None:
            return None
        if path.exists() and path.is_dir():
            return path
        return None

    def _existing_entry(path: Path | None) -> Path | None:
        if path is None:
            return None
        if path.exists():
            return path
        return None

    def _scan_pair(primary_dir: Path | None, fallback_dir: Path | None) -> IniTreeEntry:
        primary_dir = _existing_dir(primary_dir)
        fallback_dir = _existing_dir(fallback_dir)
        children: list[IniTreeEntry] = []
        names: set[str] = set()
        for folder in (primary_dir, fallback_dir):
            if folder is None:
                continue
            try:
                for child in folder.iterdir():
                    if should_skip_ini_tree_entry(child):
                        continue
                    names.add(child.name)
            except Exception:
                continue

        def _child_type(name: str) -> tuple[int, str]:
            pri = _existing_entry(primary_dir / name) if primary_dir is not None else None
            fb = _existing_entry(fallback_dir / name) if fallback_dir is not None else None
            is_dir = bool((pri is not None and pri.is_dir()) or (fb is not None and fb.is_dir()))
            return (1 if not is_dir else 0, name.lower())

        for name in sorted(names, key=_child_type):
            pri = _existing_entry(primary_dir / name) if primary_dir is not None else None
            fb = _existing_entry(fallback_dir / name) if fallback_dir is not None else None
            if (pri is not None and pri.is_dir()) or (fb is not None and fb.is_dir()):
                child = _scan_pair(
                    pri if pri is not None and pri.is_dir() else None,
                    fb if fb is not None and fb.is_dir() else None,
                )
                if pri is not None and pri.is_dir():
                    child.path = pri
                    child.source = "primary"
                elif fb is not None and fb.is_dir():
                    child.path = fb
                    child.source = "fallback"
                children.append(child)
                continue
            if pri is not None and pri.is_file():
                children.append(IniTreeEntry(path=pri, entry_type="file", source="primary"))
            elif fb is not None and fb.is_file():
                children.append(IniTreeEntry(path=fb, entry_type="file", source="fallback"))

        return IniTreeEntry(path=primary_dir or fallback_dir or root_path, entry_type="dir", children=children)

    tree = _scan_pair(root_path, fallback)
    tree.path = root_path
    tree.source = "primary"
    return tree


def parse_ini_sections(text: str) -> list[tuple[str, int]]:
    sections: list[tuple[str, int]] = []
    for block_number, raw_line in enumerate(str(text or "").splitlines()):
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            sections.append((line, block_number))
    return sections
