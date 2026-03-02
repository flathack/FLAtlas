"""Helpers to detect and decode Freelancer BINI files into text INI."""

from __future__ import annotations

import struct
from pathlib import Path


def is_bini_bytes(data: bytes) -> bool:
    return len(data) >= 12 and data[:4] == b"BINI"


def is_bini_file(path: str | Path) -> bool:
    p = Path(path)
    try:
        with p.open("rb") as fh:
            return fh.read(4) == b"BINI"
    except Exception:
        return False


def decode_bini_to_ini_text(data: bytes) -> str:
    """Decode a BINI payload to plain INI text.

    Supported value types:
    - 1: int32
    - 2: float32
    - 3: string offset (null-terminated in string table)
    """
    if not is_bini_bytes(data):
        raise ValueError("Not a BINI file")
    strings_off = int.from_bytes(data[8:12], "little", signed=False)
    if strings_off < 12 or strings_off > len(data):
        raise ValueError("Invalid BINI string table offset")

    str_table = data[strings_off:]
    i = 12
    lines: list[str] = []

    def _get_cstr(off: int) -> str:
        if off < 0 or off >= len(str_table):
            return ""
        end = str_table.find(b"\x00", off)
        if end < 0:
            end = len(str_table)
        return str_table[off:end].decode("cp1252", errors="ignore")

    def _fmt_float(v: float) -> str:
        txt = f"{v:.7g}"
        if "." not in txt and "e" not in txt.lower():
            txt += ".0"
        return txt

    while i < strings_off:
        if i + 4 > strings_off:
            raise ValueError("Truncated BINI section header")
        sec_off = int.from_bytes(data[i : i + 2], "little", signed=False)
        entry_count = int.from_bytes(data[i + 2 : i + 4], "little", signed=False)
        i += 4

        sec_name = _get_cstr(sec_off) or "Section"
        if lines:
            lines.append("")
        lines.append(f"[{sec_name}]")

        for _ in range(entry_count):
            if i + 3 > strings_off:
                raise ValueError("Truncated BINI entry header")
            key_off = int.from_bytes(data[i : i + 2], "little", signed=False)
            value_count = int(data[i + 2])
            i += 3
            key_name = _get_cstr(key_off) or "key"
            values: list[str] = []
            for _ in range(value_count):
                if i >= strings_off:
                    raise ValueError("Truncated BINI value")
                typ = int(data[i])
                i += 1
                if i + 4 > strings_off:
                    raise ValueError("Truncated BINI value payload")
                raw = data[i : i + 4]
                i += 4
                if typ == 1:
                    values.append(str(struct.unpack("<i", raw)[0]))
                elif typ == 2:
                    values.append(_fmt_float(struct.unpack("<f", raw)[0]))
                elif typ == 3:
                    s_off = int.from_bytes(raw, "little", signed=False)
                    values.append(_get_cstr(s_off))
                else:
                    raise ValueError(f"Unsupported BINI value type: {typ}")
            lines.append(f"{key_name} = {', '.join(values)}")

    return "\n".join(lines).rstrip() + "\n"

