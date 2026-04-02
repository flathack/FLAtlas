from __future__ import annotations

import logging
import traceback
from typing import Callable

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .model_viewer_dialog import ModelViewerEntry
from .base_assembly_preview import BaseAssemblyPreviewView
from .view_2d import SystemView
from .view_3d import QT3D_AVAILABLE

from .view_3d_object_logic import parse_rotate

import math


class _AxisGizmoOverlay(QWidget):
    """Small 2D axis indicator drawn as an overlay in the top-right corner."""

    _AXIS_COLORS = {
        "x": QColor(224, 92, 92),
        "y": QColor(88, 208, 118),
        "z": QColor(96, 156, 236),
    }

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._mode: str = "navigate"
        self._axis: str = "x"
        self._yaw_deg: float = 0.0
        self._pitch_deg: float = 0.0
        self.setFixedSize(90, 90)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_state(self, mode: str, axis: str) -> None:
        self._mode = mode
        self._axis = axis
        self.update()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.move(parent.width() - self.width() - 4, 4)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.parentWidget() and event.type() == QEvent.Resize:
            self._reposition()
        return super().eventFilter(watched, event)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._reposition()

    def paintEvent(self, _event) -> None:  # noqa: N802
        if self._mode == "navigate":
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy = 45, 50
        length = 32
        yaw = math.radians(30)
        pitch = math.radians(20)
        cos_y, sin_y = math.cos(yaw), math.sin(yaw)
        cos_p, sin_p = math.cos(pitch), math.sin(pitch)
        axes_3d = {
            "x": (1.0, 0.0, 0.0),
            "y": (0.0, 1.0, 0.0),
            "z": (0.0, 0.0, 1.0),
        }

        def project(vx, vy, vz):
            rx = vx * cos_y + vz * sin_y
            ry = -vx * sin_y * sin_p + vy * cos_p + vz * cos_y * sin_p
            return cx + rx * length, cy - ry * length

        for axis_name in ("x", "y", "z"):
            vx, vy, vz = axes_3d[axis_name]
            ex, ey = project(vx, vy, vz)
            color = QColor(self._AXIS_COLORS[axis_name])
            is_active = axis_name == self._axis
            pen = QPen(color, 3.0 if is_active else 1.8)
            painter.setPen(pen)
            painter.drawLine(int(cx), int(cy), int(ex), int(ey))
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(int(ex) - 4, int(ey) - 4, 8, 8)
            font = painter.font()
            font.setPixelSize(11)
            font.setBold(is_active)
            painter.setFont(font)
            painter.setPen(color if is_active else color.darker(120))
            painter.drawText(int(ex) + 5, int(ey) + 4, axis_name.upper())
        mode_label = "Move" if self._mode == "move" else "Rotate"
        font = painter.font()
        font.setPixelSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor(200, 200, 200) if self.palette().window().color().lightnessF() < 0.5 else QColor(80, 80, 80))
        painter.drawText(2, 12, mode_label)
        painter.end()


class BaseBuilderDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        base_nickname: str,
        scene,
        part_entries: list[ModelViewerEntry],
        scene_payload_provider: Callable[[], tuple[list[object], list[object], float]],
        existing_parts_provider: Callable[[], list[dict[str, str]]],
        selected_scene_data_provider: Callable[[object | None], object | None],
        configure_3d_view_callback: Callable[[BaseAssemblyPreviewView], None] | None,
        embedded_preview_factory: Callable[[ModelViewerEntry, QWidget], QWidget | None],
        add_part_callback: Callable[[ModelViewerEntry], None],
        delete_selected_callback: Callable[[], None],
        save_callback: Callable[[], None],
        undo_callback: Callable[[], bool] | None,
        history_provider: Callable[[], list[dict[str, object]]] | None,
        is_dirty_callback: Callable[[], bool] | None,
        select_existing_part_callback: Callable[[str], None],
        select_object_callback: Callable[[object], None],
        clear_selection_callback: Callable[[], None],
        begin_transform_callback: Callable[[str, str], bool],
        update_transform_callback: Callable[[float], None],
        finish_transform_callback: Callable[[bool], None],
        closed_callback: Callable[[], None] | None = None,
    ):
        super().__init__(parent)
        self.setModal(False)
        self.resize(1480, 860)
        self._base_nickname = str(base_nickname).strip()
        self._window_title_base = f"Base Builder - {self._base_nickname}"
        self.setWindowTitle(self._window_title_base)

        self._all_part_entries = list(part_entries)
        self._scene_payload_provider = scene_payload_provider
        self._existing_parts_provider = existing_parts_provider
        self._selected_scene_data_provider = selected_scene_data_provider
        self._configure_3d_view_callback = configure_3d_view_callback
        self._embedded_preview_factory = embedded_preview_factory
        self._add_part_callback = add_part_callback
        self._delete_selected_callback = delete_selected_callback
        self._save_callback = save_callback
        self._undo_callback = undo_callback
        self._history_provider = history_provider
        self._is_dirty_callback = is_dirty_callback
        self._select_existing_part_callback = select_existing_part_callback
        self._select_object_callback = select_object_callback
        self._clear_selection_callback = clear_selection_callback
        self._begin_transform_callback = begin_transform_callback
        self._update_transform_callback = update_transform_callback
        self._finish_transform_callback = finish_transform_callback
        self._closed_callback = closed_callback
        self._current_part_entry: ModelViewerEntry | None = None
        self._preview_widget: QWidget | None = None
        self._transform_state: dict[str, object] | None = None
        self._selected_scene_object = None
        self._scene_initialized = False
        self._last_centered_object = None
        self._syncing_existing_part_list = False
        self._viewport_mode = "navigate"
        self._viewport_axis = "x"
        self._part_filter_timer = QTimer(self)
        self._part_filter_timer.setSingleShot(True)
        self._part_filter_timer.setInterval(220)
        self._part_filter_timer.timeout.connect(self._apply_pending_part_filter)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        content_row = QHBoxLayout()
        content_row.setSpacing(10)
        root.addLayout(content_row, 1)

        left_col = QVBoxLayout()
        left_col.setSpacing(8)
        content_row.addLayout(left_col, 7)

        transform_box = QGroupBox("Transform", self)
        transform_layout = QVBoxLayout(transform_box)
        transform_layout.setContentsMargins(8, 8, 8, 8)
        transform_layout.setSpacing(4)

        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(6)

        move_row = QHBoxLayout()
        move_row.setSpacing(3)
        move_row.addWidget(QLabel("Move", transform_box))
        self._move_x_btn = self._build_transform_button("X", "move", "x")
        self._move_y_btn = self._build_transform_button("Y", "move", "y")
        self._move_z_btn = self._build_transform_button("Z", "move", "z")
        move_row.addWidget(self._move_x_btn)
        move_row.addWidget(self._move_y_btn)
        move_row.addWidget(self._move_z_btn)
        toolbar_row.addLayout(move_row)

        rotate_row = QHBoxLayout()
        rotate_row.setSpacing(3)
        rotate_row.addWidget(QLabel("Rot", transform_box))
        self._rot_x_btn = self._build_transform_button("X", "rotate", "x")
        self._rot_y_btn = self._build_transform_button("Y", "rotate", "y")
        self._rot_z_btn = self._build_transform_button("Z", "rotate", "z")
        rotate_row.addWidget(self._rot_x_btn)
        rotate_row.addWidget(self._rot_y_btn)
        rotate_row.addWidget(self._rot_z_btn)
        toolbar_row.addLayout(rotate_row)

        sep = QFrame(transform_box)
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        toolbar_row.addWidget(sep)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(3)
        mode_row.addWidget(QLabel("Mode", transform_box))
        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        self._mode_nav_btn = self._build_mode_button("Nav", "navigate")
        self._mode_move_btn = self._build_mode_button("Move", "move")
        self._mode_rotate_btn = self._build_mode_button("Rot", "rotate")
        mode_row.addWidget(self._mode_nav_btn)
        mode_row.addWidget(self._mode_move_btn)
        mode_row.addWidget(self._mode_rotate_btn)
        toolbar_row.addLayout(mode_row)

        axis_row = QHBoxLayout()
        axis_row.setSpacing(3)
        axis_row.addWidget(QLabel("Axis", transform_box))
        self._axis_group = QButtonGroup(self)
        self._axis_group.setExclusive(True)
        self._axis_x_btn = self._build_axis_button("X", "x")
        self._axis_y_btn = self._build_axis_button("Y", "y")
        self._axis_z_btn = self._build_axis_button("Z", "z")
        axis_row.addWidget(self._axis_x_btn)
        axis_row.addWidget(self._axis_y_btn)
        axis_row.addWidget(self._axis_z_btn)
        toolbar_row.addLayout(axis_row)

        step_row = QHBoxLayout()
        step_row.setSpacing(3)
        step_row.addWidget(QLabel("Step", transform_box))
        self._step_spin = QSpinBox(transform_box)
        self._step_spin.setRange(1, 360)
        self._step_spin.setValue(15)
        self._step_spin.setSuffix("°")
        self._step_spin.setToolTip("Step size for rotation (degrees)")
        self._step_spin.setFixedWidth(65)
        step_row.addWidget(self._step_spin)
        self._step_minus_btn = QPushButton("\u2212", transform_box)
        self._step_minus_btn.setFixedSize(28, 28)
        self._step_minus_btn.setToolTip("Step -N in current mode/axis")
        self._step_minus_btn.clicked.connect(lambda: self._apply_precision_step(-1))
        step_row.addWidget(self._step_minus_btn)
        self._step_plus_btn = QPushButton("+", transform_box)
        self._step_plus_btn.setFixedSize(28, 28)
        self._step_plus_btn.setToolTip("Step +N in current mode/axis")
        self._step_plus_btn.clicked.connect(lambda: self._apply_precision_step(1))
        step_row.addWidget(self._step_plus_btn)
        toolbar_row.addLayout(step_row)

        sep2 = QFrame(transform_box)
        sep2.setFrameShape(QFrame.VLine)
        sep2.setFrameShadow(QFrame.Sunken)
        toolbar_row.addWidget(sep2)

        self._reset_camera_btn = QPushButton("Reset Cam", transform_box)
        self._reset_camera_btn.setMinimumHeight(28)
        self._reset_camera_btn.clicked.connect(self._reset_camera)
        toolbar_row.addWidget(self._reset_camera_btn)

        toolbar_row.addWidget(QLabel("Zoom", transform_box))
        self._zoom_slider = QSlider(Qt.Horizontal, transform_box)
        self._zoom_slider.setRange(20, 300)
        self._zoom_slider.setSingleStep(5)
        self._zoom_slider.setPageStep(20)
        self._zoom_slider.setValue(100)
        self._zoom_slider.valueChanged.connect(self._apply_preview_zoom)
        toolbar_row.addWidget(self._zoom_slider, 1)
        self._zoom_value_label = QLabel("1.00x", transform_box)
        toolbar_row.addWidget(self._zoom_value_label)

        transform_layout.addLayout(toolbar_row)

        self._selection_label = QLabel("Selection: base or no child part selected", transform_box)
        self._selection_label.setWordWrap(False)
        transform_layout.addWidget(self._selection_label)
        self._transform_status = QLabel(
            "Navigate: left drag orbits, middle drag pans, wheel zooms. Move/Rotate: select a child part, choose axis, then drag in the 3D view.",
            transform_box,
        )
        self._transform_status.setWordWrap(False)
        transform_layout.addWidget(self._transform_status)

        rot_display_row = QHBoxLayout()
        rot_display_row.setSpacing(6)
        rot_display_row.addWidget(QLabel("Rotation:", transform_box))
        self._rot_x_label = QLabel("X: 0.0", transform_box)
        self._rot_x_label.setStyleSheet("color: #e05c5c; font-weight: bold;")
        self._rot_x_label.setMinimumWidth(70)
        rot_display_row.addWidget(self._rot_x_label)
        self._rot_y_label = QLabel("Y: 0.0", transform_box)
        self._rot_y_label.setStyleSheet("color: #58d076; font-weight: bold;")
        self._rot_y_label.setMinimumWidth(70)
        rot_display_row.addWidget(self._rot_y_label)
        self._rot_z_label = QLabel("Z: 0.0", transform_box)
        self._rot_z_label.setStyleSheet("color: #609cec; font-weight: bold;")
        self._rot_z_label.setMinimumWidth(70)
        rot_display_row.addWidget(self._rot_z_label)
        rot_display_row.addStretch(1)
        transform_layout.addLayout(rot_display_row)

        left_col.addWidget(transform_box)

        self._build_view_3d: BaseAssemblyPreviewView | None = None
        self._build_view_2d: SystemView | None = None
        if QT3D_AVAILABLE:
            self._build_view_3d = BaseAssemblyPreviewView()
            if callable(self._configure_3d_view_callback):
                self._configure_3d_view_callback(self._build_view_3d)
            self._build_view_3d.object_selected.connect(self._on_view_object_selected)
            if hasattr(self._build_view_3d, "set_transform_handlers"):
                self._build_view_3d.set_transform_handlers(
                    self._begin_viewport_transform,
                    self._update_viewport_transform,
                    self._finish_viewport_transform,
                )
            if hasattr(self._build_view_3d, "context_menu_requested"):
                self._build_view_3d.context_menu_requested.connect(lambda _pos, _item: None)
            left_col.addWidget(self._build_view_3d, 1)
            self._gizmo_overlay = _AxisGizmoOverlay(self._build_view_3d)
            self._gizmo_overlay.raise_()
            self._build_view_3d.installEventFilter(self._gizmo_overlay)
            self._apply_preview_zoom(self._zoom_slider.value())
            self._apply_viewport_interaction_settings()
        else:
            self._build_view_2d = SystemView()
            self._build_view_2d.setScene(scene)
            self._build_view_2d.set_world_scale(1.0)
            self._build_view_2d.set_left_drag_pan_enabled(False)
            self._build_view_2d.object_selected.connect(self._on_view_object_selected)
            self._build_view_2d.zone_clicked.connect(lambda _zone: self._clear_selection_callback())
            self._build_view_2d.background_clicked.connect(lambda _pos: self._clear_selection_callback())
            self._build_view_2d.context_menu_requested.connect(lambda _pos, _item: None)
            self._build_view_2d.setFrameShape(QFrame.StyledPanel)
            left_col.addWidget(self._build_view_2d, 1)

        existing_box = QGroupBox("Existing Parts", self)
        existing_layout = QHBoxLayout(existing_box)
        existing_layout.setContentsMargins(8, 8, 8, 8)
        existing_layout.setSpacing(6)
        self._existing_summary_label = QLabel(existing_box)
        existing_layout.addWidget(self._existing_summary_label)
        self._existing_part_combo = QComboBox(existing_box)
        self._existing_part_combo.currentIndexChanged.connect(self._on_existing_part_selection_changed)
        existing_layout.addWidget(self._existing_part_combo, 1)
        left_col.addWidget(existing_box)

        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        content_row.addLayout(right_col, 1)
        content_row.setStretch(0, 3)
        content_row.setStretch(1, 1)

        catalog_box = QGroupBox("Parts", self)
        catalog_box.setMaximumWidth(420)
        catalog_layout = QVBoxLayout(catalog_box)
        catalog_layout.setContentsMargins(8, 8, 8, 8)
        catalog_layout.setSpacing(6)
        self._search_edit = QLineEdit(catalog_box)
        self._search_edit.setPlaceholderText("Filter parts by name, archetype or file")
        self._search_edit.textChanged.connect(self._schedule_part_list_rebuild)
        self._search_edit.returnPressed.connect(self._apply_pending_part_filter)
        catalog_layout.addWidget(self._search_edit)
        self._summary_label = QLabel(catalog_box)
        catalog_layout.addWidget(self._summary_label)
        self._part_list = QListWidget(catalog_box)
        self._part_list.currentItemChanged.connect(self._on_part_selection_changed)
        self._part_list.itemDoubleClicked.connect(lambda _item: self._add_selected_part())
        catalog_layout.addWidget(self._part_list, 1)
        right_col.addWidget(catalog_box, 4)

        action_box = QGroupBox("Part Actions", self)
        action_box.setMaximumWidth(420)
        action_layout = QHBoxLayout(action_box)
        action_layout.setContentsMargins(8, 8, 8, 8)
        self._add_btn = QPushButton("Add", action_box)
        self._add_btn.setMinimumHeight(42)
        self._add_btn.clicked.connect(self._add_selected_part)
        action_layout.addWidget(self._add_btn)
        self._undo_btn = QPushButton("Undo", action_box)
        self._undo_btn.setMinimumHeight(42)
        self._undo_btn.clicked.connect(self._undo_last_change)
        self._undo_btn.setEnabled(False)
        action_layout.addWidget(self._undo_btn)
        self._delete_btn = QPushButton("Delete Selected Part", action_box)
        self._delete_btn.clicked.connect(self._delete_selected_callback)
        self._delete_btn.setEnabled(False)
        self._delete_btn.setMinimumHeight(42)
        action_layout.addWidget(self._delete_btn)
        right_col.addWidget(action_box)

        history_box = QGroupBox("History", self)
        history_box.setMaximumWidth(420)
        history_layout = QVBoxLayout(history_box)
        history_layout.setContentsMargins(8, 8, 8, 8)
        history_layout.setSpacing(6)
        self._history_summary_label = QLabel("0 changes", history_box)
        history_layout.addWidget(self._history_summary_label)
        self._history_list = QListWidget(history_box)
        self._history_list.setSelectionMode(QListWidget.SingleSelection)
        self._history_list.setFocusPolicy(Qt.NoFocus)
        history_layout.addWidget(self._history_list, 1)
        right_col.addWidget(history_box, 1)

        preview_box = QGroupBox("Part Preview", self)
        preview_box.setMaximumWidth(420)
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setSpacing(6)
        self._preview_placeholder = QLabel("Select a part to load the preview.", preview_box)
        self._preview_placeholder.setAlignment(Qt.AlignCenter)
        self._preview_placeholder.setMinimumHeight(160)
        preview_layout.addWidget(self._preview_placeholder)
        self._preview_host = QWidget(preview_box)
        self._preview_host_layout = QVBoxLayout(self._preview_host)
        self._preview_host_layout.setContentsMargins(0, 0, 0, 0)
        self._preview_host_layout.setSpacing(0)
        preview_layout.addWidget(self._preview_host, 1)
        right_col.addWidget(preview_box, 3)

        bottom_row = QHBoxLayout()
        root.addLayout(bottom_row)
        self._save_btn = QPushButton("Save To Game", self)
        self._save_btn.clicked.connect(self._save_callback)
        bottom_row.addWidget(self._save_btn)
        self._close_btn = QPushButton("Close", self)
        self._close_btn.clicked.connect(self.close)
        bottom_row.addWidget(self._close_btn)
        bottom_row.addStretch(1)

        self._transform_buttons = (
            self._move_x_btn,
            self._move_y_btn,
            self._move_z_btn,
            self._rot_x_btn,
            self._rot_y_btn,
            self._rot_z_btn,
        )
        self._mode_nav_btn.setChecked(True)
        self._update_mode_button_style(self._mode_nav_btn, True)
        self._axis_x_btn.setChecked(True)
        self._update_axis_button_styles()
        QShortcut(QKeySequence("Q"), self).activated.connect(lambda: self._set_viewport_mode("navigate"))
        QShortcut(QKeySequence("W"), self).activated.connect(lambda: self._set_viewport_mode("move"))
        QShortcut(QKeySequence("E"), self).activated.connect(lambda: self._set_viewport_mode("rotate"))
        QShortcut(QKeySequence("X"), self).activated.connect(lambda: self._set_viewport_axis("x"))
        QShortcut(QKeySequence("Y"), self).activated.connect(lambda: self._set_viewport_axis("y"))
        QShortcut(QKeySequence("Z"), self).activated.connect(lambda: self._set_viewport_axis("z"))
        QShortcut(QKeySequence("F"), self).activated.connect(self._reset_camera)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self._undo_last_change)
        self._rebuild_part_list(select_first=True)
        self.refresh_existing_parts()
        self.refresh_history()
        self.set_dirty_state(self._has_unsaved_changes())

    def _build_mode_button(self, label: str, mode: str) -> QPushButton:
        btn = QPushButton(label, self)
        btn.setCheckable(True)
        btn.setMinimumSize(52, 28)
        btn.clicked.connect(lambda _checked=False, value=mode: self._set_viewport_mode(value))
        self._mode_group.addButton(btn)
        self._update_mode_button_style(btn, False)
        return btn

    _MODE_ACTIVE_STYLE = (
        "QPushButton:checked { background-color: #3a7bd5; color: #fff; font-weight: bold; border: 1px solid #2a5fa5; }"
    )
    _MODE_INACTIVE_STYLE = ""

    def _update_mode_button_style(self, btn: QPushButton, active: bool) -> None:
        btn.setStyleSheet(self._MODE_ACTIVE_STYLE if active else self._MODE_INACTIVE_STYLE)

    _AXIS_COLORS = {"x": "#e05c5c", "y": "#58d076", "z": "#609cec"}

    def _axis_button_style(self, axis: str, active: bool = False) -> str:
        c = self._AXIS_COLORS.get(axis.lower(), "")
        if not c:
            return ""
        if active:
            return (
                f"QPushButton {{ color: #fff; font-weight: bold; background-color: {c}; border: 1px solid {c}; }}"
            )
        return f"QPushButton {{ color: {c}; font-weight: bold; }}"

    def _update_axis_button_styles(self) -> None:
        ax = self._viewport_axis
        self._axis_x_btn.setStyleSheet(self._axis_button_style("x", ax == "x"))
        self._axis_y_btn.setStyleSheet(self._axis_button_style("y", ax == "y"))
        self._axis_z_btn.setStyleSheet(self._axis_button_style("z", ax == "z"))

    def _build_axis_button(self, label: str, axis: str) -> QPushButton:
        btn = QPushButton(label, self)
        btn.setCheckable(True)
        btn.setMinimumSize(34, 28)
        btn.setStyleSheet(self._axis_button_style(axis))
        btn.clicked.connect(lambda _checked=False, value=axis: self._set_viewport_axis(value))
        self._axis_group.addButton(btn)
        return btn

    def _build_transform_button(self, label: str, mode: str, axis: str) -> QPushButton:
        btn = QPushButton(label, self)
        btn.setMinimumSize(34, 28)
        btn.setStyleSheet(self._axis_button_style(axis))
        btn.pressed.connect(lambda m=mode, a=axis, b=btn: self._start_transform(m, a, b))
        btn.released.connect(self._finish_transform)
        return btn

    def _on_view_object_selected(self, obj) -> None:
        self._select_object_callback(obj)

    def _set_viewport_mode(self, mode: str) -> None:
        value = str(mode or "navigate").strip().lower()
        if value not in {"navigate", "move", "rotate"}:
            value = "navigate"
        self._viewport_mode = value
        self._mode_nav_btn.setChecked(value == "navigate")
        self._mode_move_btn.setChecked(value == "move")
        self._mode_rotate_btn.setChecked(value == "rotate")
        self._update_mode_button_style(self._mode_nav_btn, value == "navigate")
        self._update_mode_button_style(self._mode_move_btn, value == "move")
        self._update_mode_button_style(self._mode_rotate_btn, value == "rotate")
        self._apply_viewport_interaction_settings()

    def _set_viewport_axis(self, axis: str) -> None:
        value = str(axis or "x").strip().lower()
        if value not in {"x", "y", "z"}:
            value = "x"
        self._viewport_axis = value
        self._axis_x_btn.setChecked(value == "x")
        self._axis_y_btn.setChecked(value == "y")
        self._axis_z_btn.setChecked(value == "z")
        self._update_axis_button_styles()
        self._apply_viewport_interaction_settings()

    def _apply_viewport_interaction_settings(self) -> None:
        mode_label = {
            "navigate": "Navigate: left drag orbits, middle drag pans, wheel zooms.",
            "move": f"Move mode ({self._viewport_axis.upper()}): drag in the 3D view to move the selected child part.",
            "rotate": f"Rotate mode ({self._viewport_axis.upper()}): drag in the 3D view to rotate the selected child part.",
        }.get(self._viewport_mode, "")
        if self._transform_state is None:
            self._transform_status.setText(mode_label)
        gizmo = getattr(self, "_gizmo_overlay", None)
        if gizmo is not None:
            gizmo.set_state(self._viewport_mode, self._viewport_axis)
        if self._build_view_3d is None:
            return
        if hasattr(self._build_view_3d, "set_interaction_mode"):
            self._build_view_3d.set_interaction_mode(self._viewport_mode)
        if hasattr(self._build_view_3d, "set_transform_axis"):
            self._build_view_3d.set_transform_axis(self._viewport_axis)

    def _schedule_part_list_rebuild(self) -> None:
        self._part_filter_timer.start()

    def _apply_pending_part_filter(self) -> None:
        if self._part_filter_timer.isActive():
            self._part_filter_timer.stop()
        self._rebuild_part_list(select_first=False)

    def _rebuild_part_list(self, *, select_first: bool = False) -> None:
        filter_text = self._search_edit.text().strip().lower()
        selected_entry = self._current_part_entry
        target_row = -1
        self._part_list.blockSignals(True)
        self._part_list.clear()
        visible_entries: list[ModelViewerEntry] = []
        for entry in self._all_part_entries:
            if filter_text and filter_text not in entry.search_blob:
                continue
            visible_entries.append(entry)
            label = entry.display_name or entry.nickname
            item = QListWidgetItem(f"{label} [{entry.archetype}]", self._part_list)
            item.setData(Qt.UserRole, entry)
            if selected_entry is entry:
                target_row = self._part_list.count() - 1
        self._summary_label.setText(f"{len(visible_entries)} parts")
        if target_row >= 0:
            self._part_list.setCurrentRow(target_row)
        elif select_first and self._part_list.count() > 0:
            self._part_list.setCurrentRow(0)
        else:
            self._part_list.setCurrentRow(-1)
        self._part_list.blockSignals(False)

        current = self._part_list.currentItem()
        entry = current.data(Qt.UserRole) if current is not None else None
        if not isinstance(entry, ModelViewerEntry):
            entry = None
        self._set_preview_entry(entry)

    def _on_part_selection_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        entry = current.data(Qt.UserRole) if current is not None else None
        if not isinstance(entry, ModelViewerEntry):
            entry = None
        self._set_preview_entry(entry)

    def _set_preview_entry(self, entry: ModelViewerEntry | None) -> None:
        if entry is self._current_part_entry:
            if entry is None:
                if self._preview_widget is None and self._preview_placeholder.isVisible():
                    return
            elif self._preview_widget is not None:
                return
        self._current_part_entry = entry
        if self._preview_widget is not None:
            self._preview_widget.setParent(None)
            self._preview_widget.deleteLater()
            self._preview_widget = None
        if entry is None:
            self._preview_placeholder.setText("Select a part to load the preview.")
            self._preview_placeholder.setVisible(True)
            return
        self._preview_placeholder.setVisible(False)
        widget = self._embedded_preview_factory(entry, self._preview_host, minimal=True)
        if widget is None:
            self._preview_placeholder.setText("No preview available for the selected part.")
            self._preview_placeholder.setVisible(True)
            return
        self._preview_widget = widget
        self._preview_host_layout.addWidget(widget)
        self._schedule_preview_fit(widget)

    def _schedule_preview_fit(self, widget: QWidget) -> None:
        def _fit() -> None:
            if self._preview_widget is not widget:
                return
            if hasattr(widget, "fit_preview_to_view"):
                try:
                    widget.fit_preview_to_view()
                    return
                except Exception:
                    pass
            if hasattr(widget, "_reset_preview_camera"):
                try:
                    widget._reset_preview_camera()
                except Exception:
                    pass

        QTimer.singleShot(0, _fit)
        QTimer.singleShot(40, _fit)
        QTimer.singleShot(150, _fit)

    def _add_selected_part(self) -> None:
        if self._current_part_entry is None:
            return
        try:
            self._add_part_callback(self._current_part_entry)
        except Exception:
            _log = logging.getLogger(__name__)
            _log.error(
                "Base builder: crash in _add_part_callback for entry=%r:\n%s",
                getattr(self._current_part_entry, "archetype", "<unknown>"),
                traceback.format_exc(),
            )
            QMessageBox.critical(
                self,
                "Base Builder Error",
                f"Failed to add part. Check the log for details.\n\n"
                f"{traceback.format_exc(limit=3)}",
            )

    def _has_unsaved_changes(self) -> bool:
        return bool(callable(self._is_dirty_callback) and self._is_dirty_callback())

    def set_dirty_state(self, dirty: bool) -> None:
        self.setWindowTitle(f"{self._window_title_base}{' *' if dirty else ''}")

    def refresh_history(self) -> None:
        rows = self._history_provider() if callable(self._history_provider) else []
        current_row = -1
        can_undo = False
        self._history_list.blockSignals(True)
        self._history_list.clear()
        for index, row in enumerate(rows or []):
            if not isinstance(row, dict):
                continue
            label = str(row.get("label", "Base Builder") or "Base Builder").strip()
            timestamp = str(row.get("timestamp", "") or "").strip()
            suffix_parts: list[str] = []
            if row.get("is_current"):
                suffix_parts.append("current")
                current_row = self._history_list.count()
                can_undo = index > 0
            if row.get("is_saved"):
                suffix_parts.append("saved")
            suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
            prefix = f"[{timestamp}] " if timestamp else ""
            self._history_list.addItem(f"{prefix}{label}{suffix}")
        self._history_summary_label.setText(f"{max(0, self._history_list.count() - 1)} changes")
        if current_row >= 0:
            self._history_list.setCurrentRow(current_row)
        self._undo_btn.setEnabled(can_undo)
        self._history_list.blockSignals(False)

    def _undo_last_change(self) -> None:
        if not callable(self._undo_callback):
            return
        if self._undo_callback():
            self.refresh_history()
            self.set_dirty_state(self._has_unsaved_changes())

    def _on_existing_part_selection_changed(self, _index: int) -> None:
        if self._syncing_existing_part_list:
            return
        nickname = str(self._existing_part_combo.currentData(Qt.UserRole) or "").strip()
        if nickname:
            self._select_existing_part_callback(nickname)

    def set_selected_scene_object(self, *, scene_object=None, label: str, can_transform: bool, can_delete: bool) -> None:
        self._selected_scene_object = scene_object
        self._selection_label.setText(f"Selection: {label}")
        self._delete_btn.setEnabled(bool(can_delete))
        for btn in self._transform_buttons:
            btn.setEnabled(bool(can_transform))
        self._update_rotation_display()
        if self._build_view_3d is not None:
            self._build_view_3d.set_selected(scene_object)
            if hasattr(self._build_view_3d, "set_selected_native_scene_data"):
                scene_data = self._selected_scene_data_provider(scene_object)
                self._build_view_3d.set_selected_native_scene_data(scene_object, scene_data)
        self._sync_existing_part_selection()
        if not can_transform and self._transform_state is not None:
            self._finish_transform(cancelled=True)

    def _sync_existing_part_selection(self) -> None:
        selected_nick = str(getattr(self._selected_scene_object, "nickname", "") or "").strip().lower()
        self._syncing_existing_part_list = True
        try:
            target_row = -1
            for row in range(self._existing_part_combo.count()):
                item_nick = str(self._existing_part_combo.itemData(row, Qt.UserRole) or "").strip().lower()
                if item_nick == selected_nick:
                    target_row = row
                    break
            self._existing_part_combo.setCurrentIndex(target_row)
        finally:
            self._syncing_existing_part_list = False

    def center_on_object(self, obj) -> None:
        if obj is None:
            return
        if self._build_view_3d is not None and self._scene_initialized and obj is self._last_centered_object:
            return
        if self._build_view_3d is not None:
            try:
                self._build_view_3d.center_on_item(obj)
                self._last_centered_object = obj
                self._tighten_3d_camera()
                if hasattr(self._build_view_3d, "refresh_native_scene_previews"):
                    self._build_view_3d.refresh_native_scene_previews()
                return
            except Exception:
                try:
                    self._build_view_3d.center_on_item(obj)
                    self._last_centered_object = obj
                    self._tighten_3d_camera()
                    if hasattr(self._build_view_3d, "refresh_native_scene_previews"):
                        self._build_view_3d.refresh_native_scene_previews()
                    return
                except Exception:
                    pass
        if self._build_view_2d is not None:
            try:
                self._build_view_2d.centerOn(obj)
                self._last_centered_object = obj
            except Exception:
                pass

    def update_scene_object_position(self, obj, scale: float) -> None:
        if self._build_view_3d is None:
            return
        try:
            self._build_view_3d.update_object_position(obj, scale)
        except Exception:
            self.refresh_existing_parts()

    def update_scene_object_rotation(self, obj) -> None:
        if self._build_view_3d is None:
            return
        try:
            self._build_view_3d.update_object_rotation(obj)
        except Exception:
            self.refresh_existing_parts()

    def _start_transform(self, mode: str, axis: str, button: QPushButton | None) -> bool:
        if self._transform_state is not None:
            self._finish_transform(cancelled=False)
        if not self._begin_transform_callback(str(mode), str(axis)):
            return False
        self._transform_state = {
            "mode": str(mode),
            "axis": str(axis),
            "button": button,
            "origin_global": QCursor.pos() if button is not None else None,
            "accumulated_delta": 0.0,
            "source": "button" if button is not None else "viewport",
        }
        if isinstance(button, QPushButton):
            button.setDown(True)
            try:
                button.grabMouse()
            except Exception:
                pass
        self._transform_status.setText(
            f"{str(mode).title()} {str(axis).upper()}: drag in the 3D view or keep using the axis buttons for precise adjustments."
        )
        if button is not None:
            app = QApplication.instance()
            if app is not None:
                app.installEventFilter(self)
        return True

    def _apply_precision_step(self, direction: int) -> None:
        """Apply a step in current mode and axis using the step size from the spin box."""
        if self._selected_scene_object is None:
            return
        mode = self._viewport_mode
        if mode not in {"move", "rotate"}:
            return
        axis = self._viewport_axis
        if not self._begin_transform_callback(mode, axis):
            return
        step_value = self._step_spin.value()
        if mode == "move":
            axis_sensitivity = {"x": 6.0, "y": 4.0, "z": 6.0}.get(axis, 5.0)
            delta = float(direction) * float(step_value) / axis_sensitivity
        else:
            # rotate: step_value is degrees, sensitivity 0.2 → delta for N degrees = N / 0.2
            delta = float(direction) * float(step_value) / 0.2
        self._update_transform_callback(delta)
        self._finish_transform_callback(True)
        self._update_rotation_display()

    def _begin_viewport_transform(self, mode: str, axis: str) -> bool:
        if self._selected_scene_object is None:
            return False
        return self._start_transform(mode, axis, None)

    def _update_viewport_transform(self, delta: float) -> None:
        if self._transform_state is None:
            return
        self._transform_state["accumulated_delta"] = float(delta)
        self._update_transform_callback(float(delta))

    def _finish_viewport_transform(self, commit: bool) -> None:
        if self._transform_state is None:
            return
        self._finish_transform(cancelled=not bool(commit))

    def _finish_transform(self, cancelled: bool = False) -> None:
        state = self._transform_state
        if state is None:
            return
        self._transform_state = None
        button = state.get("button")
        if isinstance(button, QPushButton):
            button.setDown(False)
            try:
                button.releaseMouse()
            except Exception:
                pass
        if state.get("source") == "button":
            app = QApplication.instance()
            if app is not None:
                try:
                    app.removeEventFilter(self)
                except Exception:
                    pass
        self._finish_transform_callback(not cancelled)
        self._apply_viewport_interaction_settings()
        self._update_rotation_display()

    def _update_rotation_display(self) -> None:
        obj = self._selected_scene_object
        if obj is None:
            self._rot_x_label.setText("X: —")
            self._rot_y_label.setText("Y: —")
            self._rot_z_label.setText("Z: —")
            return
        raw = getattr(obj, "data", {}).get("rotate", "0,0,0")
        rx, ry, rz = parse_rotate(raw)
        self._rot_x_label.setText(f"X: {rx:.1f}°")
        self._rot_y_label.setText(f"Y: {ry:.1f}°")
        self._rot_z_label.setText(f"Z: {rz:.1f}°")

    def eventFilter(self, watched, event) -> bool:
        state = self._transform_state
        if state is None:
            return super().eventFilter(watched, event)
        if event.type() == QEvent.MouseMove:
            global_pos = getattr(event, "globalPosition", None)
            if callable(global_pos):
                point = global_pos().toPoint()
            else:
                point = QCursor.pos()
            origin_point = state.get("origin_global")
            if origin_point is None:
                origin_point = point
            dx = float(point.x() - origin_point.x())
            dy = float(point.y() - origin_point.y())
            step_delta = dx if abs(dx) >= abs(dy) else -dy
            if abs(step_delta) < 0.01:
                return False
            accumulated_delta = float(state.get("accumulated_delta", 0.0)) + float(step_delta)
            state["accumulated_delta"] = accumulated_delta
            self._update_transform_callback(accumulated_delta)
            try:
                QCursor.setPos(origin_point)
            except Exception:
                pass
            return True
        if event.type() == QEvent.MouseButtonRelease:
            self._finish_transform(cancelled=False)
            return False
        if event.type() == QEvent.KeyPress and getattr(event, "key", lambda: None)() == Qt.Key_Escape:
            self._finish_transform(cancelled=True)
            return True
        if event.type() == QEvent.WindowDeactivate:
            self._finish_transform(cancelled=False)
            return False
        return super().eventFilter(watched, event)

    def refresh_existing_parts(self) -> None:
        existing_parts = list(self._existing_parts_provider() or [])
        self._syncing_existing_part_list = True
        try:
            self._existing_part_combo.clear()
            for row in existing_parts:
                nickname = str(row.get("nickname", "") or "").strip()
                label = str(row.get("label", nickname) or nickname).strip()
                archetype = str(row.get("archetype", "") or "").strip()
                self._existing_part_combo.addItem(f"{label} [{archetype}]", nickname)
            self._existing_summary_label.setText(f"{len(existing_parts)} placed parts")
        finally:
            self._syncing_existing_part_list = False
        self._sync_existing_part_selection()
        if self._build_view_3d is None:
            return None
        camera_state = None
        if self._scene_initialized and hasattr(self._build_view_3d, "get_camera_state"):
            try:
                camera_state = self._build_view_3d.get_camera_state()
            except Exception:
                camera_state = None
        objects, zones, scale = self._scene_payload_provider()
        self._build_view_3d.set_data(objects, zones, scale)
        self._build_view_3d.set_selected(self._selected_scene_object)
        if hasattr(self._build_view_3d, "set_selected_native_scene_data"):
            scene_data = self._selected_scene_data_provider(self._selected_scene_object)
            self._build_view_3d.set_selected_native_scene_data(self._selected_scene_object, scene_data)
        if hasattr(self._build_view_3d, "refresh_native_scene_previews"):
            self._build_view_3d.refresh_native_scene_previews()
        if camera_state is not None and hasattr(self._build_view_3d, "set_camera_state"):
            try:
                self._build_view_3d.set_camera_state(camera_state)
                self._scene_initialized = True
                return None
            except Exception:
                pass
        self._scene_initialized = True
        if self._selected_scene_object is not None:
            self.center_on_object(self._selected_scene_object)
        return None

    def _apply_preview_zoom(self, slider_value: int) -> None:
        zoom_factor = max(0.2, float(slider_value) / 100.0)
        self._zoom_value_label.setText(f"{zoom_factor:.2f}x")
        if self._build_view_3d is None or not hasattr(self._build_view_3d, "set_preview_zoom_factor"):
            return
        try:
            self._build_view_3d.set_preview_zoom_factor(zoom_factor)
        except Exception:
            pass

    def _tighten_3d_camera(self) -> None:
        if self._build_view_3d is None or not hasattr(self._build_view_3d, "get_camera_state"):
            return
        try:
            state = self._build_view_3d.get_camera_state()
        except Exception:
            return
        if not isinstance(state, dict):
            return
        current_distance = float(state.get("distance", 0.0) or 0.0)
        if current_distance <= 0.0:
            return
        next_distance = max(90.0, min(current_distance * 0.35, 1400.0))
        state["distance"] = next_distance
        try:
            self._build_view_3d.set_camera_state(state)
        except Exception:
            pass

    def _reset_camera(self) -> None:
        focus_obj = self._selected_scene_object
        if focus_obj is None:
            objects, _zones, _scale = self._scene_payload_provider()
            focus_obj = objects[0] if objects else None
        if focus_obj is None:
            return
        self._last_centered_object = None
        self.center_on_object(focus_obj)

    def closeEvent(self, event) -> None:
        self._finish_transform(cancelled=False)
        if self._has_unsaved_changes():
            answer = QMessageBox.question(
                self,
                "Unsaved Base Builder Changes",
                "The Base Builder draft has unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.StandardButton.Save:
                self._save_callback()
                if self._has_unsaved_changes():
                    event.ignore()
                    return
        if self._build_view_3d is not None and hasattr(self._build_view_3d, "clear_scene"):
            try:
                self._build_view_3d.clear_scene()
            except Exception:
                pass
        if callable(self._closed_callback):
            try:
                self._closed_callback()
            except Exception:
                pass
        super().closeEvent(event)
