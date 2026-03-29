from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
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
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .model_viewer_dialog import ModelViewerEntry
from .base_assembly_preview import BaseAssemblyPreviewView
from .view_2d import SystemView
from .view_3d import QT3D_AVAILABLE


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
        self.setWindowTitle(f"Base Builder - {base_nickname}")

        self._all_part_entries = list(part_entries)
        self._scene_payload_provider = scene_payload_provider
        self._existing_parts_provider = existing_parts_provider
        self._selected_scene_data_provider = selected_scene_data_provider
        self._configure_3d_view_callback = configure_3d_view_callback
        self._embedded_preview_factory = embedded_preview_factory
        self._add_part_callback = add_part_callback
        self._delete_selected_callback = delete_selected_callback
        self._save_callback = save_callback
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

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        header = QLabel(
            f"Base: {str(base_nickname).strip()}\n"
            "Build the station directly in the 3D view on the left. Select a placed child part, choose Navigate/Move/Rotate, then drag directly in the viewport. The axis buttons remain available for precise fallback adjustments.",
            self,
        )
        header.setWordWrap(True)
        root.addWidget(header)

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
        toolbar_row.addStretch(1)
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

        utility_row = QHBoxLayout()
        utility_row.setSpacing(6)
        self._reset_camera_btn = QPushButton("Reset Camera", transform_box)
        self._reset_camera_btn.setMinimumHeight(30)
        self._reset_camera_btn.setMinimumWidth(110)
        self._reset_camera_btn.clicked.connect(self._reset_camera)
        utility_row.addWidget(self._reset_camera_btn)
        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(6)
        zoom_row.addWidget(QLabel("Zoom", transform_box))
        self._zoom_slider = QSlider(Qt.Horizontal, transform_box)
        self._zoom_slider.setRange(20, 300)
        self._zoom_slider.setSingleStep(5)
        self._zoom_slider.setPageStep(20)
        self._zoom_slider.setValue(100)
        self._zoom_slider.valueChanged.connect(self._apply_preview_zoom)
        zoom_row.addWidget(self._zoom_slider, 1)
        self._zoom_value_label = QLabel("1.00x", transform_box)
        zoom_row.addWidget(self._zoom_value_label)
        utility_row.addLayout(zoom_row, 1)
        transform_layout.addLayout(utility_row)
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
        self._search_edit.textChanged.connect(self._rebuild_part_list)
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
        self._delete_btn = QPushButton("Delete Selected Part", action_box)
        self._delete_btn.clicked.connect(self._delete_selected_callback)
        self._delete_btn.setEnabled(False)
        self._delete_btn.setMinimumHeight(42)
        action_layout.addWidget(self._delete_btn)
        right_col.addWidget(action_box)

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
        right_col.addWidget(preview_box, 1)

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
        self._axis_x_btn.setChecked(True)
        QShortcut(QKeySequence("Q"), self).activated.connect(lambda: self._set_viewport_mode("navigate"))
        QShortcut(QKeySequence("W"), self).activated.connect(lambda: self._set_viewport_mode("move"))
        QShortcut(QKeySequence("E"), self).activated.connect(lambda: self._set_viewport_mode("rotate"))
        QShortcut(QKeySequence("X"), self).activated.connect(lambda: self._set_viewport_axis("x"))
        QShortcut(QKeySequence("Y"), self).activated.connect(lambda: self._set_viewport_axis("y"))
        QShortcut(QKeySequence("Z"), self).activated.connect(lambda: self._set_viewport_axis("z"))
        QShortcut(QKeySequence("F"), self).activated.connect(self._reset_camera)
        self._rebuild_part_list()
        self.refresh_existing_parts()

    def _build_mode_button(self, label: str, mode: str) -> QPushButton:
        btn = QPushButton(label, self)
        btn.setCheckable(True)
        btn.setMinimumSize(52, 28)
        btn.clicked.connect(lambda _checked=False, value=mode: self._set_viewport_mode(value))
        self._mode_group.addButton(btn)
        return btn

    def _build_axis_button(self, label: str, axis: str) -> QPushButton:
        btn = QPushButton(label, self)
        btn.setCheckable(True)
        btn.setMinimumSize(34, 28)
        btn.clicked.connect(lambda _checked=False, value=axis: self._set_viewport_axis(value))
        self._axis_group.addButton(btn)
        return btn

    def _build_transform_button(self, label: str, mode: str, axis: str) -> QPushButton:
        btn = QPushButton(label, self)
        btn.setMinimumSize(34, 28)
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
        self._apply_viewport_interaction_settings()

    def _set_viewport_axis(self, axis: str) -> None:
        value = str(axis or "x").strip().lower()
        if value not in {"x", "y", "z"}:
            value = "x"
        self._viewport_axis = value
        self._axis_x_btn.setChecked(value == "x")
        self._axis_y_btn.setChecked(value == "y")
        self._axis_z_btn.setChecked(value == "z")
        self._apply_viewport_interaction_settings()

    def _apply_viewport_interaction_settings(self) -> None:
        mode_label = {
            "navigate": "Navigate: left drag orbits, middle drag pans, wheel zooms.",
            "move": f"Move mode ({self._viewport_axis.upper()}): drag in the 3D view to move the selected child part.",
            "rotate": f"Rotate mode ({self._viewport_axis.upper()}): drag in the 3D view to rotate the selected child part.",
        }.get(self._viewport_mode, "")
        if self._transform_state is None:
            self._transform_status.setText(mode_label)
        if self._build_view_3d is None:
            return
        if hasattr(self._build_view_3d, "set_interaction_mode"):
            self._build_view_3d.set_interaction_mode(self._viewport_mode)
        if hasattr(self._build_view_3d, "set_transform_axis"):
            self._build_view_3d.set_transform_axis(self._viewport_axis)

    def _rebuild_part_list(self) -> None:
        filter_text = self._search_edit.text().strip().lower()
        self._part_list.clear()
        visible_entries: list[ModelViewerEntry] = []
        for entry in self._all_part_entries:
            if filter_text and filter_text not in entry.search_blob:
                continue
            visible_entries.append(entry)
            label = entry.display_name or entry.nickname
            item = QListWidgetItem(f"{label} [{entry.archetype}]", self._part_list)
            item.setData(Qt.UserRole, entry)
        self._summary_label.setText(f"{len(visible_entries)} parts")
        if self._part_list.count() > 0:
            self._part_list.setCurrentRow(0)
        else:
            self._set_preview_entry(None)

    def _on_part_selection_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        entry = current.data(Qt.UserRole) if current is not None else None
        if not isinstance(entry, ModelViewerEntry):
            entry = None
        self._set_preview_entry(entry)

    def _set_preview_entry(self, entry: ModelViewerEntry | None) -> None:
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
        widget = self._embedded_preview_factory(entry, self._preview_host)
        if widget is None:
            self._preview_placeholder.setText("No preview available for the selected part.")
            self._preview_placeholder.setVisible(True)
            return
        self._preview_widget = widget
        self._preview_host_layout.addWidget(widget)

    def _add_selected_part(self) -> None:
        if self._current_part_entry is None:
            return
        self._add_part_callback(self._current_part_entry)

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
