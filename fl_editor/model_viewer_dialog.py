from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .ui_helpers import connect_debounced_line_edit


@dataclass(frozen=True)
class ModelViewerEntry:
    category_key: str
    category_label: str
    nickname: str
    display_name: str
    archetype: str
    da_archetype: str
    model_path: Path
    source_ini_path: Path
    source_section: str
    ids_name: str = ""
    type_value: str = ""
    render_kind: str = ""
    preview_path: Path | None = None
    material_library_paths: tuple[Path, ...] = ()
    ring: str = ""
    atmosphere_range: str = ""
    burn_color: str = ""

    @property
    def title_text(self) -> str:
        return self.display_name or self.nickname

    @property
    def search_blob(self) -> str:
        parts = (
            self.category_label,
            self.nickname,
            self.display_name,
            self.archetype,
            self.da_archetype,
            self.source_section,
            str(self.source_ini_path),
            str(self.model_path),
            self.type_value,
            self.render_kind,
        )
        return " ".join(part for part in parts if part).lower()


class ModelViewerWidget(QWidget):
    def __init__(
        self,
        parent,
        *,
        entries: list[ModelViewerEntry],
        preview_callback: Callable[[ModelViewerEntry], None],
        embedded_preview_factory: Callable[[ModelViewerEntry, QWidget], QWidget | None],
        open_ini_callback: Callable[[ModelViewerEntry], None],
        refresh_callback: Callable[[], list[ModelViewerEntry]],
    ):
        super().__init__(parent)
        self._entries = list(entries)
        self._preview_callback = preview_callback
        self._embedded_preview_factory = embedded_preview_factory
        self._open_ini_callback = open_ini_callback
        self._refresh_callback = refresh_callback
        self._current_entry: ModelViewerEntry | None = None
        self._embedded_preview_widget: QWidget | None = None
        self._preview_zoom_busy = False
        self._pending_preview_entry: ModelViewerEntry | None = None
        self._preview_load_timer = QTimer(self)
        self._preview_load_timer.setSingleShot(True)
        self._preview_load_timer.setInterval(120)
        self._preview_load_timer.timeout.connect(self._load_pending_embedded_preview)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        layout.addLayout(top_row)

        self._search_edit = QLineEdit(self)
        self._search_edit.setPlaceholderText("Search model, archetype, category or path")
        self._search_timer = connect_debounced_line_edit(self._search_edit, self._rebuild_tree)
        top_row.addWidget(self._search_edit, 1)

        self._summary_label = QLabel(self)
        top_row.addWidget(self._summary_label)

        self._refresh_btn = QPushButton("Refresh", self)
        self._refresh_btn.clicked.connect(self._refresh_entries)
        top_row.addWidget(self._refresh_btn)

        splitter = QSplitter(Qt.Horizontal, self)
        layout.addWidget(splitter, 1)

        left = QWidget(splitter)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        self._tree = QTreeWidget(left)
        self._tree.setHeaderLabels(("Model", "Archetype", "Render"))
        self._tree.setRootIsDecorated(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        self._tree.itemDoubleClicked.connect(self._on_item_activated)
        left_layout.addWidget(self._tree, 1)
        splitter.addWidget(left)

        right = QWidget(splitter)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self._right_tabs = QTabWidget(right)
        right_layout.addWidget(self._right_tabs, 1)

        preview_tab = QWidget(self._right_tabs)
        preview_tab_layout = QVBoxLayout(preview_tab)
        preview_tab_layout.setContentsMargins(0, 0, 0, 0)
        preview_tab_layout.setSpacing(8)

        preview_box = QGroupBox("3D Preview", preview_tab)
        preview_box_layout = QVBoxLayout(preview_box)
        preview_box_layout.setContentsMargins(6, 6, 6, 6)
        preview_box_layout.setSpacing(6)
        preview_zoom_row = QHBoxLayout()
        self._preview_zoom_label = QLabel("Zoom", preview_box)
        preview_zoom_row.addWidget(self._preview_zoom_label)
        self._preview_zoom_slider = QSlider(Qt.Horizontal, preview_box)
        self._preview_zoom_slider.setRange(10, 300)
        self._preview_zoom_slider.setValue(100)
        self._preview_zoom_slider.setEnabled(False)
        self._preview_zoom_slider.valueChanged.connect(self._on_preview_zoom_changed)
        preview_zoom_row.addWidget(self._preview_zoom_slider, 1)
        self._preview_zoom_value = QLabel("100%", preview_box)
        preview_zoom_row.addWidget(self._preview_zoom_value)
        preview_box_layout.addLayout(preview_zoom_row)
        self._preview_placeholder = QLabel("Select a model to load the live 3D preview.", preview_box)
        self._preview_placeholder.setAlignment(Qt.AlignCenter)
        self._preview_placeholder.setMinimumHeight(300)
        preview_box_layout.addWidget(self._preview_placeholder)
        self._preview_host = QWidget(preview_box)
        self._preview_host_layout = QVBoxLayout(self._preview_host)
        self._preview_host_layout.setContentsMargins(0, 0, 0, 0)
        self._preview_host_layout.setSpacing(0)
        preview_box_layout.addWidget(self._preview_host, 1)
        preview_tab_layout.addWidget(preview_box, 1)

        actions_row = QHBoxLayout()
        self._preview_btn = QPushButton("Open Separate Preview", preview_tab)
        self._preview_btn.clicked.connect(self._preview_selected)
        actions_row.addWidget(self._preview_btn)
        self._open_ini_btn = QPushButton("Open Source INI", preview_tab)
        self._open_ini_btn.clicked.connect(self._open_source_ini)
        actions_row.addWidget(self._open_ini_btn)
        self._reveal_model_btn = QPushButton("Open Model File", preview_tab)
        self._reveal_model_btn.clicked.connect(self._open_model_file)
        actions_row.addWidget(self._reveal_model_btn)
        actions_row.addStretch(1)
        preview_tab_layout.addLayout(actions_row)
        self._right_tabs.addTab(preview_tab, "Preview")

        details_tab = QWidget(self._right_tabs)
        details_tab_layout = QVBoxLayout(details_tab)
        details_tab_layout.setContentsMargins(0, 0, 0, 0)
        details_tab_layout.setSpacing(8)

        details_box = QGroupBox("Details", details_tab)
        details_form = QFormLayout(details_box)
        self._name_value = QLabel("-")
        self._name_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_form.addRow("Name", self._name_value)
        self._nickname_value = QLabel("-")
        self._nickname_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_form.addRow("Nickname", self._nickname_value)
        self._category_value = QLabel("-")
        self._category_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_form.addRow("Category", self._category_value)
        self._archetype_value = QLabel("-")
        self._archetype_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_form.addRow("Archetype", self._archetype_value)
        self._type_value = QLabel("-")
        self._type_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_form.addRow("Type", self._type_value)
        self._render_value = QLabel("-")
        self._render_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_form.addRow("Render", self._render_value)
        self._ids_value = QLabel("-")
        self._ids_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_form.addRow("ids_name", self._ids_value)
        self._source_value = QLabel("-")
        self._source_value.setWordWrap(True)
        self._source_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_form.addRow("Source INI", self._source_value)
        self._model_value = QLabel("-")
        self._model_value.setWordWrap(True)
        self._model_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_form.addRow("Model", self._model_value)
        self._da_value = QLabel("-")
        self._da_value.setWordWrap(True)
        self._da_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_form.addRow("DA Archetype", self._da_value)
        details_tab_layout.addWidget(details_box)

        extra_box = QGroupBox("Preview Hints", details_tab)
        extra_form = QFormLayout(extra_box)
        self._materials_value = QLabel("-")
        self._materials_value.setWordWrap(True)
        self._materials_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        extra_form.addRow("Materials", self._materials_value)
        self._ring_value = QLabel("-")
        self._ring_value.setWordWrap(True)
        self._ring_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        extra_form.addRow("Ring", self._ring_value)
        self._atmo_value = QLabel("-")
        self._atmo_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        extra_form.addRow("Atmosphere", self._atmo_value)
        self._burn_value = QLabel("-")
        self._burn_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        extra_form.addRow("Burn Color", self._burn_value)
        details_tab_layout.addWidget(extra_box)
        details_tab_layout.addStretch(1)
        self._right_tabs.addTab(details_tab, "Details")

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)

        self._rebuild_tree()
        self._sync_buttons()

    def set_entries(self, entries: list[ModelViewerEntry]) -> None:
        self._entries = list(entries)
        self._rebuild_tree()

    def _refresh_entries(self) -> None:
        self.set_entries(self._refresh_callback())

    def _matching_entries(self) -> list[ModelViewerEntry]:
        query = self._search_edit.text().strip().lower()
        if not query:
            return list(self._entries)
        return [entry for entry in self._entries if query in entry.search_blob]

    def _rebuild_tree(self) -> None:
        previous_key = None
        if self._current_entry is not None:
            previous_key = (self._current_entry.category_key, self._current_entry.nickname.lower(), str(self._current_entry.model_path).lower())
        self._tree.clear()
        matches = self._matching_entries()
        grouped: dict[str, list[ModelViewerEntry]] = {}
        labels: dict[str, str] = {}
        for entry in matches:
            grouped.setdefault(entry.category_key, []).append(entry)
            labels.setdefault(entry.category_key, entry.category_label)
        selected_item: QTreeWidgetItem | None = None
        for category_key, entries in grouped.items():
            label = labels.get(category_key, category_key)
            top_item = QTreeWidgetItem((f"{label} ({len(entries)})", "", ""))
            top_item.setFlags(top_item.flags() & ~Qt.ItemIsSelectable)
            self._tree.addTopLevelItem(top_item)
            for entry in entries:
                item = QTreeWidgetItem((entry.title_text, entry.archetype, entry.render_kind))
                item.setData(0, Qt.UserRole, entry)
                top_item.addChild(item)
                item_key = (entry.category_key, entry.nickname.lower(), str(entry.model_path).lower())
                if previous_key is not None and item_key == previous_key:
                    selected_item = item
            top_item.setExpanded(True)
        if selected_item is None and self._tree.topLevelItemCount() > 0:
            first_group = self._tree.topLevelItem(0)
            if first_group is not None and first_group.childCount() > 0:
                selected_item = first_group.child(0)
        if selected_item is not None:
            self._tree.setCurrentItem(selected_item)
        else:
            self._set_current_entry(None)
        self._summary_label.setText(f"{len(matches)} models")

    def _on_selection_changed(self) -> None:
        item = self._tree.currentItem()
        entry = item.data(0, Qt.UserRole) if item is not None else None
        self._set_current_entry(entry if isinstance(entry, ModelViewerEntry) else None)

    def _set_current_entry(self, entry: ModelViewerEntry | None) -> None:
        self._current_entry = entry
        if entry is None:
            for label in (
                self._name_value,
                self._nickname_value,
                self._category_value,
                self._archetype_value,
                self._type_value,
                self._render_value,
                self._ids_value,
                self._source_value,
                self._model_value,
                self._da_value,
                self._materials_value,
                self._ring_value,
                self._atmo_value,
                self._burn_value,
            ):
                label.setText("-")
            self._set_embedded_preview_entry(None)
            self._sync_buttons()
            return
        self._name_value.setText(entry.title_text)
        self._nickname_value.setText(entry.nickname or "-")
        self._category_value.setText(entry.category_label or "-")
        self._archetype_value.setText(entry.archetype or "-")
        self._type_value.setText(entry.type_value or "-")
        self._render_value.setText(entry.render_kind or "-")
        self._ids_value.setText(entry.ids_name or "-")
        self._source_value.setText(str(entry.source_ini_path))
        self._model_value.setText(str(entry.model_path))
        self._da_value.setText(entry.da_archetype or "-")
        if entry.material_library_paths:
            self._materials_value.setText("\n".join(str(path) for path in entry.material_library_paths))
        else:
            self._materials_value.setText("-")
        self._ring_value.setText(entry.ring or "-")
        self._atmo_value.setText(entry.atmosphere_range or "-")
        self._burn_value.setText(entry.burn_color or "-")
        self._set_embedded_preview_entry(entry)
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        has_entry = self._current_entry is not None
        self._preview_btn.setEnabled(has_entry)
        self._open_ini_btn.setEnabled(has_entry)
        self._reveal_model_btn.setEnabled(has_entry)

    def _clear_embedded_preview(self) -> None:
        self._preview_load_timer.stop()
        self._pending_preview_entry = None
        if self._embedded_preview_widget is not None:
            self._embedded_preview_widget.setParent(None)
            self._embedded_preview_widget.deleteLater()
            self._embedded_preview_widget = None
        self._set_preview_zoom_controls_enabled(False)
        self._sync_preview_zoom_slider(1.0)

    def _set_preview_zoom_controls_enabled(self, enabled: bool) -> None:
        self._preview_zoom_slider.setEnabled(bool(enabled))
        self._preview_zoom_label.setEnabled(bool(enabled))
        self._preview_zoom_value.setEnabled(bool(enabled))

    def _sync_preview_zoom_slider(self, zoom_factor: float) -> None:
        self._preview_zoom_busy = True
        try:
            slider_value = max(
                self._preview_zoom_slider.minimum(),
                min(self._preview_zoom_slider.maximum(), int(round(float(zoom_factor) * 100.0))),
            )
            self._preview_zoom_slider.setValue(slider_value)
            self._preview_zoom_value.setText(f"{slider_value}%")
        finally:
            self._preview_zoom_busy = False

    def _on_preview_zoom_changed(self, value: int) -> None:
        self._preview_zoom_value.setText(f"{int(value)}%")
        if self._preview_zoom_busy:
            return
        if self._embedded_preview_widget is None:
            return
        if hasattr(self._embedded_preview_widget, "set_preview_zoom_factor"):
            try:
                self._embedded_preview_widget.set_preview_zoom_factor(float(value) / 100.0)
            except Exception:
                pass

    def _set_embedded_preview_entry(self, entry: ModelViewerEntry | None) -> None:
        self._clear_embedded_preview()
        if entry is None:
            self._preview_placeholder.setVisible(True)
            self._preview_placeholder.setText("Select a model to load the live 3D preview.")
            return
        self._pending_preview_entry = entry
        self._preview_placeholder.setVisible(True)
        self._preview_placeholder.setText("Loading live 3D preview...")
        self._preview_load_timer.start()

    def _load_pending_embedded_preview(self) -> None:
        entry = self._pending_preview_entry
        if entry is None:
            return
        self._pending_preview_entry = None
        preview_widget = self._embedded_preview_factory(entry, self._preview_host)
        if preview_widget is None:
            self._preview_placeholder.setVisible(True)
            self._preview_placeholder.setText("This model could not be previewed inline.")
            return
        self._embedded_preview_widget = preview_widget
        self._preview_host_layout.addWidget(preview_widget)
        self._preview_placeholder.setVisible(False)
        self._set_preview_zoom_controls_enabled(hasattr(preview_widget, "set_preview_zoom_factor"))
        zoom_factor = 1.0
        if hasattr(preview_widget, "get_preview_zoom_factor"):
            try:
                zoom_factor = float(preview_widget.get_preview_zoom_factor())
            except Exception:
                zoom_factor = 1.0
        self._sync_preview_zoom_slider(zoom_factor)

    def _preview_selected(self) -> None:
        if self._current_entry is None:
            return
        self._preview_callback(self._current_entry)

    def _open_source_ini(self) -> None:
        if self._current_entry is None:
            return
        self._open_ini_callback(self._current_entry)

    def _open_model_file(self) -> None:
        if self._current_entry is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._current_entry.model_path)))

    def _on_item_activated(self, item: QTreeWidgetItem) -> None:
        entry = item.data(0, Qt.UserRole)
        if isinstance(entry, ModelViewerEntry):
            self._preview_callback(entry)


class ModelViewerDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        entries: list[ModelViewerEntry],
        preview_callback: Callable[[ModelViewerEntry], None],
        embedded_preview_factory: Callable[[ModelViewerEntry, QWidget], QWidget | None],
        open_ini_callback: Callable[[ModelViewerEntry], None],
        refresh_callback: Callable[[], list[ModelViewerEntry]],
    ):
        super().__init__(parent)
        self.setWindowTitle("3D Model Viewer")
        self.resize(1240, 760)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._viewer_widget = ModelViewerWidget(
            self,
            entries=entries,
            preview_callback=preview_callback,
            embedded_preview_factory=embedded_preview_factory,
            open_ini_callback=open_ini_callback,
            refresh_callback=refresh_callback,
        )
        layout.addWidget(self._viewer_widget)

    def set_entries(self, entries: list[ModelViewerEntry]) -> None:
        self._viewer_widget.set_entries(entries)
