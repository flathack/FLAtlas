from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .bini import is_bini_bytes


@dataclass(slots=True)
class _SectionLayout:
    name: str
    body_lines: list[str] = field(default_factory=list)


def _read_text_for_layout(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if is_bini_bytes(raw):
        return None
    for encoding in ("utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("cp1252", errors="ignore")


def _parse_existing_layout(text: str) -> tuple[list[str], list[_SectionLayout]]:
    preamble: list[str] = []
    sections: list[_SectionLayout] = []
    current: _SectionLayout | None = None

    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            current = _SectionLayout(name=line[1:-1].strip())
            sections.append(current)
            continue
        if current is None:
            preamble.append(raw_line)
        else:
            current.body_lines.append(raw_line)
    return preamble, sections


def _is_comment_or_blank(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith(";") or stripped.startswith("//")


def _split_inline_comment(value_text: str) -> tuple[str, str, str]:
    semicolon_index = value_text.find(";")
    if semicolon_index <= 0:
        return value_text, "", ""
    value_part = value_text[:semicolon_index]
    comment_prefix = value_part[len(value_part.rstrip()) :]
    return value_part, comment_prefix, value_text[semicolon_index:]


def _rewrite_entry_line(raw_line: str, key: str, value: str, inline_comment: str = "") -> str:
    key_prefix, separator, value_suffix = raw_line.partition("=")
    if not separator:
        return f"{key} = {value}"
    leading = key_prefix[: len(key_prefix) - len(key_prefix.lstrip())]
    key_suffix = key_prefix[len(key_prefix.rstrip()) :]
    value_prefix = value_suffix[: len(value_suffix) - len(value_suffix.lstrip())]
    _old_value, inline_comment_prefix, existing_inline_comment = _split_inline_comment(value_suffix)
    comment = str(inline_comment or "") or f"{inline_comment_prefix}{existing_inline_comment}"
    return f"{leading}{key}{key_suffix}{separator}{value_prefix}{value}{comment}"


def _serialize_section_with_layout(
    sec_name: str,
    entries: list[tuple[str, str]],
    layout: _SectionLayout | None,
) -> list[str]:
    if layout is None:
        lines = [f"[{sec_name}]"]
        for entry in entries:
            key, value = entry
            lines.append(f"{key} = {value}{getattr(entry, 'inline_comment', '') or ''}")
        return lines

    lines = [f"[{sec_name}]"]
    entries_by_key: dict[str, list[tuple[str, str, int]]] = {}
    for entry_index, (key, value) in enumerate(entries):
        entries_by_key.setdefault(str(key or "").strip().lower(), []).append((key, value, entry_index))

    seen_by_key: dict[str, int] = {}
    used_entry_indexes: set[int] = set()

    for raw_line in layout.body_lines:
        if _is_comment_or_blank(raw_line) or "=" not in raw_line:
            lines.append(raw_line)
            continue
        raw_key, _separator, _value = raw_line.partition("=")
        key_token = raw_key.strip().lower()
        occurrence = seen_by_key.get(key_token, 0)
        seen_by_key[key_token] = occurrence + 1
        candidates = entries_by_key.get(key_token, [])
        if occurrence >= len(candidates):
            continue
        key, value, entry_index = candidates[occurrence]
        entry = entries[entry_index]
        used_entry_indexes.add(entry_index)
        lines.append(_rewrite_entry_line(raw_line, str(key), str(value), getattr(entry, "inline_comment", "")))

    for entry_index, (key, value) in enumerate(entries):
        if entry_index not in used_entry_indexes:
            entry = entries[entry_index]
            lines.append(f"{key} = {value}{getattr(entry, 'inline_comment', '') or ''}")
    return lines


def _layout_by_section_occurrence(layout_sections: list[_SectionLayout]) -> dict[tuple[str, int], _SectionLayout]:
    result: dict[tuple[str, int], _SectionLayout] = {}
    counts: dict[str, int] = {}
    for layout in layout_sections:
        key = str(layout.name or "").strip().lower()
        occurrence = counts.get(key, 0)
        counts[key] = occurrence + 1
        result[(key, occurrence)] = layout
    return result


def update_ids_entry_in_sections(
    sections: list,
    sec_type: str,
    obj_nick: str,
    key: str,
    value: str,
) -> bool:
    target_section = str(sec_type or "").strip().lower()
    target_nickname = str(obj_nick or "").strip().lower()
    target_key = str(key or "").strip().lower()

    for sec_name, entries in sections:
        if str(sec_name or "").strip().lower() != target_section:
            continue
        nickname = next(
            (entry_value for entry_key, entry_value in entries if str(entry_key or "").strip().lower() == "nickname"),
            "",
        )
        if str(nickname or "").strip().lower() != target_nickname:
            continue
        for index, (entry_key, _entry_value) in enumerate(entries):
            if str(entry_key or "").strip().lower() == target_key:
                entries[index] = (entry_key, value)
                return True
        return False
    return False


def serialize_sections_to_ini_text(sections: list) -> str:
    lines: list[str] = []
    for index, (sec_name, entries) in enumerate(sections):
        if index > 0:
            lines.append("")
        lines.append(f"[{sec_name}]")
        for entry in entries:
            key, value = entry
            lines.append(f"{key} = {value}{getattr(entry, 'inline_comment', '') or ''}")
    return "\n".join(lines) + "\n"


def serialize_sections_to_ini_text_preserving_layout(sections: list, original_text: str) -> str:
    preamble, layout_sections = _parse_existing_layout(original_text)
    layouts = _layout_by_section_occurrence(layout_sections)
    section_counts: dict[str, int] = {}
    lines: list[str] = list(preamble)

    for sec_name, entries in sections:
        key = str(sec_name or "").strip().lower()
        occurrence = section_counts.get(key, 0)
        section_counts[key] = occurrence + 1
        lines.extend(_serialize_section_with_layout(sec_name, list(entries), layouts.get((key, occurrence))))

    return "\n".join(lines).rstrip("\n") + "\n"


def serialize_sections_to_ini_text_for_file(filepath: str | Path, sections: list) -> str:
    target = Path(filepath)
    original_text = _read_text_for_layout(target) if target.exists() else None
    if original_text is None:
        return serialize_sections_to_ini_text(sections)
    return serialize_sections_to_ini_text_preserving_layout(sections, original_text)


def write_sections_to_file(filepath: str | Path, sections: list) -> None:
    target = Path(filepath)
    target.write_text(serialize_sections_to_ini_text_for_file(target, sections), encoding="utf-8")


def append_ini_section_block(filepath: str | Path, sec_name: str, entries: list[tuple[str, str]]) -> None:
    section_text = serialize_sections_to_ini_text([(sec_name, entries)])
    with Path(filepath).open("a", encoding="utf-8") as handle:
        handle.write("\n" + section_text)
