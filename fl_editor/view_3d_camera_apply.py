from __future__ import annotations

from typing import Any, Callable, Iterable

from PySide6.QtGui import QVector3D


def apply_sky_translation(*, sky_transform: Any, sky_translation_xyz: tuple[float, float, float]) -> None:
    sky_transform.setTranslation(QVector3D(*sky_translation_xyz))


def apply_label_scales(*, label_transforms: Iterable[Any], label_scales: Iterable[float]) -> None:
    for tr, scale in zip(label_transforms, label_scales):
        tr.setScale(float(scale))


def apply_camera_update_effects(
    *,
    camera: Any,
    cam_target_xyz: tuple[float, float, float],
    sky_transform: Any | None,
    label_transforms: Iterable[Any],
    state: dict[str, object],
    update_axis_gizmo: Callable[[], None] | None = None,
) -> None:
    camera.setPosition(QVector3D(*state["camera_pos_xyz"]))
    camera.setViewCenter(QVector3D(*cam_target_xyz))
    if sky_transform is not None:
        apply_sky_translation(
            sky_transform=sky_transform,
            sky_translation_xyz=tuple(state["sky_translation_xyz"]),
        )
    apply_label_scales(label_transforms=label_transforms, label_scales=list(state["label_scales"]))
    if update_axis_gizmo is not None:
        update_axis_gizmo()
