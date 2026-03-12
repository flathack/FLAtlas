"""Help tree loading for bundled XML help files."""

from __future__ import annotations

from copy import deepcopy
import xml.etree.ElementTree as ET
from pathlib import Path


def help_tree_file_candidates(base_dir: Path, language: str) -> list[Path]:
    lang = "en" if str(language or "").strip().lower() == "en" else "de"
    return [
        base_dir / f"tree_{lang}.xml",
        base_dir / "tree_en.xml",
        base_dir / "tree_de.xml",
    ]


def help_xml_inner_html(node: ET.Element) -> str:
    parts: list[str] = []
    if node.text:
        parts.append(node.text)
    for child in list(node):
        child_copy = deepcopy(child)
        child_copy.tail = None
        parts.append(ET.tostring(child_copy, encoding="unicode", method="html"))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts).strip()


def load_help_tree_sections(base_dir: Path, language: str) -> list[dict[str, object]]:
    entry_fallback = "Entry" if str(language or "").strip().lower() == "en" else "Eintrag"
    for src in help_tree_file_candidates(base_dir, language):
        if not src.exists():
            continue
        try:
            root = ET.parse(src).getroot()
        except Exception:
            continue
        sections: list[dict[str, object]] = []
        for sec in root.findall("section"):
            sec_title = str(sec.get("title", "") or "").strip() or "Help"
            children: list[dict[str, str]] = []
            for item in sec.findall("item"):
                item_title = str(item.get("title", "") or "").strip()
                content = item.find("content")
                content_html = help_xml_inner_html(content) if content is not None else ""
                if item_title or content_html:
                    children.append(
                        {
                            "title": item_title or entry_fallback,
                            "content": content_html or "<p>-</p>",
                        }
                    )
            sections.append({"title": sec_title, "children": children})
        if sections:
            return sections
    return []
