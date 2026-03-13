from __future__ import annotations

from fl_editor.cmp_orientation_debug import build_cmp_orientation_debug_from_hints, cmp_orientation_debug_rows
from fl_editor.freelancer_mesh_data import FreelancerCmpTransformHint


def _hint(
    *,
    part_name: str,
    combined_rotation_rows_xyz=None,
    normalized_rotation_rows_xyz=None,
    translation_magnitude: float | None = None,
) -> FreelancerCmpTransformHint:
    return FreelancerCmpTransformHint(
        part_name=part_name,
        part_index=0,
        record_index=0,
        row_width=3,
        row_count=3,
        translation_xyz=(0.0, 0.0, 0.0),
        combined_translation_xyz=(0.0, 0.0, 0.0),
        leading_vector_xyz=None,
        normalized_forward_xyz=None,
        normalized_rotation_rows_xyz=normalized_rotation_rows_xyz,
        combined_rotation_rows_xyz=combined_rotation_rows_xyz,
        translation_magnitude=translation_magnitude,
    )


def test_cmp_orientation_debug_from_hints_handles_empty_input():
    snapshot = build_cmp_orientation_debug_from_hints(())

    assert snapshot["hint_count"] == 0
    assert snapshot["best_part_name"] is None
    assert snapshot["suggested_up_correction_euler_deg"] == (0.0, 0.0, 0.0)


def test_cmp_orientation_debug_from_hints_reports_identity_axes_without_correction():
    rows = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    snapshot = build_cmp_orientation_debug_from_hints((_hint(part_name="Part_Core", combined_rotation_rows_xyz=rows),))

    assert snapshot["best_axis_map"] == {"local_x": "+X", "local_y": "+Y", "local_z": "+Z"}
    assert snapshot["suggested_up_correction_euler_deg"] == (0.0, 0.0, 0.0)


def test_cmp_orientation_debug_from_hints_suggests_roll_180_when_up_is_inverted():
    rows = ((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0))
    snapshot = build_cmp_orientation_debug_from_hints((_hint(part_name="Part_Core", combined_rotation_rows_xyz=rows),))

    assert snapshot["best_axis_map"]["local_y"] == "-Y"
    assert snapshot["suggested_up_correction_euler_deg"] == (0.0, 0.0, 180.0)


def test_cmp_orientation_debug_rows_formats_snapshot_for_ui_debug():
    rows = cmp_orientation_debug_rows(
        {
            "hint_count": 3,
            "hints_with_combined_rotation": 2,
            "hints_with_local_rotation": 1,
            "best_part_name": "Part_Core",
            "best_rotation_source": "combined",
            "best_axis_map": {"local_x": "+X", "local_y": "-Y", "local_z": "+Z"},
            "suggested_up_correction_euler_deg": (0.0, 0.0, 180.0),
        }
    )

    assert ("best_part_name", "Part_Core") in rows
    assert ("axis_map", "X=+X Y=-Y Z=+Z") in rows
    assert ("suggested_up_correction_euler_deg", "0.0, 0.0, 180.0") in rows
