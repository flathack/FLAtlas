"""Qt dialog for exporting changed mod files."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .i18n import tr
from .mod_export import (
    ModExportPlan,
    collect_changed_files,
    default_exclusion_labels,
    default_script_xml,
    filter_export_plan,
    write_changed_files_zip,
    write_flmod_package,
)
from .mod_manager_paths import mod_manager_safe_name_for_fs
from .ui_helpers import configure_readonly_table


class ModExportDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        profile_name: str,
        mod_root: Path,
        reference_root: Path,
        default_dir: Path,
    ):
        super().__init__(parent)
        self._mod_root = Path(mod_root)
        self._reference_root = Path(reference_root)
        self._plan: ModExportPlan | None = None
        self._exported_count: int | None = None
        self._manual_exclusions: set[str] = set()
        self._script_manually_edited = False
        self.setWindowTitle(tr("mod_export.title"))
        self.resize(920, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self.summary_lbl = QLabel(tr("mod_export.summary_pending"))
        self.summary_lbl.setWordWrap(True)
        root.addWidget(self.summary_lbl)

        form_box = QGroupBox(tr("mod_export.package_group"))
        form = QFormLayout(form_box)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.format_combo = QComboBox()
        self.format_combo.addItem(tr("mod_export.format.flmod"), "flmod")
        self.format_combo.addItem(tr("mod_export.format.zip"), "zip")
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        form.addRow(tr("mod_export.format"), self.format_combo)

        self.name_edit = QLineEdit(profile_name or "FLAtlas Export")
        self.name_edit.textChanged.connect(self._refresh_script_from_fields)
        form.addRow(tr("mod_export.name"), self.name_edit)

        self.author_edit = QLineEdit()
        self.author_edit.textChanged.connect(self._refresh_script_from_fields)
        form.addRow(tr("mod_export.author"), self.author_edit)

        self.savesafe_cb = QCheckBox(tr("mod_export.savesafe"))
        self.savesafe_cb.setChecked(True)
        self.savesafe_cb.toggled.connect(self._refresh_script_from_fields)
        form.addRow("", self.savesafe_cb)

        self.description_edit = QTextEdit()
        self.description_edit.setAcceptRichText(False)
        self.description_edit.setMinimumHeight(70)
        self.description_edit.textChanged.connect(self._refresh_script_from_fields)
        form.addRow(tr("mod_export.description"), self.description_edit)

        path_row = QWidget()
        path_l = QHBoxLayout(path_row)
        path_l.setContentsMargins(0, 0, 0, 0)
        path_l.setSpacing(6)
        self.target_edit = QLineEdit()
        path_l.addWidget(self.target_edit, 1)
        self.browse_btn = QPushButton(tr("welcome.browse"))
        self.browse_btn.clicked.connect(self._browse_target)
        path_l.addWidget(self.browse_btn)
        form.addRow(tr("mod_export.target"), path_row)
        root.addWidget(form_box)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        files_tab = QWidget()
        files_l = QVBoxLayout(files_tab)
        files_l.setContentsMargins(0, 0, 0, 0)
        file_buttons = QWidget()
        file_buttons_l = QHBoxLayout(file_buttons)
        file_buttons_l.setContentsMargins(0, 0, 0, 0)
        file_buttons_l.setSpacing(6)
        self.scan_btn = QPushButton(tr("mod_export.scan"))
        self.scan_btn.clicked.connect(self.scan)
        file_buttons_l.addWidget(self.scan_btn)
        self.exclusions_btn = QPushButton(tr("mod_export.exclusions"))
        self.exclusions_btn.clicked.connect(self._show_exclusions)
        file_buttons_l.addWidget(self.exclusions_btn)
        file_buttons_l.addStretch(1)
        files_l.addWidget(file_buttons)
        self.files_table = QTableWidget(0, 5)
        configure_readonly_table(self.files_table)
        self.files_table.setHorizontalHeaderLabels(
            [
                tr("mod_export.col.status"),
                tr("mod_export.col.path"),
                tr("mod_export.col.size"),
                tr("mod_export.col.sha"),
                tr("mod_export.col.action"),
            ]
        )
        header = self.files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.files_table.setColumnWidth(3, 190)
        files_l.addWidget(self.files_table)
        self.tabs.addTab(files_tab, tr("mod_export.tab.files"))

        script_tab = QWidget()
        script_l = QVBoxLayout(script_tab)
        script_l.setContentsMargins(0, 0, 0, 0)
        script_hint = QLabel(tr("mod_export.script_hint"))
        script_hint.setWordWrap(True)
        script_l.addWidget(script_hint)
        self.script_edit = QPlainTextEdit()
        self.script_edit.textChanged.connect(self._mark_script_edited)
        script_l.addWidget(self.script_edit, 1)
        self.regenerate_script_btn = QPushButton(tr("mod_export.regenerate_script"))
        self.regenerate_script_btn.clicked.connect(self._force_refresh_script_from_fields)
        script_l.addWidget(self.regenerate_script_btn)
        self.tabs.addTab(script_tab, tr("mod_export.tab.script"))

        self.errors_tab = QWidget()
        errors_l = QVBoxLayout(self.errors_tab)
        errors_l.setContentsMargins(0, 0, 0, 0)
        self.errors_edit = QPlainTextEdit()
        self.errors_edit.setReadOnly(True)
        errors_l.addWidget(self.errors_edit)
        self.errors_tab_index = self.tabs.addTab(self.errors_tab, tr("mod_export.tab.errors"))
        self.tabs.setTabVisible(self.errors_tab_index, False)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        export_btn = self.buttons.button(QDialogButtonBox.Ok)
        if export_btn is not None:
            export_btn.setText(tr("mod_export.export"))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

        self._force_refresh_script_from_fields()
        self._set_default_target(default_dir)
        self._on_format_changed()
        self._update_accept_state()

    @property
    def plan(self) -> ModExportPlan | None:
        if self._plan is None:
            return None
        return filter_export_plan(self._plan, self._manual_exclusions)

    def selected_format(self) -> str:
        return str(self.format_combo.currentData() or "flmod")

    def target_path(self) -> Path:
        return Path(self.target_edit.text().strip())

    def script_xml(self) -> str:
        return self.script_edit.toPlainText()

    @property
    def exported_count(self) -> int | None:
        return self._exported_count

    def scan(self) -> None:
        progress = QProgressDialog(tr("mod_export.scan_progress"), tr("btn.cancel"), 0, 100, self)
        progress.setWindowTitle(tr("mod_export.scan"))
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        def _progress(_stage: str, current: int, total: int, path: str) -> bool:
            maximum = max(1, int(total))
            progress.setMaximum(maximum)
            progress.setValue(min(maximum, max(0, int(current))))
            progress.setLabelText(tr("mod_export.scan_progress_path").format(path=Path(path).name or path))
            QApplication.processEvents()
            return not progress.wasCanceled()

        self.scan_btn.setEnabled(False)
        try:
            plan = collect_changed_files(self._mod_root, self._reference_root, progress=_progress)
        except Exception as exc:
            QMessageBox.warning(self, tr("mod_export.title"), tr("mod_export.err.scan_failed").format(error=str(exc)))
            return
        finally:
            progress.setValue(progress.maximum())
            progress.close()
            self.scan_btn.setEnabled(True)

        self._plan = plan
        self._manual_exclusions.clear()
        self._populate_files()
        self._update_summary()
        self._update_errors()
        self._update_accept_state()
        if not plan.export_files and not any("cancelled" in err.lower() for err in plan.errors):
            QMessageBox.information(self, tr("mod_export.title"), tr("mod_export.no_changes"))

    def accept(self) -> None:
        if self._plan is None:
            QMessageBox.information(self, tr("mod_export.title"), tr("mod_export.scan_required"))
            return
        plan = self.plan
        if plan is None or not plan.export_files:
            QMessageBox.information(self, tr("mod_export.title"), tr("mod_export.no_changes"))
            return
        if not self.target_edit.text().strip():
            self.target_edit.setFocus()
            return
        target = self.target_path()
        if target.exists():
            answer = QMessageBox.question(
                self,
                tr("mod_export.title"),
                tr("mod_export.overwrite_confirm").format(path=str(target)),
            )
            if answer != QMessageBox.Yes:
                return
        progress = QProgressDialog(tr("mod_export.export_progress"), tr("btn.cancel"), 0, 100, self)
        progress.setWindowTitle(tr("mod_export.export"))
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        def _progress(_stage: str, current: int, total: int, path: str) -> bool:
            maximum = max(1, int(total))
            progress.setMaximum(maximum)
            progress.setValue(min(maximum, max(0, int(current))))
            progress.setLabelText(tr("mod_export.export_progress_path").format(path=Path(path).name or path))
            QApplication.processEvents()
            return not progress.wasCanceled()

        export_btn = self.buttons.button(QDialogButtonBox.Ok)
        if export_btn is not None:
            export_btn.setEnabled(False)
        try:
            fmt = self.selected_format()
            if fmt == "flmod":
                self._exported_count = write_flmod_package(plan, target, script_xml=self.script_xml(), progress=_progress)
            else:
                self._exported_count = write_changed_files_zip(plan, target, include_manifest=True, progress=_progress)
        except Exception as exc:
            QMessageBox.warning(self, tr("mod_export.title"), tr("mod_export.err.write_failed").format(error=str(exc)))
            return
        finally:
            progress.setValue(progress.maximum())
            progress.close()
            if export_btn is not None:
                export_btn.setEnabled(True)
        super().accept()

    def _populate_files(self) -> None:
        files = list(self._plan.export_files if self._plan is not None else [])
        self.files_table.setRowCount(len(files))
        for row, item in enumerate(files):
            is_excluded = item.relative_path.lower() in self._manual_exclusions
            for col, value in enumerate(
                (
                    item.status,
                    item.relative_path,
                    f"{item.size:,}".replace(",", "."),
                    item.sha256[:16],
                )
            ):
                cell = QTableWidgetItem(str(value))
                cell.setToolTip(item.sha256 if col == 3 else str(value))
                if is_excluded:
                    cell.setFlags(cell.flags() & ~Qt.ItemIsEnabled)
                self.files_table.setItem(row, col, cell)
            button = QPushButton(tr("mod_export.include") if is_excluded else tr("mod_export.exclude"))
            button.clicked.connect(lambda _checked=False, rel=item.relative_path: self._toggle_manual_exclusion(rel))
            self.files_table.setCellWidget(row, 4, button)

    def _update_summary(self) -> None:
        plan = self._plan
        if plan is None:
            self.summary_lbl.setText(tr("mod_export.summary_pending"))
            return
        filtered = self.plan or plan
        self.summary_lbl.setText(
            tr("mod_export.summary").format(
                new=filtered.new_count,
                modified=filtered.modified_count,
                unchanged=plan.unchanged_count,
            )
            + (
                "\n" + tr("mod_export.manual_excluded_count").format(count=len(self._manual_exclusions))
                if self._manual_exclusions
                else ""
            )
        )

    def _update_errors(self) -> None:
        plan = self._plan
        errors = list(plan.errors) if plan is not None else []
        self.errors_edit.setPlainText("\n".join(errors))
        self.tabs.setTabVisible(self.errors_tab_index, bool(errors))

    def _update_accept_state(self) -> None:
        ok_btn = self.buttons.button(QDialogButtonBox.Ok)
        if ok_btn is not None:
            plan = self.plan
            ok_btn.setEnabled(bool(plan is not None and plan.export_files))

    def _toggle_manual_exclusion(self, relative_path: str) -> None:
        key = str(relative_path or "").replace("\\", "/").lower()
        if not key:
            return
        if key in self._manual_exclusions:
            self._manual_exclusions.remove(key)
        else:
            self._manual_exclusions.add(key)
        self._populate_files()
        self._update_summary()
        self._update_accept_state()

    def _show_exclusions(self) -> None:
        lines = [tr("mod_export.exclusions_builtin")]
        lines.extend(f"- {item}" for item in default_exclusion_labels())
        if self._manual_exclusions:
            lines.append("")
            lines.append(tr("mod_export.exclusions_manual"))
            lines.extend(f"- {item}" for item in sorted(self._manual_exclusions))
        QMessageBox.information(self, tr("mod_export.exclusions"), "\n".join(lines))

    def _script_from_fields(self) -> str:
        return default_script_xml(
            name=self.name_edit.text().strip() or "FLAtlas Export",
            author=self.author_edit.text().strip(),
            description=self.description_edit.toPlainText().strip(),
            savesafe=self.savesafe_cb.isChecked(),
        )

    def _mark_script_edited(self) -> None:
        if not bool(getattr(self, "_updating_script", False)):
            self._script_manually_edited = True

    def _refresh_script_from_fields(self) -> None:
        if self._script_manually_edited:
            return
        self._set_script_text(self._script_from_fields())

    def _force_refresh_script_from_fields(self) -> None:
        self._script_manually_edited = False
        self._set_script_text(self._script_from_fields())

    def _set_script_text(self, text: str) -> None:
        self._updating_script = True
        try:
            self.script_edit.setPlainText(text)
        finally:
            self._updating_script = False

    def _set_default_target(self, default_dir: Path) -> None:
        safe_name = mod_manager_safe_name_for_fs(self.name_edit.text().strip() or "FLAtlas_Export")
        suffix = ".flmod" if self.selected_format() == "flmod" else ".zip"
        self.target_edit.setText(str(Path(default_dir) / f"{safe_name}{suffix}"))

    def _on_format_changed(self) -> None:
        fmt = self.selected_format()
        self.name_edit.setEnabled(fmt == "flmod")
        self.author_edit.setEnabled(fmt == "flmod")
        self.description_edit.setEnabled(fmt == "flmod")
        self.savesafe_cb.setEnabled(fmt == "flmod")
        self.script_edit.setEnabled(fmt == "flmod")
        self.regenerate_script_btn.setEnabled(fmt == "flmod")
        current = self.target_edit.text().strip()
        if current:
            path = Path(current)
            suffix = ".flmod" if fmt == "flmod" else ".zip"
            self.target_edit.setText(str(path.with_suffix(suffix)))

    def _browse_target(self) -> None:
        fmt = self.selected_format()
        filter_text = tr("mod_export.filter.flmod") if fmt == "flmod" else tr("mod_export.filter.zip")
        path, _selected = QFileDialog.getSaveFileName(
            self,
            tr("mod_export.target_title"),
            self.target_edit.text().strip(),
            filter_text,
        )
        if path:
            target = Path(path)
            if fmt == "flmod" and target.suffix.lower() != ".flmod":
                target = target.with_suffix(".flmod")
            elif fmt == "zip" and target.suffix.lower() != ".zip":
                target = target.with_suffix(".zip")
            self.target_edit.setText(str(target))
