from __future__ import annotations

from fl_editor.native_preview_style import native_preview_color_key, native_preview_rgb


def test_native_preview_color_key_prefers_part_model_and_level() -> None:
    assert native_preview_color_key(
        model_name="li_fighter.3db",
        level_name="Level0",
        part_name="Part_Wing",
        group_start=2,
        group_count=4,
    ) == "Part_Wing|li_fighter.3db|Level0|2|4"


def test_native_preview_rgb_is_stable_and_bright() -> None:
    color = native_preview_rgb(
        model_name="li_fighter.3db",
        level_name="Level0",
        part_name="Part_Wing",
        group_start=2,
        group_count=4,
    )
    assert color == native_preview_rgb(
        model_name="li_fighter.3db",
        level_name="Level0",
        part_name="Part_Wing",
        group_start=2,
        group_count=4,
    )
    assert all(96 <= channel <= 191 for channel in color)
    assert color != native_preview_rgb(
        model_name="li_fighter.3db",
        level_name="Level0",
        part_name="Part_Engine",
        group_start=2,
        group_count=4,
    )
    assert color != native_preview_rgb(
        model_name="li_fighter.3db",
        level_name="Level0",
        part_name="Part_Wing",
        group_start=3,
        group_count=4,
    )
