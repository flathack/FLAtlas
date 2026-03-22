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


def list_ini_tree_entries_with_fallback(root_path: Path, fallback_root: Path | None) -> list[IniTreeEntry]:
    fallback = fallback_root if isinstance(fallback_root, Path) else None

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

    primary_dir = _existing_dir(root_path)
    fallback_dir = _existing_dir(fallback)
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
            if pri is not None and pri.is_dir():
                children.append(IniTreeEntry(path=pri, entry_type="dir", source="primary"))
            elif fb is not None and fb.is_dir():
                children.append(IniTreeEntry(path=fb, entry_type="dir", source="fallback"))
            continue
        if pri is not None and pri.is_file():
            children.append(IniTreeEntry(path=pri, entry_type="file", source="primary"))
        elif fb is not None and fb.is_file():
            children.append(IniTreeEntry(path=fb, entry_type="file", source="fallback"))
    return children


def parse_ini_sections(text: str) -> list[tuple[str, int]]:
    lines = str(text or "").splitlines()
    sections: list[tuple[str, int]] = []
    raw_sections: list[tuple[str, int]] = []
    for block_number, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            raw_sections.append((line, block_number))

    id_keys = ("nickname", "base", "name", "system", "file")
    for idx, (section_title, block_number) in enumerate(raw_sections):
        end = raw_sections[idx + 1][1] if idx + 1 < len(raw_sections) else len(lines)
        detail = ""
        for raw in lines[block_number + 1:end]:
            line = raw.strip()
            if not line or line.startswith(";") or line.startswith("//") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            key = k.strip().lower()
            if key in id_keys:
                detail = f"{k.strip()} = {v.strip()}"
                break
        if detail:
            sections.append((f"{section_title}  {detail}", block_number))
        else:
            sections.append((section_title, block_number))
    return sections


def _parse_ini_section_blocks(text: str) -> list[tuple[str, str, str]]:
    lines = str(text or "").splitlines()
    section_headers = parse_ini_sections(text)
    raw_headers: list[tuple[str, int]] = []
    for block_number, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            raw_headers.append((line, block_number))
    if not section_headers or not raw_headers:
        return []
    blocks: list[tuple[str, str, str]] = []
    for idx, (section_title, block_number) in enumerate(section_headers):
        end = section_headers[idx + 1][1] if idx + 1 < len(section_headers) else len(lines)
        block_text = "\n".join(lines[block_number:end]).strip()
        raw_title = raw_headers[idx][0] if idx < len(raw_headers) else section_title.split("  ", 1)[0]
        blocks.append((raw_title, section_title, block_text))
    return blocks


def compare_ini_sections(current_text: str, counterpart_text: str) -> dict[str, list[str]]:
    current_blocks = _parse_ini_section_blocks(current_text)
    counterpart_blocks = _parse_ini_section_blocks(counterpart_text)
    current_by_title: dict[str, list[tuple[str, str]]] = {}
    counterpart_by_title: dict[str, list[tuple[str, str]]] = {}

    for raw_title, display_title, block_text in current_blocks:
        current_by_title.setdefault(raw_title, []).append((display_title, block_text))
    for raw_title, display_title, block_text in counterpart_blocks:
        counterpart_by_title.setdefault(raw_title, []).append((display_title, block_text))

    added: list[str] = []
    removed: list[str] = []
    changed: list[str] = []

    all_titles = sorted(set(current_by_title.keys()) | set(counterpart_by_title.keys()))
    for raw_title in all_titles:
        current_list = current_by_title.get(raw_title, [])
        counterpart_list = counterpart_by_title.get(raw_title, [])
        total_occurrences = max(len(current_list), len(counterpart_list))
        common_count = min(len(current_list), len(counterpart_list))

        def _label(index: int) -> str:
            current_display = current_list[index][0] if index < len(current_list) else ""
            counterpart_display = counterpart_list[index][0] if index < len(counterpart_list) else ""
            label = current_display or counterpart_display or raw_title
            if total_occurrences <= 1:
                return label
            return f"{label} (#{index + 1})"

        for idx in range(common_count):
            if current_list[idx][1] != counterpart_list[idx][1]:
                changed.append(_label(idx))
        for idx in range(common_count, len(current_list)):
            added.append(_label(idx))
        for idx in range(common_count, len(counterpart_list)):
            removed.append(_label(idx))

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
    }
