from __future__ import annotations

import math
from typing import Any

from .freelancer_mesh_data import FreelancerCmpTransformHint, FreelancerMeshData


def build_cmp_orientation_debug_snapshot(mesh_data: FreelancerMeshData) -> dict[str, Any]:
    return build_cmp_orientation_debug_from_hints(mesh_data.cmp_transform_hints)


def cmp_orientation_debug_rows(snapshot: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    suggested = snapshot.get("suggested_up_correction_euler_deg", (0.0, 0.0, 0.0))
    axis_map = snapshot.get("best_axis_map", {}) or {}
    return (
        ("hint_count", str(snapshot.get("hint_count", 0))),
        ("combined_rotation_hints", str(snapshot.get("hints_with_combined_rotation", 0))),
        ("local_rotation_hints", str(snapshot.get("hints_with_local_rotation", 0))),
        ("best_part_name", str(snapshot.get("best_part_name") or "n/a")),
        ("best_rotation_source", str(snapshot.get("best_rotation_source") or "n/a")),
        (
            "axis_map",
            f"X={axis_map.get('local_x', '?')} Y={axis_map.get('local_y', '?')} Z={axis_map.get('local_z', '?')}",
        ),
        (
            "suggested_up_correction_euler_deg",
            f"{float(suggested[0]):.1f}, {float(suggested[1]):.1f}, {float(suggested[2]):.1f}",
        ),
    )


def build_cmp_orientation_debug_from_hints(
    hints: tuple[FreelancerCmpTransformHint, ...],
) -> dict[str, Any]:
    candidate_rows: list[tuple[str, str, tuple[tuple[float, float, float], ...], float]] = []
    for hint in hints:
        if hint.combined_rotation_rows_xyz is not None and len(hint.combined_rotation_rows_xyz) >= 3:
            score = float(abs(hint.translation_magnitude or 0.0))
            candidate_rows.append((hint.part_name, "combined", hint.combined_rotation_rows_xyz, score))
            continue
        if hint.normalized_rotation_rows_xyz is not None and len(hint.normalized_rotation_rows_xyz) >= 3:
            score = float(abs(hint.translation_magnitude or 0.0)) + 10_000.0
            candidate_rows.append((hint.part_name, "local", hint.normalized_rotation_rows_xyz, score))

    best_part = None
    best_source = None
    best_rows = None
    if candidate_rows:
        best_part, best_source, best_rows, _score = sorted(candidate_rows, key=lambda item: item[3])[0]

    diagnostics: dict[str, Any] = {
        "hint_count": len(hints),
        "hints_with_combined_rotation": sum(1 for hint in hints if hint.combined_rotation_rows_xyz is not None),
        "hints_with_local_rotation": sum(1 for hint in hints if hint.normalized_rotation_rows_xyz is not None),
        "hints_with_combined_translation": sum(1 for hint in hints if hint.combined_translation_xyz is not None),
        "hints_with_forward_hint": sum(1 for hint in hints if hint.normalized_forward_xyz is not None),
        "best_part_name": best_part,
        "best_rotation_source": best_source,
        "best_rotation_rows": best_rows,
    }
    if best_rows is None:
        diagnostics["suggested_up_correction_euler_deg"] = (0.0, 0.0, 0.0)
        diagnostics["best_axis_map"] = {}
        diagnostics["best_rotation_determinant"] = None
        diagnostics["best_rotation_orthogonality_error"] = None
        return diagnostics

    local_x_axis, local_y_axis, local_z_axis = _columns_from_rows(best_rows)
    diagnostics["best_axes"] = {
        "local_x": local_x_axis,
        "local_y": local_y_axis,
        "local_z": local_z_axis,
    }
    diagnostics["best_axis_map"] = {
        "local_x": _axis_label(local_x_axis),
        "local_y": _axis_label(local_y_axis),
        "local_z": _axis_label(local_z_axis),
    }
    diagnostics["best_rotation_determinant"] = _det3(best_rows)
    diagnostics["best_rotation_orthogonality_error"] = _orthogonality_error(best_rows)
    diagnostics["suggested_up_correction_euler_deg"] = _up_correction_from_local_y(local_y_axis)
    return diagnostics


def _columns_from_rows(
    rows: tuple[tuple[float, float, float], ...],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    r0, r1, r2 = rows[0], rows[1], rows[2]
    return (
        (float(r0[0]), float(r1[0]), float(r2[0])),
        (float(r0[1]), float(r1[1]), float(r2[1])),
        (float(r0[2]), float(r1[2]), float(r2[2])),
    )


def _axis_label(axis: tuple[float, float, float]) -> str:
    names = ("X", "Y", "Z")
    values = (float(axis[0]), float(axis[1]), float(axis[2]))
    index = max(range(3), key=lambda idx: abs(values[idx]))
    sign = "+" if values[index] >= 0.0 else "-"
    return f"{sign}{names[index]}"


def _up_correction_from_local_y(local_y_axis: tuple[float, float, float]) -> tuple[float, float, float]:
    label = _axis_label(local_y_axis)
    if label == "+Y":
        return (0.0, 0.0, 0.0)
    if label == "-Y":
        return (0.0, 0.0, 180.0)
    if label == "+Z":
        return (-90.0, 0.0, 0.0)
    if label == "-Z":
        return (90.0, 0.0, 0.0)
    if label == "+X":
        return (0.0, 0.0, -90.0)
    return (0.0, 0.0, 90.0)


def _det3(rows: tuple[tuple[float, float, float], ...]) -> float:
    a, b, c = rows[0], rows[1], rows[2]
    return float(
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def _orthogonality_error(rows: tuple[tuple[float, float, float], ...]) -> float:
    a, b, c = rows[0], rows[1], rows[2]
    return float(
        abs(_dot(a, b))
        + abs(_dot(a, c))
        + abs(_dot(b, c))
        + abs(_norm(a) - 1.0)
        + abs(_norm(b) - 1.0)
        + abs(_norm(c) - 1.0)
    )


def _dot(lhs: tuple[float, float, float], rhs: tuple[float, float, float]) -> float:
    return float(lhs[0] * rhs[0] + lhs[1] * rhs[1] + lhs[2] * rhs[2])


def _norm(value: tuple[float, float, float]) -> float:
    return math.sqrt(float(value[0] * value[0] + value[1] * value[1] + value[2] * value[2]))
