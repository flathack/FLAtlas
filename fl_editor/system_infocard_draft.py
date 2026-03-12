"""Helpers for generating system infocard draft content."""

from __future__ import annotations

from .infocard_utils import escape_xml_text


def collect_base_ids_from_universe_sections(sections, *, entry_get_value) -> dict[str, str]:
    result: dict[str, str] = {}
    for sec_name, entries in sections:
        if str(sec_name).strip().lower() != "base":
            continue
        base_nick = str(entry_get_value(entries, "nickname")).strip().lower()
        if not base_nick:
            continue
        ids_value = str(entry_get_value(entries, "strid_name")).strip()
        if not ids_value:
            ids_value = str(entry_get_value(entries, "ids_name")).strip()
        if ids_value:
            result[base_nick] = ids_value
    return result


def build_system_infocard_draft_xml(
    *,
    sys_name: str,
    lang: str,
    object_count: int,
    zone_count: int,
    star_count: int,
    nebula_count: int,
    asteroid_count: int,
    dest_names: list[str],
    local_faction_disp: str,
    base_names: list[str],
    planet_names: list[str],
) -> str:
    if str(lang).strip().lower() == "de":
        title = f"★ {sys_name} ★"
        p1 = f"Das {sys_name}-System ist ein Sternensystem in Sirius."
        p2 = (
            f"Objekte: {object_count} · Zonen: {zone_count} · Sterne: {star_count} · "
            f"Nebel: {nebula_count} · Asteroidenfelder: {asteroid_count}."
        )
        p3 = "Sprungverbindungen: " + (", ".join(dest_names) if dest_names else "Keine direkten Verbindungen erkannt.")
        p4 = f"Lokale Fraktion: {local_faction_disp}." if local_faction_disp else "Lokale Fraktion: Unbekannt."
        p5 = "Basen: " + (", ".join(base_names) if base_names else "Keine Basen bekannt.")
        p6 = "Planeten: " + (", ".join(planet_names) if planet_names else "Keine Planeten bekannt.")
    else:
        title = f"★ {sys_name} ★"
        p1 = f"The {sys_name} system is a star system in Sirius."
        p2 = (
            f"Objects: {object_count} · Zones: {zone_count} · Stars: {star_count} · "
            f"Nebulae: {nebula_count} · Asteroid fields: {asteroid_count}."
        )
        p3 = "Jump connections: " + (", ".join(dest_names) if dest_names else "No direct connections detected.")
        p4 = f"Local faction: {local_faction_disp}." if local_faction_disp else "Local faction: unknown."
        p5 = "Bases: " + (", ".join(base_names) if base_names else "No known bases.")
        p6 = "Planets: " + (", ".join(planet_names) if planet_names else "No known planets.")

    return (
        "<RDL>\n"
        "  <PUSH/>\n"
        "  <JUST loc=\"c\"/>\n"
        "  <TRA bold=\"true\" color=\"#FFD700\"/>\n"
        f"  <TEXT>{escape_xml_text(title)}</TEXT>\n"
        "  <TRA bold=\"false\" color=\"default\"/>\n"
        "  <PARA/>\n"
        "  <JUST loc=\"l\"/>\n"
        "  <PARA/>\n"
        f"  <TEXT>{escape_xml_text(p1)}</TEXT>\n"
        "  <PARA/>\n"
        f"  <TEXT>{escape_xml_text(p2)}</TEXT>\n"
        "  <PARA/>\n"
        f"  <TEXT>{escape_xml_text(p3)}</TEXT>\n"
        "  <PARA/>\n"
        f"  <TEXT>{escape_xml_text(p4)}</TEXT>\n"
        "  <PARA/>\n"
        f"  <TEXT>{escape_xml_text(p5)}</TEXT>\n"
        "  <PARA/>\n"
        f"  <TEXT>{escape_xml_text(p6)}</TEXT>\n"
        "  <PARA/>\n"
        "  <POP/>\n"
        "</RDL>"
    )
