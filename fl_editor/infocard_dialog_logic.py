"""Helpers for validating infocard XML dialog input."""

from __future__ import annotations

import xml.etree.ElementTree as ET


def validate_infocard_xml(raw_text: str) -> tuple[bool, str]:
    xml_text = str(raw_text or "").strip()
    if not xml_text:
        return False, ""
    try:
        ET.fromstring(xml_text)
    except Exception as exc:
        return False, str(exc)
    return True, xml_text
