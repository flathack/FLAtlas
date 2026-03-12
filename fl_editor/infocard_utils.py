"""Infocard XML helpers extracted from the main window."""

from __future__ import annotations

import re


def default_infocard_xml_template() -> str:
    return (
        "<RDL>\n"
        "  <PUSH/>\n"
        "  <TEXT>Title</TEXT>\n"
        "  <PARA/>\n"
        "  <TEXT>Infocard description text...</TEXT>\n"
        "  <POP/>\n"
        "</RDL>"
    )


def escape_xml_text(value: str) -> str:
    txt = str(value or "")
    return (
        txt.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def xml_to_plain_preview(xml_text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", str(xml_text or ""))
    return re.sub(r"\s+", " ", cleaned).strip()


def infocard_flags_to_css(flags: int) -> str:
    styles: list[str] = []
    if flags & 1:
        styles.append("font-weight:700;")
    if flags & 2:
        styles.append("font-style:italic;")
    if flags & 4:
        styles.append("text-decoration: underline;")
    return "".join(styles)


def infocard_normalize_align(loc: str) -> str:
    val = str(loc or "").strip().lower()
    if val in ("l", "left"):
        return "left"
    if val in ("c", "center", "centre"):
        return "center"
    if val in ("r", "right"):
        return "right"
    return "left"


def infocard_normalize_color(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "default"
    low = raw.lower()
    if low in ("default", "def", "none"):
        return "default"
    if re.fullmatch(r"#?[0-9a-fA-F]{6}", raw):
        if not raw.startswith("#"):
            raw = f"#{raw}"
        return raw.upper()
    return "default"


def infocard_apply_tra_to_state(state: dict[str, str | int], attrs: dict[str, str]) -> None:
    if "data" in attrs:
        try:
            state["flags"] = int(str(attrs.get("data", "0")).strip() or "0")
        except Exception:
            pass
    for key, bit in (("bold", 1), ("italic", 2), ("underline", 4)):
        if key not in attrs:
            continue
        value = str(attrs.get(key, "")).strip().lower()
        current = int(state.get("flags", 0) or 0)
        if value in ("1", "true", "yes", "on"):
            state["flags"] = current | bit
        elif value in ("0", "false", "no", "off"):
            state["flags"] = current & (~bit)
    if "color" in attrs:
        state["color"] = infocard_normalize_color(str(attrs.get("color", "")))


def build_infocard_xml_from_fields(title: str, body: str, align: str, flags: int, color: str) -> str:
    title_text = str(title or "").strip()
    body_text = str(body or "").strip()
    if not title_text and not body_text:
        return default_infocard_xml_template()
    normalized_align = infocard_normalize_align(align)
    align_short = "l" if normalized_align == "left" else ("c" if normalized_align == "center" else "r")
    normalized_color = infocard_normalize_color(color)
    lines = ["<RDL>", "  <PUSH/>", f"  <JUST loc=\"{align_short}\"/>"]
    tra_parts = [
        f"bold=\"{'true' if (flags & 1) else 'false'}\"",
        f"italic=\"{'true' if (flags & 2) else 'false'}\"",
        f"underline=\"{'true' if (flags & 4) else 'false'}\"",
        f"color=\"{normalized_color}\"",
    ]
    lines.append(f"  <TRA {' '.join(tra_parts)} />")
    if title_text:
        lines.append(f"  <TEXT>{escape_xml_text(title_text)}</TEXT>")
    body_lines = [line.strip() for line in body_text.splitlines()]
    body_lines = [line for line in body_lines if line]
    if body_lines:
        if title_text:
            lines.append("  <PARA/>")
        for idx, line in enumerate(body_lines):
            lines.append(f"  <TEXT>{escape_xml_text(line)}</TEXT>")
            if idx < len(body_lines) - 1:
                lines.append("  <PARA/>")
    lines.extend(["  <POP/>", "</RDL>"])
    return "\n".join(lines)


def default_scene_infocard_xml(title: str, description_text: str) -> str:
    return (
        "<RDL>\n"
        "  <PUSH/>\n"
        f"  <TEXT>{escape_xml_text(str(title or '').strip() or 'Infocard')}</TEXT>\n"
        "  <PARA/>\n"
        f"  <TEXT>{escape_xml_text(description_text)}</TEXT>\n"
        "  <POP/>\n"
        "</RDL>"
    )
