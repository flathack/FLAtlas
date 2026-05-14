"""Small zone-related dialogs used by the main dialog facade."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
)

from .i18n import tr
from .simple_dialog_logic import build_exclusion_zone_data, build_patrol_zone_payload
from .ui_helpers import configure_contains_completer


class SimpleZoneDialog(QDialog):
    """Dialog zum Erstellen einer einfachen Zone (z.B. Population-Zone).

    Felder: Name, Kommentar, Shape (Dropdown), Sort (Standard 99).
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.zone_create"))
        self.setMinimumWidth(420)
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("z.B. pop_br01_dublin_gate")
        layout.addRow(tr("dlg.name"), self.name_edit)

        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText("z.B. Dublin Jumpgate")
        layout.addRow(tr("dlg.comment"), self.comment_edit)

        self.shape_cb = QComboBox()
        self.shape_cb.addItems([
            "SPHERE", "ELLIPSOID", "BOX", "CYLINDER", "RING",
        ])
        layout.addRow("Shape:", self.shape_cb)

        self.sort_spin = QSpinBox()
        self.sort_spin.setRange(0, 999)
        self.sort_spin.setValue(99)
        layout.addRow("Sort:", self.sort_spin)

        self.damage_spin = QSpinBox()
        self.damage_spin.setRange(0, 2_000_000)
        self.damage_spin.setValue(0)
        layout.addRow("Damage:", self.damage_spin)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)


class PatrolZoneDialog(QDialog):
    """Dialog zum Erstellen einer Patrol-Zone."""

    def __init__(self, parent, *, encounters: list[str], factions: list[str]):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.patrol_zone_create"))
        self.setMinimumWidth(480)
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("z.B. path_daumann2")
        layout.addRow(tr("dlg.name"), self.name_edit)

        self.usage_cb = QComboBox()
        self.usage_cb.addItems(["patrol", "trade"])
        self.usage_cb.setCurrentText("patrol")
        layout.addRow("Usage:", self.usage_cb)

        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText(tr("dlg.optional"))
        layout.addRow(tr("dlg.comment"), self.comment_edit)

        self.sort_spin = QSpinBox()
        self.sort_spin.setRange(0, 999)
        self.sort_spin.setValue(99)
        layout.addRow("Sort:", self.sort_spin)

        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(100, 50_000)
        self.radius_spin.setValue(750)
        layout.addRow("Cylinder Radius:", self.radius_spin)

        self.damage_spin = QSpinBox()
        self.damage_spin.setRange(0, 2_000_000)
        self.damage_spin.setValue(0)
        layout.addRow("Damage:", self.damage_spin)

        self.toughness_spin = QSpinBox()
        self.toughness_spin.setRange(0, 100)
        self.toughness_spin.setValue(6)
        layout.addRow("Toughness:", self.toughness_spin)

        self.density_spin = QSpinBox()
        self.density_spin.setRange(0, 100)
        self.density_spin.setValue(3)
        layout.addRow("Density:", self.density_spin)

        self.repop_spin = QSpinBox()
        self.repop_spin.setRange(0, 10_000)
        self.repop_spin.setValue(90)
        layout.addRow("Repop Time:", self.repop_spin)

        self.battle_spin = QSpinBox()
        self.battle_spin.setRange(0, 10_000)
        self.battle_spin.setValue(4)
        layout.addRow("Max Battle Size:", self.battle_spin)

        self.pop_type_cb = QComboBox()
        self.pop_type_cb.setEditable(True)
        self._apply_pop_type_items("patrol")
        layout.addRow("Pop Type:", self.pop_type_cb)
        self.usage_cb.currentTextChanged.connect(self._on_usage_changed)

        self.relief_spin = QSpinBox()
        self.relief_spin.setRange(0, 10_000)
        self.relief_spin.setValue(30)
        layout.addRow("Relief Time:", self.relief_spin)

        self.path_name_edit = QLineEdit("patrol")
        layout.addRow("Path Label:", self.path_name_edit)

        self.path_index_spin = QSpinBox()
        self.path_index_spin.setRange(1, 999)
        self.path_index_spin.setValue(1)
        layout.addRow("Path Index:", self.path_index_spin)

        self.encounter_cb = QComboBox()
        self.encounter_cb.setEditable(True)
        self.encounter_cb.addItems(encounters or [])
        self._apply_encounter_default("patrol")
        layout.addRow("Encounter:", self.encounter_cb)

        self.faction_cb = QComboBox()
        self.faction_cb.setEditable(True)
        self.faction_cb.addItems(factions or [])
        configure_contains_completer(self.faction_cb)
        layout.addRow("Faction:", self.faction_cb)

        self.levels_edit = QLineEdit("6")
        layout.addRow("Encounter Level:", self.levels_edit)

        self.chance_spin = QDoubleSpinBox()
        self.chance_spin.setRange(0.0, 1.0)
        self.chance_spin.setSingleStep(0.01)
        self.chance_spin.setDecimals(2)
        self.chance_spin.setValue(0.29)
        layout.addRow("Encounter Chance:", self.chance_spin)

        self.last_diff_cb = QCheckBox("Use lower chance for last level")
        self.last_diff_cb.setChecked(False)
        layout.addRow(self.last_diff_cb)

        self.last_chance_spin = QSpinBox()
        self.last_chance_spin.setRange(0, 100)
        self.last_chance_spin.setValue(10)
        layout.addRow("Last Level Chance:", self.last_chance_spin)

        self.mission_eligible_cb = QCheckBox("Mission Eligible")
        self.mission_eligible_cb.setChecked(True)
        layout.addRow(self.mission_eligible_cb)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    @staticmethod
    def _pop_types_for_usage(usage: str) -> list[str]:
        u = (usage or "").strip().lower()
        if u == "trade":
            return ["trade_path", "mining_path"]
        return ["lane_patrol", "attack_patrol", "field_patrol", "mining_path", "scavenger_path"]

    def _apply_pop_type_items(self, usage: str):
        current = self.pop_type_cb.currentText().strip() if hasattr(self, "pop_type_cb") else ""
        items = self._pop_types_for_usage(usage)
        self.pop_type_cb.clear()
        self.pop_type_cb.addItems(items)
        if current:
            self.pop_type_cb.setCurrentText(current)
        else:
            self.pop_type_cb.setCurrentText(items[0] if items else "")

    def _apply_encounter_default(self, usage: str) -> None:
        current = self.encounter_cb.currentText().strip() if hasattr(self, "encounter_cb") else ""
        all_items = [self.encounter_cb.itemText(i) for i in range(self.encounter_cb.count())] if hasattr(self, "encounter_cb") else []
        preferred = (
            ["tradep_trade_armored", "tradep_trade_trader", "tradep_trade_transport"]
            if (usage or "").strip().lower() == "trade"
            else ["patrolp_assault", "patrolp_bh_assault", "patrolp_gov_assault"]
        )
        chosen = current
        if not chosen or chosen not in all_items:
            chosen = next((item for item in preferred if item in all_items), preferred[0])
        self.encounter_cb.setCurrentText(chosen)

    def _on_usage_changed(self, usage: str):
        self._apply_pop_type_items(usage)
        self._apply_encounter_default(usage)
        if (usage or "").strip().lower() == "trade":
            self.levels_edit.setText("6")
            self.chance_spin.setValue(0.40)
        else:
            self.levels_edit.setText("6")
            self.chance_spin.setValue(0.29)

    def accept(self):
        usage = self.usage_cb.currentText().strip().lower()
        pop_type = self.pop_type_cb.currentText().strip().lower()
        allowed = {p.lower() for p in self._pop_types_for_usage(usage)}
        is_comma = "," in pop_type
        is_exotic = bool(pop_type) and pop_type not in allowed
        if is_comma or is_exotic:
            why = "kommagetrennt" if is_comma else "nicht standard für diese Usage"
            msg = (
                f"Der Pop Type '{self.pop_type_cb.currentText().strip()}' ist {why}.\n\n"
                "Soll trotzdem fortgefahren werden?"
            )
            ans = QMessageBox.question(
                self,
                "Pop Type Warnung",
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return
        super().accept()

    def payload(self) -> dict:
        return build_patrol_zone_payload(
            name=self.name_edit.text(),
            usage=self.usage_cb.currentText(),
            comment=self.comment_edit.text(),
            sort=self.sort_spin.value(),
            radius=self.radius_spin.value(),
            damage=self.damage_spin.value(),
            toughness=self.toughness_spin.value(),
            density=self.density_spin.value(),
            repop_time=self.repop_spin.value(),
            max_battle_size=self.battle_spin.value(),
            pop_type=self.pop_type_cb.currentText(),
            relief_time=self.relief_spin.value(),
            path_label=self.path_name_edit.text(),
            path_index=self.path_index_spin.value(),
            encounter=self.encounter_cb.currentText(),
            faction=self.faction_cb.currentText(),
            levels_text=self.levels_edit.text(),
            default_chance=int(round(float(self.chance_spin.value()) * 100.0)),
            last_diff_enabled=self.last_diff_cb.isChecked(),
            last_chance=self.last_chance_spin.value(),
            mission_eligible=self.mission_eligible_cb.isChecked(),
        )


class ExclusionZoneDialog(QDialog):
    """Dialog zum Erstellen einer Exclusion-Zone für ein Feld."""

    def __init__(
        self,
        parent,
        nickname_suggestion: str,
        default_pos: tuple[float, float, float],
        default_size: tuple[float, float, float],
        *,
        supports_shell: bool = False,
        shell_options: list[str] | None = None,
    ):
        super().__init__(parent)
        del default_pos, default_size
        self.setWindowTitle(tr("dlg.exclusion_create"))
        self.setMinimumWidth(460)
        layout = QFormLayout(self)
        self._supports_shell = bool(supports_shell)

        self.nick_edit = QLineEdit(nickname_suggestion)
        layout.addRow(tr("dlg.exclusion_nickname"), self.nick_edit)

        self.shape_cb = QComboBox()
        self.shape_cb.addItems(["SPHERE", "ELLIPSOID", "BOX", "CYLINDER"])
        layout.addRow(tr("dlg.exclusion_shape"), self.shape_cb)

        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText(tr("dlg.optional"))
        layout.addRow(tr("dlg.exclusion_comment"), self.comment_edit)

        self.sort_spin = QSpinBox()
        self.sort_spin.setRange(0, 999)
        self.sort_spin.setValue(99)
        layout.addRow(tr("dlg.exclusion_sort"), self.sort_spin)

        self.link_cb = QCheckBox(tr("dlg.exclusion_link_field"))
        self.link_cb.setChecked(True)
        layout.addRow(self.link_cb)

        self.shell_enabled_cb = QCheckBox("Optical Shell")
        self.shell_enabled_cb.setChecked(False)
        self.shell_enabled_cb.setEnabled(self._supports_shell)
        layout.addRow(self.shell_enabled_cb)

        self.shell_fog_far_spin = QSpinBox()
        self.shell_fog_far_spin.setRange(0, 50000)
        self.shell_fog_far_spin.setValue(8000)
        layout.addRow("Fog Far:", self.shell_fog_far_spin)

        self.shell_path_cb = QComboBox()
        self.shell_path_cb.setEditable(True)
        self.shell_path_cb.addItems(
            [str(item).strip() for item in (shell_options or []) if str(item).strip()]
        )
        if self.shell_path_cb.count() == 0:
            self.shell_path_cb.addItem("solar\\nebula\\generic_exclusion.3db")
        self.shell_path_cb.setCurrentText("solar\\nebula\\generic_exclusion.3db")
        layout.addRow("Shell Mesh:", self.shell_path_cb)

        self.shell_scalar_spin = QDoubleSpinBox()
        self.shell_scalar_spin.setRange(0.1, 5.0)
        self.shell_scalar_spin.setSingleStep(0.1)
        self.shell_scalar_spin.setDecimals(2)
        self.shell_scalar_spin.setValue(1.0)
        layout.addRow("Shell Scalar:", self.shell_scalar_spin)

        self.shell_max_alpha_spin = QDoubleSpinBox()
        self.shell_max_alpha_spin.setRange(0.0, 1.0)
        self.shell_max_alpha_spin.setSingleStep(0.05)
        self.shell_max_alpha_spin.setDecimals(2)
        self.shell_max_alpha_spin.setValue(0.5)
        layout.addRow("Max Alpha:", self.shell_max_alpha_spin)

        self.shell_tint_edit = QLineEdit("40, 120, 120")
        self.shell_tint_edit.setPlaceholderText("R, G, B")
        layout.addRow("Exclusion Tint:", self.shell_tint_edit)

        self.shell_enabled_cb.toggled.connect(self._sync_shell_controls)
        self._sync_shell_controls()

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _sync_shell_controls(self) -> None:
        enabled = self._supports_shell and self.shell_enabled_cb.isChecked()
        for widget in (
            self.shell_fog_far_spin,
            self.shell_path_cb,
            self.shell_scalar_spin,
            self.shell_max_alpha_spin,
            self.shell_tint_edit,
        ):
            widget.setEnabled(enabled)

    def get_data(self) -> dict:
        return build_exclusion_zone_data(
            nickname=self.nick_edit.text(),
            shape=self.shape_cb.currentText(),
            comment=self.comment_edit.text(),
            sort=self.sort_spin.value(),
            link_to_field_zone=self.link_cb.isChecked(),
            shell_enabled=self._supports_shell and self.shell_enabled_cb.isChecked(),
            shell_fog_far=self.shell_fog_far_spin.value(),
            shell_path=self.shell_path_cb.currentText(),
            shell_scalar=self.shell_scalar_spin.value(),
            shell_max_alpha=self.shell_max_alpha_spin.value(),
            shell_tint=self.shell_tint_edit.text(),
        )


# ══════════════════════════════════════════════════════════════════════
#  Base-Erstellungsdialog
# ══════════════════════════════════════════════════════════════════════
