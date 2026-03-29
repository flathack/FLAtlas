from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMessageBox, QWidget

from fl_editor import base_builder_dialog as base_builder_dialog_module
from fl_editor.base_builder_dialog import BaseBuilderDialog
from fl_editor.model_viewer_dialog import ModelViewerEntry


def test_base_builder_dialog_search_debounces_and_does_not_rebuild_preview_on_each_keypress(qtbot, monkeypatch):
    monkeypatch.setattr(base_builder_dialog_module, "QT3D_AVAILABLE", False)

    preview_calls: list[str] = []

    def _embedded_preview_factory(entry: ModelViewerEntry, parent: QWidget):
        preview_calls.append(entry.nickname)
        return QWidget(parent)

    entries = [
        ModelViewerEntry(
            category_key="stations",
            category_label="Stations",
            nickname="smallstation_core",
            display_name="Core",
            archetype="smallstation_core",
            da_archetype="solar\\core.cmp",
            model_path=None,
            source_ini_path=None,
            source_section="Solar",
        ),
        ModelViewerEntry(
            category_key="stations",
            category_label="Stations",
            nickname="smallstation_wing",
            display_name="Wing",
            archetype="smallstation_wing",
            da_archetype="solar\\wing.cmp",
            model_path=None,
            source_ini_path=None,
            source_section="Solar",
        ),
    ]

    dialog = BaseBuilderDialog(
        None,
        base_nickname="Li01_01_Base",
        scene=None,
        part_entries=entries,
        scene_payload_provider=lambda: ([], [], 1.0),
        existing_parts_provider=lambda: [],
        selected_scene_data_provider=lambda _obj: None,
        configure_3d_view_callback=None,
        embedded_preview_factory=_embedded_preview_factory,
        add_part_callback=lambda _entry: None,
        delete_selected_callback=lambda: None,
        save_callback=lambda: None,
        undo_callback=lambda: False,
        history_provider=lambda: [],
        is_dirty_callback=lambda: False,
        select_existing_part_callback=lambda _nickname: None,
        select_object_callback=lambda _obj: None,
        clear_selection_callback=lambda: None,
        begin_transform_callback=lambda _mode, _axis: False,
        update_transform_callback=lambda _delta: None,
        finish_transform_callback=lambda _commit: None,
    )
    qtbot.addWidget(dialog)

    assert dialog._part_list.count() == 2
    assert preview_calls == ["smallstation_core"]

    dialog._search_edit.setText("wing")

    assert dialog._part_list.count() == 2
    assert preview_calls == ["smallstation_core"]

    qtbot.wait(260)

    assert dialog._part_list.count() == 1
    assert dialog._part_list.currentItem() is None
    assert preview_calls == ["smallstation_core"]


def test_base_builder_dialog_close_event_can_save_dirty_draft(qtbot, monkeypatch):
    monkeypatch.setattr(base_builder_dialog_module, "QT3D_AVAILABLE", False)

    save_calls: list[str] = []
    dirty_state = {"value": True}

    dialog = BaseBuilderDialog(
        None,
        base_nickname="Li01_01_Base",
        scene=None,
        part_entries=[],
        scene_payload_provider=lambda: ([], [], 1.0),
        existing_parts_provider=lambda: [],
        selected_scene_data_provider=lambda _obj: None,
        configure_3d_view_callback=None,
        embedded_preview_factory=lambda _entry, parent: QWidget(parent),
        add_part_callback=lambda _entry: None,
        delete_selected_callback=lambda: None,
        save_callback=lambda: save_calls.append("save") or dirty_state.__setitem__("value", False),
        undo_callback=lambda: False,
        history_provider=lambda: [],
        is_dirty_callback=lambda: dirty_state["value"],
        select_existing_part_callback=lambda _nickname: None,
        select_object_callback=lambda _obj: None,
        clear_selection_callback=lambda: None,
        begin_transform_callback=lambda _mode, _axis: False,
        update_transform_callback=lambda _delta: None,
        finish_transform_callback=lambda _commit: None,
    )
    qtbot.addWidget(dialog)

    monkeypatch.setattr(
        base_builder_dialog_module.QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Save,
    )

    event = QCloseEvent()
    dialog.closeEvent(event)

    assert save_calls == ["save"]
    assert event.isAccepted() is True


def test_base_builder_dialog_close_event_can_cancel_dirty_draft(qtbot, monkeypatch):
    monkeypatch.setattr(base_builder_dialog_module, "QT3D_AVAILABLE", False)

    dialog = BaseBuilderDialog(
        None,
        base_nickname="Li01_01_Base",
        scene=None,
        part_entries=[],
        scene_payload_provider=lambda: ([], [], 1.0),
        existing_parts_provider=lambda: [],
        selected_scene_data_provider=lambda _obj: None,
        configure_3d_view_callback=None,
        embedded_preview_factory=lambda _entry, parent: QWidget(parent),
        add_part_callback=lambda _entry: None,
        delete_selected_callback=lambda: None,
        save_callback=lambda: None,
        undo_callback=lambda: False,
        history_provider=lambda: [],
        is_dirty_callback=lambda: True,
        select_existing_part_callback=lambda _nickname: None,
        select_object_callback=lambda _obj: None,
        clear_selection_callback=lambda: None,
        begin_transform_callback=lambda _mode, _axis: False,
        update_transform_callback=lambda _delta: None,
        finish_transform_callback=lambda _commit: None,
    )
    qtbot.addWidget(dialog)

    monkeypatch.setattr(
        base_builder_dialog_module.QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Cancel,
    )

    event = QCloseEvent()
    dialog.closeEvent(event)

    assert event.isAccepted() is False
