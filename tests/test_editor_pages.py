from __future__ import annotations

from PySide6.QtWidgets import QStackedWidget, QWidget

from fl_editor.editor_pages import prepare_editor_page


def test_prepare_editor_page_replaces_old_widget_and_adds_title(qapp):
    stack = QStackedWidget()
    old_page = QWidget()
    stack.addWidget(old_page)
    sync_calls: list[str] = []
    tab_specs = [("old", old_page)]

    page, root = prepare_editor_page(
        center_stack=stack,
        center_tab_specs=tab_specs,
        center_tab_index_for_widget=lambda widget: 0 if widget is old_page else -1,
        center_sync_tab_bar=lambda: sync_calls.append("synced"),
        old_page=old_page,
        title="Test Page",
    )

    assert stack.count() == 1
    assert stack.widget(0) is page
    assert tab_specs == []
    assert sync_calls == ["synced"]
    assert root.count() >= 1
    assert root.itemAt(0).widget().text() == "Test Page"
