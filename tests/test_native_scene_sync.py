from __future__ import annotations

from pathlib import Path

from fl_editor.native_scene_sync import should_sync_selected_native_scene_data


def test_should_sync_selected_native_scene_data_only_for_matching_completed_path(tmp_path: Path):
    selected = tmp_path / "selected.cmp"
    other = tmp_path / "other.cmp"

    assert should_sync_selected_native_scene_data(
        selected_model_path=selected,
        completed_model_paths=(other,),
    ) is False
    assert should_sync_selected_native_scene_data(
        selected_model_path=selected,
        completed_model_paths=(selected, other),
    ) is True


def test_should_sync_selected_native_scene_data_requires_selected_path(tmp_path: Path):
    selected = tmp_path / "selected.cmp"
    assert should_sync_selected_native_scene_data(
        selected_model_path=None,
        completed_model_paths=(selected,),
    ) is False
