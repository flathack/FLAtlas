from __future__ import annotations

from pathlib import Path


def should_sync_selected_native_scene_data(
    selected_model_path: Path | None,
    completed_model_paths: tuple[Path, ...],
) -> bool:
    if selected_model_path is None:
        return False
    if not completed_model_paths:
        return False
    return selected_model_path in set(completed_model_paths)
