from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExeOffsetSpec:
    key: str
    label_key: str
    note_key: str
    exe_name: str
    offset: int
    value_type: str
    default_value: float | int
    anchor_bytes: bytes = b""
    anchor_relative_offset: int = 0


KNOWN_EXE_OFFSETS: tuple[ExeOffsetSpec, ...] = (
    ExeOffsetSpec(
        key="chat_history_max_lines",
        label_key="mod_settings.offset.chat_history_max_lines.name",
        note_key="mod_settings.offset.chat_history_max_lines.note",
        exe_name="Freelancer.exe",
        offset=0x0691D1,
        value_type="int8",
        default_value=32,
    ),
    ExeOffsetSpec(
        key="contact_list_unit_switch",
        label_key="mod_settings.offset.contact_list_unit_switch.name",
        note_key="mod_settings.offset.contact_list_unit_switch.note",
        exe_name="Freelancer.exe",
        offset=0x0D2C02,
        value_type="int32",
        default_value=2000,
    ),
    ExeOffsetSpec(
        key="cruise_speed_display_limit",
        label_key="mod_settings.offset.cruise_speed_display_limit.name",
        note_key="mod_settings.offset.cruise_speed_display_limit.note",
        exe_name="Freelancer.exe",
        offset=0x1D7E80,
        value_type="float32",
        default_value=300.0,
    ),
    ExeOffsetSpec(
        key="tradelane_speed",
        label_key="mod_settings.offset.tradelane_speed.name",
        note_key="mod_settings.offset.tradelane_speed.note",
        exe_name="Freelancer.exe",
        offset=0x1DB7D8,
        value_type="float32",
        default_value=2500.0,
        anchor_bytes=b"HpLeftLane\x00",
        anchor_relative_offset=-4,
    ),
    ExeOffsetSpec(
        key="scanner_range_solars",
        label_key="mod_settings.offset.scanner_range_solars.name",
        note_key="mod_settings.offset.scanner_range_solars.note",
        exe_name="Freelancer.exe",
        offset=0x212434,
        value_type="float32",
        default_value=2500.0,
    ),
    ExeOffsetSpec(
        key="max_nanobots_hud_part2",
        label_key="mod_settings.offset.max_nanobots_hud_part2.name",
        note_key="mod_settings.offset.max_nanobots_hud_part2.note",
        exe_name="Freelancer.exe",
        offset=0x0DE310,
        value_type="int32",
        default_value=999,
    ),
    ExeOffsetSpec(
        key="navmap_label_upper_limit",
        label_key="mod_settings.offset.navmap_label_upper_limit.name",
        note_key="mod_settings.offset.navmap_label_upper_limit.note",
        exe_name="Freelancer.exe",
        offset=0x1D3EF0,
        value_type="float32",
        default_value=-0.198,
    ),
    ExeOffsetSpec(
        key="bracket_size_multiplier",
        label_key="mod_settings.offset.bracket_size_multiplier.name",
        note_key="mod_settings.offset.bracket_size_multiplier.note",
        exe_name="Freelancer.exe",
        offset=0x1D8EE8,
        value_type="float32",
        default_value=10.0,
    ),
    ExeOffsetSpec(
        key="base_list_tooltip",
        label_key="mod_settings.offset.base_list_tooltip.name",
        note_key="mod_settings.offset.base_list_tooltip.note",
        exe_name="Freelancer.exe",
        offset=0x08F158,
        value_type="int32",
        default_value=967,
    ),
)


def _struct_format_for_value_type(value_type: str) -> str:
    value_type = str(value_type or "").strip().lower()
    if value_type == "float32":
        return "<f"
    if value_type == "int32":
        return "<i"
    if value_type == "int8":
        return "<B"
    raise ValueError(f"Unsupported EXE offset value type: {value_type}")


def resolve_exe_offset(exe_path: str | Path, spec: ExeOffsetSpec) -> int:
    path = Path(exe_path)
    raw = path.read_bytes()
    anchor = bytes(spec.anchor_bytes or b"")
    if anchor:
        idx = raw.find(anchor)
        if idx >= 0:
            resolved = idx + int(spec.anchor_relative_offset)
            fmt = _struct_format_for_value_type(spec.value_type)
            size = struct.calcsize(fmt)
            if resolved >= 0 and resolved + size <= len(raw):
                return resolved
    return int(spec.offset)


def read_exe_offset_value(exe_path: str | Path, spec: ExeOffsetSpec) -> float | int:
    path = Path(exe_path)
    raw = path.read_bytes()
    fmt = _struct_format_for_value_type(spec.value_type)
    size = struct.calcsize(fmt)
    resolved = resolve_exe_offset(path, spec)
    if resolved < 0 or resolved + size > len(raw):
        raise ValueError(f"Offset out of range for {path}: 0x{resolved:X}")
    return struct.unpack_from(fmt, raw, resolved)[0]


def write_exe_offset_value(exe_path: str | Path, spec: ExeOffsetSpec, value: float | int) -> None:
    path = Path(exe_path)
    raw = bytearray(path.read_bytes())
    fmt = _struct_format_for_value_type(spec.value_type)
    size = struct.calcsize(fmt)
    resolved = resolve_exe_offset(path, spec)
    if resolved < 0 or resolved + size > len(raw):
        raise ValueError(f"Offset out of range for {path}: 0x{resolved:X}")
    struct.pack_into(fmt, raw, resolved, value)
    path.write_bytes(raw)


def parse_exe_offset_value(text: str, spec: ExeOffsetSpec) -> float | int:
    raw = str(text or "").strip().replace(",", ".")
    if not raw:
        raise ValueError("Empty value")
    if spec.value_type == "float32":
        return float(raw)
    if spec.value_type == "int32":
        return int(raw, 10)
    if spec.value_type == "int8":
        value = int(raw, 10)
        if value < 0 or value > 255:
            raise ValueError("Value out of range for uint8")
        return value
    raise ValueError(f"Unsupported EXE offset value type: {spec.value_type}")


def format_exe_offset_value(value: float | int, spec: ExeOffsetSpec) -> str:
    if spec.value_type == "float32":
        text = f"{float(value):.7g}"
        if "." not in text and "e" not in text.lower():
            text += ".0"
        return text
    return str(int(value))
