from __future__ import annotations

from .view_3d_object_logic import parse_pos


def object_position_update_state(*, pos_raw: str, scale: float, label_y_offset: float) -> dict[str, tuple[float, float, float]]:
    fx, fy, fz = parse_pos(pos_raw)
    base = (float(fx) * float(scale), float(fy) * float(scale), float(fz) * float(scale))
    return {
        "translation_xyz": base,
        "label_translation_xyz": (
            base[0] + 1.0,
            base[1] + float(label_y_offset),
            base[2] + 1.0,
        ),
    }
