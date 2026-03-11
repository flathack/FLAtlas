"""Runtime helpers for the Freelancer.ini editor dialog."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from .i18n import tr
from .models import SolarObject
from .text_write_utils import write_text_with_fallback


@dataclass
class FreelancerIniEditorMeta:
    shown_path: str
    info_html: str
    choices: list[tuple[str, str]]
    selected_dll: str


def resource_dlls_from_text(raw_text: str) -> list[str]:
    lines = str(raw_text or "").splitlines()
    in_resources = False
    out: list[str] = []
    seen: set[str] = set()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("//"):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_resources = line[1:-1].strip().lower() == "resources"
            continue
        if not in_resources or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip().lower() != "dll":
            continue
        dll = value.split(",", 1)[0].strip()
        if not dll:
            continue
        dll_key = dll.lower()
        if dll_key in seen:
            continue
        seen.add(dll_key)
        out.append(dll)
    return out


def build_freelancer_ini_editor_meta(
    *,
    ini_read: Path,
    ini_write: Path | None,
    is_overlay_mode: bool,
    editor_text: str,
    baseline_dlls: list[str],
    current_dlls_from_ini: list[str],
    preferred_dll: str,
    default_dll: str,
) -> FreelancerIniEditorMeta:
    shown_path = str(ini_write if is_overlay_mode and ini_write is not None else ini_read)
    current_dlls = resource_dlls_from_text(editor_text) if str(editor_text or "").strip() else list(current_dlls_from_ini)
    baseline_set = {dll.lower() for dll in baseline_dlls}
    current_set = {dll.lower() for dll in current_dlls}
    custom = [dll for dll in current_dlls if dll.lower() not in baseline_set]
    status_key = "freelancer_ini_editor.compare.same" if current_set == baseline_set else "freelancer_ini_editor.compare.diff"
    lines = [tr("freelancer_ini_editor.compare").format(status=tr(status_key))]
    if custom:
        lines.append(tr("freelancer_ini_editor.custom_dlls").format(dlls=", ".join(custom)))
    else:
        lines.append(tr("freelancer_ini_editor.custom_dlls_none"))
    choices = [
        (tr("freelancer_ini_editor.dll_custom_item").format(dll=dll), dll)
        for dll in custom
    ]
    choices.append((tr("freelancer_ini_editor.dll_create_item").format(dll=default_dll), default_dll))
    selected = str(preferred_dll or "").strip() or (custom[0] if custom else default_dll)
    return FreelancerIniEditorMeta(
        shown_path=shown_path,
        info_html="<br>".join(lines),
        choices=choices,
        selected_dll=selected,
    )


def normalize_freelancer_ini_text(text: str) -> str:
    out = str(text or "").replace("\r\n", "\n")
    if not out.endswith("\n"):
        out += "\n"
    return out


def apply_selected_resource_dll(editor_text: str, dll_name: str, insert_resource_dll_line) -> tuple[str, bool]:
    selected = str(dll_name or "").strip()
    if not selected:
        return str(editor_text or ""), False
    current_dlls = resource_dlls_from_text(editor_text)
    if selected.lower() in {dll.lower() for dll in current_dlls}:
        return str(editor_text or ""), False
    updated_text, _added = insert_resource_dll_line(str(editor_text or ""), selected)
    return updated_text, True


def refresh_after_freelancer_ini_save(window: Any, target: Path) -> None:
    window._reload_dll_name_cache()
    window._refresh_system_name_cache(window._primary_game_path())
    window._apply_system_name_mode_to_ui()
    window._rebuild_object_combo()
    if isinstance(window._selected, SolarObject):
        window.name_lbl.setText(f"📍 {window._object_display_label(window._selected)}")
    window.statusBar().showMessage(tr("freelancer_ini_editor.saved").format(path=str(target)))


def open_freelancer_ini_editor(window: Any) -> None:
    ini_read = window._find_freelancer_ini_read()
    if ini_read is None:
        QMessageBox.warning(window, tr("msg.not_found"), tr("freelancer_ini_editor.no_file"))
        return
    ini_write = window._find_freelancer_ini_write()
    if ini_write is None:
        QMessageBox.warning(window, tr("msg.not_found"), tr("freelancer_ini_editor.no_file"))
        return

    dlg = QDialog(window)
    dlg.setWindowTitle(tr("freelancer_ini_editor.title"))
    dlg.resize(980, 760)
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(8)

    path_lbl = QLabel("")
    path_lbl.setTextFormat(Qt.RichText)
    layout.addWidget(path_lbl)

    info_lbl = QLabel("")
    info_lbl.setWordWrap(True)
    info_lbl.setTextFormat(Qt.RichText)
    layout.addWidget(info_lbl)

    dll_row = QHBoxLayout()
    dll_row.setSpacing(6)
    dll_row.addWidget(QLabel(tr("freelancer_ini_editor.dll_choice")))
    dll_choice_cb = QComboBox()
    dll_row.addWidget(dll_choice_cb, 1)
    dll_apply_btn = QPushButton(tr("freelancer_ini_editor.dll_use"))
    dll_row.addWidget(dll_apply_btn)
    layout.addLayout(dll_row)

    editor = QTextEdit()
    editor.setAcceptRichText(False)
    layout.addWidget(editor, 1)

    buttons = QHBoxLayout()
    buttons.addStretch(1)
    reload_btn = QPushButton(tr("freelancer_ini_editor.reload"))
    save_btn = QPushButton(tr("freelancer_ini_editor.save"))
    close_btn = QPushButton(tr("dlg.close"))
    buttons.addWidget(reload_btn)
    buttons.addWidget(save_btn)
    buttons.addWidget(close_btn)
    layout.addLayout(buttons)

    baseline_path = window._bundled_freelancer_ini_path()
    baseline_dlls = window._resource_dlls_from_freelancer_ini(baseline_path) if baseline_path.is_file() else []
    preferred_dll = str(window._cfg.get("ids.resource_dll_name", "") or "").strip()
    default_flatlas_dll = "FLAtlas_resources.dll"

    def _refresh_meta() -> None:
        nonlocal ini_read, ini_write, preferred_dll
        ini_read = window._find_freelancer_ini_read() or ini_read
        ini_write = window._find_freelancer_ini_write() or ini_write
        meta = build_freelancer_ini_editor_meta(
            ini_read=ini_read,
            ini_write=ini_write,
            is_overlay_mode=window._is_overlay_mode(),
            editor_text=editor.toPlainText(),
            baseline_dlls=baseline_dlls,
            current_dlls_from_ini=window._resource_dlls_from_freelancer_ini(ini_read),
            preferred_dll=preferred_dll,
            default_dll=default_flatlas_dll,
        )
        path_lbl.setText(tr("freelancer_ini_editor.path").format(path=meta.shown_path))
        info_lbl.setText(meta.info_html)
        dll_choice_cb.blockSignals(True)
        dll_choice_cb.clear()
        for label, dll in meta.choices:
            dll_choice_cb.addItem(label, dll)
        idx = dll_choice_cb.findData(meta.selected_dll)
        if idx < 0:
            idx = 0
        if idx >= 0:
            dll_choice_cb.setCurrentIndex(idx)
        dll_choice_cb.blockSignals(False)

    def _reload() -> None:
        src = ini_write if ini_write and ini_write.is_file() else ini_read
        if src is None:
            editor.clear()
            return
        editor.setPlainText(window._read_text_best_effort(src))
        _refresh_meta()

    def _save() -> None:
        target = window._find_freelancer_ini_write()
        if target is None:
            QMessageBox.warning(window, tr("msg.not_found"), tr("freelancer_ini_editor.no_file"))
            return
        try:
            write_text_with_fallback(target, normalize_freelancer_ini_text(editor.toPlainText()), ensure_parent=True)
        except Exception as exc:
            QMessageBox.critical(window, tr("msg.save_error"), tr("freelancer_ini_editor.save_failed").format(error=exc))
            return
        _refresh_meta()
        refresh_after_freelancer_ini_save(window, target)

    def _apply_dll_choice() -> None:
        nonlocal preferred_dll
        dll_name = str(dll_choice_cb.currentData() or "").strip()
        if not dll_name:
            return
        updated_text, changed = apply_selected_resource_dll(
            editor.toPlainText(),
            dll_name,
            window._insert_resource_dll_line,
        )
        if changed:
            editor.setPlainText(updated_text)
        preferred_dll = dll_name
        window._cfg.set("ids.resource_dll_name", preferred_dll)
        _refresh_meta()
        window.statusBar().showMessage(tr("freelancer_ini_editor.dll_selected").format(dll=preferred_dll))

    reload_btn.clicked.connect(_reload)
    save_btn.clicked.connect(_save)
    dll_apply_btn.clicked.connect(_apply_dll_choice)
    close_btn.clicked.connect(dlg.reject)

    _reload()
    dlg.exec()
