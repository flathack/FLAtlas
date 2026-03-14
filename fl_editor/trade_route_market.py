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


def trade_route_patch_marketgood_field(
    sections: list[tuple[str, list[tuple[str, str]]]],
    *,
    base: str,
    commodity: str,
    field_index: int,
    new_value: str,
) -> tuple[list[tuple[str, list[tuple[str, str]]]], bool]:
    """Patch a single field in an existing MarketGood entry.

    *field_index*: 0=commodity, 1=stock_start, 2=stock_flag, 3=stock_min,
    4=stock_max, 5=relation_flag, 6=multiplier.

    Returns ``(updated_sections, changed)``.
    """
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
            if not fields or str(fields[0]).strip().lower() != commodity_low:
                new_entries.append((key, value))
                continue
            while len(fields) < 7:
                fields.append("0")
            if 0 <= field_index < len(fields):
                fields[field_index] = str(new_value)
                changed = True
            new_entries.append(("MarketGood", ", ".join(fields)))
        out[idx] = (sec_name, new_entries)
        break
    return out, changed


def extract_base_market_goods(
    sections: list[tuple[str, list[tuple[str, str]]]],
    base: str,
) -> list[dict]:
    """Extract all MarketGood entries for a specific base.

    Returns a list of dicts with keys: commodity, stock_start, stock_flag,
    stock_min, stock_max, relation_flag, multiplier, raw_line.
    """
    base_low = str(base or "").strip().lower()
    result: list[dict] = []
    for sec_name, entries in sections:
        if str(sec_name).lower() != "basegood":
            continue
        sec_base = ""
        for key, value in entries:
            if str(key).lower() == "base":
                sec_base = str(value).strip().lower()
                break
        if sec_base != base_low:
            continue
        for key, value in entries:
            if str(key).lower() != "marketgood":
                continue
            fields = [f.strip() for f in str(value).split(",")]
            if len(fields) < 7:
                continue
            try:
                result.append({
                    "commodity": fields[0],
                    "stock_start": fields[1],
                    "stock_flag": fields[2],
                    "stock_min": int(float(fields[3])) if fields[3] else 0,
                    "stock_max": int(float(fields[4])) if fields[4] else 0,
                    "relation_flag": int(float(fields[5])),
                    "multiplier": float(fields[6]),
                    "raw_line": value,
                })
            except (ValueError, IndexError):
                continue
        break
    return result


def list_bases_with_commodity(
    sections: list[tuple[str, list[tuple[str, str]]]],
    commodity: str,
) -> list[dict]:
    """Find all bases that trade a specific commodity.

    Returns list of dicts: base, relation_flag, multiplier.
    """
    commodity_low = str(commodity or "").strip().lower()
    result: list[dict] = []
    for sec_name, entries in sections:
        if str(sec_name).lower() != "basegood":
            continue
        base_nick = ""
        for key, value in entries:
            if str(key).lower() == "base":
                base_nick = str(value).strip().lower()
                break
        if not base_nick:
            continue
        for key, value in entries:
            if str(key).lower() != "marketgood":
                continue
            fields = [f.strip() for f in str(value).split(",")]
            if len(fields) < 7:
                continue
            if str(fields[0]).strip().lower() != commodity_low:
                continue
            try:
                result.append({
                    "base": base_nick,
                    "relation_flag": int(float(fields[5])),
                    "multiplier": float(fields[6]),
                })
            except (ValueError, IndexError):
                continue
    return result
