"""Helpers for reading and mutating trade route market sections."""

from __future__ import annotations


def trade_route_format_multiplier(multiplier: float) -> str:
    value = float(multiplier)
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def trade_route_upsert_marketgood_section(
    sections: list[tuple[str, list[tuple[str, str]]]],
    *,
    base: str,
    commodity: str,
    relation_flag: int,
    multiplier_text: str,
) -> list[tuple[str, list[tuple[str, str]]]]:
    base_low = str(base or "").strip().lower()
    commodity_low = str(commodity or "").strip().lower()
    out = list(sections)
    sec_idx: int | None = None
    for idx, (sec_name, entries) in enumerate(out):
        if str(sec_name).lower() != "basegood":
            continue
        sec_base = ""
        for key, value in entries:
            if str(key).lower() == "base":
                sec_base = str(value).strip().lower()
                break
        if sec_base == base_low:
            sec_idx = idx
            break
    if sec_idx is None:
        out.append(("BaseGood", [("base", base)]))
        sec_idx = len(out) - 1

    sec_name, entries = out[sec_idx]
    new_entries: list[tuple[str, str]] = []
    patched = False
    for key, value in entries:
        if str(key).lower() != "marketgood":
            new_entries.append((key, value))
            continue
        fields = [field.strip() for field in str(value).split(",")]
        if not fields or str(fields[0]).strip().lower() != commodity_low:
            new_entries.append((key, value))
            continue
        while len(fields) < 7:
            fields.append("0")
        fields[0] = commodity
        if not fields[1]:
            fields[1] = "0"
        if not fields[2]:
            fields[2] = "-1"
        if not fields[3]:
            fields[3] = "0"
        if not fields[4]:
            fields[4] = "0"
        fields[5] = str(int(relation_flag))
        fields[6] = str(multiplier_text)
        new_entries.append(("MarketGood", ", ".join(fields)))
        patched = True

    if not patched:
        stock_min = "150" if int(relation_flag) == 0 else "0"
        stock_max = "500" if int(relation_flag) == 0 else "0"
        new_entries.append(
            (
                "MarketGood",
                f"{commodity}, 0, -1, {stock_min}, {stock_max}, {int(relation_flag)}, {multiplier_text}",
            )
        )

    out[sec_idx] = (sec_name, new_entries)
    return out


def trade_route_remove_marketgood_section(
    sections: list[tuple[str, list[tuple[str, str]]]],
    *,
    base: str,
    commodity: str,
) -> tuple[list[tuple[str, list[tuple[str, str]]]], bool]:
    base_low = str(base or "").strip().lower()
    commodity_low = str(commodity or "").strip().lower()
    out = list(sections)
    changed = False
    for idx, (sec_name, entries) in enumerate(out):
        if str(sec_name).lower() != "basegood":
            continue
        sec_base = ""
        for key, value in entries:
            if str(key).lower() == "base":
                sec_base = str(value).strip().lower()
                break
        if sec_base != base_low:
            continue
        new_entries: list[tuple[str, str]] = []
        for key, value in entries:
            if str(key).lower() != "marketgood":
                new_entries.append((key, value))
                continue
            fields = [field.strip() for field in str(value).split(",")]
            if fields and str(fields[0]).strip().lower() == commodity_low:
                changed = True
                continue
            new_entries.append((key, value))
        out[idx] = (sec_name, new_entries)
        break
    return out, changed


def serialize_ini_sections(sections: list[tuple[str, list[tuple[str, str]]]]) -> str:
    lines: list[str] = []
    for sec_name, entries in sections:
        lines.append(f"[{sec_name}]")
        for key, value in entries:
            lines.append(f"{key} = {value}")
        lines.append("")
    return "\n".join(lines)
