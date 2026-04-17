"""Dialoge für den Freelancer System Editor.

Enthaelt:
- ZoneCreationDialog     – Zonentyp, Name und Referenzdatei
- SolarCreationDialog    – Sonne / Planet erstellen
- ObjectCreationDialog   – Beliebiges Objekt erstellen
- MeshPreviewDialog      – 3D-Vorschau eines Archetype-Modells
- SystemCreationDialog   – Neues Sternensystem erstellen
- SystemSettingsDialog   – System-Metadaten bearbeiten
- TradeLaneDialog        – Tradelane-Parameter eingeben
- TradeLaneEditDialog    – Tradelane-Routen bearbeiten/loeschen
- ZonePopulationDialog   – Zone-Population bearbeiten (Encounter/Factions)
- SimpleZoneDialog       – Einfache Zone erstellen (Pop-Zone)
- BaseCreationDialog     – Neue Base erstellen
- BaseEditDialog         – Base-Attribute und Market bearbeiten
- DockingRingDialog      – Docking Ring + Base in einem Schritt erstellen
"""

from __future__ import annotations

import math
from pathlib import Path
import re
from typing import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)
from PySide6.QtCore import QEvent, QPointF, Qt, QUrl, QSize, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QVector3D, QGuiApplication
from shiboken6 import isValid

from .cmp_loader import build_native_model_debug_rows
from .freelancer_mesh_data import FreelancerBounds, FreelancerMeshData
from .native_preview_qt3d import (
    _disable_backface_culling,
    apply_native_geometry_material,
    build_annulus_renderer,
    build_solid_annulus_renderer,
    build_qt3d_texture_material,
    build_native_geometry_material,
    build_native_geometry_renderer,
    build_native_wireframe_entity,
)
from .view_3d_object_logic import rotation_quaternion_from_fl
from .native_preview_reference import (
    build_native_preview_reference_rows,
    build_native_preview_reference_summary,
    sort_native_preview_reference_rows,
)
from .native_preview_scene_data import build_native_preview_scene_data, texture_path_for_geometry
from .orbit_drag import orbit_drag_angles
from .qt3d_compat import (
    QT3D_AVAILABLE,
    QConeMesh3D,
    QCuboidMesh3D,
    QCylinderMesh3D,
    QDirectionalLight3D,
    QEntity3D,
    QMesh3D,
    QOrbitCameraController3D,
    QPhongMaterial3D,
    QPhongAlphaMaterial3D,
    QQuaternion,
    QSphereMesh3D,
    QTransform3D,
    Qt3DWindow3D,
)
from .base_dialog_logic import (
    build_template_apply_state,
    build_base_creation_payload,
    build_room_lock_state,
    build_room_row_state,
    build_room_npc_display_rows,
    build_room_npc_tab_state,
    build_default_room_reset_state,
    build_start_room_state,
    build_template_change_state,
    build_template_selection_context,
    collect_active_room_names,
    collect_room_npc_rows,
    collect_room_states,
    build_template_room_plan,
    default_role_for_room,
    default_scene_for_room,
    faction_display_from_any,
    faction_nick_from_display,
    make_copied_npc_rows,
    normalize_role_for_room,
    role_options_for_room,
    safe_nick_part,
    scene_options_for_room,
    split_npc_list,
    xml_to_plain_preview,
)
from .base_edit_page import (
    build_base_edit_commodity_tab,
    build_base_edit_equip_tab,
    build_base_edit_properties_tab,
    build_base_edit_ships_tab,
)
from .base_edit_logic import (
    build_base_edit_obj_properties,
    build_ship_market_data_map,
    can_open_infocard,
    collect_ship_market_goods,
    extract_assigned_nicknames,
)
from .base_edit_readers import (
    collect_combo_data_or_texts,
    collect_first_column_raw_rows,
    collect_first_column_values_from_cells,
    collect_market_rows_from_cells,
    collect_non_empty_combo_texts,
    collect_table_raw_rows,
    collect_table_values_from_cells,
    optional_text_value,
)
from .docking_ring_logic import build_docking_ring_payload, build_docking_ring_room_state
from .i18n import tr
from .ui_helpers import configure_contains_completer
from .simple_dialog_logic import (
    build_buoy_payload,
    build_category_object_payload,
    build_exclusion_zone_data,
    build_light_source_payload,
    build_object_creation_payload,
    build_patrol_zone_payload,
    build_solar_creation_payload,
    build_trade_lane_payload,
)
from .system_dialog_logic import build_system_creation_payload, build_system_settings_result


# ══════════════════════════════════════════════════════════════════════
#  Zone-Erstellungsdialog
# ══════════════════════════════════════════════════════════════════════

class ZoneCreationDialog(QDialog):
    """Zonentyp, Name und Referenzdatei wählen."""

    def __init__(
        self,
        parent,
        asteroids: list[str],
        nebulas: list[str],
        zone_music_options: list[str] | None = None,
        nebula_spacedust_options: list[str] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.zone_create"))
        self.setMinimumWidth(500)
        layout = QFormLayout(self)

        self.type_cb = QComboBox()
        self.type_cb.addItems(["Asteroid Field", "Nebula"])
        layout.addRow(tr("dlg.type"), self.type_cb)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("z.B. PleioneNebula")
        layout.addRow(tr("dlg.zone_name"), self.name_edit)

        self.ids_name_edit = QLineEdit()
        self.ids_name_edit.setPlaceholderText("Ingame Name (optional)")
        layout.addRow("Ingame Name:", self.ids_name_edit)

        self.ref_cb = QComboBox()
        self.type_cb.currentTextChanged.connect(self._on_type_changed)
        self._ast_list = asteroids
        self._neb_list = nebulas
        self._zone_music_options = [str(item).strip() for item in (zone_music_options or []) if str(item).strip()]
        self._nebula_spacedust_options = [
            str(item).strip() for item in (nebula_spacedust_options or []) if str(item).strip()
        ]
        self.music_cb = QComboBox()
        self.music_cb.setEditable(True)
        layout.addRow(tr("dlg.ref_file"), self.ref_cb)
        layout.addRow("Music:", self.music_cb)

        self.damage_spin = QSpinBox()
        self.damage_spin.setRange(0, 2_000_000)
        self.damage_spin.setValue(0)
        layout.addRow("Damage:", self.damage_spin)

        self.asteroid_property_flags_cb = QComboBox()
        self.asteroid_property_flags_cb.setEditable(True)
        self.asteroid_property_flags_cb.addItem("66 - Standard rock field", "66")
        self.asteroid_property_flags_cb.addItem("65 - Standard ice field", "65")
        self.asteroid_property_flags_cb.addItem("130 - Standard debris field", "130")
        self.asteroid_property_flags_cb.addItem("129 - Debris / hidden helper variant", "129")
        self.asteroid_property_flags_cb.addItem("4128 - Minefield / dangerous field variant", "4128")
        self.asteroid_property_flags_cb.addItem("16466 - Gas pocket / special field variant", "16466")
        self.asteroid_property_flags_cb.addItem("131072 - Hidden / helper zone", "131072")
        self.asteroid_property_flags_cb.addItem("0 - No flag", "0")
        self.asteroid_property_flags_cb.setCurrentIndex(0)
        configure_contains_completer(self.asteroid_property_flags_cb)
        self._asteroid_property_flags_row = layout.rowCount()
        layout.addRow("Property Flags:", self.asteroid_property_flags_cb)

        self.asteroid_visit_cb = QComboBox()
        self.asteroid_visit_cb.setEditable(True)
        self.asteroid_visit_cb.addItem("32 - Standard asteroid field", "32")
        self.asteroid_visit_cb.addItem("36 - Standard variant, often debris/alt field", "36")
        self.asteroid_visit_cb.addItem("128 - Hidden / helper zone", "128")
        self.asteroid_visit_cb.addItem("0 - No special visit flags", "0")
        self.asteroid_visit_cb.setCurrentIndex(0)
        configure_contains_completer(self.asteroid_visit_cb)
        self._asteroid_visit_row = layout.rowCount()
        layout.addRow("Visit:", self.asteroid_visit_cb)

        self.asteroid_sort_spin = QDoubleSpinBox()
        self.asteroid_sort_spin.setRange(0.0, 999.5)
        self.asteroid_sort_spin.setDecimals(1)
        self.asteroid_sort_spin.setSingleStep(0.5)
        self.asteroid_sort_spin.setValue(99.0)
        self._asteroid_sort_row = layout.rowCount()
        layout.addRow("Sort:", self.asteroid_sort_spin)

        self.asteroid_spacedust_cb = QComboBox()
        self.asteroid_spacedust_cb.setEditable(True)
        self.asteroid_spacedust_cb.addItems(self._nebula_spacedust_options)
        self.asteroid_spacedust_cb.setCurrentText("asteroiddust")
        configure_contains_completer(self.asteroid_spacedust_cb)
        self._asteroid_spacedust_row = layout.rowCount()
        layout.addRow("Space Dust:", self.asteroid_spacedust_cb)

        self.asteroid_spacedust_particles_spin = QSpinBox()
        self.asteroid_spacedust_particles_spin.setRange(0, 500)
        self.asteroid_spacedust_particles_spin.setValue(50)
        self._asteroid_spacedust_particles_row = layout.rowCount()
        layout.addRow("Dust Max Particles:", self.asteroid_spacedust_particles_spin)

        self.asteroid_comment_edit = QLineEdit()
        self.asteroid_comment_edit.setPlaceholderText("z.B. Devon Field")
        self._asteroid_comment_row = layout.rowCount()
        layout.addRow("Comment:", self.asteroid_comment_edit)

        self.visit_cb = QComboBox()
        self.visit_cb.setEditable(True)
        self.visit_cb.addItem("32 - Standard nebula (vanilla-typisch)", "32")
        self.visit_cb.addItem("36 - Vanilla-Variante (zusätzliches Flag, genaue Bedeutung unklar)", "36")
        self.visit_cb.addItem("0 - Keine speziellen Visit-Flags", "0")
        self.visit_cb.addItem("128 - Versteckt / nicht auf Karte zeigen", "128")
        self.visit_cb.setCurrentIndex(0)
        configure_contains_completer(self.visit_cb)
        self._visit_row = layout.rowCount()
        layout.addRow("Visit:", self.visit_cb)

        self.spacedust_cb = QComboBox()
        self.spacedust_cb.setEditable(True)
        self.spacedust_cb.addItems(self._nebula_spacedust_options)
        self.spacedust_cb.setCurrentText("attractdust_purple")
        configure_contains_completer(self.spacedust_cb)
        self._spacedust_row = layout.rowCount()
        layout.addRow("Space Dust:", self.spacedust_cb)

        self.spacedust_particles_spin = QSpinBox()
        self.spacedust_particles_spin.setRange(0, 500)
        self.spacedust_particles_spin.setValue(50)
        self._spacedust_particles_row = layout.rowCount()
        layout.addRow("Dust Max Particles:", self.spacedust_particles_spin)

        self.interference_spin = QDoubleSpinBox()
        self.interference_spin.setRange(0.0, 1.0)
        self.interference_spin.setDecimals(2)
        self.interference_spin.setSingleStep(0.05)
        self.interference_spin.setValue(0.6)
        self._interference_row = layout.rowCount()
        layout.addRow("Interference:", self.interference_spin)

        self.property_flags_cb = QComboBox()
        self.property_flags_cb.setEditable(True)
        self.property_flags_cb.addItem("32768 - Standard nebula flag", "32768")
        self.property_flags_cb.addItem("49152 - Vanilla variant", "49152")
        self.property_flags_cb.addItem("16384 - Rare vanilla variant", "16384")
        self.property_flags_cb.addItem("0 - No flag", "0")
        self.property_flags_cb.setCurrentIndex(0)
        configure_contains_completer(self.property_flags_cb)
        self._property_flags_row = layout.rowCount()
        layout.addRow("Property Flags:", self.property_flags_cb)

        self.fog_color = QColor(60, 55, 120)
        self.fog_color_btn = QPushButton(self._fog_color_label())
        self.fog_color_btn.clicked.connect(self._choose_fog_color)
        self._apply_fog_button_style()
        self._fog_color_row = layout.rowCount()
        layout.addRow("Fog Color:", self.fog_color_btn)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)
        self._on_type_changed("Asteroid Field")

    def _on_type_changed(self, typ: str):
        self.ref_cb.clear()
        if typ == "Asteroid Field":
            self.ref_cb.addItems(self._ast_list)
            music_values = [
                "zone_field_asteroid_rock",
                "zone_field_asteroid_ice",
                "zone_field_asteroid_mine",
                "zone_field_asteroid_lava",
                "zone_field_asteroid_nomad",
                "zone_field_debris",
                "zone_field_mine",
                "zone_field_ice",
                "zone_badlands",
            ]
        else:
            self.ref_cb.addItems(self._neb_list)
            music_values = [
                "zone_nebula_crow",
                "zone_nebula_barrier",
                "zone_nebula_walker",
                "zone_nebula_dmatter",
                "zone_nebula_nomad",
                "zone_nebula_edge",
            ]
        for item in self._zone_music_options:
            if item not in music_values:
                music_values.append(item)
        current_music = self.music_cb.currentText().strip()
        self.music_cb.blockSignals(True)
        self.music_cb.clear()
        self.music_cb.addItem("")
        self.music_cb.addItems(music_values)
        if current_music and current_music in music_values:
            self.music_cb.setCurrentText(current_music)
        else:
            self.music_cb.setCurrentText("")
        self.music_cb.blockSignals(False)
        self._set_asteroid_fields_visible(typ == "Asteroid Field")
        self._set_nebula_fields_visible(typ == "Nebula")

    def _set_asteroid_fields_visible(self, visible: bool) -> None:
        for row in (
            self._asteroid_property_flags_row,
            self._asteroid_visit_row,
            self._asteroid_sort_row,
            self._asteroid_spacedust_row,
            self._asteroid_spacedust_particles_row,
            self._asteroid_comment_row,
        ):
            label_item = self.layout().itemAt(row, QFormLayout.LabelRole)
            field_item = self.layout().itemAt(row, QFormLayout.FieldRole)
            if label_item and label_item.widget():
                label_item.widget().setVisible(visible)
            if field_item and field_item.widget():
                field_item.widget().setVisible(visible)

    def _set_nebula_fields_visible(self, visible: bool) -> None:
        for row in (
            self._visit_row,
            self._spacedust_row,
            self._spacedust_particles_row,
            self._interference_row,
            self._property_flags_row,
            self._fog_color_row,
        ):
            label_item = self.layout().itemAt(row, QFormLayout.LabelRole)
            field_item = self.layout().itemAt(row, QFormLayout.FieldRole)
            if label_item and label_item.widget():
                label_item.widget().setVisible(visible)
            if field_item and field_item.widget():
                field_item.widget().setVisible(visible)

    def _fog_color_label(self) -> str:
        return f"{self.fog_color.red()}, {self.fog_color.green()}, {self.fog_color.blue()}"

    def _apply_fog_button_style(self) -> None:
        self.fog_color_btn.setText(self._fog_color_label())
        self.fog_color_btn.setStyleSheet(
            "text-align:left; padding:4px 8px;"
            f"background-color: rgb({self.fog_color.red()}, {self.fog_color.green()}, {self.fog_color.blue()});"
            "color: white;"
        )

    def _choose_fog_color(self) -> None:
        chosen = QColorDialog.getColor(self.fog_color, self, "Nebula Fog Color")
        if chosen.isValid():
            self.fog_color = chosen
            self._apply_fog_button_style()


# ══════════════════════════════════════════════════════════════════════
#  SimpleZoneDialog – Einfache Zone erstellen
# ══════════════════════════════════════════════════════════════════════

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

class BaseCreationDialog(QDialog):
    """Dialog zum Erstellen einer neuen Base (Station/Planet-Basis).

    Sammelt alle nötigen Parameter für:
    - [Object] im System-INI
    - [BaseInfo] + [Room] in der Base-INI
    - Room-INI-Dateien
    - [Base] in universe.ini
    """

    ROOM_CHOICES = [
        ("Deck", True),
        ("Bar", True),
        ("Trader", True),
        ("Equipment", False),
        ("ShipDealer", False),
    ]
    ROOM_SCENE_PRESETS = {
        "deck": "Scripts\\Bases\\Li_08_Deck_ambi_int_01.thn",
        "bar": "Scripts\\Bases\\Li_09_bar_ambi_int_s020x.thn",
        "trader": "Scripts\\Bases\\Li_01_Trader_ambi_int_01.thn",
        "equipment": "Scripts\\Bases\\Li_01_equipment_ambi_int_01.thn",
        "shipdealer": "Scripts\\Bases\\Li_01_shipdealer_ambi_int_01.thn",
        "cityscape": "Scripts\\Bases\\Li_01_cityscape_ambi_day_01.thn",
    }
    ROLE_OPTIONS_BY_ROOM = {
        "bar": ["bartender", "BarFly", "NewsVendor"],
        "trader": ["trader"],
        "equipment": ["Equipment"],
        "shipdealer": ["ShipDealer"],
        "deck": ["ShipDealer", "trader", "Equipment", "bartender"],
        "cityscape": ["trader"],
    }

    PILOT_CHOICES = [
        "pilot_solar_easiest",
        "pilot_solar_easy",
        "pilot_solar_hard",
        "pilot_solar_hardest",
    ]

    VOICE_CHOICES = [
        "atc_leg_m01",
        "atc_leg_f01",
        "atc_leg_f01a",
        "mc_leg_m01",
        "pilot_f_leg_m01",
        "pilot_f_leg_f01",
        "pilot_f_leg_f01a",
        "pilot_f_leg_f01b",
        "pilot_f_leg_m01b",
        "pilot_f_mil_m01",
        "pilot_f_mil_m01a",
        "pilot_f_mil_m01b",
        "pilot_f_mil_m02",
        "pilot_f_mil_m02a",
        "pilot_f_mil_m02b",
        "pilot_f_ill_m01",
        "pilot_f_ill_m01a",
        "pilot_f_ill_m01b",
        "pilot_f_ill_m02",
        "pilot_f_ill_m02a",
        "pilot_f_ill_m02b",
        "pilot_c_leg_m01",
        "pilot_c_leg_m01a",
        "pilot_c_leg_m01b",
        "pilot_c_ill_m01",
        "pilot_c_ill_m01a",
        "pilot_c_ill_m01b",
        "pilot_c_ill_m02",
        "pilot_c_ill_m02a",
        "pilot_c_ill_m02b",
        "pilot_c_ill_f01",
        "pilot_c_ill_f01a",
        "pilot_c_ill_f01b",
    ]

    def __init__(
        self,
        parent,
        system_nick: str,
        archetypes: list[str],
        loadouts: list[str],
        factions: list[str],
        existing_bases: list[str] | list[tuple[str, str]] | None = None,
        next_base_num: int = 1,
        pilots: list[str] | None = None,
        voices: list[str] | None = None,
        heads: list[str] | None = None,
        bodies: list[str] | None = None,
        template_room_details: dict[str, list[dict]] | None = None,
        template_room_npcs: dict[str, dict[str, list[str]]] | None = None,
        template_virtual_targets: dict[str, list[str]] | None = None,
        template_data_provider: Callable[[str], dict[str, object]] | None = None,
        ids_info_template_xml: str = "",
        default_loadouts_by_archetype: dict[str, str] | None = None,
        market_equip_groups: dict[str, list[str]] | None = None,
        market_misc_goods: list[list[str]] | None = None,
        market_commodity_nicks: list[str] | None = None,
        market_commodity_goods: list[list[str]] | None = None,
        market_commodity_prices: dict[str, int] | None = None,
        market_ship_nicks: list[str] | None = None,
        market_ship_goods: list[list[str]] | None = None,
        market_display_names: dict[str, str] | None = None,
        market_base_prices: dict[str, int] | None = None,
        market_shipdealer_enabled: bool = True,
        default_faction: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.base_create"))
        self.setMinimumSize(980, 760)
        self._updating_rooms = False
        self._ids_info_template_xml = str(ids_info_template_xml or "").strip()
        self._default_loadouts_by_archetype = {
            str(k or "").strip().lower(): str(v or "").strip()
            for k, v in dict(default_loadouts_by_archetype or {}).items()
            if str(k or "").strip() and str(v or "").strip()
        }
        self._market_display_names = {
            str(k or "").strip().lower(): str(v or "").strip()
            for k, v in dict(market_display_names or {}).items()
            if str(k or "").strip()
        }
        self._template_data_provider = template_data_provider
        self._template_load_attempted: set[str] = set()
        self._market_tabs_enabled = bool(
            market_equip_groups is not None
            or market_commodity_nicks is not None
            or market_ship_nicks is not None
        )
        self._market_shipdealer_enabled = bool(market_shipdealer_enabled)
        self._market_commodity_prices = dict(market_commodity_prices or {})
        self._market_base_prices = {
            str(k or "").strip().lower(): int(v or 0)
            for k, v in dict(market_base_prices or {}).items()
            if str(k or "").strip()
        }
        self._market_ship_market_data: dict[str, list[str]] = {}
        self._faction_display_options: list[str] = []
        self._faction_display_by_nick: dict[str, str] = {}
        for f in list(factions or []):
            txt = str(f or "").strip()
            if not txt:
                continue
            if txt not in self._faction_display_options:
                self._faction_display_options.append(txt)
            nick = txt.split(" - ", 1)[0].strip() if " - " in txt else txt
            if nick and nick.lower() not in self._faction_display_by_nick:
                self._faction_display_by_nick[nick.lower()] = txt
        self._template_room_details = {
            str(k or "").strip().lower(): list(v or [])
            for k, v in (template_room_details or {}).items()
            if str(k or "").strip()
        }
        self._template_room_npcs = {
            str(k or "").strip().lower(): {}
            for k, _v in (template_room_npcs or {}).items()
            if str(k or "").strip()
        }
        for k, v in (template_room_npcs or {}).items():
            base_key = str(k or "").strip().lower()
            if not base_key or not isinstance(v, dict):
                continue
            room_map: dict[str, list[dict[str, str]]] = {}
            for rk, rv in dict(v or {}).items():
                room_key = str(rk or "").strip().lower()
                if not room_key:
                    continue
                rows: list[dict[str, str]] = []
                for item in list(rv or []):
                    if isinstance(item, dict):
                        npc_nick = str(item.get("nickname", "") or "").strip()
                        name_text = str(item.get("name_text", "") or "").strip()
                    else:
                        npc_nick = str(item or "").strip()
                        name_text = npc_nick
                    if not npc_nick:
                        continue
                    rep = str(item.get("reputation", "") if isinstance(item, dict) else "").strip()
                    aff = str(item.get("affiliation", "") if isinstance(item, dict) else "").strip()
                    role = str(item.get("role", "") if isinstance(item, dict) else "").strip()
                    rows.append(
                        {
                            "nickname": npc_nick,
                            "name_text": name_text or npc_nick,
                            "reputation": rep,
                            "affiliation": aff,
                            "role": role,
                        }
                    )
                if rows:
                    room_map[room_key] = rows
            self._template_room_npcs[base_key] = room_map
        self._template_virtual_targets = {
            str(k or "").strip().lower(): [
                str(x or "").strip().lower()
                for x in list(v or [])
                if str(x or "").strip()
            ]
            for k, v in (template_virtual_targets or {}).items()
            if str(k or "").strip()
        }
        self._template_load_attempted.update(self._template_room_details.keys())
        self._template_load_attempted.update(self._template_room_npcs.keys())
        self._template_load_attempted.update(self._template_virtual_targets.keys())
        self._scene_options_by_room: dict[str, list[str]] = {}
        for room, scene in self.ROOM_SCENE_PRESETS.items():
            self._scene_options_by_room.setdefault(room, [])
            if scene not in self._scene_options_by_room[room]:
                self._scene_options_by_room[room].append(scene)
        for _base_key, rows in self._template_room_details.items():
            for d in rows:
                room = str(d.get("room", "") or "").strip().lower()
                scene = str(d.get("scene", "") or "").strip()
                if not room or not scene:
                    continue
                lst = self._scene_options_by_room.setdefault(room, [])
                if scene not in lst:
                    lst.append(scene)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QFormLayout(content)
        self._main_form_layout = layout
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

        sys_upper = system_nick.upper() if system_nick else ""
        num_str = f"{next_base_num:02d}"

        # --- Basis-Infos ---
        grp_base = QGroupBox(tr("dlg.grp_base"))
        gl_base = QFormLayout(grp_base)

        self.base_nick_edit = QLineEdit(f"{sys_upper}_{num_str}_Base")
        gl_base.addRow("Base Nickname:", self.base_nick_edit)

        self.obj_nick_edit = QLineEdit(f"{sys_upper}_{num_str}")
        gl_base.addRow(tr("dlg.obj_nickname"), self.obj_nick_edit)

        self.ids_name_edit = QLineEdit()
        self.ids_name_edit.setPlaceholderText("Name")
        gl_base.addRow("Name:", self.ids_name_edit)

        self.ids_info_preview = QTextEdit()
        self.ids_info_preview.setReadOnly(True)
        self.ids_info_preview.setMinimumHeight(130)
        self.ids_info_preview.setLineWrapMode(QTextEdit.WidgetWidth)
        self.ids_info_preview.setPlainText(self._xml_to_plain_preview(self._ids_info_template_xml))
        gl_base.addRow("ids_info (Template Li01_03_Base):", self.ids_info_preview)

        layout.addRow(grp_base)

        # --- Objekt-Parameter ---
        grp_obj = QGroupBox(tr("dlg.grp_space_object"))
        gl_obj = QFormLayout(grp_obj)

        all_archs = list(dict.fromkeys([str(a).strip() for a in archetypes if str(a).strip()]))
        self.arch_cb = QComboBox()
        self.arch_cb.setEditable(True)
        self.arch_cb.addItems(all_archs)
        gl_obj.addRow(tr("lbl.archetype"), self.arch_cb)

        self.loadout_cb = QComboBox()
        self.loadout_cb.setEditable(True)
        self.loadout_cb.setInsertPolicy(QComboBox.NoInsert)
        self.loadout_cb.addItem("")
        self.loadout_cb.addItems(loadouts)
        loadout_completer = QCompleter(self.loadout_cb.model(), self.loadout_cb)
        loadout_completer.setCaseSensitivity(Qt.CaseInsensitive)
        loadout_completer.setFilterMode(Qt.MatchContains)
        loadout_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.loadout_cb.setCompleter(loadout_completer)
        gl_obj.addRow("Loadout:", self.loadout_cb)

        self.faction_cb = QComboBox()
        self.faction_cb.setEditable(True)
        self.faction_cb.addItem("")
        self.faction_cb.addItems(factions)
        configure_contains_completer(self.faction_cb)
        if str(default_faction or "").strip():
            self.faction_cb.setCurrentText(str(default_faction).strip())
        gl_obj.addRow("Reputation:", self.faction_cb)

        self.pilot_cb = QComboBox()
        self.pilot_cb.setEditable(True)
        pilot_list = list(dict.fromkeys(self.PILOT_CHOICES + (pilots or [])))
        pilot_list = [p for p in pilot_list if p.lower().startswith("pilot_solar")]
        self.pilot_cb.addItems(pilot_list)
        self.pilot_cb.setCurrentText("pilot_solar_easiest")
        gl_obj.addRow("Pilot:", self.pilot_cb)

        self.voice_cb = QComboBox()
        self.voice_cb.setEditable(True)
        voice_list = list(dict.fromkeys(self.VOICE_CHOICES + (voices or [])))
        self.voice_cb.addItem("")
        self.voice_cb.addItems(voice_list)
        self.voice_cb.setCurrentText("atc_leg_m01")
        gl_obj.addRow("Voice:", self.voice_cb)

        # Space Costume: Head + Body Dropdowns
        costume_grp = QGroupBox(tr("dlg.grp_space_costume"))
        costume_layout = QFormLayout(costume_grp)
        self.head_cb = QComboBox()
        self.head_cb.setEditable(True)
        self.head_cb.addItem("")
        if heads:
            self.head_cb.addItems(heads)
        else:
            self.head_cb.addItems(["benchmark_male_head", "benchmark_female_head"])
        self.head_cb.setCurrentText("benchmark_male_head")
        costume_layout.addRow("Head:", self.head_cb)

        self.body_cb = QComboBox()
        self.body_cb.setEditable(True)
        self.body_cb.addItem("")
        if bodies:
            self.body_cb.addItems(bodies)
        else:
            self.body_cb.addItems(["benchmark_male_body", "benchmark_female_body"])
        self.body_cb.setCurrentText("benchmark_male_body")
        costume_layout.addRow("Body:", self.body_cb)
        gl_obj.addRow(costume_grp)

        layout.addRow(grp_obj)
        self.arch_cb.currentTextChanged.connect(self._on_archetype_changed)
        self._on_archetype_changed(self.arch_cb.currentText())

        # --- Rooms ---
        grp_rooms = QGroupBox(tr("dlg.grp_rooms"))
        gl_rooms = QFormLayout(grp_rooms)

        self.template_cb = QComboBox()
        self.template_cb.setEditable(True)
        self.template_cb.addItem("")
        if existing_bases:
            for item in existing_bases:
                if isinstance(item, tuple) and len(item) >= 2:
                    label = str(item[0] or "").strip()
                    nick = str(item[1] or "").strip()
                    if label and nick:
                        self.template_cb.addItem(label, nick)
                else:
                    txt = str(item or "").strip()
                    if txt:
                        self.template_cb.addItem(txt, txt)
        self.template_cb.setToolTip(tr("dlg.copy_rooms_tip"))
        gl_rooms.addRow("Room Template kopieren:", self.template_cb)

        self.copy_npcs_cb = QCheckBox("Copy NPCs")
        self.copy_npcs_cb.setChecked(True)
        gl_rooms.addRow("", self.copy_npcs_cb)

        self.randomize_npc_appearance_cb = QCheckBox("Random NPC head/body")
        self.randomize_npc_appearance_cb.setChecked(False)
        gl_rooms.addRow("", self.randomize_npc_appearance_cb)

        self.template_info_lbl = QLabel("")
        self.template_info_lbl.setWordWrap(True)
        self.template_info_lbl.setStyleSheet("color: #9aa3ad;")
        gl_rooms.addRow("", self.template_info_lbl)

        self.room_table = QTableWidget(0, 3)
        self.room_table.setHorizontalHeaderLabels(["Use", "Room", "Scene"])
        self.room_table.verticalHeader().setVisible(False)
        self.room_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.room_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.room_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        gl_rooms.addRow(self.room_table)
        self.room_table.itemChanged.connect(self._on_room_table_item_changed)

        self._room_npc_tables: dict[str, QTableWidget] = {}
        self._room_npc_panels: dict[str, QWidget] = {}
        self.room_npc_widget = QWidget()
        self.room_npc_layout = QVBoxLayout(self.room_npc_widget)
        self.room_npc_layout.setContentsMargins(0, 0, 0, 0)
        self.room_npc_layout.setSpacing(6)
        self.room_npc_tabs = QTabWidget()
        self.room_npc_layout.addWidget(self.room_npc_tabs)
        gl_rooms.addRow("NPCs pro Raum:", self.room_npc_widget)

        self._reset_room_rows_to_defaults()

        self.start_room_cb = QComboBox()
        gl_rooms.addRow(tr("dlg.start_room"), self.start_room_cb)

        self.price_var_spin = QDoubleSpinBox()
        self.price_var_spin.setRange(0.0, 1.0)
        self.price_var_spin.setSingleStep(0.05)
        self.price_var_spin.setDecimals(2)
        self.price_var_spin.setValue(0.15)
        gl_rooms.addRow(tr("dlg.price_variance"), self.price_var_spin)

        layout.addRow(grp_rooms)
        self.template_cb.currentIndexChanged.connect(self._on_template_changed)
        self.copy_npcs_cb.toggled.connect(self._on_template_changed)
        self._refresh_start_room_choices(preferred="Deck")
        self._on_template_changed()

        # --- Universe ---
        grp_uni = QGroupBox(tr("dlg.grp_universe_registry"))
        gl_uni = QFormLayout(grp_uni)
        self.bgcs_edit = QLineEdit()
        self.bgcs_edit.setPlaceholderText("z.B. W02bF35")
        gl_uni.addRow("BGCS_base_run_by:", self.bgcs_edit)
        layout.addRow(grp_uni)

        if self._market_tabs_enabled:
            self._build_market_tabs(
                market_equip_groups or {},
                market_misc_goods or [],
                market_commodity_nicks or [],
                market_commodity_goods or [],
                market_ship_nicks or [],
                market_ship_goods or [],
            )

        # --- Buttons ---
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _on_archetype_changed(self, archetype: str):
        arch_key = str(archetype or "").strip().lower()
        if not arch_key:
            return
        default_loadout = self._default_loadouts_by_archetype.get(arch_key, "").strip()
        if not default_loadout:
            return
        self.loadout_cb.setCurrentText(default_loadout)

    def payload(self) -> dict:
        room_states = collect_room_states(
            row_count=self.room_table.rowCount(),
            room_name_at=lambda row: (
                self.room_table.item(row, 1).text().strip() if self.room_table.item(row, 1) else ""
            ),
            enabled_at=lambda row: bool(
                self.room_table.item(row, 0) and self.room_table.item(row, 0).checkState() == Qt.Checked
            ),
            scene_at=lambda row: (
                self.room_table.cellWidget(row, 2).currentText().strip()
                if isinstance(self.room_table.cellWidget(row, 2), QComboBox)
                else ""
            ),
            npc_rows_at=self._collect_room_npc_rows,
        )
        data = build_base_creation_payload(
            base_nickname=self.base_nick_edit.text().strip(),
            obj_nickname=self.obj_nick_edit.text().strip(),
            ids_name_text=self.ids_name_edit.text().strip(),
            ids_info_template_xml=self._ids_info_template_xml,
            archetype=self.arch_cb.currentText().strip(),
            loadout=self.loadout_cb.currentText().strip(),
            reputation=self.faction_cb.currentText().strip(),
            pilot=self.pilot_cb.currentText().strip(),
            voice=self.voice_cb.currentText().strip(),
            head=self.head_cb.currentText().strip(),
            body=self.body_cb.currentText().strip(),
            room_states=room_states,
            start_room=self.start_room_cb.currentText().strip(),
            price_variance=self.price_var_spin.value(),
            template_base=str(self.template_cb.currentData() or self.template_cb.currentText()).strip(),
            copy_template_npcs=bool(self.copy_npcs_cb.isChecked()),
            randomize_npc_head_body=bool(self.randomize_npc_appearance_cb.isChecked()),
            bgcs_base_run_by=self.bgcs_edit.text().strip(),
        )
        if self._market_tabs_enabled:
            data["market_misc_goods"] = self._collect_market_table_rows(self.market_equip_table, max_cols=7)
            data["market_commodities_goods"] = self._collect_market_table_rows(self.market_comm_table, max_cols=7)
            data["market_ships_goods"] = self._collect_market_ship_goods()
        return data

    @staticmethod
    def _nick_from_display(raw: str) -> str:
        txt = str(raw or "").strip()
        if not txt:
            return ""
        if " - " in txt:
            return txt.split(" - ", 1)[0].strip()
        return txt

    def _display_for_nick(self, nick: str) -> str:
        n = str(nick or "").strip()
        if not n:
            return ""
        ingame = self._market_display_names.get(n.lower(), "").strip()
        if ingame:
            return f"{n} - {ingame}"
        return n

    def _build_market_tabs(
        self,
        equip_groups: dict[str, list[str]],
        misc_goods: list[list[str]],
        commodity_nicks: list[str],
        commodity_goods: list[list[str]],
        ship_nicks: list[str],
        ship_goods: list[list[str]],
    ):
        grp_market = QGroupBox("Market")
        v_market = QVBoxLayout(grp_market)
        self.market_tabs = QTabWidget()
        v_market.addWidget(self.market_tabs)
        self._build_market_equip_tab(equip_groups, misc_goods)
        self._build_market_commodity_tab(commodity_nicks, commodity_goods)
        self._build_market_ship_tab(ship_nicks, ship_goods)
        if isinstance(getattr(self, "_main_form_layout", None), QFormLayout):
            self._main_form_layout.addRow(grp_market)
        else:
            self.layout().addWidget(grp_market)

    def _build_market_equip_tab(self, equip_groups: dict[str, list[str]], equip_goods: list[list[str]]):
        tab = QWidget()
        hl = QHBoxLayout(tab)
        left_v = QVBoxLayout()
        left_v.addWidget(QLabel(tr("dlg.available")))
        filt = QLineEdit()
        filt.setPlaceholderText("Filter …")
        left_v.addWidget(filt)
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        left_v.addWidget(tree)
        hl.addLayout(left_v, 1)
        mid = QVBoxLayout()
        mid.addStretch()
        btn_r = QPushButton("→")
        btn_l = QPushButton("←")
        mid.addWidget(btn_r)
        mid.addWidget(btn_l)
        mid.addStretch()
        hl.addLayout(mid)
        right_v = QVBoxLayout()
        right_v.addWidget(QLabel(tr("dlg.on_this_base")))
        cols = [
            "Nickname",
            "Level",
            "Rep",
            "Min-Stock",
            "Max-Stock",
            tr("dlg.col_sell_buy"),
            tr("dlg.col_price_multi"),
            tr("dlg.col_base_price"),
            tr("dlg.col_end_price"),
        ]
        table = QTableWidget(0, len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        right_v.addWidget(table)
        hl.addLayout(right_v, 2)
        self.market_equip_tree = tree
        self.market_equip_table = table

        def _set_price_cells(row: int, nick: str, multi_str: str):
            base_price = int(self._market_base_prices.get(str(nick or "").strip().lower(), 0) or 0)
            bp = QTableWidgetItem(str(base_price))
            bp.setFlags(bp.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 7, bp)
            try:
                multi = float(multi_str)
            except Exception:
                multi = 1.0
            ep = QTableWidgetItem(str(round(base_price * multi)))
            ep.setFlags(ep.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 8, ep)

        def _recalc(row: int, col: int):
            if col not in (0, 6):
                return
            it_n = table.item(row, 0)
            it_m = table.item(row, 6)
            if not it_n:
                return
            nick = str(it_n.data(Qt.UserRole) or "").strip() or self._nick_from_display(it_n.text())
            _set_price_cells(row, nick, it_m.text().strip() if it_m else "1")

        table.cellChanged.connect(_recalc)

        assigned: set[str] = set()
        table.blockSignals(True)
        for row in equip_goods:
            if not row:
                continue
            nick = str(row[0]).strip()
            if not nick:
                continue
            assigned.add(nick.lower())
            r = table.rowCount()
            table.insertRow(r)
            it = QTableWidgetItem(self._display_for_nick(nick))
            it.setData(Qt.UserRole, nick)
            table.setItem(r, 0, it)
            defaults = ["0", "-1", "10", "10", "0", "1"]
            # Editable MarketGood fields are cols 1..6; price columns are derived.
            for c in range(1, 7):
                val = row[c].strip() if c < len(row) else defaults[c - 1]
                table.setItem(r, c, QTableWidgetItem(val))
            _set_price_cells(r, nick, row[6].strip() if len(row) > 6 else "1")
        table.blockSignals(False)
        table.resizeColumnToContents(0)

        for grp, nicks in equip_groups.items():
            g = QTreeWidgetItem(tree, [grp])
            f = g.font(0)
            f.setBold(True)
            g.setFont(0, f)
            g.setFlags(g.flags() & ~Qt.ItemIsSelectable)
            for nick in nicks:
                n = str(nick).strip()
                if not n or n.lower() in assigned:
                    continue
                c = QTreeWidgetItem(g, [self._display_for_nick(n)])
                c.setData(0, Qt.UserRole, n)

        def _filter(text: str):
            t = text.lower()
            for gi in range(tree.topLevelItemCount()):
                group = tree.topLevelItem(gi)
                any_vis = False
                for ci in range(group.childCount()):
                    ch = group.child(ci)
                    vis = t in ch.text(0).lower()
                    ch.setHidden(not vis)
                    any_vis = any_vis or vis
                group.setHidden(not any_vis)
        filt.textChanged.connect(_filter)

        def _add_nick(nick: str):
            if not nick:
                return
            r = table.rowCount()
            table.insertRow(r)
            it = QTableWidgetItem(self._display_for_nick(nick))
            it.setData(Qt.UserRole, nick)
            table.setItem(r, 0, it)
            for c, val in enumerate(["0", "-1", "10", "10", "0", "1"], start=1):
                table.setItem(r, c, QTableWidgetItem(val))
            _set_price_cells(r, nick, "1")
            table.resizeColumnToContents(0)

        def _move_right():
            for it in tree.selectedItems():
                nick = str(it.data(0, Qt.UserRole) or "").strip()
                if not nick:
                    continue
                _add_nick(nick)
                p = it.parent()
                if p:
                    p.removeChild(it)
        def _move_left():
            rows = sorted({idx.row() for idx in table.selectedIndexes()}, reverse=True)
            for r in rows:
                it = table.item(r, 0)
                nick = str(it.data(Qt.UserRole) if it else "").strip()
                txt = it.text().strip() if it else ""
                if not nick and txt:
                    nick = self._nick_from_display(txt)
                if nick:
                    placed = False
                    for gi in range(tree.topLevelItemCount()):
                        g = tree.topLevelItem(gi)
                        if str(nick).lower() in {str(x).lower() for x in equip_groups.get(g.text(0), [])}:
                            ch = QTreeWidgetItem(g, [self._display_for_nick(nick)])
                            ch.setData(0, Qt.UserRole, nick)
                            placed = True
                            break
                    if not placed and tree.topLevelItemCount() > 0:
                        ch = QTreeWidgetItem(tree.topLevelItem(0), [self._display_for_nick(nick)])
                        ch.setData(0, Qt.UserRole, nick)
                table.removeRow(r)
        btn_r.clicked.connect(_move_right)
        btn_l.clicked.connect(_move_left)
        self.market_tabs.addTab(tab, "Equipment")

    def _build_market_commodity_tab(self, all_nicks: list[str], comm_goods: list[list[str]]):
        tab = QWidget()
        hl = QHBoxLayout(tab)
        left_v = QVBoxLayout()
        left_v.addWidget(QLabel(tr("dlg.available")))
        filt = QLineEdit()
        filt.setPlaceholderText("Filter …")
        left_v.addWidget(filt)
        avail = QListWidget()
        avail.setSelectionMode(QListWidget.ExtendedSelection)
        avail.setSortingEnabled(True)
        left_v.addWidget(avail)
        hl.addLayout(left_v, 1)
        mid = QVBoxLayout()
        mid.addStretch()
        btn_r = QPushButton("→")
        btn_l = QPushButton("←")
        mid.addWidget(btn_r)
        mid.addWidget(btn_l)
        mid.addStretch()
        hl.addLayout(mid)
        right_v = QVBoxLayout()
        right_v.addWidget(QLabel(tr("dlg.on_this_base")))
        cols = ["Nickname", "Level", "Rep", "Min-Stock", "Max-Stock", tr("dlg.col_sell_buy"), tr("dlg.col_price_multi"), tr("dlg.col_base_price"), tr("dlg.col_end_price")]
        table = QTableWidget(0, len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        right_v.addWidget(table)
        hl.addLayout(right_v, 2)
        self.market_comm_available = avail
        self.market_comm_table = table

        def _set_price_cells(row: int, nick: str, multi_str: str):
            base_price = int(self._market_commodity_prices.get(nick, 0) or 0)
            bp = QTableWidgetItem(str(base_price))
            bp.setFlags(bp.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 7, bp)
            try:
                multi = float(multi_str)
            except Exception:
                multi = 1.0
            ep = QTableWidgetItem(str(round(base_price * multi)))
            ep.setFlags(ep.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 8, ep)

        def _recalc(row: int, col: int):
            if col not in (0, 6):
                return
            it_n = table.item(row, 0)
            it_m = table.item(row, 6)
            if not it_n:
                return
            nick = str(it_n.data(Qt.UserRole) or "").strip()
            if not nick:
                nick = self._nick_from_display(it_n.text())
            _set_price_cells(row, nick, it_m.text().strip() if it_m else "1")

        table.cellChanged.connect(_recalc)

        assigned: set[str] = set()
        table.blockSignals(True)
        for row in comm_goods:
            if not row:
                continue
            nick = str(row[0]).strip()
            if not nick:
                continue
            assigned.add(nick.lower())
            r = table.rowCount()
            table.insertRow(r)
            it = QTableWidgetItem(self._display_for_nick(nick))
            it.setData(Qt.UserRole, nick)
            table.setItem(r, 0, it)
            defaults = ["0", "-1", "0", "0", "0", "1"]
            for c in range(1, 7):
                val = row[c].strip() if c < len(row) else defaults[c - 1]
                table.setItem(r, c, QTableWidgetItem(val))
            _set_price_cells(r, nick, row[6].strip() if len(row) > 6 else "1")
        table.blockSignals(False)
        table.resizeColumnToContents(0)

        for nick in sorted(all_nicks, key=str.lower):
            n = str(nick).strip()
            if not n or n.lower() in assigned:
                continue
            it = QListWidgetItem(self._display_for_nick(n))
            it.setData(Qt.UserRole, n)
            avail.addItem(it)

        def _filter(text: str):
            t = text.lower()
            for i in range(avail.count()):
                it = avail.item(i)
                it.setHidden(t not in it.text().lower())
        filt.textChanged.connect(_filter)

        def _add_nick(nick: str):
            r = table.rowCount()
            table.insertRow(r)
            it = QTableWidgetItem(self._display_for_nick(nick))
            it.setData(Qt.UserRole, nick)
            table.setItem(r, 0, it)
            for c, val in enumerate(["0", "-1", "0", "0", "0", "1"], start=1):
                table.setItem(r, c, QTableWidgetItem(val))
            _set_price_cells(r, nick, "1")
            table.resizeColumnToContents(0)

        def _move_right():
            table.blockSignals(True)
            for it in avail.selectedItems():
                nick = str(it.data(Qt.UserRole) or "").strip()
                if nick:
                    _add_nick(nick)
                avail.takeItem(avail.row(it))
            table.blockSignals(False)

        def _move_left():
            rows = sorted({idx.row() for idx in table.selectedIndexes()}, reverse=True)
            for r in rows:
                it = table.item(r, 0)
                nick = str(it.data(Qt.UserRole) if it else "").strip()
                if not nick and it:
                    nick = self._nick_from_display(it.text())
                if nick:
                    li = QListWidgetItem(self._display_for_nick(nick))
                    li.setData(Qt.UserRole, nick)
                    avail.addItem(li)
                table.removeRow(r)

        btn_r.clicked.connect(_move_right)
        btn_l.clicked.connect(_move_left)
        self.market_tabs.addTab(tab, "Commodities")

    def _build_market_ship_tab(self, all_ship_nicks: list[str], ship_goods: list[list[str]]):
        tab = QWidget()
        vl = QVBoxLayout(tab)
        info = QLabel(tr("dlg.max_ships"))
        info.setWordWrap(True)
        vl.addWidget(info)
        self.market_ship_combos: list[QComboBox] = []
        assigned_ships = [str(r[0]).strip() for r in ship_goods if r]
        self._market_ship_market_data = {}
        for row in ship_goods:
            if row:
                self._market_ship_market_data[str(row[0]).strip().lower()] = list(row)
        sorted_ships = sorted([str(n).strip() for n in all_ship_nicks if str(n).strip()], key=str.lower)
        for slot in range(3):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"Slot {slot + 1}:"))
            cb = QComboBox()
            cb.setEditable(True)
            cb.addItem("", "")
            for nick in sorted_ships:
                cb.addItem(self._display_for_nick(nick), nick)
            if slot < len(assigned_ships) and assigned_ships[slot]:
                want = assigned_ships[slot].strip()
                ix = cb.findData(want)
                if ix >= 0:
                    cb.setCurrentIndex(ix)
                else:
                    cb.setCurrentText(self._display_for_nick(want))
            row.addWidget(cb, 1)
            vl.addLayout(row)
            self.market_ship_combos.append(cb)
        vl.addStretch()
        if not self._market_shipdealer_enabled:
            tab.setEnabled(False)
            info.setText("Kein ShipDealer-Raum (auch nicht virtuell) erkannt. Schiff-Markt ist deaktiviert.")
        self.market_tabs.addTab(tab, "Schiffe")

    def _collect_market_table_rows(self, table: QTableWidget, max_cols: int | None = None) -> list[list[str]]:
        if not isinstance(table, QTableWidget):
            return []
        return collect_market_rows_from_cells(
            row_count=table.rowCount(),
            column_count=table.columnCount(),
            cell_text=lambda row, col: (
                table.item(row, col).text().strip() if table.item(row, col) else ""
            ),
            cell_data=lambda row, col: (
                str(table.item(row, col).data(Qt.UserRole) if table.item(row, col) else "").strip()
            ),
            normalize_first_col=self._nick_from_display,
            max_cols=max_cols,
        )

    def _collect_market_ship_goods(self) -> list[list[str]]:
        if not self._market_shipdealer_enabled:
            return [list(v) for v in self._market_ship_market_data.values()]
        selected_nicks = collect_combo_data_or_texts(
            combos=getattr(self, "market_ship_combos", []),
            combo_data=lambda combo: combo.currentData() if isinstance(combo, QComboBox) else "",
            combo_text=lambda combo: combo.currentText() if isinstance(combo, QComboBox) else "",
            normalize_text=self._nick_from_display,
        )
        return collect_ship_market_goods(selected_nicks, self._market_ship_market_data)

    @staticmethod
    def _split_npc_list(raw: str) -> list[str]:
        return split_npc_list(raw)

    @staticmethod
    def _xml_to_plain_preview(raw_xml: str) -> str:
        return xml_to_plain_preview(raw_xml)

    @classmethod
    def _default_scene_for_room(cls, room_name: str) -> str:
        return default_scene_for_room(room_name, cls.ROOM_SCENE_PRESETS)

    def _scene_options_for_room(self, room_name: str) -> list[str]:
        return scene_options_for_room(room_name, self._scene_options_by_room, self.ROOM_SCENE_PRESETS)

    def _find_room_row(self, room_name: str) -> int:
        target = str(room_name or "").strip().lower()
        for r in range(self.room_table.rowCount()):
            item = self.room_table.item(r, 1)
            if item and item.text().strip().lower() == target:
                return r
        return -1

    def _set_room_row(self, room_name: str, enabled: bool, scene: str, npc_rows: list[dict] | None = None):
        state = build_room_row_state(
            room_name=room_name,
            enabled=enabled,
            scene=scene,
            scene_options=self._scene_options_for_room(room_name),
            default_scene=self._default_scene_for_room(room_name),
        )
        room_txt = str(state["room_name"])
        if not room_txt:
            return
        row = self._find_room_row(room_txt)
        if row < 0:
            row = self.room_table.rowCount()
            self.room_table.insertRow(row)

            check_item = QTableWidgetItem("")
            check_item.setFlags((check_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled) & ~Qt.ItemIsEditable)
            self.room_table.setItem(row, 0, check_item)

            room_item = QTableWidgetItem(room_txt)
            room_item.setFlags(room_item.flags() & ~Qt.ItemIsEditable)
            self.room_table.setItem(row, 1, room_item)

            scene_cb = QComboBox()
            scene_cb.setEditable(False)
            for preset in list(state["scene_options"]):
                scene_cb.addItem(preset)
            self.room_table.setCellWidget(row, 2, scene_cb)

        check_item = self.room_table.item(row, 0)
        room_item = self.room_table.item(row, 1)
        if room_item:
            room_item.setText(room_txt)
        if check_item:
            check_item.setCheckState(Qt.Checked if bool(state["enabled"]) else Qt.Unchecked)

        scene_cb = self.room_table.cellWidget(row, 2)
        if isinstance(scene_cb, QComboBox):
            scene_cb.clear()
            for preset in list(state["scene_options"]):
                scene_cb.addItem(preset)
            scene_val = str(state["selected_scene"])
            if scene_cb.findText(scene_val) >= 0:
                scene_cb.setCurrentText(scene_val)
            elif scene_cb.count() > 0:
                scene_cb.setCurrentIndex(0)

        self._set_room_npc_rows(room_txt, list(npc_rows or []))

    def _clear_room_npc_panels(self):
        self.room_npc_tabs.clear()
        self._room_npc_tables.clear()
        self._room_npc_panels.clear()

    def _active_room_order(self) -> list[str]:
        return collect_active_room_names(
            row_count=self.room_table.rowCount(),
            room_name_at=lambda row: (
                self.room_table.item(row, 1).text().strip() if self.room_table.item(row, 1) else ""
            ),
            enabled_at=lambda row: bool(
                self.room_table.item(row, 0) and self.room_table.item(row, 0).checkState() == Qt.Checked
            ),
        )

    def _refresh_room_npc_tabs(self):
        current_room = (
            self.room_npc_tabs.tabText(self.room_npc_tabs.currentIndex())
            if self.room_npc_tabs.count() > 0
            else ""
        )
        state = build_room_npc_tab_state(
            active_rooms=self._active_room_order(),
            current_room=current_room,
        )
        while self.room_npc_tabs.count() > 0:
            self.room_npc_tabs.removeTab(0)
        for room_name in list(state["active_rooms"]):
            key = room_name.lower()
            panel = self._room_npc_panels.get(key)
            if panel is None:
                self._ensure_room_npc_table(room_name)
                panel = self._room_npc_panels.get(key)
            if panel is not None:
                self.room_npc_tabs.addTab(panel, room_name)
        selected_room = str(state["selected_room"])
        if selected_room:
            for idx in range(self.room_npc_tabs.count()):
                if self.room_npc_tabs.tabText(idx).strip().lower() == selected_room.lower():
                    self.room_npc_tabs.setCurrentIndex(idx)
                    break

    def _ensure_room_npc_table(self, room_name: str) -> QTableWidget:
        key = str(room_name or "").strip().lower()
        if key in self._room_npc_tables:
            return self._room_npc_tables[key]
        panel = QWidget()
        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(0, 0, 0, 0)
        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Nickname", "Name", "Reputation", "Affiliation", "Role"])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        table.setColumnWidth(0, 260)
        table.horizontalHeader().setMinimumSectionSize(120)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        vbox.addWidget(table)
        btn_row = QWidget()
        btn_l = QHBoxLayout(btn_row)
        btn_l.setContentsMargins(0, 0, 0, 0)
        btn_add = QPushButton("NPC +")
        btn_del = QPushButton("NPC -")
        btn_l.addWidget(btn_add)
        btn_l.addWidget(btn_del)
        btn_l.addStretch(1)
        vbox.addWidget(btn_row)
        self._room_npc_panels[key] = panel
        self._room_npc_tables[key] = table

        def _add_row():
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(""))
            table.setItem(row, 1, QTableWidgetItem(""))
            base_rep = self._base_reputation_display_default()
            table.setCellWidget(row, 2, self._make_faction_combo(base_rep))
            table.setCellWidget(row, 3, self._make_faction_combo(base_rep))
            table.setCellWidget(row, 4, self._make_role_combo(self._default_role_for_room(room_name), room_name))
            table.setCurrentCell(row, 0)

        def _del_row():
            row = table.currentRow()
            if row >= 0:
                table.removeRow(row)

        btn_add.clicked.connect(_add_row)
        btn_del.clicked.connect(_del_row)
        self._refresh_room_npc_tabs()
        return table

    def _set_room_npc_rows(self, room_name: str, rows: list[dict]):
        table = self._ensure_room_npc_table(room_name)
        table.setRowCount(0)
        base_rep = self._base_reputation_display_default()
        display_rows = build_room_npc_display_rows(
            rows=list(rows or []),
            faction_display_from_any_fn=self._faction_display_from_any,
            default_reputation_display=base_rep,
            normalize_role=self._normalize_role_for_room,
            default_role=self._default_role_for_room,
            room_name=room_name,
        )
        for row in display_rows:
            nick = str(row["nickname"])
            name_text = str(row["name_text"])
            ridx = table.rowCount()
            table.insertRow(ridx)
            nick_item = QTableWidgetItem(nick)
            extra_data = {
                key: str(row.get(key, "")).strip()
                for key in ("body", "head", "lefthand", "righthand")
                if str(row.get(key, "")).strip()
            }
            if extra_data:
                nick_item.setData(Qt.UserRole, extra_data)
            table.setItem(ridx, 0, nick_item)
            table.setItem(ridx, 1, QTableWidgetItem(name_text))
            table.setCellWidget(ridx, 2, self._make_faction_combo(str(row["reputation_display"])))
            table.setCellWidget(ridx, 3, self._make_faction_combo(str(row["affiliation_display"])))
            table.setCellWidget(
                ridx,
                4,
                self._make_role_combo(str(row["role_display"]), room_name),
            )

    def _collect_room_npc_rows(self, room_name: str) -> list[dict[str, str]]:
        key = str(room_name or "").strip().lower()
        table = self._room_npc_tables.get(key)
        if not isinstance(table, QTableWidget):
            return []
        return collect_room_npc_rows(
            row_count=table.rowCount(),
            nickname_at=lambda row: table.item(row, 0).text() if table.item(row, 0) else "",
            name_text_at=lambda row: table.item(row, 1).text() if table.item(row, 1) else "",
            reputation_at=lambda row: (
                table.cellWidget(row, 2).currentText() if isinstance(table.cellWidget(row, 2), QComboBox) else ""
            ),
            affiliation_at=lambda row: (
                table.cellWidget(row, 3).currentText() if isinstance(table.cellWidget(row, 3), QComboBox) else ""
            ),
            role_at=lambda row: (
                table.cellWidget(row, 4).currentText() if isinstance(table.cellWidget(row, 4), QComboBox) else ""
            ),
            room_name=room_name,
            normalize_role=self._normalize_role_for_room,
            faction_nick_from_display_fn=self._faction_nick_from_display,
            default_role=self._default_role_for_room,
            extra_row_data_at=lambda row: (
                table.item(row, 0).data(Qt.UserRole)
                if table.item(row, 0) is not None
                else None
            ),
        )

    def _faction_nick_from_display(self, raw: str) -> str:
        return faction_nick_from_display(raw, self._faction_display_by_nick)

    def _faction_display_from_any(self, raw: str) -> str:
        return faction_display_from_any(raw, self._faction_display_by_nick)

    def _base_reputation_display_default(self) -> str:
        raw = self.faction_cb.currentText().strip() if hasattr(self, "faction_cb") else ""
        return self._faction_display_from_any(raw) or raw

    def _make_faction_combo(self, current: str) -> QComboBox:
        cb = QComboBox()
        cb.setEditable(True)
        opts = list(self._faction_display_options)
        cur_txt = str(current or "").strip()
        if cur_txt and cur_txt not in opts:
            opts.insert(0, cur_txt)
        cb.addItems(opts)
        if cur_txt:
            cb.setCurrentText(cur_txt)
        configure_contains_completer(cb)
        return cb

    @staticmethod
    def _default_role_for_room(room_name: str) -> str:
        return default_role_for_room(room_name)

    def _role_options_for_room(self, room_name: str) -> list[str]:
        return role_options_for_room(room_name, self.ROLE_OPTIONS_BY_ROOM)

    def _normalize_role_for_room(self, role: str, room_name: str) -> str:
        return normalize_role_for_room(role, room_name, self.ROLE_OPTIONS_BY_ROOM)

    def _make_role_combo(self, current: str, room_name: str) -> QComboBox:
        cb = QComboBox()
        cb.setEditable(False)
        opts = self._role_options_for_room(room_name)
        cur = self._normalize_role_for_room(current, room_name)
        cb.addItems(opts)
        if cur:
            cb.setCurrentText(cur)
        return cb

    @staticmethod
    def _safe_nick_part(raw: str) -> str:
        return safe_nick_part(raw)

    def _make_copied_npc_rows(self, room_name: str, template_rows: list[dict], used_nicks: set[str]) -> list[dict]:
        return make_copied_npc_rows(
            room_name,
            template_rows,
            used_nicks,
            base_nickname=self.base_nick_edit.text().strip(),
            base_reputation_display=self._base_reputation_display_default(),
            faction_display_by_nick=self._faction_display_by_nick,
            role_options_by_room=self.ROLE_OPTIONS_BY_ROOM,
        )

    def _set_room_npc_enabled(self, room_name: str, enabled: bool, reason: str = ""):
        key = str(room_name or "").strip().lower()
        panel = self._room_npc_panels.get(key)
        if panel is not None:
            panel.setEnabled(enabled)
            panel.setToolTip(reason if not enabled else "")

    def _set_room_row_locked(self, room_name: str, locked: bool, reason: str = ""):
        state = build_room_lock_state(
            room_name=room_name,
            locked=locked,
            reason=reason,
        )
        row = self._find_room_row(str(state["room_name"]))
        if row < 0:
            return
        check_item = self.room_table.item(row, 0)
        room_item = self.room_table.item(row, 1)
        if check_item:
            flags = check_item.flags() | Qt.ItemIsUserCheckable
            if bool(state["force_unchecked"]):
                check_item.setCheckState(Qt.Unchecked)
            if bool(state["check_enabled"]):
                check_item.setFlags((flags | Qt.ItemIsEnabled) & ~Qt.ItemIsEditable)
            else:
                check_item.setFlags((flags & ~Qt.ItemIsEnabled) & ~Qt.ItemIsEditable)
        if room_item:
            room_item.setToolTip(str(state["room_tooltip"]))
        scene_cb = self.room_table.cellWidget(row, 2)
        if isinstance(scene_cb, QComboBox):
            scene_cb.setEnabled(bool(state["scene_enabled"]))
            scene_cb.setToolTip(str(state["scene_tooltip"]))
        self._set_room_npc_enabled(
            str(state["room_name"]),
            bool(state["npc_enabled"]),
            str(state["npc_reason"]),
        )

    def _reset_room_rows_to_defaults(self):
        prev = self._updating_rooms
        self._updating_rooms = True
        try:
            state = build_default_room_reset_state(
                room_choices=self.ROOM_CHOICES,
                default_scene_for_room_fn=self._default_scene_for_room,
            )
            self.room_table.setRowCount(0)
            self._clear_room_npc_panels()
            for row in list(state["rows"]):
                self._set_room_row(
                    str(row["room_name"]),
                    bool(row["enabled"]),
                    str(row["scene"]),
                    list(row["npc_rows"]),
                )
            self.template_info_lbl.setText(str(state["info_text"]))
            self._refresh_room_npc_tabs()
        finally:
            self._updating_rooms = prev

    def _on_room_table_item_changed(self, _item: QTableWidgetItem):
        if self._updating_rooms:
            return
        self._refresh_room_npc_tabs()
        self._refresh_start_room_choices()

    def _ensure_template_data_loaded(self, template_value: str):
        template_key = self._nick_from_display(template_value).lower()
        if not template_key or template_key in self._template_load_attempted:
            return
        self._template_load_attempted.add(template_key)
        if not callable(self._template_data_provider):
            return
        try:
            payload = self._template_data_provider(template_key) or {}
        except Exception:
            return

        details = payload.get("details", []) if isinstance(payload, dict) else []
        if isinstance(details, list):
            normalized_details = [dict(row) for row in details if isinstance(row, dict)]
            if normalized_details:
                self._template_room_details[template_key] = normalized_details
                for row in normalized_details:
                    room = str(row.get("room", "") or "").strip().lower()
                    scene = str(row.get("scene", "") or "").strip()
                    if not room or not scene:
                        continue
                    options = self._scene_options_by_room.setdefault(room, [])
                    if scene not in options:
                        options.append(scene)

        room_npcs = payload.get("room_npcs", {}) if isinstance(payload, dict) else {}
        if isinstance(room_npcs, dict):
            normalized_room_map: dict[str, list[dict[str, str]]] = {}
            for room_key, rows in room_npcs.items():
                normalized_room = str(room_key or "").strip().lower()
                if not normalized_room or not isinstance(rows, list):
                    continue
                normalized_rows: list[dict[str, str]] = []
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    npc_nick = str(row.get("nickname", "") or "").strip()
                    if not npc_nick:
                        continue
                    normalized_rows.append(
                        {
                            "nickname": npc_nick,
                            "name_text": str(row.get("name_text", "") or npc_nick).strip() or npc_nick,
                            "reputation": str(row.get("reputation", "") or "").strip(),
                            "affiliation": str(row.get("affiliation", "") or "").strip(),
                            "role": str(row.get("role", "") or "").strip(),
                            "body": str(row.get("body", "") or "").strip(),
                            "head": str(row.get("head", "") or "").strip(),
                            "lefthand": str(row.get("lefthand", "") or "").strip(),
                            "righthand": str(row.get("righthand", "") or "").strip(),
                        }
                    )
                if normalized_rows:
                    normalized_room_map[normalized_room] = normalized_rows
            if normalized_room_map:
                self._template_room_npcs[template_key] = normalized_room_map

        virtual_targets = payload.get("virtual_targets", []) if isinstance(payload, dict) else []
        if isinstance(virtual_targets, list):
            normalized_targets = [
                str(target or "").strip().lower()
                for target in virtual_targets
                if str(target or "").strip()
            ]
            if normalized_targets:
                self._template_virtual_targets[template_key] = normalized_targets

    def _refresh_start_room_choices(self, preferred: str = ""):
        state = build_start_room_state(
            active_rooms=collect_active_room_names(
                row_count=self.room_table.rowCount(),
                room_name_at=lambda row: (
                    self.room_table.item(row, 1).text().strip() if self.room_table.item(row, 1) else ""
                ),
                enabled_at=lambda row: bool(
                    self.room_table.item(row, 0) and self.room_table.item(row, 0).checkState() == Qt.Checked
                ),
            ),
            preferred=preferred,
            current=self.start_room_cb.currentText().strip(),
        )
        self.start_room_cb.blockSignals(True)
        self.start_room_cb.clear()
        self.start_room_cb.addItems(list(state["active_rooms"]))
        target = str(state["target_room"])
        if target and self.start_room_cb.findText(target) >= 0:
            self.start_room_cb.setCurrentText(target)
        self.start_room_cb.blockSignals(False)

    def _on_template_changed(self):
        if self._updating_rooms:
            return
        self._updating_rooms = True
        try:
            template_value = str(self.template_cb.currentData() or self.template_cb.currentText() or "").strip()
            self._ensure_template_data_loaded(template_value)
            change_state = build_template_change_state(
                template_value=template_value,
                template_room_details=self._template_room_details,
                template_room_npcs=self._template_room_npcs,
                template_virtual_targets=self._template_virtual_targets,
                room_choices=self.ROOM_CHOICES,
                copy_template_npcs=bool(self.copy_npcs_cb.isChecked()),
                base_nickname=self.base_nick_edit.text().strip(),
                base_reputation_display=self._base_reputation_display_default(),
                faction_display_by_nick=self._faction_display_by_nick,
                role_options_by_room=self.ROLE_OPTIONS_BY_ROOM,
            )
            if bool(change_state["reset_to_defaults"]):
                self._reset_room_rows_to_defaults()
                for lock_state in list(change_state["room_locks"]):
                    self._set_room_row_locked(str(lock_state["room_name"]), False)
                self._refresh_room_npc_tabs()
                self._refresh_start_room_choices(preferred=str(change_state["preferred_start"]))
                return

            # Template-Auswahl als Vorauswahl: zunächst alles deaktivieren.
            for r in range(self.room_table.rowCount()):
                it = self.room_table.item(r, 0)
                if it:
                    it.setCheckState(Qt.Unchecked)

            for application in list(change_state["applications"]):
                room_name = str(application.get("room_name", "")).strip()
                scene = str(application.get("scene", "")).strip()
                npc_rows = list(application.get("npc_rows", []))
                self._set_room_row(room_name, True, scene, npc_rows)

            for lock_state in list(change_state["room_locks"]):
                self._set_room_row_locked(
                    str(lock_state["room_name"]),
                    bool(lock_state["locked"]),
                    str(lock_state["reason"]),
                )

            self.template_info_lbl.setText(str(change_state["info_text"]))
            self._refresh_room_npc_tabs()
            self._refresh_start_room_choices(preferred=str(change_state["preferred_start"]))
        finally:
            self._updating_rooms = False


# ══════════════════════════════════════════════════════════════════════
#  Solar-Erstellungsdialog  (Sonne / Planet)
# ══════════════════════════════════════════════════════════════════════

class SolarCreationDialog(QDialog):
    """Dialog zum Erstellen einer Sonne oder eines Planeten."""

    def __init__(
        self,
        parent,
        title: str,
        archetypes: list[str],
        default_radius: int,
        default_damage: int,
        stars: list[str] | None = None,
        default_star: str = "med_white_sun",
        enable_planet_ring: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._burn_rgb = ""
        self._planet_prefill_enabled = bool(enable_planet_ring)
        self._default_radius = int(default_radius)
        self._default_atmosphere_range = 2000
        layout = QFormLayout(self)
        self.star_cb = None
        self.atmo_spin = None

        self.nick_edit = QLineEdit()
        layout.addRow("Nickname:", self.nick_edit)

        self.ids_name_edit = QLineEdit()
        self.ids_name_edit.setPlaceholderText("Ingame Name (optional)")
        layout.addRow("Ingame Name:", self.ids_name_edit)

        self.arch_cb = QComboBox()
        self.arch_cb.setEditable(True)
        self.arch_cb.addItems(archetypes)
        layout.addRow(tr("lbl.archetype"), self.arch_cb)

        burn_row = QWidget()
        burn_l = QHBoxLayout(burn_row)
        burn_l.setContentsMargins(0, 0, 0, 0)
        self.burn_btn = QPushButton(tr("dlg.burn_color"))
        self.burn_lbl = QLabel(tr("dlg.optional"))
        burn_l.addWidget(self.burn_btn)
        burn_l.addWidget(self.burn_lbl)
        layout.addRow("Burn Color:", burn_row)

        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(100, 2_000_000)
        self.radius_spin.setValue(default_radius)
        layout.addRow("Death-Zone Radius:", self.radius_spin)

        self.damage_spin = QSpinBox()
        self.damage_spin.setRange(1, 2_000_000)
        self.damage_spin.setValue(default_damage)
        layout.addRow("Death-Zone Damage:", self.damage_spin)

        self.atmo_spin = QSpinBox()
        self.atmo_spin.setRange(0, 2_000_000)
        self.atmo_spin.setValue(self._default_atmosphere_range)
        layout.addRow("atmosphere_range:", self.atmo_spin)

        self.planet_ring_edit = None
        if enable_planet_ring:
            self.planet_ring_edit = QLineEdit()
            self.planet_ring_edit.setPlaceholderText("Optional, z.B. solar\\rings\\my_planet_ring.ini")
            layout.addRow("Planet Ring:", self.planet_ring_edit)

        if stars is not None:
            self.star_cb = QComboBox()
            self.star_cb.setEditable(True)
            self.star_cb.addItems(stars)
            self.star_cb.setCurrentText(default_star)
            layout.addRow("Star:", self.star_cb)
            self.atmo_spin.setValue(5000)

        self.burn_btn.clicked.connect(self._pick_burn)
        self.arch_cb.currentTextChanged.connect(self._on_archetype_changed)
        self._on_archetype_changed(self.arch_cb.currentText())

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    @staticmethod
    def _planet_size_from_archetype(archetype: str) -> int | None:
        match = re.search(r"_(\d+(?:\.\d+)?)\s*$", str(archetype or "").strip())
        if match is None:
            return None
        try:
            value = int(float(match.group(1)))
        except ValueError:
            return None
        return value if value > 0 else None

    def _on_archetype_changed(self, archetype: str) -> None:
        if not self._planet_prefill_enabled:
            return
        size = self._planet_size_from_archetype(archetype)
        if size is None:
            self.radius_spin.setValue(self._default_radius)
            self.atmo_spin.setValue(self._default_atmosphere_range)
            return
        self.radius_spin.setValue(size + 100)
        self.atmo_spin.setValue(size + 200)

    def _pick_burn(self):
        col = QColorDialog.getColor(parent=self)
        if not col.isValid():
            return
        self._burn_rgb = f"{col.red()}, {col.green()}, {col.blue()}"
        self.burn_lbl.setText(self._burn_rgb)

    def payload(self) -> dict:
        return build_solar_creation_payload(
            nickname=self.nick_edit.text(),
            ids_name_text=self.ids_name_edit.text(),
            archetype=self.arch_cb.currentText(),
            burn_color=self._burn_rgb,
            radius=self.radius_spin.value(),
            damage=self.damage_spin.value(),
            star=self.star_cb.currentText() if self.star_cb else "",
            atmosphere_range=self.atmo_spin.value(),
            planet_ring=self.planet_ring_edit.text() if self.planet_ring_edit else "",
        )


class LightSourceDialog(QDialog):
    """Dialog zum Erstellen einer LightSource-Sektion."""

    def __init__(
        self,
        parent,
        *,
        nickname: str,
        types: list[str],
        atten_curves: list[str],
    ):
        super().__init__(parent)
        self.setWindowTitle("Lichtquelle hinzufügen")
        self._color_rgb = "255, 255, 255"

        layout = QFormLayout(self)

        self.nick_edit = QLineEdit(nickname)
        layout.addRow("Nickname:", self.nick_edit)

        self.type_cb = QComboBox()
        self.type_cb.setEditable(True)
        self.type_cb.addItems(types or ["DIRECTIONAL", "POINT"])
        if self.type_cb.findText("DIRECTIONAL") >= 0:
            self.type_cb.setCurrentText("DIRECTIONAL")
        layout.addRow("Type:", self.type_cb)

        color_row = QWidget()
        color_l = QHBoxLayout(color_row)
        color_l.setContentsMargins(0, 0, 0, 0)
        self.color_btn = QPushButton(tr("dlg.pick_color"))
        self.color_lbl = QLabel(self._color_rgb)
        color_l.addWidget(self.color_btn)
        color_l.addWidget(self.color_lbl)
        layout.addRow("Color:", color_row)

        self.range_spin = QSpinBox()
        self.range_spin.setRange(1, 2_000_000)
        self.range_spin.setValue(100000)
        layout.addRow("Range:", self.range_spin)

        self.atten_cb = QComboBox()
        self.atten_cb.setEditable(True)
        self.atten_cb.addItems(atten_curves or ["DYNAMIC_DIRECTION"])
        if self.atten_cb.findText("DYNAMIC_DIRECTION") >= 0:
            self.atten_cb.setCurrentText("DYNAMIC_DIRECTION")
        layout.addRow("atten_curve:", self.atten_cb)

        self.color_btn.clicked.connect(self._pick_color)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _pick_color(self):
        col = QColorDialog.getColor(parent=self)
        if not col.isValid():
            return
        self._color_rgb = f"{col.red()}, {col.green()}, {col.blue()}"
        self.color_lbl.setText(self._color_rgb)

    def payload(self) -> dict:
        return build_light_source_payload(
            nickname=self.nick_edit.text(),
            light_type=self.type_cb.currentText(),
            color=self._color_rgb,
            range_value=self.range_spin.value(),
            atten_curve=self.atten_cb.currentText(),
        )


# ══════════════════════════════════════════════════════════════════════
#  Objekt-Erstellungsdialog
# ══════════════════════════════════════════════════════════════════════

class ObjectCreationDialog(QDialog):
    """Dialog zum Erstellen eines beliebigen Objekts."""

    def __init__(
        self,
        parent,
        archetypes: list[str],
        loadouts: list[str],
        factions: list[str],
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.object_create"))
        layout = QFormLayout(self)

        self.nick_edit = QLineEdit()
        layout.addRow("Nickname:", self.nick_edit)

        self.ids_name_edit = QLineEdit()
        self.ids_name_edit.setPlaceholderText("Ingame Name (optional)")
        layout.addRow("Ingame Name:", self.ids_name_edit)

        self.arch_cb = QComboBox()
        self.arch_cb.setEditable(True)
        self.arch_cb.addItems(archetypes)
        layout.addRow(tr("lbl.archetype"), self.arch_cb)

        self.loadout_cb = QComboBox()
        self.loadout_cb.setEditable(True)
        self.loadout_cb.addItem("")
        self.loadout_cb.addItems(loadouts)
        self.loadout_cb.setCurrentIndex(0)
        layout.addRow("Loadout:", self.loadout_cb)

        self.faction_cb = QComboBox()
        self.faction_cb.setEditable(True)
        self.faction_cb.addItem("")
        self.faction_cb.addItems(factions)
        self.faction_cb.setCurrentIndex(0)
        configure_contains_completer(self.faction_cb)
        layout.addRow("Reputation:", self.faction_cb)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def payload(self) -> dict:
        return build_object_creation_payload(
            nickname=self.nick_edit.text(),
            ids_name_text=self.ids_name_edit.text(),
            archetype=self.arch_cb.currentText(),
            loadout=self.loadout_cb.currentText(),
            faction=self.faction_cb.currentText(),
        )



class CategoryObjectDialog(QDialog):
    """Dialog für Wracks, Weapon Platforms und Depots."""

    def __init__(
        self,
        parent,
        *,
        title: str,
        archetypes: list[str],
        loadouts: list[str],
        factions: list[str] = None,
        show_reputation: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QFormLayout(self)

        self.arch_cb = QComboBox()
        self.arch_cb.setEditable(True)
        self.arch_cb.addItems(archetypes)
        layout.addRow(tr("lbl.archetype"), self.arch_cb)

        self.ids_name_edit = QLineEdit()
        self.ids_name_edit.setPlaceholderText("Ingame Name (optional)")
        layout.addRow("Ingame Name:", self.ids_name_edit)

        self.loadout_cb = QComboBox()
        self.loadout_cb.setEditable(True)
        self.loadout_cb.addItem("")
        self.loadout_cb.addItems(loadouts)
        self.loadout_cb.setCurrentIndex(0)
        layout.addRow(tr("lbl.loadout"), self.loadout_cb)

        self.faction_cb = None
        self.rep_edit = None
        if show_reputation and factions:
            self.faction_cb = QComboBox()
            self.faction_cb.setEditable(True)
            self.faction_cb.addItem("")
            self.faction_cb.addItems(factions)
            self.faction_cb.setCurrentIndex(0)
            configure_contains_completer(self.faction_cb)
            layout.addRow(tr("lbl.faction"), self.faction_cb)
            self.rep_edit = QLineEdit()
            self.rep_edit.setPlaceholderText("optional")
            layout.addRow(tr("lbl.reputation"), self.rep_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def payload(self) -> dict:
        return build_category_object_payload(
            archetype=self.arch_cb.currentText(),
            ids_name_text=self.ids_name_edit.text(),
            loadout=self.loadout_cb.currentText(),
            faction=self.faction_cb.currentText() if self.faction_cb else "",
            rep=self.rep_edit.text() if self.rep_edit else "",
        )


class BuoyDialog(QDialog):
    """Dialog zum Erstellen von Nav-/Hazard-Buoys in Linie oder Kreis."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.buoy_create"))
        layout = QFormLayout(self)

        self.type_cb = QComboBox()
        self.type_cb.addItems(["nav_buoy", "hazard_buoy"])
        layout.addRow(tr("dlg.buoy_type"), self.type_cb)

        self.pattern_cb = QComboBox()
        self.pattern_cb.addItems(["LINE", "CIRCLE", "SINGLE"])
        layout.addRow(tr("dlg.pattern"), self.pattern_cb)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 128)
        self.count_spin.setValue(8)
        self.count_lbl = QLabel(tr("dlg.count"))
        layout.addRow(self.count_lbl, self.count_spin)

        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(100, 100000)
        self.spacing_spin.setValue(3000)
        self.spacing_lbl = QLabel(tr("dlg.spacing_line"))
        layout.addRow(self.spacing_lbl, self.spacing_spin)

        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(100, 200000)
        self.radius_spin.setValue(12000)
        self.radius_lbl = QLabel(tr("dlg.radius_circle"))
        layout.addRow(self.radius_lbl, self.radius_spin)

        self.pattern_cb.currentTextChanged.connect(self._update_visibility)
        self._update_visibility(self.pattern_cb.currentText())

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _update_visibility(self, pattern: str):
        pat = (pattern or "").upper()
        line_mode = pat == "LINE"
        circle_mode = pat == "CIRCLE"
        single_mode = pat == "SINGLE"
        self.count_lbl.setVisible(circle_mode)
        self.count_spin.setVisible(circle_mode)
        self.spacing_lbl.setVisible(line_mode)
        self.spacing_spin.setVisible(line_mode)
        # Radius wird per Maus bestimmt, daher kein Eingabefeld mehr anzeigen.
        self.radius_lbl.setVisible(False)
        self.radius_spin.setVisible(False)
        if single_mode:
            self.count_spin.setValue(1)
        elif circle_mode and self.count_spin.value() < 2:
            self.count_spin.setValue(2)

    def payload(self) -> dict:
        return build_buoy_payload(
            buoy_type=self.type_cb.currentText(),
            pattern=self.pattern_cb.currentText(),
            count=self.count_spin.value(),
            spacing=self.spacing_spin.value(),
        )


# ══════════════════════════════════════════════════════════════════════
#  3D-Vorschau-Dialog
# ══════════════════════════════════════════════════════════════════════

class MeshPreviewDialog(QDialog):
    """Zeigt ein 3D-Modell (oder einen Fallback-Primitive) in einem eigenen Fenster."""

    def __init__(
        self,
        parent,
        mesh_path: Path | None,
        title: str,
        primitive: str | None = None,
        info_text: str = "",
        native_model: FreelancerMeshData | None = None,
        material_library_paths: tuple[Path, ...] = (),
        planet_surface_texture_path: Path | None = None,
        planet_cloud_texture_path: Path | None = None,
        planet_ring_texture_path: Path | None = None,
        planet_ring_inner_ratio: float | None = None,
        planet_ring_outer_ratio: float | None = None,
        planet_ring_inner_radius: float | None = None,
        planet_ring_outer_radius: float | None = None,
        planet_ring_thickness: float | None = None,
        planet_ring_rotate_xyz: tuple[float, float, float] | None = None,
        planet_atmosphere_range: float | None = None,
        planet_burn_color: tuple[int, int, int] | None = None,
        planet_radius: float | None = None,
        scene_data: NativePreviewSceneData | None = None,
        ring_preview_mode: bool = False,
        minimal: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(720, 480)
        layout = QVBoxLayout(self)

        if not QT3D_AVAILABLE:
            layout.addWidget(
                QLabel(tr("dlg.qt3d_not_available"))
            )
            return

        self._minimal = minimal

        if minimal:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self._tabs = None
            self._reset_camera_btn = None
            self._bounds_checkbox = None
            self._wireframe_checkbox = None
            self._mesh_checkbox = None
            self._materials_checkbox = None
            self._white_background_checkbox = None
            self._part_names_checkbox = None
            self._part_names_label = None
            self._render_summary_label = None
            content_row = QHBoxLayout()
            content_row.setContentsMargins(0, 0, 0, 0)
            layout.addLayout(content_row, 1)
        else:
            self._tabs = QTabWidget(self)
            self._tabs.setObjectName("native_preview_tabs")
            layout.addWidget(self._tabs)

            preview_tab = QWidget(self)
            preview_layout = QVBoxLayout(preview_tab)
            preview_layout.setContentsMargins(0, 0, 0, 0)
            self._tabs.addTab(preview_tab, "Preview")

            details_tab = QWidget(self)
            details_tab_layout = QVBoxLayout(details_tab)
            details_tab_layout.setContentsMargins(0, 0, 0, 0)
            details_scroll = QScrollArea(details_tab)
            details_scroll.setWidgetResizable(True)
            details_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            details_content = QWidget(details_scroll)
            details_layout = QVBoxLayout(details_content)
            details_layout.setContentsMargins(0, 0, 0, 0)
            details_scroll.setWidget(details_content)
            details_tab_layout.addWidget(details_scroll)
            self._tabs.addTab(details_tab, "Details")

            if info_text:
                info_lbl = QLabel(info_text)
                info_lbl.setWordWrap(True)
                details_layout.addWidget(info_lbl)

            controls_row = QHBoxLayout()
            self._reset_camera_btn = QPushButton("Reset Camera", self)
            self._reset_camera_btn.setObjectName("native_preview_reset_camera_btn")
            self._reset_camera_btn.clicked.connect(self._reset_preview_camera)
            controls_row.addWidget(self._reset_camera_btn)
            self._bounds_checkbox = QCheckBox("Bounding Box", self)
            self._bounds_checkbox.setObjectName("native_preview_bounds_checkbox")
            self._bounds_checkbox.toggled.connect(self._set_bounds_visible)
            controls_row.addWidget(self._bounds_checkbox)
            self._wireframe_checkbox = QCheckBox("Wireframe", self)
            self._wireframe_checkbox.setObjectName("native_preview_wireframe_checkbox")
            self._wireframe_checkbox.toggled.connect(self._set_wireframe_visible)
            controls_row.addWidget(self._wireframe_checkbox)
            self._mesh_checkbox = QCheckBox("Mesh", self)
            self._mesh_checkbox.setObjectName("native_preview_mesh_checkbox")
            self._mesh_checkbox.setChecked(True)
            self._mesh_checkbox.toggled.connect(self._set_mesh_visible)
            controls_row.addWidget(self._mesh_checkbox)
            self._materials_checkbox = QCheckBox("Materials", self)
            self._materials_checkbox.setObjectName("native_preview_materials_checkbox")
            self._materials_checkbox.setChecked(False)
            self._materials_checkbox.toggled.connect(self._set_materials_visible)
            controls_row.addWidget(self._materials_checkbox)
            self._white_background_checkbox = QCheckBox("White BG", self)
            self._white_background_checkbox.setObjectName("native_preview_white_background_checkbox")
            self._white_background_checkbox.toggled.connect(self._set_preview_background_white)
            controls_row.addWidget(self._white_background_checkbox)
            self._part_names_checkbox = QCheckBox("Part Names", self)
            self._part_names_checkbox.setObjectName("native_preview_part_names_checkbox")
            self._part_names_checkbox.toggled.connect(self._set_part_names_visible)
            controls_row.addWidget(self._part_names_checkbox)
            controls_row.addStretch(1)
            preview_layout.addLayout(controls_row)

            self._part_names_label = QLabel(self)
            self._part_names_label.setObjectName("native_preview_part_names_label")
            self._part_names_label.setWordWrap(True)
            self._part_names_label.setVisible(False)
            preview_layout.addWidget(self._part_names_label)
            self._render_summary_label = QLabel(self)
            self._render_summary_label.setObjectName("native_preview_render_summary_label")
            self._render_summary_label.setWordWrap(True)
            self._render_summary_label.setVisible(False)
            preview_layout.addWidget(self._render_summary_label)

            content_row = QHBoxLayout()
            preview_layout.addLayout(content_row, 1)

        self._view3d = Qt3DWindow3D()
        self._frame_graph = getattr(self._view3d, "defaultFrameGraph", lambda: None)()
        self._is_dark_theme = self.palette().window().color().lightnessF() < 0.5
        self._preview_background_color = QColor(0, 0, 0) if self._is_dark_theme else QColor(255, 255, 255)
        self._apply_preview_background_color()
        container = QWidget.createWindowContainer(self._view3d)
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        container.setFocusPolicy(Qt.StrongFocus)
        container.setMouseTracking(True)
        container.installEventFilter(self)
        content_row.addWidget(container, 1)
        self._preview_container = container
        self._view3d.installEventFilter(self)

        self._root = QEntity3D()
        self._mesh_entity = QEntity3D(self._root)
        self._mesh_transform = QTransform3D(self._root)
        self._native_mesh_entities: list[object] = []
        self._native_mesh_refs: list[object] = []
        self._wireframe_entities: list[object] = []
        self._material_pairs: list[tuple[object, object, object]] = []
        self._planet_overlay_entities: list[object] = []
        self._bounds_entity: object | None = None
        self._planet_surface_texture_path = planet_surface_texture_path
        self._planet_cloud_texture_path = planet_cloud_texture_path
        self._planet_ring_texture_path = planet_ring_texture_path
        self._planet_ring_inner_ratio = float(planet_ring_inner_ratio) if planet_ring_inner_ratio is not None else None
        self._planet_ring_outer_ratio = float(planet_ring_outer_ratio) if planet_ring_outer_ratio is not None else None
        self._planet_ring_inner_radius = float(planet_ring_inner_radius) if planet_ring_inner_radius is not None else None
        self._planet_ring_outer_radius = float(planet_ring_outer_radius) if planet_ring_outer_radius is not None else None
        self._planet_ring_thickness = float(planet_ring_thickness) if planet_ring_thickness is not None else None
        self._planet_ring_rotate_xyz = tuple(planet_ring_rotate_xyz) if planet_ring_rotate_xyz is not None else None
        self._planet_atmosphere_range = float(planet_atmosphere_range) if planet_atmosphere_range is not None else None
        self._planet_burn_color = tuple(planet_burn_color) if planet_burn_color is not None else None
        self._planet_radius = float(planet_radius) if planet_radius is not None else None
        self._ring_preview_mode = bool(ring_preview_mode)
        self._native_part_names: tuple[str, ...] = ()
        self._preview_bounds = None
        self._preview_zoom_factor = 1.0
        self._preview_auto_fit_pending = True
        self._max_orbit_distance = 50000.0
        self._pending_drag_mode: str | None = None
        self._active_drag_mode: str | None = None
        self._press_pos = QPointF()
        self._last_drag_pos = QPointF()
        self._camera_distance = 120.0
        self._camera_yaw_deg = 0.0
        self._camera_pitch_deg = 0.0
        scene_data = scene_data if scene_data is not None else build_native_preview_scene_data(native_model)
        self._native_scene_data = scene_data
        self._native_texture_path = scene_data.texture_path
        self._native_texture_refs: list[object] = []
        self._mat_textures: dict[str, Path] = {}
        if not self._native_texture_path and material_library_paths:
            from .mat_texture_loader import extract_all_mat_textures, find_best_mat_texture
            self._mat_textures = extract_all_mat_textures(material_library_paths)
            best = find_best_mat_texture(self._mat_textures)
            if best is not None:
                self._native_texture_path = best
        native_geometries = scene_data.geometries
        native_geometry = scene_data.primary_geometry
        self._native_part_names = scene_data.part_names
        uses_composite_fallback = False
        fallback_bounds: FreelancerBounds | None = None
        mat_texture_fallback = self._native_texture_path

        def _resolve_texture(geometry, data=scene_data):
            result = texture_path_for_geometry(data, geometry)
            return result if result is not None else mat_texture_fallback

        if mesh_path is not None:
            self._mesh = QMesh3D()
            self._mesh.setSource(QUrl.fromLocalFile(str(mesh_path)))
            self._mesh_entity.addComponent(self._mesh)
        elif native_geometry is not None:
            self._mesh_entity.addComponent(build_native_geometry_renderer(native_geometry, owner=self._mesh_entity))
            self._wireframe_entities.append(build_native_wireframe_entity(root=self._root, native_geometry=native_geometry))
            for extra_geometry in native_geometries[1:]:
                ent = QEntity3D(self._root)
                renderer = build_native_geometry_renderer(extra_geometry, owner=ent)
                transform = QTransform3D(ent)
                material = build_native_geometry_material(
                    owner=ent,
                    native_geometry=extra_geometry,
                    texture_refs=self._native_texture_refs,
                    texture_resolver=_resolve_texture,
                )
                apply_native_geometry_material(material, extra_geometry)
                ent.addComponent(renderer)
                ent.addComponent(transform)
                ent.addComponent(material)
                _colored_extra = QPhongMaterial3D(ent)
                _disable_backface_culling(_colored_extra)
                apply_native_geometry_material(_colored_extra, extra_geometry)
                self._material_pairs.append((ent, material, _colored_extra))
                self._native_mesh_entities.append(ent)
                self._wireframe_entities.append(build_native_wireframe_entity(root=self._root, native_geometry=extra_geometry))
        else:
            prim = (primitive or "cube").lower()
            native_bounds = native_model.bounds if native_model is not None else None
            if prim == "sphere":
                pm = QSphereMesh3D()
                fallback_radius = self._planet_radius if self._planet_radius is not None else 35.0
                pm.setRadius(max(native_bounds.radius if native_bounds and native_bounds.radius else fallback_radius, 1.0))
            elif prim == "jumpgate":
                fallback_bounds = self._build_jumpgate_preview_entity(native_bounds)
                pm = None
                uses_composite_fallback = True
            else:
                pm = QCuboidMesh3D()
                if native_bounds is not None:
                    x_extent = max(native_bounds.max_xyz[0] - native_bounds.min_xyz[0], 1.0)
                    y_extent = max(native_bounds.max_xyz[1] - native_bounds.min_xyz[1], 1.0)
                    z_extent = max(native_bounds.max_xyz[2] - native_bounds.min_xyz[2], 1.0)
                    if hasattr(pm, "setXExtent"):
                        pm.setXExtent(x_extent)
                    if hasattr(pm, "setYExtent"):
                        pm.setYExtent(y_extent)
                    if hasattr(pm, "setZExtent"):
                        pm.setZExtent(z_extent)
            if pm is not None:
                self._mesh_entity.addComponent(pm)

        self._material = build_native_geometry_material(
            owner=self._root,
            native_geometry=native_geometry,
            texture_refs=self._native_texture_refs,
            texture_resolver=_resolve_texture,
        )
        if native_geometry is not None:
            apply_native_geometry_material(self._material, native_geometry)
        elif hasattr(self._material, "setDiffuse"):
            try:
                self._material.setDiffuse(QColor(120, 190, 255))
            except Exception:
                pass
            if hasattr(self._material, "setAmbient"):
                try:
                    self._material.setAmbient(QColor(36, 64, 96))
                except Exception:
                    pass
        if native_geometry is None and primitive and primitive.lower() == "sphere":
            textured_planet_material = build_qt3d_texture_material(
                owner=self._root,
                texture_path=self._planet_surface_texture_path,
                texture_refs=self._native_texture_refs,
                force_opaque=True,
            )
            if textured_planet_material is not None:
                self._material = textured_planet_material
        if not uses_composite_fallback:
            self._mesh_entity.addComponent(self._material)
        if native_geometry is not None and not uses_composite_fallback:
            _colored_primary = QPhongMaterial3D(self._root)
            _disable_backface_culling(_colored_primary)
            apply_native_geometry_material(_colored_primary, native_geometry)
            self._material_pairs.append((self._mesh_entity, self._material, _colored_primary))
        self._mesh_entity.addComponent(self._mesh_transform)
        if native_model is not None:
            panel = self._build_native_model_panel(native_model, scene_data)
            if not minimal:
                details_layout.addWidget(panel)
        if not minimal:
            details_layout.addStretch(1)
        self._apply_screen_constrained_size()

        self._light_entity = QEntity3D(self._root)
        self._light = QDirectionalLight3D(self._light_entity)
        self._light.setWorldDirection(QVector3D(-0.7, -1.0, -0.5))
        self._light_entity.addComponent(self._light)

        self._camera = self._view3d.camera()
        self._sync_preview_camera_projection()
        self._camera.setPosition(QVector3D(0.0, 0.0, 120.0))
        self._camera.setViewCenter(QVector3D(0.0, 0.0, 0.0))
        if scene_data.bounds is not None:
            self._preview_bounds = scene_data.bounds
        elif native_model is not None and getattr(native_model, "bounds", None) is not None:
            self._preview_bounds = native_model.bounds
        direct_ring_outer_radius = self._planet_ring_outer_radius
        if direct_ring_outer_radius is not None and float(direct_ring_outer_radius) > 0.0:
            ring_extent = float(direct_ring_outer_radius)
            if self._preview_bounds is None:
                self._preview_bounds = FreelancerBounds(
                    min_xyz=(-ring_extent, -ring_extent, -ring_extent),
                    max_xyz=(ring_extent, ring_extent, ring_extent),
                    radius=ring_extent,
                )
            else:
                min_x, min_y, min_z = self._preview_bounds.min_xyz
                max_x, max_y, max_z = self._preview_bounds.max_xyz
                self._preview_bounds = FreelancerBounds(
                    min_xyz=(min(min_x, -ring_extent), min(min_y, -ring_extent), min(min_z, -ring_extent)),
                    max_xyz=(max(max_x, ring_extent), max(max_y, ring_extent), max(max_z, ring_extent)),
                    radius=max(float(self._preview_bounds.radius or 0.0), ring_extent),
                )
        if self._preview_bounds is not None:
            self._apply_native_preview_bounds(self._camera, self._preview_bounds)
            self._build_preview_bounds_entity(self._preview_bounds)
            if self._bounds_checkbox is not None:
                self._bounds_checkbox.setEnabled(True)
        elif uses_composite_fallback and primitive and primitive.lower() == "jumpgate":
            self._preview_bounds = fallback_bounds
            self._apply_native_preview_bounds(self._camera, self._preview_bounds)
            self._build_preview_bounds_entity(self._preview_bounds)
            if self._bounds_checkbox is not None:
                self._bounds_checkbox.setEnabled(True)
        else:
            if self._bounds_checkbox is not None:
                self._bounds_checkbox.setEnabled(False)
        if self._wireframe_checkbox is not None:
            self._wireframe_checkbox.setEnabled(bool(self._wireframe_entities))
        if self._part_names_checkbox is not None:
            self._part_names_checkbox.setEnabled(bool(self._native_part_names))
        if self._materials_checkbox is not None:
            self._materials_checkbox.setEnabled(bool(self._native_texture_refs) or bool(self._mat_textures))
        overlay_radius = self._planet_radius if self._planet_radius is not None else None
        if (overlay_radius is None or overlay_radius <= 0.0) and self._preview_bounds is not None:
            try:
                overlay_radius = float(self._preview_bounds.radius or 0.0)
            except Exception:
                overlay_radius = None
        if (
            (
                self._planet_ring_inner_ratio is not None
                and self._planet_ring_outer_ratio is not None
            )
            or (
                self._planet_ring_inner_radius is not None
                and self._planet_ring_outer_radius is not None
            )
            or self._planet_cloud_texture_path is not None
            or self._planet_atmosphere_range is not None
        ):
            if overlay_radius is None or overlay_radius <= 0.0:
                overlay_radius = 35.0
            self._build_planet_overlay_entities(float(overlay_radius))
            if self._ring_preview_mode:
                self._build_ring_preview_reference_grid(float(overlay_radius))
        # Materials checkbox starts unchecked → swap to colored materials
        if self._material_pairs and (minimal or (self._materials_checkbox is not None and not self._materials_checkbox.isChecked())):
            self._set_materials_visible(False)
        if self._wireframe_entities:
            if self._wireframe_checkbox is not None:
                self._wireframe_checkbox.setChecked(True)
            elif minimal:
                self._set_wireframe_visible(True)
        if self._native_part_names and self._part_names_label is not None:
            self._part_names_label.setText("Rendered parts: " + ", ".join(self._native_part_names))
        render_summary = self._build_native_render_summary(scene_data, primitive, native_model)
        if render_summary and self._render_summary_label is not None:
            self._render_summary_label.setText(render_summary)
            self._render_summary_label.setVisible(True)

        self._cam_controller = QOrbitCameraController3D(self._root)
        self._cam_controller.setLinearSpeed(100.0)
        self._cam_controller.setLookSpeed(180.0)
        self._cam_controller.setCamera(self._camera)
        if hasattr(self._cam_controller, "setEnabled"):
            self._cam_controller.setEnabled(False)

        self._view3d.setRootEntity(self._root)
        self._sync_preview_camera_polar_state()

    def eventFilter(self, watched, event) -> bool:
        if watched in {getattr(self, "_preview_container", None), getattr(self, "_view3d", None)} and QT3D_AVAILABLE:
            event_type = event.type()
            if event_type == QEvent.MouseButtonPress:
                return self._handle_mouse_press(event)
            if event_type == QEvent.MouseMove:
                return self._handle_mouse_move(event)
            if event_type == QEvent.MouseButtonRelease:
                return self._handle_mouse_release(event)
            if event_type == QEvent.Wheel:
                return self._handle_wheel(event)
        return super().eventFilter(watched, event)

    def _handle_mouse_press(self, event) -> bool:
        button = getattr(event, "button", lambda: None)()
        position = self._event_position(event)
        self._press_pos = position
        self._last_drag_pos = position
        if button == Qt.MiddleButton:
            self._pending_drag_mode = None
            self._active_drag_mode = "pan"
            return True
        if button != Qt.LeftButton:
            return False
        self._pending_drag_mode = "orbit"
        self._active_drag_mode = None
        return False

    def _handle_mouse_move(self, event) -> bool:
        position = self._event_position(event)
        if self._active_drag_mode == "pan":
            self._pan_camera(position.x() - self._last_drag_pos.x(), position.y() - self._last_drag_pos.y())
            self._last_drag_pos = position
            return True
        if self._pending_drag_mode is not None and self._active_drag_mode is None:
            if (position - self._press_pos).manhattanLength() < 4.0:
                return False
            if self._pending_drag_mode == "orbit":
                self._active_drag_mode = "orbit"
                self._last_drag_pos = position
                self._pending_drag_mode = None
                return True
        if self._active_drag_mode == "orbit":
            delta_x = position.x() - self._last_drag_pos.x()
            delta_y = position.y() - self._last_drag_pos.y()
            self._orbit_camera(delta_x, delta_y)
            self._last_drag_pos = position
            return True
        return False

    def _handle_mouse_release(self, event) -> bool:
        button = getattr(event, "button", lambda: None)()
        if button == Qt.MiddleButton and self._active_drag_mode == "pan":
            self._active_drag_mode = None
            return True
        if button != Qt.LeftButton:
            return False
        if self._active_drag_mode == "orbit":
            self._active_drag_mode = None
            self._pending_drag_mode = None
            return True
        self._pending_drag_mode = None
        return False

    def _handle_wheel(self, event) -> bool:
        try:
            delta = event.angleDelta().y()
        except Exception:
            return False
        if abs(int(delta)) <= 0:
            return False
        factor = 0.82 if delta > 0 else 1.22
        self._camera_distance = max(2.0, min(float(self._max_orbit_distance), self._camera_distance * factor))
        self._apply_preview_camera_pose()
        return True

    def _event_position(self, event) -> QPointF:
        position = getattr(event, "position", None)
        if callable(position):
            return position()
        local_pos = getattr(event, "localPos", None)
        if callable(local_pos):
            return local_pos()
        return QPointF()

    def _orbit_camera(self, delta_x: float, delta_y: float) -> None:
        self._camera_yaw_deg, self._camera_pitch_deg = orbit_drag_angles(
            self._camera_yaw_deg,
            self._camera_pitch_deg,
            delta_x=delta_x,
            delta_y=delta_y,
        )
        self._apply_preview_camera_pose()

    def _pan_camera(self, delta_x: float, delta_y: float) -> None:
        center = self._camera.viewCenter()
        position = self._camera.position()
        forward = center - position
        distance = max(1.0, float(forward.length()))
        if forward.lengthSquared() <= 1e-9:
            return
        forward = forward.normalized()
        world_up = QVector3D(0.0, 1.0, 0.0)
        right = QVector3D.crossProduct(forward, world_up)
        if right.lengthSquared() <= 1e-9:
            right = QVector3D(1.0, 0.0, 0.0)
        else:
            right = right.normalized()
        up = QVector3D.crossProduct(right, forward)
        if up.lengthSquared() <= 1e-9:
            up = QVector3D(0.0, 1.0, 0.0)
        else:
            up = up.normalized()
        viewport_size = max(240.0, float(min(self.width(), self.height()) or 0.0))
        factor = (distance / viewport_size) * 1.65
        translation = (right * float(-delta_x) * factor) + (up * float(delta_y) * factor)
        self._camera.setViewCenter(center + translation)
        self._camera.setPosition(position + translation)
        self._sync_preview_camera_polar_state()

    def _sync_preview_camera_polar_state(self) -> None:
        center = self._camera.viewCenter()
        position = self._camera.position()
        offset = position - center
        distance = max(1.0, float(offset.length()))
        self._camera_distance = distance
        if distance <= 1e-6:
            return
        self._camera_yaw_deg = math.degrees(math.atan2(float(offset.x()), float(offset.z())))
        ratio = max(-1.0, min(1.0, float(offset.y()) / distance))
        self._camera_pitch_deg = math.degrees(math.asin(ratio))

    def _apply_preview_camera_pose(self) -> None:
        center = self._camera.viewCenter()
        distance = max(1.0, float(self._camera_distance))
        yaw_rad = math.radians(float(self._camera_yaw_deg))
        pitch_rad = math.radians(float(self._camera_pitch_deg))
        cos_pitch = math.cos(pitch_rad)
        offset = QVector3D(
            math.sin(yaw_rad) * cos_pitch * distance,
            math.sin(pitch_rad) * distance,
            math.cos(yaw_rad) * cos_pitch * distance,
        )
        self._camera.setPosition(center + offset)

    def _build_planet_overlay_entities(self, radius: float) -> None:
        if radius <= 0.0:
            return

        if (
            self._planet_ring_inner_radius is not None
            and self._planet_ring_outer_radius is not None
        ):
            inner_radius = max(1.0, float(self._planet_ring_inner_radius))
            outer_radius = max(inner_radius + 1.0, float(self._planet_ring_outer_radius))
        elif self._planet_ring_inner_ratio is not None and self._planet_ring_outer_ratio is not None:
            inner_radius = float(radius) * max(1.02, float(self._planet_ring_inner_ratio))
            outer_radius = float(radius) * max(1.08, float(self._planet_ring_outer_ratio))
        else:
            inner_radius = None
            outer_radius = None

        if inner_radius is not None and outer_radius is not None:
            ring_ent = QEntity3D(self._root)
            ring_height = self._planet_ring_thickness
            if ring_height is None or float(ring_height) <= 0.0:
                ring_height = max(1.0, min((outer_radius - inner_radius) * 0.12, radius * 0.08))
            ring_renderer = build_solid_annulus_renderer(
                owner=ring_ent,
                inner_radius=inner_radius,
                outer_radius=outer_radius,
                height=float(ring_height),
                segments=128,
            )
            ring_material = None
            if not self._ring_preview_mode:
                ring_material = build_qt3d_texture_material(
                    owner=ring_ent,
                    texture_path=self._planet_ring_texture_path,
                    texture_refs=self._native_texture_refs,
                )
            if ring_material is None:
                ring_color = QColor(236, 232, 212, 230) if self._is_dark_theme else QColor(58, 66, 82, 220)
                if self._ring_preview_mode:
                    ring_material = QPhongMaterial3D(ring_ent)
                    _disable_backface_culling(ring_material)
                else:
                    ring_material = QPhongAlphaMaterial3D(ring_ent)
                    ring_material.setAlpha(0.26)
                ring_material.setDiffuse(ring_color)
                try:
                    ring_material.setAmbient(ring_color.lighter(115 if self._is_dark_theme else 95))
                except Exception:
                    pass
            ring_tr = QTransform3D(ring_ent)
            if self._planet_ring_rotate_xyz is not None and len(self._planet_ring_rotate_xyz) >= 3:
                try:
                    ring_tr.setRotation(
                        rotation_quaternion_from_fl(
                            float(self._planet_ring_rotate_xyz[0]),
                            float(self._planet_ring_rotate_xyz[1]),
                            float(self._planet_ring_rotate_xyz[2]),
                        )
                    )
                except Exception:
                    pass
            ring_ent.addComponent(ring_renderer)
            ring_ent.addComponent(ring_material)
            ring_ent.addComponent(ring_tr)
            self._planet_overlay_entities.extend([ring_ent, ring_renderer, ring_material, ring_tr])

        has_cloud_layer = bool(self._planet_cloud_texture_path)
        cloud_material = None
        if has_cloud_layer:
            cloud_material = build_qt3d_texture_material(
                owner=self._root,
                texture_path=self._planet_cloud_texture_path,
                texture_refs=self._native_texture_refs,
            )
        if cloud_material is not None:
            cloud_ent = QEntity3D(self._root)
            cloud_mesh = QSphereMesh3D()
            cloud_mesh.setRadius(float(radius) * 1.018)
            if hasattr(cloud_mesh, "setRings"):
                cloud_mesh.setRings(56)
            if hasattr(cloud_mesh, "setSlices"):
                cloud_mesh.setSlices(84)
            cloud_tr = QTransform3D(cloud_ent)
            cloud_ent.addComponent(cloud_mesh)
            cloud_ent.addComponent(cloud_material)
            cloud_ent.addComponent(cloud_tr)
            self._planet_overlay_entities.extend([cloud_ent, cloud_mesh, cloud_material, cloud_tr])

        if self._planet_atmosphere_range is None or self._planet_atmosphere_range <= radius:
            return
        burn_rgb = self._planet_burn_color or (255, 222, 160)
        atmosphere_color = QColor(int(burn_rgb[0]), int(burn_rgb[1]), int(burn_rgb[2]), 170)
        ratio = max(1.01, min(1.65, float(self._planet_atmosphere_range) / max(float(radius), 1e-6)))
        for scale, alpha in ((ratio, 0.10), (min(ratio + 0.03, 1.28), 0.05)):
            ent = QEntity3D(self._root)
            mesh = QSphereMesh3D()
            mesh.setRadius(float(radius) * float(scale))
            if hasattr(mesh, "setRings"):
                mesh.setRings(56)
            if hasattr(mesh, "setSlices"):
                mesh.setSlices(84)
            mat = QPhongAlphaMaterial3D(ent)
            mat.setAlpha(float(alpha))
            mat.setDiffuse(atmosphere_color)
            try:
                mat.setAmbient(atmosphere_color.lighter(120))
            except Exception:
                pass
            tr = QTransform3D(ent)
            ent.addComponent(mesh)
            ent.addComponent(mat)
            ent.addComponent(tr)
            self._planet_overlay_entities.extend([ent, mesh, mat, tr])

    def _build_ring_preview_reference_grid(self, radius: float) -> None:
        grid_radius = max(float(radius) * 2.6, 60.0)
        if self._planet_ring_outer_radius is not None and float(self._planet_ring_outer_radius) > 0.0:
            grid_radius = max(grid_radius, float(self._planet_ring_outer_radius) * 1.18)
        grid_y = -max(float(radius), 8.0)
        line_thickness = max(0.18, grid_radius * 0.0022)
        grid_color = QColor(108, 148, 196, 210) if self._is_dark_theme else QColor(128, 146, 170, 220)
        axis_x_color = QColor(214, 116, 116, 230) if self._is_dark_theme else QColor(166, 74, 74, 220)
        axis_z_color = QColor(114, 176, 226, 230) if self._is_dark_theme else QColor(70, 114, 166, 220)
        divisions = 8
        cell = (grid_radius * 2.0) / float(divisions)

        def add_line(*, x_extent: float, z_extent: float, translation: QVector3D, color: QColor, is_axis: bool = False) -> None:
            ent = QEntity3D(self._root)
            mesh = QCuboidMesh3D()
            mesh.setXExtent(max(0.2, x_extent))
            mesh.setYExtent(max(0.05, line_thickness * (1.35 if is_axis else 1.0)))
            mesh.setZExtent(max(0.2, z_extent))
            mat = QPhongMaterial3D(ent)
            mat.setDiffuse(color)
            try:
                mat.setAmbient(color.lighter(118 if self._is_dark_theme else 96))
            except Exception:
                pass
            tr = QTransform3D(ent)
            tr.setTranslation(translation)
            ent.addComponent(mesh)
            ent.addComponent(mat)
            ent.addComponent(tr)
            self._planet_overlay_entities.extend([ent, mesh, mat, tr])

        half = grid_radius
        for index in range(divisions + 1):
            offset = -half + (cell * index)
            is_center = abs(offset) <= 1e-6
            add_line(
                x_extent=grid_radius * 2.0,
                z_extent=line_thickness,
                translation=QVector3D(0.0, grid_y, offset),
                color=axis_x_color if is_center else grid_color,
                is_axis=is_center,
            )
            add_line(
                x_extent=line_thickness,
                z_extent=grid_radius * 2.0,
                translation=QVector3D(offset, grid_y, 0.0),
                color=axis_z_color if is_center else grid_color,
                is_axis=is_center,
            )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_screen_constrained_size()
        QTimer.singleShot(0, self._apply_initial_preview_fit)

    def closeEvent(self, event) -> None:
        self._preview_auto_fit_pending = False
        super().closeEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_preview_camera_projection()

    def _preview_camera_is_usable(self) -> bool:
        camera = getattr(self, "_camera", None)
        if camera is None:
            return False
        try:
            return bool(isValid(self) and isValid(camera))
        except Exception:
            return False

    def _apply_initial_preview_fit(self) -> None:
        if not self._preview_camera_is_usable():
            self._preview_auto_fit_pending = False
            return
        self._sync_preview_camera_projection()
        if not bool(getattr(self, "_preview_auto_fit_pending", False)):
            return
        self._preview_auto_fit_pending = False
        if self._preview_bounds is not None:
            self._apply_native_preview_bounds(self._camera, self._preview_bounds)

    def fit_preview_to_view(self) -> None:
        self._preview_auto_fit_pending = False
        if not self._preview_camera_is_usable():
            return
        self._sync_preview_camera_projection()
        if self._preview_bounds is not None:
            self._apply_native_preview_bounds(self._camera, self._preview_bounds)

    def _effective_preview_aspect_ratio(self) -> float:
        container = getattr(self, "_preview_container", None)
        if container is not None:
            width = max(1, int(container.width()))
            height = max(1, int(container.height()))
            if width > 0 and height > 0:
                return max(float(width) / float(height), 0.1)
        return 16.0 / 9.0

    def _sync_preview_camera_projection(self) -> None:
        if not self._preview_camera_is_usable():
            return
        camera = self._camera
        try:
            near_plane, far_plane = self._preview_projection_planes()
            camera.lens().setPerspectiveProjection(45.0, self._effective_preview_aspect_ratio(), near_plane, far_plane)
        except Exception:
            pass

    def _preview_projection_planes(self) -> tuple[float, float]:
        bounds = getattr(self, "_preview_bounds", None)
        radius = 1.0
        if bounds is not None:
            try:
                radius = max(float(getattr(bounds, "radius", 0.0) or 0.0), 1.0)
            except Exception:
                radius = 1.0
        distance = max(1.0, float(getattr(self, "_camera_distance", 120.0) or 120.0))
        near_plane = max(0.1, min(250.0, radius * 0.03, distance * 0.18))
        far_plane = max(50000.0, distance + (radius * 6.5), radius * 9.0)
        self._max_orbit_distance = max(50000.0, far_plane * 0.82)
        return near_plane, far_plane

    def _apply_screen_constrained_size(self) -> None:
        screen = self.screen()
        if screen is None:
            window_handle = self.windowHandle()
            if window_handle is not None:
                screen = window_handle.screen()
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(900, 700)
            return
        available = screen.availableGeometry()
        max_width = max(720, available.width() - 40)
        max_height = max(480, available.height() - 40)
        self.setMaximumSize(max_width, max_height)
        target_width = min(900, max_width)
        target_height = min(700, max_height)
        if self.width() > max_width or self.height() > max_height:
            self.resize(min(self.width(), max_width), min(self.height(), max_height))
        elif not self.isVisible():
            self.resize(target_width, target_height)

    def _build_native_render_summary(
        self,
        scene_data: NativePreviewSceneData,
        primitive: str | None,
        native_model: FreelancerMeshData | None,
    ) -> str:
        geometry_count = len(getattr(scene_data, "geometries", ()))
        if geometry_count:
            confidence_values: list[str] = []
            seen_confidence: set[str] = set()
            for geometry in scene_data.geometries:
                confidence = str(getattr(geometry, "confidence", "") or "")
                if confidence and confidence not in seen_confidence:
                    seen_confidence.add(confidence)
                    confidence_values.append(confidence)
            render_path = "native geometry"
            summary = f"Render path: {render_path} | geometries={geometry_count}"
            if confidence_values:
                summary += " | confidence=" + ", ".join(confidence_values)
            return summary
        if native_model is None:
            return ""
        fallback = (primitive or "cube").lower()
        return f"Render path: fallback primitive | primitive={fallback}"

    def _build_jumpgate_preview_entity(self, native_bounds) -> FreelancerBounds:
        gate_radius = max(float(getattr(native_bounds, "radius", 0.0) or 0.0) * 0.78, 14.0)
        ring_thickness = max(gate_radius * 0.12, 1.4)
        hub_radius = max(gate_radius * 0.24, 3.0)
        arrow_offset = gate_radius + max(gate_radius * 0.22, 3.0)

        def make_material(diffuse: QColor, ambient: QColor | None = None) -> QPhongMaterial3D:
            material = QPhongMaterial3D(self._root)
            _disable_backface_culling(material)
            material.setDiffuse(diffuse)
            if ambient is not None and hasattr(material, "setAmbient"):
                try:
                    material.setAmbient(ambient)
                except Exception:
                    pass
            return material

        def add_part(mesh, material: QPhongMaterial3D, translation: QVector3D | None = None, rotation: QQuaternion | None = None) -> None:
            entity = QEntity3D(self._root)
            transform = QTransform3D(entity)
            try:
                mesh.setParent(entity)
            except Exception:
                pass
            try:
                material.setParent(entity)
            except Exception:
                pass
            if translation is not None:
                transform.setTranslation(translation)
            if rotation is not None:
                transform.setRotation(rotation)
            entity.addComponent(mesh)
            entity.addComponent(transform)
            entity.addComponent(material)
            self._native_mesh_entities.append(entity)
            self._native_mesh_refs.extend([entity, mesh, transform, material])

        def add_portal_ring(radius: float, thickness: float, color: QColor, segments: int = 16) -> None:
            segment_count = max(segments, 3)
            arc_len = max(1.0, (2.0 * math.pi * radius) / segment_count * 0.92)
            for index in range(segment_count):
                angle = (2.0 * math.pi * index) / segment_count
                mesh = QCuboidMesh3D()
                mesh.setXExtent(max(0.8, thickness * 0.55))
                mesh.setYExtent(max(0.9, thickness * 0.62))
                mesh.setZExtent(arc_len)
                add_part(
                    mesh,
                    make_material(color, QColor(54, 70, 96)),
                    translation=QVector3D(math.cos(angle) * radius, math.sin(angle) * radius, 0.0),
                    rotation=QQuaternion.fromAxisAndAngle(0.0, 0.0, 1.0, float(math.degrees(angle))),
                )

        add_portal_ring(gate_radius, ring_thickness, QColor(154, 164, 186), segments=18)
        add_portal_ring(gate_radius * 1.18, ring_thickness * 0.55, QColor(116, 126, 152), segments=20)

        for index in range(6):
            spoke_mesh = QCuboidMesh3D()
            spoke_mesh.setXExtent(max(0.8, ring_thickness * 0.48))
            spoke_mesh.setYExtent(max(0.7, ring_thickness * 0.42))
            spoke_mesh.setZExtent(max(4.0, gate_radius * 0.95))
            add_part(
                spoke_mesh,
                make_material(QColor(108, 116, 142), QColor(56, 64, 88)),
                translation=QVector3D(0.0, 0.0, gate_radius * 0.58),
                rotation=QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, float(index * 60)),
            )

        hub_mesh = QSphereMesh3D()
        hub_mesh.setRadius(hub_radius)
        add_part(hub_mesh, make_material(QColor(132, 186, 255), QColor(58, 86, 116)))

        if QConeMesh3D is not None:
            front_mesh = QConeMesh3D()
            front_mesh.setLength(max(2.4, gate_radius * 0.32))
            front_mesh.setBottomRadius(max(1.0, gate_radius * 0.1))
            try:
                front_mesh.setTopRadius(0.0)
            except Exception:
                pass
        else:
            front_mesh = QCylinderMesh3D()
            front_mesh.setLength(max(2.0, gate_radius * 0.28))
            front_mesh.setRadius(max(0.8, gate_radius * 0.08))
        add_part(
            front_mesh,
            make_material(QColor(92, 230, 130), QColor(44, 84, 54)),
            translation=QVector3D(0.0, 0.0, arrow_offset),
            rotation=QQuaternion.fromAxisAndAngle(1.0, 0.0, 0.0, -90.0),
        )

        rear_mesh = QSphereMesh3D()
        rear_mesh.setRadius(max(0.9, gate_radius * 0.1))
        add_part(
            rear_mesh,
            make_material(QColor(236, 108, 98), QColor(88, 50, 44)),
            translation=QVector3D(0.0, 0.0, -arrow_offset),
        )

        extent = gate_radius * 1.35
        z_extent = arrow_offset + max(gate_radius * 0.32, 3.0)
        return FreelancerBounds(
            min_xyz=(-extent, -extent, -z_extent),
            max_xyz=(extent, extent, z_extent),
            radius=max(extent, z_extent) * 1.1,
        )

    def _build_native_model_panel(self, native_model: FreelancerMeshData, scene_data: NativePreviewSceneData) -> QWidget:
        panel = QWidget(self)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        summary_grp = QGroupBox("Freelancer Native Model")
        summary_form = QFormLayout(summary_grp)
        for label, value in build_native_model_debug_rows(native_model):
            summary_form.addRow(f"{label}:", QLabel(value))
        panel_layout.addWidget(summary_grp)

        if native_model.nodes:
            nodes_grp = QGroupBox("UTF Nodes")
            nodes_layout = QVBoxLayout(nodes_grp)
            nodes_list = QListWidget(nodes_grp)
            nodes_list.setObjectName("native_nodes_list")
            for node in native_model.nodes[:40]:
                text = node.name
                if node.parent_name:
                    text += f" <- {node.parent_name}"
                if node.is_data_node:
                    text += " [data]"
                nodes_list.addItem(text)
            nodes_layout.addWidget(nodes_list)
            panel_layout.addWidget(nodes_grp)

        if native_model.parts:
            parts_grp = QGroupBox("Parts")
            parts_layout = QVBoxLayout(parts_grp)
            parts_list = QListWidget(parts_grp)
            parts_list.setObjectName("native_parts_list")
            for part in native_model.parts:
                item_text = part.name
                if part.cmp_index is not None:
                    item_text += f" | idx={part.cmp_index}"
                if part.source_name:
                    item_text += f" -> {part.source_name}"
                if part.file_name:
                    item_text += f" | file={part.file_name}"
                if part.object_name:
                    item_text += f" | object={part.object_name}"
                parts_list.addItem(item_text)
            parts_layout.addWidget(parts_list)
            panel_layout.addWidget(parts_grp)

        if native_model.preview_nodes:
            model_nodes_grp = QGroupBox("Model Nodes")
            model_nodes_layout = QVBoxLayout(model_nodes_grp)
            model_nodes_list = QListWidget(model_nodes_grp)
            model_nodes_list.setObjectName("native_model_nodes_list")
            for model_node in native_model.preview_nodes:
                item_text = f"{model_node.model_name} | refs={model_node.vmesh_ref_count}"
                if model_node.level_names:
                    item_text += f" | levels={', '.join(model_node.level_names)}"
                if model_node.matched_part_name:
                    item_text += f" | part={model_node.matched_part_name}"
                if model_node.source_names:
                    item_text += f" | src={', '.join(model_node.source_names)}"
                item_text += f" | blocks={model_node.vmesh_data_block_count}"
                item_text += f" | bytes={model_node.total_vmesh_data_bytes}"
                if model_node.bounds is not None:
                    radius = model_node.bounds.radius or 0.0
                    item_text += f" | r={radius:.2f}"
                model_nodes_list.addItem(item_text)
            model_nodes_layout.addWidget(model_nodes_list)
            panel_layout.addWidget(model_nodes_grp)

        if native_model.preview_mesh_bindings:
            preview_mesh_grp = QGroupBox("Native Preview Meshes")
            preview_mesh_layout = QVBoxLayout(preview_mesh_grp)
            preview_mesh_list = QListWidget(preview_mesh_grp)
            preview_mesh_list.setObjectName("native_preview_mesh_list")
            for binding in native_model.preview_mesh_bindings:
                item_text = binding.model_name
                if binding.level_name:
                    item_text += f" | level={binding.level_name}"
                item_text += f" | refs={binding.vmesh_ref_count}"
                item_text += f" | verts={binding.vertex_count}"
                item_text += f" | indices={binding.index_count}"
                item_text += f" | tris={binding.triangle_count}"
                item_text += f" | groups={binding.group_count}"
                item_text += f" | blocks={binding.vmesh_data_block_count}"
                item_text += f" | bytes={binding.total_vmesh_data_bytes}"
                preview_mesh_list.addItem(item_text)
            preview_mesh_layout.addWidget(preview_mesh_list)
            panel_layout.addWidget(preview_mesh_grp)

        if native_model.preview_geometry_candidates:
            geometry_grp = QGroupBox("Native Geometry Candidates")
            geometry_layout = QVBoxLayout(geometry_grp)
            geometry_list = QListWidget(geometry_grp)
            geometry_list.setObjectName("native_geometry_candidate_list")
            for candidate in native_model.preview_geometry_candidates:
                item_text = candidate.model_name
                if candidate.level_name:
                    item_text += f" | level={candidate.level_name}"
                item_text += f" | stage={candidate.decode_stage}"
                item_text += f" | render={'yes' if candidate.ready_for_native_render else 'no'}"
                item_text += f" | verts={candidate.vertex_count}"
                item_text += f" | tris={candidate.triangle_count}"
                item_text += f" | blocks={candidate.vmesh_data_block_count}"
                item_text += f" | bytes={candidate.total_vmesh_data_bytes}"
                geometry_list.addItem(item_text)
            geometry_layout.addWidget(geometry_list)
            panel_layout.addWidget(geometry_grp)

        if native_model.preview_submeshes:
            submesh_grp = QGroupBox("Native Submeshes")
            submesh_layout = QVBoxLayout(submesh_grp)
            submesh_list = QListWidget(submesh_grp)
            submesh_list.setObjectName("native_submesh_list")
            for submesh in native_model.preview_submeshes[:40]:
                item_text = submesh.model_name
                if submesh.level_name:
                    item_text += f" | level={submesh.level_name}"
                item_text += f" | v={submesh.vertex_start}+{submesh.vertex_count}"
                item_text += f" | i={submesh.index_start}+{submesh.index_count}"
                item_text += f" | g={submesh.group_start}+{submesh.group_count}"
                item_text += f" | tris={submesh.triangle_count}"
                submesh_list.addItem(item_text)
            submesh_layout.addWidget(submesh_list)
            panel_layout.addWidget(submesh_grp)

        if native_model.preview_geometry_sources:
            source_grp = QGroupBox("Native Geometry Sources")
            source_layout = QVBoxLayout(source_grp)
            source_list = QListWidget(source_grp)
            source_list.setObjectName("native_geometry_source_list")
            for source in native_model.preview_geometry_sources[:40]:
                item_text = source.model_name
                if source.level_name:
                    item_text += f" | level={source.level_name}"
                item_text += f" | ref={source.mesh_data_reference}"
                item_text += f" | resolved={'yes' if source.resolved else 'no'}"
                item_text += f" | via={source.resolution_hint}"
                if source.matched_block_index is not None:
                    item_text += f" | block={source.matched_block_index}"
                item_text += f" | tris={source.triangle_count}"
                source_list.addItem(item_text)
            source_layout.addWidget(source_list)
            panel_layout.addWidget(source_grp)

        if native_model.preview_layout_guesses:
            layout_grp = QGroupBox("Native Layout Guesses")
            layout_layout = QVBoxLayout(layout_grp)
            layout_list = QListWidget(layout_grp)
            layout_list.setObjectName("native_layout_guess_list")
            for guess in native_model.preview_layout_guesses[:40]:
                item_text = guess.model_name
                if guess.level_name:
                    item_text += f" | level={guess.level_name}"
                item_text += f" | conf={guess.confidence}"
                if guess.header_size is not None:
                    item_text += f" | h={guess.header_size}"
                if guess.vertex_stride is not None:
                    item_text += f" | vs={guess.vertex_stride}"
                if guess.index_size is not None:
                    item_text += f" | is={guess.index_size}"
                if guess.remaining_bytes is not None:
                    item_text += f" | rem={guess.remaining_bytes}"
                layout_list.addItem(item_text)
            layout_layout.addWidget(layout_list)
            panel_layout.addWidget(layout_grp)

        if native_model.preview_buffer_slices:
            slice_grp = QGroupBox("Native Buffer Slices")
            slice_layout = QVBoxLayout(slice_grp)
            slice_list = QListWidget(slice_grp)
            slice_list.setObjectName("native_buffer_slice_list")
            for buf in native_model.preview_buffer_slices[:40]:
                item_text = buf.model_name
                if buf.level_name:
                    item_text += f" | level={buf.level_name}"
                item_text += f" | h={buf.header_offset}+{buf.header_size}"
                item_text += f" | v={buf.vertex_offset}+{buf.vertex_bytes}"
                item_text += f" | i={buf.index_offset}+{buf.index_bytes}"
                item_text += f" | rem={buf.remaining_bytes}"
                item_text += f" | conf={buf.confidence}"
                slice_list.addItem(item_text)
            slice_layout.addWidget(slice_list)
            panel_layout.addWidget(slice_grp)

        if native_model.material_references:
            material_grp = QGroupBox("Native Material References")
            material_layout = QVBoxLayout(material_grp)
            material_list = QListWidget(material_grp)
            material_list.setObjectName("native_material_reference_list")
            for ref in native_model.material_references[:40]:
                item_text = f"{ref.kind}: {ref.value}"
                if ref.node_name:
                    item_text += f" | node={ref.node_name}"
                material_list.addItem(item_text)
            material_layout.addWidget(material_list)
            panel_layout.addWidget(material_grp)

        if native_model.preview_material_bindings:
            binding_grp = QGroupBox("Native Material Bindings")
            binding_layout = QVBoxLayout(binding_grp)
            binding_list = QListWidget(binding_grp)
            binding_list.setObjectName("native_material_binding_list")
            for binding in native_model.preview_material_bindings[:40]:
                item_text = binding.model_name
                if binding.level_name:
                    item_text += f" | level={binding.level_name}"
                if binding.part_name:
                    item_text += f" | part={binding.part_name}"
                item_text += f" | g={binding.group_start}+{binding.group_count}"
                if binding.texture_value:
                    item_text += f" | tex={binding.texture_value}"
                if binding.texture_candidates:
                    item_text += f" | texs={len(binding.texture_candidates)}"
                if binding.material_value:
                    item_text += f" | mat={binding.material_value}"
                item_text += f" | via={binding.match_hint}"
                binding_list.addItem(item_text)
            binding_layout.addWidget(binding_list)
            panel_layout.addWidget(binding_grp)

        if native_model.preview_material_groups:
            group_grp = QGroupBox("Native Material Groups")
            group_layout = QVBoxLayout(group_grp)
            group_list = QListWidget(group_grp)
            group_list.setObjectName("native_material_group_list")
            for group in native_model.preview_material_groups[:40]:
                item_text = f"count={group.binding_count}"
                if group.texture_value:
                    item_text += f" | tex={group.texture_value}"
                if group.texture_candidates:
                    item_text += f" | texs={len(group.texture_candidates)}"
                if group.material_value:
                    item_text += f" | mat={group.material_value}"
                if group.model_names:
                    item_text += f" | models={', '.join(group.model_names[:3])}"
                if group.group_ranges:
                    item_text += " | groups=" + ",".join(
                        f"{start}+{count}" for start, count in group.group_ranges[:3]
                    )
                item_text += f" | via={group.match_hint}"
                group_list.addItem(item_text)
            group_layout.addWidget(group_list)
            panel_layout.addWidget(group_grp)

        if self._native_texture_path is not None:
            resolved_grp = QGroupBox("Resolved Native Texture")
            resolved_layout = QVBoxLayout(resolved_grp)
            resolved_label = QLabel(str(self._native_texture_path), resolved_grp)
            resolved_label.setObjectName("native_resolved_texture_label")
            resolved_label.setWordWrap(True)
            resolved_layout.addWidget(resolved_label)
            panel_layout.addWidget(resolved_grp)

        if native_model.cmp_fix_records:
            fix_grp = QGroupBox("CMP Fix Records")
            fix_layout = QVBoxLayout(fix_grp)
            fix_list = QListWidget(fix_grp)
            fix_list.setObjectName("native_cmp_fix_list")
            for record in native_model.cmp_fix_records[:40]:
                item_text = record.part_name
                if record.part_index is not None:
                    item_text += f" | idx={record.part_index}"
                item_text += f" | rec={record.record_index}"
                item_text += f" | bytes={record.record_size}"
                item_text += f" | f32={record.float_count}"
                item_text += f" | rows={record.row_count}x{record.row_width}"
                if record.first_f32:
                    item_text += " | first=" + ",".join(f"{value:.3f}" for value in record.first_f32[:4])
                fix_list.addItem(item_text)
            fix_layout.addWidget(fix_list)
            panel_layout.addWidget(fix_grp)

        if native_model.cmp_transform_hints:
            hint_grp = QGroupBox("CMP Transform Hints")
            hint_layout = QVBoxLayout(hint_grp)
            hint_list = QListWidget(hint_grp)
            hint_list.setObjectName("native_cmp_transform_hint_list")
            for hint in native_model.cmp_transform_hints[:40]:
                item_text = hint.part_name
                if hint.part_index is not None:
                    item_text += f" | idx={hint.part_index}"
                if hint.translation_xyz is not None:
                    tx, ty, tz = hint.translation_xyz
                    item_text += f" | t=({tx:.3f},{ty:.3f},{tz:.3f})"
                if hint.translation_magnitude is not None:
                    item_text += f" | |t|={hint.translation_magnitude:.3f}"
                if hint.leading_vector_xyz is not None:
                    vx, vy, vz = hint.leading_vector_xyz
                    item_text += f" | v=({vx:.3f},{vy:.3f},{vz:.3f})"
                hint_list.addItem(item_text)
            hint_layout.addWidget(hint_list)
            panel_layout.addWidget(hint_grp)

        reference_rows = build_native_preview_reference_rows(native_model, self._native_scene_data)
        if reference_rows:
            ref_grp = QGroupBox("Native Reference Checks")
            ref_layout = QVBoxLayout(ref_grp)
            ref_list = QListWidget(ref_grp)
            ref_list.setObjectName("native_reference_check_list")
            for row in sort_native_preview_reference_rows(reference_rows)[:40]:
                cx, cy, cz = row.center_xyz
                item_text = row.model_name
                if row.part_name:
                    item_text += f" | part={row.part_name}"
                item_text += f" | idx={row.geometry_index}"
                item_text += f" | c=({cx:.3f},{cy:.3f},{cz:.3f})"
                if row.raw_center_xyz != row.center_xyz:
                    rcx, rcy, rcz = row.raw_center_xyz
                    item_text += f" | lc=({rcx:.3f},{rcy:.3f},{rcz:.3f})"
                item_text += f" | r={row.radius:.3f}"
                item_text += f" | tex={'yes' if row.has_texture else 'no'}"
                if row.texture_name:
                    item_text += f" | tex={row.texture_name}"
                if row.translation_xyz is not None:
                    tx, ty, tz = row.translation_xyz
                    item_text += f" | t=({tx:.3f},{ty:.3f},{tz:.3f})"
                    if row.translation_source:
                        item_text += f" | t-src={row.translation_source}"
                    item_text += f" | d={row.translation_delta:.3f}"
                    item_text += f" | ok={'yes' if row.translation_matches_center else 'no'}"
                    if row.translation_severity:
                        item_text += f" | sev={row.translation_severity}"
                if row.rotation_severity:
                    item_text += f" | rot={row.rotation_severity}"
                    if row.rotation_source:
                        item_text += f" | r-src={row.rotation_source}"
                    if row.rotation_determinant is not None:
                        item_text += f" | det={row.rotation_determinant:.3f}"
                    if row.rotation_orthogonality_error is not None:
                        item_text += f" | ortho={row.rotation_orthogonality_error:.3f}"
                ref_list.addItem(item_text)
            summary = build_native_preview_reference_summary(reference_rows)
            summary_label = QLabel(
                (
                    f"rows={summary.total_rows} | hints={summary.rows_with_translation_hint} "
                    f"| match={summary.rows_with_matching_translation} "
                    f"| mismatch={summary.rows_with_mismatching_translation} "
                    f"| high={summary.rows_with_high_mismatch} "
                    f"| rot={summary.rows_with_rotation_hint} "
                    f"| rot-risk={summary.rows_with_rotation_warn_or_high} "
                    f"| t-combined={summary.rows_with_combined_translation_hint} "
                    f"| t-local={summary.rows_with_local_translation_fallback} "
                    f"| r-combined={summary.rows_with_combined_rotation_hint} "
                    f"| r-local={summary.rows_with_local_rotation_fallback} "
                    f"| no-tex={summary.rows_without_texture} "
                    f"| max-delta={summary.max_translation_delta:.3f}"
                ),
                ref_grp,
            )
            summary_label.setObjectName("native_reference_summary_label")
            ref_layout.addWidget(ref_list)
            ref_layout.addWidget(summary_label)
            panel_layout.addWidget(ref_grp)

        if native_model.vmesh_references:
            vmesh_grp = QGroupBox("VMesh References")
            vmesh_layout = QVBoxLayout(vmesh_grp)
            vmesh_list = QListWidget(vmesh_grp)
            vmesh_list.setObjectName("native_vmesh_list")
            for name in native_model.vmesh_references:
                vmesh_list.addItem(name)
            vmesh_layout.addWidget(vmesh_list)
            panel_layout.addWidget(vmesh_grp)

        if native_model.vmesh_data_blocks:
            vmesh_data_grp = QGroupBox("VMesh Data Blocks")
            vmesh_data_layout = QVBoxLayout(vmesh_data_grp)
            vmesh_data_list = QListWidget(vmesh_data_grp)
            vmesh_data_list.setObjectName("native_vmesh_data_list")
            for block in native_model.vmesh_data_blocks:
                item_text = str(block.source_name or "<unnamed>")
                item_text += f" | bytes={block.used_size}"
                if block.header_hex:
                    item_text += f" | hex={block.header_hex}"
                if block.header_u32:
                    item_text += " | u32=" + ",".join(str(value) for value in block.header_u32[:4])
                vmesh_data_list.addItem(item_text)
            vmesh_data_layout.addWidget(vmesh_data_list)
            panel_layout.addWidget(vmesh_data_grp)

        if native_model.warnings:
            warn_grp = QGroupBox("Warnings")
            warn_layout = QVBoxLayout(warn_grp)
            warn_list = QListWidget(warn_grp)
            warn_list.setObjectName("native_warning_list")
            for warning in native_model.warnings:
                warn_list.addItem(warning)
            warn_layout.addWidget(warn_list)
            panel_layout.addWidget(warn_grp)

        panel_layout.addStretch(1)
        return panel

    def _build_preview_bounds_entity(self, bounds) -> None:
        entity = QEntity3D(self._root)
        mesh = QCuboidMesh3D()
        x_extent = max(bounds.max_xyz[0] - bounds.min_xyz[0], 1.0)
        y_extent = max(bounds.max_xyz[1] - bounds.min_xyz[1], 1.0)
        z_extent = max(bounds.max_xyz[2] - bounds.min_xyz[2], 1.0)
        if hasattr(mesh, "setXExtent"):
            mesh.setXExtent(x_extent)
        if hasattr(mesh, "setYExtent"):
            mesh.setYExtent(y_extent)
        if hasattr(mesh, "setZExtent"):
            mesh.setZExtent(z_extent)
        transform = QTransform3D(entity)
        transform.setTranslation(
            QVector3D(
                (bounds.min_xyz[0] + bounds.max_xyz[0]) * 0.5,
                (bounds.min_xyz[1] + bounds.max_xyz[1]) * 0.5,
                (bounds.min_xyz[2] + bounds.max_xyz[2]) * 0.5,
            )
        )
        material = QPhongMaterial3D(entity)
        _disable_backface_culling(material)
        material.setDiffuse(QColor(220, 220, 220))
        entity.addComponent(mesh)
        entity.addComponent(transform)
        entity.addComponent(material)
        entity.setEnabled(False)
        self._bounds_entity = entity

    def _set_bounds_visible(self, visible: bool) -> None:
        if self._bounds_entity is not None:
            self._bounds_entity.setEnabled(bool(visible))

    def _set_wireframe_visible(self, visible: bool) -> None:
        for entity in self._wireframe_entities:
            entity.setEnabled(bool(visible))

    def _set_mesh_visible(self, visible: bool) -> None:
        self._mesh_entity.setEnabled(bool(visible))
        for entity in self._native_mesh_entities:
            entity.setEnabled(bool(visible))

    def _set_materials_visible(self, use_textures: bool) -> None:
        for entity, textured_mat, colored_mat in self._material_pairs:
            if use_textures:
                entity.removeComponent(colored_mat)
                entity.addComponent(textured_mat)
            else:
                entity.removeComponent(textured_mat)
                entity.addComponent(colored_mat)

    def _set_part_names_visible(self, visible: bool) -> None:
        if self._part_names_label is not None:
            self._part_names_label.setVisible(bool(visible and self._native_part_names))

    def _set_preview_background_white(self, enabled: bool) -> None:
        if enabled:
            self._preview_background_color = QColor(255, 255, 255)
        else:
            self._preview_background_color = QColor(0, 0, 0) if self._is_dark_theme else QColor(255, 255, 255)
        self._apply_preview_background_color()

    def _apply_preview_background_color(self) -> None:
        if self._frame_graph is not None and hasattr(self._frame_graph, "setClearColor"):
            try:
                self._frame_graph.setClearColor(self._preview_background_color)
            except Exception:
                pass

    def _reset_preview_camera(self) -> None:
        self._preview_zoom_factor = 1.0
        if self._preview_bounds is not None and self._preview_camera_is_usable():
            self._apply_native_preview_bounds(self._camera, self._preview_bounds)
        else:
            self._sync_preview_camera_polar_state()

    def get_preview_camera_state(self) -> dict[str, object] | None:
        if not self._preview_camera_is_usable():
            return None
        try:
            center = self._camera.viewCenter()
            position = self._camera.position()
        except Exception:
            return None
        return {
            "center": (float(center.x()), float(center.y()), float(center.z())),
            "position": (float(position.x()), float(position.y()), float(position.z())),
            "distance": float(self._camera_distance),
            "yaw_deg": float(self._camera_yaw_deg),
            "pitch_deg": float(self._camera_pitch_deg),
            "zoom_factor": float(self._preview_zoom_factor),
        }

    def set_preview_camera_state(self, state: dict[str, object] | None) -> None:
        if not state or not self._preview_camera_is_usable():
            return
        try:
            center = state.get("center")
            position = state.get("position")
            if isinstance(center, (tuple, list)) and len(center) >= 3:
                self._camera.setViewCenter(QVector3D(float(center[0]), float(center[1]), float(center[2])))
            if isinstance(position, (tuple, list)) and len(position) >= 3:
                self._camera.setPosition(QVector3D(float(position[0]), float(position[1]), float(position[2])))
            self._camera_distance = max(1.0, float(state.get("distance", self._camera_distance) or self._camera_distance))
            self._camera_yaw_deg = float(state.get("yaw_deg", self._camera_yaw_deg) or self._camera_yaw_deg)
            self._camera_pitch_deg = float(state.get("pitch_deg", self._camera_pitch_deg) or self._camera_pitch_deg)
            self._preview_zoom_factor = max(0.1, min(5.0, float(state.get("zoom_factor", self._preview_zoom_factor) or self._preview_zoom_factor)))
            self._sync_preview_camera_projection()
        except Exception:
            self._sync_preview_camera_polar_state()

    def set_preview_zoom_factor(self, zoom_factor: float) -> None:
        try:
            value = float(zoom_factor)
        except Exception:
            return
        self._preview_zoom_factor = max(0.1, min(5.0, value))
        if not self._preview_camera_is_usable():
            return
        if self._preview_bounds is not None:
            self._apply_native_preview_bounds(self._camera, self._preview_bounds)
            return
        try:
            center = self._camera.viewCenter()
            position = self._camera.position()
            offset = position - center
            if offset.lengthSquared() <= 1e-9:
                return
            self._camera.setPosition(center + (offset.normalized() * (120.0 / self._preview_zoom_factor)))
        except Exception:
            pass

    def get_preview_zoom_factor(self) -> float:
        return float(getattr(self, "_preview_zoom_factor", 1.0))

    def _apply_native_preview_bounds(self, camera, bounds) -> None:
        try:
            if camera is None or not isValid(camera):
                return
        except Exception:
            return
        min_x, min_y, min_z = bounds.min_xyz
        max_x, max_y, max_z = bounds.max_xyz
        center = QVector3D(
            (min_x + max_x) * 0.5,
            (min_y + max_y) * 0.5,
            (min_z + max_z) * 0.5,
        )
        radius = max(bounds.radius or 0.0, 1.0)
        camera.setViewCenter(center)
        zoom_factor = max(0.1, float(getattr(self, "_preview_zoom_factor", 1.0)))
        if self._ring_preview_mode:
            offset = QVector3D(radius * 1.22, radius * 0.9, radius * 3.32) / zoom_factor
        else:
            offset = QVector3D(radius * 1.18, radius * 0.84, radius * 3.05) / zoom_factor
        self._camera_distance = max(1.0, float(offset.length()))
        self._camera_yaw_deg = math.degrees(math.atan2(float(offset.x()), float(offset.z())))
        ratio = max(-1.0, min(1.0, float(offset.y()) / max(1.0, float(offset.length()))))
        self._camera_pitch_deg = math.degrees(math.asin(ratio))
        self._sync_preview_camera_projection()
        self._apply_preview_camera_pose()


# ══════════════════════════════════════════════════════════════════════
#  System-Erstellungsdialog
# ══════════════════════════════════════════════════════════════════════

class ObjectRingDialog(QDialog):
    """Ring-Dialog mit eingebetteter Live-Preview fuer beliebige Objekte."""

    def __init__(
        self,
        parent,
        *,
        object_label: str,
        ring_presets: list[str],
        initial_state: dict[str, object] | None = None,
        preview_builder: Callable[[dict[str, object], QWidget], QWidget | None] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Ring konfigurieren")
        self.resize(1120, 760)
        self._preview_builder = preview_builder
        self._preview_widget: QWidget | None = None
        self._preview_refresh_timer = QTimer(self)
        self._preview_refresh_timer.setSingleShot(True)
        self._preview_refresh_timer.setInterval(180)
        self._preview_refresh_timer.timeout.connect(self._refresh_preview)
        initial = dict(initial_state or {})

        layout = QVBoxLayout(self)
        header = QLabel(f"Objekt: {object_label}", self)
        header.setWordWrap(True)
        header.setStyleSheet("font-weight: 600; font-size: 11pt;")
        layout.addWidget(header)

        content_row = QHBoxLayout()
        layout.addLayout(content_row, 1)

        controls = QWidget(self)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout()
        controls_layout.addLayout(form)

        self.enable_cb = QCheckBox("Ring aktiv", self)
        self.enable_cb.setChecked(bool(initial.get("enabled", True)))
        form.addRow(self.enable_cb)

        self.ring_ini_cb = QComboBox(self)
        self.ring_ini_cb.setEditable(True)
        self.ring_ini_cb.addItems([str(item) for item in ring_presets if str(item).strip()])
        self.ring_ini_cb.setCurrentText(str(initial.get("ring_ini", "") or ""))
        form.addRow("Ring preset:", self.ring_ini_cb)

        self.zone_nick_edit = QLineEdit(str(initial.get("zone_nickname", "") or ""), self)
        form.addRow("Zone nickname:", self.zone_nick_edit)

        self.outer_spin = QDoubleSpinBox(self)
        self.outer_spin.setRange(1.0, 9_999_999.0)
        self.outer_spin.setDecimals(2)
        self.outer_spin.setValue(float(initial.get("outer_radius", 3000.0) or 3000.0))
        form.addRow("Outer radius:", self.outer_spin)

        self.inner_spin = QDoubleSpinBox(self)
        self.inner_spin.setRange(1.0, 9_999_999.0)
        self.inner_spin.setDecimals(2)
        self.inner_spin.setValue(float(initial.get("inner_radius", 1500.0) or 1500.0))
        form.addRow("Inner radius:", self.inner_spin)

        self.thickness_spin = QDoubleSpinBox(self)
        self.thickness_spin.setRange(1.0, 9_999_999.0)
        self.thickness_spin.setDecimals(2)
        self.thickness_spin.setValue(float(initial.get("thickness", 500.0) or 500.0))
        form.addRow("Thickness:", self.thickness_spin)

        self.rot_x_spin = QDoubleSpinBox(self)
        self.rot_x_spin.setRange(-360.0, 360.0)
        self.rot_x_spin.setDecimals(2)
        self.rot_x_spin.setValue(float(initial.get("rotate_x", 0.0) or 0.0))
        form.addRow("Rotate X:", self.rot_x_spin)

        self.rot_y_spin = QDoubleSpinBox(self)
        self.rot_y_spin.setRange(-360.0, 360.0)
        self.rot_y_spin.setDecimals(2)
        self.rot_y_spin.setValue(float(initial.get("rotate_y", 0.0) or 0.0))
        form.addRow("Rotate Y:", self.rot_y_spin)

        self.rot_z_spin = QDoubleSpinBox(self)
        self.rot_z_spin.setRange(-360.0, 360.0)
        self.rot_z_spin.setDecimals(2)
        self.rot_z_spin.setValue(float(initial.get("rotate_z", 0.0) or 0.0))
        form.addRow("Rotate Z:", self.rot_z_spin)

        help_lbl = QLabel(
            "Freelancer speichert Ringe direkt am Objekt und in einer eigenen `shape = ring` Zone. "
            "Änderungen in diesem Dialog aktualisieren die 3D-Vorschau sofort.",
            self,
        )
        help_lbl.setWordWrap(True)
        help_lbl.setStyleSheet("color: palette(mid);")
        controls_layout.addWidget(help_lbl)
        controls_layout.addStretch(1)
        content_row.addWidget(controls, 0)

        preview_group = QGroupBox("3D Preview", self)
        preview_layout = QVBoxLayout(preview_group)
        self._preview_status_lbl = QLabel("Preview wird vorbereitet…", preview_group)
        self._preview_status_lbl.setWordWrap(True)
        preview_layout.addWidget(self._preview_status_lbl)
        self._preview_host = QWidget(preview_group)
        self._preview_host_layout = QVBoxLayout(self._preview_host)
        self._preview_host_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(self._preview_host, 1)
        content_row.addWidget(preview_group, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._accept_with_validation)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.enable_cb.toggled.connect(self._sync_enabled_state)
        self.enable_cb.toggled.connect(self._queue_preview_refresh)
        self.ring_ini_cb.currentTextChanged.connect(self._queue_preview_refresh)
        self.zone_nick_edit.textChanged.connect(self._queue_preview_refresh)
        self.outer_spin.valueChanged.connect(self._queue_preview_refresh)
        self.inner_spin.valueChanged.connect(self._queue_preview_refresh)
        self.thickness_spin.valueChanged.connect(self._queue_preview_refresh)
        self.rot_x_spin.valueChanged.connect(self._queue_preview_refresh)
        self.rot_y_spin.valueChanged.connect(self._queue_preview_refresh)
        self.rot_z_spin.valueChanged.connect(self._queue_preview_refresh)

        self._sync_enabled_state()
        self._refresh_preview()

    def _sync_enabled_state(self) -> None:
        enabled = bool(self.enable_cb.isChecked())
        for widget in (
            self.ring_ini_cb,
            self.zone_nick_edit,
            self.outer_spin,
            self.inner_spin,
            self.thickness_spin,
            self.rot_x_spin,
            self.rot_y_spin,
            self.rot_z_spin,
        ):
            widget.setEnabled(enabled)

    def _queue_preview_refresh(self, *_args) -> None:
        timer = getattr(self, "_preview_refresh_timer", None)
        if timer is None:
            self._refresh_preview()
            return
        timer.start()

    def _refresh_preview(self, *_args) -> None:
        previous_camera_state = None
        if self._preview_widget is not None:
            getter = getattr(self._preview_widget, "get_preview_camera_state", None)
            if callable(getter):
                try:
                    previous_camera_state = getter()
                except Exception:
                    previous_camera_state = None
            self._preview_host_layout.removeWidget(self._preview_widget)
            self._preview_widget.deleteLater()
            self._preview_widget = None
        if not callable(self._preview_builder):
            self._preview_status_lbl.setText("Keine Preview verfügbar.")
            return
        preview = self._preview_builder(self.payload(), self._preview_host)
        if preview is None:
            self._preview_status_lbl.setText("Für dieses Objekt ist aktuell keine 3D-Preview verfügbar.")
            return
        self._preview_widget = preview
        self._preview_host_layout.addWidget(preview, 1)
        setter = getattr(preview, "set_preview_camera_state", None)
        if previous_camera_state is not None and callable(setter):
            try:
                setter(previous_camera_state)
            except Exception:
                pass
        self._preview_status_lbl.setText("Änderungen werden direkt in der Vorschau aktualisiert.")

    def _accept_with_validation(self) -> None:
        payload = self.payload()
        if bool(payload.get("enabled")):
            if not str(payload.get("ring_ini", "") or "").strip():
                QMessageBox.warning(self, "Ring", "Bitte ein Ring-Preset auswählen.")
                return
            if not str(payload.get("zone_nickname", "") or "").strip():
                QMessageBox.warning(self, "Ring", "Bitte einen Zone-Nickname angeben.")
                return
            inner = float(payload.get("inner_radius", 0.0) or 0.0)
            outer = float(payload.get("outer_radius", 0.0) or 0.0)
            if inner >= outer:
                QMessageBox.warning(self, "Ring", "Inner radius muss kleiner als Outer radius sein.")
                return
        self.accept()

    def payload(self) -> dict[str, object]:
        return {
            "enabled": bool(self.enable_cb.isChecked()),
            "ring_ini": str(self.ring_ini_cb.currentText() or "").strip(),
            "zone_nickname": str(self.zone_nick_edit.text() or "").strip(),
            "outer_radius": float(self.outer_spin.value()),
            "inner_radius": float(self.inner_spin.value()),
            "thickness": float(self.thickness_spin.value()),
            "rotate_x": float(self.rot_x_spin.value()),
            "rotate_y": float(self.rot_y_spin.value()),
            "rotate_z": float(self.rot_z_spin.value()),
        }


class SystemCreationDialog(QDialog):
    """Dialog zum Erstellen eines neuen Sternensystems."""

    def __init__(
        self,
        parent,
        music_space: list[str],
        music_danger: list[str],
        music_battle: list[str],
        bg_basic: list[str],
        bg_complex: list[str],
        bg_nebulae: list[str],
        factions: list[str],
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.system_create"))
        self.setMinimumWidth(420)
        layout = QFormLayout(self)

        # 1. Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("z. B. Taharka")
        layout.addRow(tr("dlg.system_name"), self.name_edit)

        # 2. Prefix
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("z. B. TE")
        self.prefix_edit.setMaxLength(4)
        layout.addRow("System Prefix:", self.prefix_edit)

        # 3. Größe
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1000, 10_000_000)
        self.size_spin.setValue(100000)
        layout.addRow(tr("dlg.system_range"), self.size_spin)

        # 4. Space Color
        self._space_rgb = "0, 0, 0"
        space_row = QWidget()
        sl = QHBoxLayout(space_row)
        sl.setContentsMargins(0, 0, 0, 0)
        self.space_color_btn = QPushButton(tr("dlg.pick_color"))
        self.space_color_lbl = QLabel(self._space_rgb)
        self.space_color_btn.clicked.connect(self._pick_space_color)
        sl.addWidget(self.space_color_btn)
        sl.addWidget(self.space_color_lbl)
        layout.addRow("Space Color:", space_row)

        # 5-7. Music
        self.music_space_cb = self._combo(music_space, "music_br_space")
        layout.addRow("Music Space:", self.music_space_cb)
        self.music_danger_cb = self._combo(music_danger, "music_br_danger")
        layout.addRow("Music Danger:", self.music_danger_cb)
        self.music_battle_cb = self._combo(music_battle, "music_br_battle")
        layout.addRow("Music Battle:", self.music_battle_cb)

        # 8. Ambient Color
        self._ambient_rgb = "60, 20, 10"
        ambient_row = QWidget()
        al = QHBoxLayout(ambient_row)
        al.setContentsMargins(0, 0, 0, 0)
        self.ambient_color_btn = QPushButton(tr("dlg.pick_color"))
        self.ambient_color_lbl = QLabel(self._ambient_rgb)
        self.ambient_color_btn.clicked.connect(self._pick_ambient_color)
        al.addWidget(self.ambient_color_btn)
        al.addWidget(self.ambient_color_lbl)
        layout.addRow("Ambient Color:", ambient_row)

        # 9-11. Background
        self.bg_basic_cb = self._combo(
            bg_basic, r"solar\starsphere\starsphere_stars_basic.cmp"
        )
        layout.addRow("Basic Stars:", self.bg_basic_cb)
        self.bg_complex_cb = self._combo(
            bg_complex, r"solar\starsphere\starsphere_br01_stars.cmp"
        )
        layout.addRow("Complex Stars:", self.bg_complex_cb)
        self.bg_nebulae_cb = self._combo(
            bg_nebulae, r"solar\starsphere\starsphere_br01.cmp"
        )
        layout.addRow("Nebulae:", self.bg_nebulae_cb)

        # 12. Light Source Color
        self._light_rgb = "253, 230, 180"
        light_row = QWidget()
        ll = QHBoxLayout(light_row)
        ll.setContentsMargins(0, 0, 0, 0)
        self.light_color_btn = QPushButton(tr("dlg.pick_color"))
        self.light_color_lbl = QLabel(self._light_rgb)
        self.light_color_btn.clicked.connect(self._pick_light_color)
        ll.addWidget(self.light_color_btn)
        ll.addWidget(self.light_color_lbl)
        layout.addRow("Light Source Color:", light_row)

        # Local Faction
        self.faction_cb = self._combo(factions, "li_n_grp")
        layout.addRow("Local Faction:", self.faction_cb)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    @staticmethod
    def _combo(items: list[str], default: str) -> QComboBox:
        cb = QComboBox()
        cb.setEditable(True)
        cb.addItems(items)
        cb.setCurrentText(default)
        configure_contains_completer(cb)
        return cb

    def _pick_space_color(self):
        col = QColorDialog.getColor(parent=self)
        if col.isValid():
            self._space_rgb = f"{col.red()}, {col.green()}, {col.blue()}"
            self.space_color_lbl.setText(self._space_rgb)

    def _pick_ambient_color(self):
        col = QColorDialog.getColor(parent=self)
        if col.isValid():
            self._ambient_rgb = f"{col.red()}, {col.green()}, {col.blue()}"
            self.ambient_color_lbl.setText(self._ambient_rgb)

    def _pick_light_color(self):
        col = QColorDialog.getColor(parent=self)
        if col.isValid():
            self._light_rgb = f"{col.red()}, {col.green()}, {col.blue()}"
            self.light_color_lbl.setText(self._light_rgb)

    def payload(self) -> dict:
        return build_system_creation_payload(
            name=self.name_edit.text(),
            prefix=self.prefix_edit.text(),
            size=self.size_spin.value(),
            space_color=self._space_rgb,
            music_space=self.music_space_cb.currentText(),
            music_danger=self.music_danger_cb.currentText(),
            music_battle=self.music_battle_cb.currentText(),
            ambient_color=self._ambient_rgb,
            bg_basic=self.bg_basic_cb.currentText(),
            bg_complex=self.bg_complex_cb.currentText(),
            bg_nebulae=self.bg_nebulae_cb.currentText(),
            light_color=self._light_rgb,
            local_faction=self.faction_cb.currentText(),
        )


# ══════════════════════════════════════════════════════════════════════
#  SystemSettingsDialog – System-Metadaten bearbeiten
# ══════════════════════════════════════════════════════════════════════

class SystemSettingsDialog(QDialog):
    """Dialog zum Bearbeiten der System-Metadaten (Musik, Farben, Hintergrund…)."""

    def __init__(self, parent, *,
                 current: dict,
                 music_options: dict[str, list[str]],
                 bg_options: dict[str, list[str]],
                 factions: list[str],
                 dust_options: list[str]):
        super().__init__(parent)
        nickname = current.get("nickname", "System")
        self.setWindowTitle(f"{nickname} – Einstellungen")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        def _combo(items: list[str], cur: str) -> QComboBox:
            cb = QComboBox()
            cb.setEditable(True)
            cb.addItems(items)
            cb.setCurrentText(cur)
            configure_contains_completer(cb)
            return cb

        # Music
        self.music_space_cb = _combo(music_options.get("space", []),
                                     current.get("music_space", ""))
        form.addRow("Music Space:", self.music_space_cb)

        self.music_danger_cb = _combo(music_options.get("danger", []),
                                      current.get("music_danger", ""))
        form.addRow("Music Danger:", self.music_danger_cb)

        self.music_battle_cb = _combo(music_options.get("battle", []),
                                      current.get("music_battle", ""))
        form.addRow("Music Battle:", self.music_battle_cb)

        # Space Color
        self._space_rgb = current.get("space_color", "0, 0, 0")
        self.space_color_lbl = QLabel(self._space_rgb)
        space_btn = QPushButton(tr("dlg.pick_color"))
        space_btn.clicked.connect(self._pick_space_color)
        space_row = QHBoxLayout()
        space_row.addWidget(space_btn)
        space_row.addWidget(self.space_color_lbl)
        form.addRow("Space Color:", space_row)

        # Local Faction
        self.local_faction_cb = _combo(factions, current.get("local_faction", ""))
        form.addRow("Local Faction:", self.local_faction_cb)

        # Ambient Color
        self._ambient_rgb = current.get("ambient_color", "0, 0, 0")
        self.ambient_color_lbl = QLabel(self._ambient_rgb)
        ambient_btn = QPushButton(tr("dlg.pick_color"))
        ambient_btn.clicked.connect(self._pick_ambient_color)
        ambient_row = QHBoxLayout()
        ambient_row.addWidget(ambient_btn)
        ambient_row.addWidget(self.ambient_color_lbl)
        form.addRow("Ambient Color:", ambient_row)

        # Dust
        self.dust_cb = _combo(dust_options, current.get("dust", ""))
        form.addRow("Dust:", self.dust_cb)

        # Background
        self.bg_basic_cb = _combo(bg_options.get("basic_stars", []),
                                   current.get("bg_basic", ""))
        form.addRow("Background Basic:", self.bg_basic_cb)

        self.bg_complex_cb = _combo(bg_options.get("complex_stars", []),
                                     current.get("bg_complex", ""))
        form.addRow("Background Complex:", self.bg_complex_cb)

        self.bg_nebulae_cb = _combo(bg_options.get("nebulae", []),
                                     current.get("bg_nebulae", ""))
        form.addRow("Background Nebulae:", self.bg_nebulae_cb)

        layout.addLayout(form)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _pick_space_color(self):
        col = QColorDialog.getColor(parent=self)
        if col.isValid():
            self._space_rgb = f"{col.red()}, {col.green()}, {col.blue()}"
            self.space_color_lbl.setText(self._space_rgb)

    def _pick_ambient_color(self):
        col = QColorDialog.getColor(parent=self)
        if col.isValid():
            self._ambient_rgb = f"{col.red()}, {col.green()}, {col.blue()}"
            self.ambient_color_lbl.setText(self._ambient_rgb)

    def result_data(self) -> dict:
        return build_system_settings_result(
            music_space=self.music_space_cb.currentText(),
            music_danger=self.music_danger_cb.currentText(),
            music_battle=self.music_battle_cb.currentText(),
            space_color=self._space_rgb,
            local_faction=self.local_faction_cb.currentText(),
            ambient_color=self._ambient_rgb,
            dust=self.dust_cb.currentText(),
            bg_basic=self.bg_basic_cb.currentText(),
            bg_complex=self.bg_complex_cb.currentText(),
            bg_nebulae=self.bg_nebulae_cb.currentText(),
        )


# ══════════════════════════════════════════════════════════════════════
#  TradeLaneDialog – Tradelane-Parameter eingeben
# ══════════════════════════════════════════════════════════════════════

class TradeLaneDialog(QDialog):
    """Dialog zum Konfigurieren einer neuen Tradelane zwischen zwei Punkten."""

    # Bekannte Loadouts
    _LOADOUTS = [
        "trade_lane_ring_li_01", "trade_lane_ring_li_02",
        "trade_lane_ring_li_03", "trade_lane_ring_br_01",
        "trade_lane_ring_br_02", "trade_lane_ring_co_01",
        "trade_lane_ring_ku_01", "trade_lane_ring_rh_01",
    ]
    _PILOTS = [
        "pilot_solar_easiest", "pilot_solar_easy", "pilot_solar_hard",
    ]

    def __init__(self, parent, *,
                 system_nick: str,
                 start_num: int,
                 ring_count: int,
                 distance: float,
                 factions: list[str],
                 extra_loadouts: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.tradelane_create"))
        self.setMinimumWidth(440)
        self._distance = distance

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        # Anzahl Ringe (vorberechnet, editierbar)
        self.count_spin = QSpinBox()
        self.count_spin.setRange(2, 200)
        self.count_spin.setValue(ring_count)
        form.addRow(tr("dlg.ring_count"), self.count_spin)

        # Abstand zwischen Ringen
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(500, 50000)
        self.spacing_spin.setSingleStep(500)
        self.spacing_spin.setValue(7500)
        self.spacing_spin.setSuffix(tr("dlg.units"))
        self.spacing_spin.valueChanged.connect(self._on_spacing_changed)
        form.addRow(tr("dlg.spacing"), self.spacing_spin)

        # Startnummer
        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, 99999)
        self.start_spin.setValue(start_num)
        form.addRow(tr("dlg.start_number"), self.start_spin)

        # Loadout
        loadouts = list(self._LOADOUTS)
        if extra_loadouts:
            for lo in extra_loadouts:
                if lo not in loadouts:
                    loadouts.append(lo)
        loadouts.sort(key=str.lower)
        self.loadout_cb = QComboBox()
        self.loadout_cb.setEditable(True)
        self.loadout_cb.addItems(loadouts)
        self.loadout_cb.setCurrentText(loadouts[0] if loadouts else "")
        form.addRow("Loadout:", self.loadout_cb)

        # Reputation
        self.reputation_cb = QComboBox()
        self.reputation_cb.setEditable(True)
        self.reputation_cb.addItems(factions)
        configure_contains_completer(self.reputation_cb)
        form.addRow("Reputation:", self.reputation_cb)

        # Difficulty
        self.diff_spin = QSpinBox()
        self.diff_spin.setRange(1, 7)
        self.diff_spin.setValue(1)
        form.addRow("Difficulty Level:", self.diff_spin)

        # Pilot
        self.pilot_cb = QComboBox()
        self.pilot_cb.setEditable(True)
        self.pilot_cb.addItems(self._PILOTS)
        self.pilot_cb.setCurrentText("pilot_solar_easiest")
        form.addRow("Pilot:", self.pilot_cb)

        # Anzeigename
        self.ids_name_edit = QLineEdit("")
        self.ids_name_edit.setPlaceholderText(tr("dlg.tradelane_name_ph"))
        form.addRow(tr("dlg.tradelane_name"), self.ids_name_edit)

        # tradelane_space_name Start
        self.space_name_start_edit = QLineEdit("")
        self.space_name_start_edit.setPlaceholderText(tr("dlg.tradelane_start_name_ph"))
        form.addRow(tr("dlg.tradelane_start_name"), self.space_name_start_edit)

        # tradelane_space_name Ende
        self.space_name_end_edit = QLineEdit("")
        self.space_name_end_edit.setPlaceholderText(tr("dlg.tradelane_end_name_ph"))
        form.addRow(tr("dlg.tradelane_end_name"), self.space_name_end_edit)

        layout.addLayout(form)

        # Info-Label
        info = QLabel(
            f"System: {system_nick}  •  "
            f"Nicknames: {system_nick}_Trade_Lane_Ring_N\n"
            f"{tr('dlg.spacing_info')}"
        )
        info.setStyleSheet("color:#999; font-size:8pt; margin-top:6px;")
        layout.addWidget(info)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_spacing_changed(self, val: int):
        if val > 0 and self._distance > 0:
            count = max(2, round(self._distance / val) + 1)
            self.count_spin.setValue(count)

    def payload(self) -> dict:
        return build_trade_lane_payload(
            ring_count=self.count_spin.value(),
            spacing=self.spacing_spin.value(),
            start_num=self.start_spin.value(),
            loadout=self.loadout_cb.currentText(),
            reputation=self.reputation_cb.currentText(),
            difficulty_level=self.diff_spin.value(),
            pilot=self.pilot_cb.currentText(),
            ids_name=self.ids_name_edit.text(),
            space_name_start=self.space_name_start_edit.text(),
            space_name_end=self.space_name_end_edit.text(),
        )


# ══════════════════════════════════════════════════════════════════════
#  TradeLaneEditDialog – Bestehende Tradelane-Routen bearbeiten
# ══════════════════════════════════════════════════════════════════════

class TradeLaneEditDialog(QDialog):
    """Dialog zum Verwalten bestehender Tradelane-Routen.

    Zeigt alle erkannten Routen als Liste.  Der User kann:
    - Eine Route komplett löschen
    - Start-/Endpunkt einer Route neu setzen (Positionen verschieben)
    """

    def __init__(self, parent, *, chains: list[list[dict]]):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.tradelane_edit"))
        self.setMinimumWidth(520)
        self.setMinimumHeight(360)
        self._chains = chains
        self._action: str | None = None
        self._selected_chain_idx: int = -1

        layout = QVBoxLayout(self)

        info = QLabel(tr("dlg.routes_found").format(count=len(chains)))
        info.setStyleSheet("font-weight:bold; margin-bottom:4px;")
        layout.addWidget(info)

        self.chain_list = QListWidget()
        for i, chain in enumerate(chains):
            first = chain[0]["nickname"]
            last = chain[-1]["nickname"]
            count = len(chain)
            route_name = str(chain[0].get("route_name", "") or "").strip() or "-"
            start_name = str(chain[0].get("start_name", "") or "").strip() or "-"
            end_name = str(chain[0].get("end_name", "") or "").strip() or "-"
            item_text = (
                f"Route {i+1}: {first} → {last} ({count} Ringe)\n"
                f"{tr('dlg.tradelane_name')} {route_name} | "
                f"{tr('dlg.tradelane_start_name')} {start_name} | "
                f"{tr('dlg.tradelane_end_name')} {end_name}"
            )
            item = QListWidgetItem(item_text)
            hint = item.sizeHint()
            item.setSizeHint(QSize(hint.width(), hint.height() + 18))
            item.setData(256, i)
            self.chain_list.addItem(item)
        self.chain_list.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self.chain_list)

        # Detail-Box
        self.detail_grp = QGroupBox(tr("dlg.grp_details"))
        dl = QVBoxLayout(self.detail_grp)
        self.detail_lbl = QLabel(tr("dlg.select_route"))
        self.detail_lbl.setWordWrap(True)
        self.detail_lbl.setStyleSheet("font-size:9pt;")
        dl.addWidget(self.detail_lbl)

        name_form = QFormLayout()
        self.route_name_edit = QLineEdit()
        self.start_name_edit = QLineEdit()
        self.end_name_edit = QLineEdit()
        self.route_name_edit.setPlaceholderText(tr("dlg.tradelane_name_ph"))
        self.start_name_edit.setPlaceholderText(tr("dlg.tradelane_start_name_ph"))
        self.end_name_edit.setPlaceholderText(tr("dlg.tradelane_end_name_ph"))
        name_form.addRow(tr("dlg.tradelane_name"), self.route_name_edit)
        name_form.addRow(tr("dlg.tradelane_start_name"), self.start_name_edit)
        name_form.addRow(tr("dlg.tradelane_end_name"), self.end_name_edit)
        dl.addLayout(name_form)

        self.save_names_btn = QPushButton(tr("btn.save"))
        self.save_names_btn.setEnabled(False)
        self.save_names_btn.clicked.connect(self._on_save_names)
        dl.addWidget(self.save_names_btn)

        btn_row = QHBoxLayout()
        self.delete_btn = QPushButton(tr("dlg.delete_route"))
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self.delete_btn)

        self.reposition_btn = QPushButton(tr("dlg.reposition_route"))
        self.reposition_btn.setEnabled(False)
        self.reposition_btn.clicked.connect(self._on_reposition)
        btn_row.addWidget(self.reposition_btn)
        dl.addLayout(btn_row)

        layout.addWidget(self.detail_grp)

        # Schließen
        close_btn = QPushButton(tr("dlg.close"))
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def _on_selection_changed(self, row: int):
        self._selected_chain_idx = row
        enabled = (0 <= row < len(self._chains))
        self.delete_btn.setEnabled(enabled)
        self.reposition_btn.setEnabled(enabled)
        self.save_names_btn.setEnabled(enabled)
        if enabled:
            chain = self._chains[row]
            first = chain[0]
            last = chain[-1]
            route_name = str(first.get("route_name", "") or "").strip() or "-"
            start_name = str(first.get("start_name", "") or "").strip() or "-"
            end_name = str(first.get("end_name", "") or "").strip() or "-"
            self.route_name_edit.setText("" if route_name == "-" else route_name)
            self.start_name_edit.setText("" if start_name == "-" else start_name)
            self.end_name_edit.setText("" if end_name == "-" else end_name)
            self.detail_lbl.setText(
                f"Start: {first['nickname']}  pos=({first.get('pos', '?')})\n"
                f"Ende:  {last['nickname']}  pos=({last.get('pos', '?')})\n"
                f"{tr('dlg.tradelane_name')} {route_name}\n"
                f"{tr('dlg.tradelane_start_name')} {start_name}\n"
                f"{tr('dlg.tradelane_end_name')} {end_name}\n"
                f"Ringe: {len(chain)}   "
                f"Loadout: {first.get('loadout', '?')}   "
                f"Rotation: {first.get('rotate', '?')}"
            )
        else:
            self.route_name_edit.clear()
            self.start_name_edit.clear()
            self.end_name_edit.clear()
            self.detail_lbl.setText(tr("dlg.select_route"))

    def _on_delete(self):
        self._action = "delete"
        self.accept()

    def _on_reposition(self):
        self._action = "reposition"
        self.accept()

    def _on_save_names(self):
        self._action = "update_names"
        self.accept()

    @property
    def action(self) -> str | None:
        return self._action

    @property
    def selected_chain_index(self) -> int:
        return self._selected_chain_idx

    @property
    def edited_names(self) -> tuple[str, str, str]:
        return (
            self.route_name_edit.text().strip(),
            self.start_name_edit.text().strip(),
            self.end_name_edit.text().strip(),
        )


# ══════════════════════════════════════════════════════════════════════
#  ZonePopulationDialog – Zone Population bearbeiten
# ══════════════════════════════════════════════════════════════════════

class ZonePopulationDialog(QDialog):
    """Zone-Population bearbeiten – Encounter und Factions verwalten.

    Zeigt die Population-Parameter einer Zone (toughness, density, …)
    sowie bestehende Encounters mit zugehörigen Factions.  Der User kann
    Encounters und Factions hinzufügen, bearbeiten und entfernen.
    """

    _POP_KEYS = frozenset({
        "toughness", "density", "repop_time",
        "max_battle_size", "pop_type", "relief_time",
    })
    _PROFILE_POP_TYPES: dict[str, list[str]] = {
        "field": ["field", "lootable_field", "mining_field"],
        "patrol": ["lane_patrol", "attack_patrol", "field_patrol", "scavenger_path"],
        "lane": ["trade_lane", "trade_path", "lane_patrol", "mining_path"],
        "generic": [
            "field",
            "lootable_field",
            "mining_field",
            "lane_patrol",
            "attack_patrol",
            "field_patrol",
            "scavenger_path",
            "trade_lane",
            "trade_path",
            "mining_path",
        ],
    }
    _PROFILE_DEFAULTS: dict[str, dict[str, str | int]] = {
        "field": {
            "toughness": 10,
            "density": 5,
            "repop_time": 25,
            "max_battle_size": 4,
            "pop_type": "field",
            "relief_time": 25,
            "encounter_level": 10,
            "encounter_chance": "0.100000",
            "faction_weight": "1.000000",
        },
        "patrol": {
            "toughness": 19,
            "density": 10,
            "repop_time": 90,
            "max_battle_size": 10,
            "pop_type": "lane_patrol",
            "relief_time": 30,
            "encounter_level": 19,
            "encounter_chance": "0.150000",
            "faction_weight": "1.000000",
        },
        "lane": {
            "toughness": 12,
            "density": 6,
            "repop_time": 45,
            "max_battle_size": 4,
            "pop_type": "trade_lane",
            "relief_time": 25,
            "encounter_level": 12,
            "encounter_chance": "0.100000",
            "faction_weight": "1.000000",
        },
        "generic": {
            "toughness": 12,
            "density": 6,
            "repop_time": 45,
            "max_battle_size": 6,
            "pop_type": "attack_patrol",
            "relief_time": 30,
            "encounter_level": 12,
            "encounter_chance": "0.100000",
            "faction_weight": "1.000000",
        },
    }

    def __init__(
        self,
        parent,
        *,
        zone_nickname: str,
        entries: list[tuple[str, str]],
        encounter_params: list[str],
        all_encounters: list[str],
        factions: list[str],
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.zone_pop").format(nickname=zone_nickname))
        self.setMinimumWidth(720)
        self.setMinimumHeight(580)
        self._encounter_params = sorted(encounter_params)
        self._all_encounters = sorted(all_encounters)
        self._factions = sorted(factions)
        self._other_entries: list[tuple[str, str]] = []
        self._new_encounter_params: set[str] = set()

        # Parse bestehende Einträge
        pop, dr, encs = self._parse(entries)
        self._zone_profile = self._infer_zone_profile(entries, pop)
        self._profile_defaults = self._defaults_for_profile(self._zone_profile)

        lay = QVBoxLayout(self)

        # ── Population-Parameter ──────────────────────────────────────
        pop_grp = QGroupBox(tr("dlg.grp_pop_params"))
        form = QFormLayout(pop_grp)

        self.toughness_spin = QSpinBox()
        self.toughness_spin.setRange(0, 100)
        self.toughness_spin.setValue(self._int(pop.get("toughness", str(self._profile_defaults["toughness"]))))
        self.toughness_spin.setToolTip("Empfohlene Encounter-Staerke fuer diese Zone. Vanilla liegt meist im Bereich 1 bis 19.")
        form.addRow("Toughness:", self.toughness_spin)

        self.density_spin = QSpinBox()
        self.density_spin.setRange(0, 100)
        self.density_spin.setValue(self._int(pop.get("density", str(self._profile_defaults["density"]))))
        self.density_spin.setToolTip("Wie dicht die Population insgesamt ist. 0 bedeutet praktisch keine Spawns.")
        form.addRow("Density:", self.density_spin)

        self.repop_spin = QSpinBox()
        self.repop_spin.setRange(0, 9999)
        self.repop_spin.setValue(self._int(pop.get("repop_time", str(self._profile_defaults["repop_time"]))))
        self.repop_spin.setToolTip("Zeit bis neue NPCs nachspawnen.")
        form.addRow("Repop Time:", self.repop_spin)

        self.battle_spin = QSpinBox()
        self.battle_spin.setRange(0, 100)
        self.battle_spin.setValue(self._int(pop.get("max_battle_size", str(self._profile_defaults["max_battle_size"]))))
        self.battle_spin.setToolTip("Maximale Anzahl aktiver Kampfteilnehmer. Meist kleiner oder gleich Density.")
        form.addRow("Max Battle Size:", self.battle_spin)

        self.pop_type_combo = QComboBox()
        self.pop_type_combo.setEditable(True)
        pop_types = self._pop_types_for_profile(self._zone_profile)
        self.pop_type_combo.addItems(pop_types)
        cur_pt = pop.get("pop_type", str(self._profile_defaults["pop_type"]))
        if cur_pt:
            idx = self.pop_type_combo.findText(cur_pt)
            if idx >= 0:
                self.pop_type_combo.setCurrentIndex(idx)
            else:
                self.pop_type_combo.setCurrentText(cur_pt)
        self.pop_type_combo.setToolTip(
            "Bestimmt die Art der Population. Beispiele: field/lootable_field fuer Felder, "
            "attack_patrol fuer Patrouillen, trade_lane oder trade_path fuer Verkehrs-Zonen."
        )
        form.addRow("Pop Type:", self.pop_type_combo)

        self.relief_spin = QSpinBox()
        self.relief_spin.setRange(0, 9999)
        self.relief_spin.setValue(self._int(pop.get("relief_time", str(self._profile_defaults["relief_time"]))))
        self.relief_spin.setToolTip("Abklingzeit fuer neue Gefechte oder Entlastung der Zone.")
        form.addRow("Relief Time:", self.relief_spin)
        profile_label = QLabel(self._profile_summary_text())
        profile_label.setWordWrap(True)
        profile_label.setToolTip("Atlas erkennt daraus passende Standardwerte und Pop-Type-Empfehlungen.")
        form.addRow("Zone Style:", profile_label)

        lay.addWidget(pop_grp)

        # ── Density Restrictions ──────────────────────────────────────
        dr_grp = QGroupBox(tr("dlg.grp_density"))
        dr_lay = QVBoxLayout(dr_grp)
        self.dr_list = QListWidget()
        self.dr_list.setMaximumHeight(120)
        self.dr_list.setToolTip("Format: <Zahl>, <Encounter>. Die Restriction sollte auf einen vorhandenen Encounter zeigen.")
        for d in dr:
            item = QListWidgetItem(d)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.dr_list.addItem(item)
        dr_lay.addWidget(self.dr_list)

        dr_btn_row = QHBoxLayout()
        dr_add = QPushButton("+ Hinzufügen")
        dr_add.clicked.connect(self._add_density_restriction)
        dr_rem = QPushButton(tr("dlg.remove"))
        dr_rem.clicked.connect(self._remove_density_restriction)
        dr_btn_row.addWidget(dr_add)
        dr_btn_row.addWidget(dr_rem)
        dr_btn_row.addStretch()
        dr_lay.addLayout(dr_btn_row)
        lay.addWidget(dr_grp)

        # ── Encounters & Factions ─────────────────────────────────────
        enc_grp = QGroupBox(tr("dlg.grp_encounters"))
        enc_lay = QVBoxLayout(enc_grp)
        enc_help = QLabel(
            "Encounter-Zeile: Name, Level, Chance. Faction-Kinder darunter: Faction, Gewicht. "
            "Chance ist ein Float von 0.0 bis 1.0, Gewicht ist relativ innerhalb dieses Encounters. "
            "Die Summe aller Encounter-Chancen und die Summe aller Faction-Gewichte pro Encounter darf jeweils 1.0 nicht uebersteigen."
        )
        enc_help.setWordWrap(True)
        enc_help.setToolTip("Beispiel: encounter = area_scout, 12, 0.100000 und faction = fc_j_grp, 1.000000")
        enc_lay.addWidget(enc_help)

        self.enc_tree = QTreeWidget()
        self.enc_tree.setHeaderLabels(["Name", "Level / Gewicht", "Chance (0.0 - 1.0)"])
        self.enc_tree.setColumnWidth(0, 300)
        self.enc_tree.setColumnWidth(1, 120)
        self.enc_tree.setColumnWidth(2, 80)
        self.enc_tree.setAlternatingRowColors(True)
        self.enc_tree.setToolTip(
            "Top-Level = Encounter mit Level und Spawn-Chance. Untereintraege = Factions mit relativem Gewicht."
        )

        for enc in encs:
            enc_item = QTreeWidgetItem([enc["name"], enc["count"], enc["chance"]])
            enc_item.setFlags(enc_item.flags() | Qt.ItemIsEditable)
            for fac in enc["factions"]:
                fac_item = QTreeWidgetItem([fac["name"], fac["weight"], ""])
                fac_item.setFlags(fac_item.flags() | Qt.ItemIsEditable)
                enc_item.addChild(fac_item)
            self.enc_tree.addTopLevelItem(enc_item)
            enc_item.setExpanded(True)

        if self.enc_tree.topLevelItemCount() == 0 and self._all_encounters:
            default_encounter = QTreeWidgetItem([
                self._all_encounters[0],
                str(self._profile_defaults["encounter_level"]),
                str(self._profile_defaults["encounter_chance"]),
            ])
            default_encounter.setFlags(default_encounter.flags() | Qt.ItemIsEditable)
            if self._factions:
                default_faction = QTreeWidgetItem([
                    self._factions[0],
                    str(self._profile_defaults["faction_weight"]),
                    "",
                ])
                default_faction.setFlags(default_faction.flags() | Qt.ItemIsEditable)
                default_encounter.addChild(default_faction)
            self.enc_tree.addTopLevelItem(default_encounter)
            default_encounter.setExpanded(True)

        enc_lay.addWidget(self.enc_tree)

        enc_btn_row = QHBoxLayout()
        enc_add = QPushButton(tr("dlg.add_encounter"))
        enc_add.clicked.connect(self._add_encounter)
        fac_add = QPushButton(tr("dlg.add_faction"))
        fac_add.clicked.connect(self._add_faction)
        enc_rem = QPushButton(tr("dlg.remove"))
        enc_rem.clicked.connect(self._remove_enc_item)
        enc_btn_row.addWidget(enc_add)
        enc_btn_row.addWidget(fac_add)
        enc_btn_row.addWidget(enc_rem)
        enc_btn_row.addStretch()
        enc_lay.addLayout(enc_btn_row)
        lay.addWidget(enc_grp)

        # ── OK / Abbrechen ────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    # ------------------------------------------------------------------
    #  Parsing
    # ------------------------------------------------------------------
    @staticmethod
    def _int(val: str) -> int:
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    @classmethod
    def _pop_types_for_profile(cls, profile: str) -> list[str]:
        profile_key = str(profile or "").strip().lower() or "generic"
        primary = list(cls._PROFILE_POP_TYPES.get(profile_key, cls._PROFILE_POP_TYPES["generic"]))
        known: list[str] = []
        for key in (profile_key, "generic"):
            for item in cls._PROFILE_POP_TYPES.get(key, []):
                if item not in known:
                    known.append(item)
        return primary + [item for item in known if item not in primary]

    @classmethod
    def _recommended_pop_types_for_profile(cls, profile: str) -> set[str]:
        profile_key = str(profile or "").strip().lower() or "generic"
        return {item.lower() for item in cls._PROFILE_POP_TYPES.get(profile_key, [])}

    @staticmethod
    def _defaults_for_profile(profile: str) -> dict[str, str | int]:
        profile_key = str(profile or "").strip().lower() or "generic"
        defaults = dict(ZonePopulationDialog._PROFILE_DEFAULTS["generic"])
        defaults.update(ZonePopulationDialog._PROFILE_DEFAULTS.get(profile_key, {}))
        return defaults

    @staticmethod
    def _safe_int(text: str, default: int = 0) -> int:
        try:
            return int(str(text or "").strip())
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_float(text: str, default: float = 0.0) -> float:
        try:
            return float(str(text or "").strip())
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _format_float(text: str, default: str) -> str:
        raw = str(text or "").strip()
        if not raw:
            return str(default)
        try:
            return f"{float(raw):.6f}"
        except (TypeError, ValueError):
            return raw

    @staticmethod
    def _sum_exceeds_one(value: float) -> bool:
        return value > 1.000001

    @classmethod
    def _infer_zone_profile(cls, entries: list[tuple[str, str]], pop: dict[str, str]) -> str:
        values: dict[str, str] = {}
        combined_bits: list[str] = []
        for key, value in entries:
            kl = str(key or "").strip().lower()
            txt = str(value or "").strip()
            if kl and kl not in values:
                values[kl] = txt
            combined_bits.append(f"{kl}={txt}".lower())
        pop_type = str(pop.get("pop_type", "") or "").strip().lower()
        usage = str(values.get("usage", "") or "").strip().lower()
        zone_type = str(values.get("type", "") or "").strip().lower()
        comment = str(values.get("comment", "") or "").strip().lower()
        zone_nick = str(values.get("nickname", "") or "").strip().lower()
        source_text = " ".join(bit for bit in combined_bits if bit)
        if any(token in pop_type for token in ("trade", "lane")) or usage in {"trade", "lane"}:
            return "lane"
        if any(token in source_text for token in ("trade_lane", "tradelane", "lane_ring", "lane segment")):
            return "lane"
        if any(token in pop_type for token in ("field", "lootable", "mining")):
            return "field"
        if zone_type in {"asteroids", "nebula"}:
            return "field"
        if any(token in comment for token in ("asteroid", "nebula", "field", "debris")):
            return "field"
        if any(token in zone_nick for token in ("asteroid", "nebula", "field", "debris")):
            return "field"
        if pop_type:
            return "patrol"
        return "generic"

    def _profile_summary_text(self) -> str:
        labels = {
            "field": "Field Zone erkannt. Empfohlen: field, lootable_field oder mining_field.",
            "patrol": "Patrol Zone erkannt. Empfohlen: lane_patrol, attack_patrol oder field_patrol.",
            "lane": "Traffic/Trade Zone erkannt. Empfohlen: trade_lane oder trade_path.",
            "generic": "Keine klare Zonenart erkannt. Atlas validiert vorsichtig und laesst Custom-Setups zu.",
        }
        return labels.get(self._zone_profile, labels["generic"])

    def _parse(self, entries: list[tuple[str, str]]):
        """Zerlegt die Zonen-Einträge in Population-Felder, Density
        Restrictions und Encounter/Faction-Strukturen."""
        pop: dict[str, str] = {}
        dr: list[str] = []
        encs: list[dict] = []
        current_enc: dict | None = None

        for k, v in entries:
            kl = k.lower()
            if kl in self._POP_KEYS:
                pop[kl] = v.strip()
            elif kl == "density_restriction":
                dr.append(v.strip())
            elif kl == "encounter":
                parts = [p.strip() for p in v.split(",")]
                current_enc = {
                    "name": parts[0] if parts else "",
                    "count": parts[1] if len(parts) > 1 else "1",
                    "chance": parts[2] if len(parts) > 2 else "0.100000",
                    "factions": [],
                }
                encs.append(current_enc)
            elif kl == "faction" and current_enc is not None:
                parts = [p.strip() for p in v.split(",")]
                current_enc["factions"].append({
                    "name": parts[0] if parts else "",
                    "weight": parts[1] if len(parts) > 1 else "1.000000",
                })
            else:
                self._other_entries.append((k, v))

        return pop, dr, encs

    # ------------------------------------------------------------------
    #  Density Restrictions
    # ------------------------------------------------------------------
    def _add_density_restriction(self):
        item = QListWidgetItem("1, encounter_name")
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.dr_list.addItem(item)
        self.dr_list.editItem(item)

    def _remove_density_restriction(self):
        row = self.dr_list.currentRow()
        if row >= 0:
            self.dr_list.takeItem(row)

    # ------------------------------------------------------------------
    #  Encounters & Factions
    # ------------------------------------------------------------------
    def _add_encounter(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("dlg.encounter_select"))
        dlg.setMinimumWidth(400)
        lay = QVBoxLayout(dlg)

        lay.addWidget(QLabel(tr("dlg.choose_encounter")))
        combo = QComboBox()
        combo.setEditable(True)
        # Bereits im System vorhandene EncounterParameters zuerst anzeigen,
        # dann alle verfügbaren Encounter-INIs
        existing = set(self._encounter_params)
        items_existing: list[str] = []
        items_new: list[str] = []
        for e in self._all_encounters:
            if e in existing:
                items_existing.append(e)
            else:
                items_new.append(e)
        if items_existing:
            for e in items_existing:
                combo.addItem(f"✓  {e}", e)
        if items_new:
            for e in items_new:
                combo.addItem(f"◻  {e}  (neu)", e)
        configure_contains_completer(combo)
        lay.addWidget(combo)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec() != QDialog.Accepted:
            return
        sel_data = combo.currentData()
        name = sel_data if sel_data else combo.currentText().strip()
        if not name:
            return

        # Falls der Encounter noch nicht als EncounterParameters existiert
        if name not in set(self._encounter_params):
            self._new_encounter_params.add(name)

        enc_item = QTreeWidgetItem([
            name,
            str(self._profile_defaults["encounter_level"]),
            str(self._profile_defaults["encounter_chance"]),
        ])
        enc_item.setFlags(enc_item.flags() | Qt.ItemIsEditable)
        self.enc_tree.addTopLevelItem(enc_item)
        enc_item.setExpanded(True)
        self.enc_tree.setCurrentItem(enc_item)

    def _add_faction(self):
        current = self.enc_tree.currentItem()
        if current is None:
            return
        # Falls ein Faction-Kind gewählt ist → zum Encounter-Eltern gehen
        parent = current.parent()
        if parent is not None:
            current = parent

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("dlg.faction_select"))
        dlg.setMinimumWidth(400)
        lay = QVBoxLayout(dlg)

        lay.addWidget(QLabel(tr("dlg.choose_faction")))
        combo = QComboBox()
        combo.setEditable(True)
        for f in self._factions:
            combo.addItem(f)
        configure_contains_completer(combo)
        lay.addWidget(combo)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec() != QDialog.Accepted:
            return
        name = combo.currentText().strip()
        if not name:
            return

        fac_item = QTreeWidgetItem([name, str(self._profile_defaults["faction_weight"]), ""])
        fac_item.setFlags(fac_item.flags() | Qt.ItemIsEditable)
        current.addChild(fac_item)
        current.setExpanded(True)
        self.enc_tree.setCurrentItem(fac_item)

    def _remove_enc_item(self):
        current = self.enc_tree.currentItem()
        if current is None:
            return
        parent = current.parent()
        if parent is not None:
            parent.removeChild(current)
        else:
            idx = self.enc_tree.indexOfTopLevelItem(current)
            if idx >= 0:
                self.enc_tree.takeTopLevelItem(idx)

    def _collect_population_state(self) -> dict[str, object]:
        encounters: list[dict[str, object]] = []
        for i in range(self.enc_tree.topLevelItemCount()):
            enc_item = self.enc_tree.topLevelItem(i)
            factions: list[dict[str, str]] = []
            for j in range(enc_item.childCount()):
                fac_item = enc_item.child(j)
                factions.append({
                    "name": fac_item.text(0).strip(),
                    "weight": fac_item.text(1).strip(),
                })
            encounters.append({
                "name": enc_item.text(0).strip(),
                "count": enc_item.text(1).strip(),
                "chance": enc_item.text(2).strip(),
                "factions": factions,
            })
        density_restrictions = [
            self.dr_list.item(i).text().strip()
            for i in range(self.dr_list.count())
            if self.dr_list.item(i).text().strip()
        ]
        return {
            "toughness": self.toughness_spin.value(),
            "density": self.density_spin.value(),
            "repop_time": self.repop_spin.value(),
            "max_battle_size": self.battle_spin.value(),
            "pop_type": self.pop_type_combo.currentText().strip(),
            "relief_time": self.relief_spin.value(),
            "density_restrictions": density_restrictions,
            "encounters": encounters,
        }

    def _validate_population_state(self) -> tuple[list[str], list[str]]:
        state = self._collect_population_state()
        errors: list[str] = []
        warnings: list[str] = []
        pop_type = str(state["pop_type"]).strip()
        pop_type_lower = pop_type.lower()
        recommended = self._recommended_pop_types_for_profile(self._zone_profile)
        encounter_names: set[str] = set()
        total_encounter_chance = 0.0
        for idx, encounter in enumerate(state["encounters"], start=1):
            name = str(encounter["name"]).strip()
            count_text = str(encounter["count"]).strip()
            chance_text = str(encounter["chance"]).strip()
            factions = list(encounter["factions"])
            encounter_label = name or f"#{idx}"
            if not name:
                errors.append(f"Encounter {idx} hat keinen Namen.")
            elif name.lower() in encounter_names:
                warnings.append(f"Encounter '{name}' ist mehrfach eingetragen.")
            else:
                encounter_names.add(name.lower())
            level = self._safe_int(count_text, default=-1)
            if level <= 0:
                errors.append(f"Encounter '{encounter_label}' braucht ein Level > 0.")
            chance = self._safe_float(chance_text, default=-1.0)
            if chance < 0.0 or chance > 1.0:
                errors.append(f"Encounter '{encounter_label}' braucht eine Chance zwischen 0.0 und 1.0.")
            elif chance == 0.0:
                warnings.append(f"Encounter '{encounter_label}' hat Chance 0.0 und wird nie spawnen.")
            else:
                total_encounter_chance += chance
            if level > 19:
                warnings.append(f"Encounter '{encounter_label}' hat Level {level}. Vanilla liegt meist bei 1 bis 19.")
            if not factions:
                errors.append(f"Encounter '{encounter_label}' hat keine Faction-Zuordnung.")
            total_faction_weight = 0.0
            for fidx, faction in enumerate(factions, start=1):
                fname = str(faction["name"]).strip()
                weight = self._safe_float(str(faction["weight"]).strip(), default=-1.0)
                if not fname:
                    errors.append(f"Encounter '{encounter_label}' hat eine leere Faction in Zeile {fidx}.")
                if weight <= 0.0:
                    errors.append(f"Faction '{fname or fidx}' in Encounter '{encounter_label}' braucht ein Gewicht > 0.")
                else:
                    total_faction_weight += weight
                if weight > 10.0:
                    warnings.append(
                        f"Faction '{fname or fidx}' in Encounter '{encounter_label}' hat ein sehr hohes Gewicht ({weight:.3f})."
                    )
            if self._sum_exceeds_one(total_faction_weight):
                errors.append(
                    f"Die Summe der Faction-Gewichte in Encounter '{encounter_label}' darf 1.0 nicht uebersteigen "
                    f"(aktuell {total_faction_weight:.6f})."
                )
        for raw in state["density_restrictions"]:
            parts = [p.strip() for p in str(raw).split(",")]
            if len(parts) < 2 or not parts[0] or not parts[1]:
                errors.append(f"Density Restriction '{raw}' ist ungueltig. Erwartet wird 'Anzahl, Encounter'.")
                continue
            amount = self._safe_int(parts[0], default=-1)
            if amount < 0:
                errors.append(f"Density Restriction '{raw}' braucht vorne eine Zahl.")
            if parts[1].lower() not in encounter_names:
                errors.append(f"Density Restriction '{raw}' verweist auf einen unbekannten Encounter.")
        if self._sum_exceeds_one(total_encounter_chance):
            errors.append(
                f"Die Summe aller Encounter-Chancen darf 1.0 nicht uebersteigen (aktuell {total_encounter_chance:.6f})."
            )
        if pop_type and recommended and pop_type_lower not in recommended:
            expected = ", ".join(self._pop_types_for_profile(self._zone_profile)[:3])
            warnings.append(
                f"Pop Type '{pop_type}' ist ungewoehnlich fuer diesen Zone Style. Empfohlen sind z. B. {expected}."
            )
        density = int(state["density"])
        max_battle_size = int(state["max_battle_size"])
        repop_time = int(state["repop_time"])
        relief_time = int(state["relief_time"])
        if state["encounters"] and density <= 0:
            warnings.append("Die Zone hat Encounters, aber Density ist 0. Damit wird praktisch nichts spawnen.")
        if density > 0 and max_battle_size > density:
            warnings.append("Max Battle Size ist groesser als Density. Das ist oft ein Hinweis auf unausgewogene Werte.")
        if repop_time > 0 and relief_time > 0 and relief_time > repop_time:
            warnings.append("Relief Time ist groesser als Repop Time. Das ist meist ungewoehnlich.")
        mission_eligible = any(
            str(key).strip().lower() == "mission_eligible" and str(value).strip().lower() in {"true", "1", "yes"}
            for key, value in self._other_entries
        )
        if mission_eligible and self._zone_profile == "field":
            warnings.append("Mission Eligible ist aktiv, obwohl die Zone eher wie ein Field aussieht.")
        return errors, warnings

    def accept(self):
        errors, warnings = self._validate_population_state()
        if errors:
            QMessageBox.warning(
                self,
                "Zone Population",
                "Bitte korrigiere zuerst diese Punkte:\n\n- " + "\n- ".join(errors),
            )
            return
        if warnings:
            ans = QMessageBox.question(
                self,
                "Zone Population Warnung",
                "Diese Kombination ist speicherbar, aber auffaellig:\n\n- "
                + "\n- ".join(warnings)
                + "\n\nSoll trotzdem fortgefahren werden?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return
        super().accept()

    # ------------------------------------------------------------------
    #  Ergebnis
    # ------------------------------------------------------------------
    def build_entries(self) -> list[tuple[str, str]]:
        """Rekonstruiert die Zonen-Einträge aus dem Dialog-Zustand."""
        result: list[tuple[str, str]] = list(self._other_entries)

        # Population-Parameter
        result.append(("toughness", str(self.toughness_spin.value())))
        result.append(("density", str(self.density_spin.value())))
        result.append(("repop_time", str(self.repop_spin.value())))
        result.append(("max_battle_size", str(self.battle_spin.value())))
        result.append(("pop_type", self.pop_type_combo.currentText()))
        result.append(("relief_time", str(self.relief_spin.value())))

        # Density Restrictions
        for i in range(self.dr_list.count()):
            text = self.dr_list.item(i).text().strip()
            if text:
                result.append(("density_restriction", text))

        # Encounters mit Factions
        for i in range(self.enc_tree.topLevelItemCount()):
            enc_item = self.enc_tree.topLevelItem(i)
            name = enc_item.text(0).strip()
            count = enc_item.text(1).strip()
            chance = enc_item.text(2).strip()
            if name:
                chance_text = self._format_float(chance, str(self._profile_defaults["encounter_chance"]))
                result.append(("encounter", f"{name}, {count}, {chance_text}"))
                for j in range(enc_item.childCount()):
                    fac_item = enc_item.child(j)
                    fname = fac_item.text(0).strip()
                    fweight = fac_item.text(1).strip()
                    if fname:
                        weight_text = self._format_float(fweight, str(self._profile_defaults["faction_weight"]))
                        result.append(("faction", f"{fname}, {weight_text}"))

        return result

    @property
    def new_encounter_params(self) -> set[str]:
        """Encounter-Nicknames, die als [EncounterParameters] angelegt
        werden müssen (im System-INI noch nicht vorhanden)."""
        return set(self._new_encounter_params)


# ══════════════════════════════════════════════════════════════════════
#  Base-Edit-Dialog
# ══════════════════════════════════════════════════════════════════════

class BaseEditDialog(QDialog):
    """Dialog zum Bearbeiten einer existierenden Base.

    Tabs:
    - Eigenschaften: Objektattribute (archetype, loadout, voice, …)
    - Equipment: Gruppierter Baum links, Tabelle mit Parametern rechts
    - Commodities: Liste links, Tabelle mit Parametern + Preisberechnung rechts
    - Schiffe: 3 Slot-Boxen mit Dropdown-Auswahl
    """

    def __init__(
        self,
        parent,
        base_nickname: str,
        obj_entries: list[tuple[str, str]],
        misc_goods: list[list[str]],
        comm_goods: list[list[str]],
        ship_goods: list[list[str]],
        all_equip_groups: dict[str, list[str]] | None = None,
        all_commodity_nicks: list[str] | None = None,
        commodity_prices: dict[str, int] | None = None,
        all_ship_nicks: list[str] | None = None,
        market_display_names: dict[str, str] | None = None,
        pilots: list[str] | None = None,
        voices: list[str] | None = None,
        heads: list[str] | None = None,
        bodies: list[str] | None = None,
        archetypes: list[str] | None = None,
        loadouts: list[str] | None = None,
        factions: list[str] | None = None,
        current_name_text: str = "",
        current_infocard_xml: str = "",
        infocard_jump_cb=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.base_edit").format(nickname=base_nickname))
        self.setMinimumSize(1000, 660)
        self._base_nick = base_nickname
        self._infocard_jump_cb = infocard_jump_cb
        self._market_display_names = {
            str(k).strip().lower(): str(v).strip()
            for k, v in dict(market_display_names or {}).items()
            if str(k).strip()
        }

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # ── Tab 1: Eigenschaften ──
        build_base_edit_properties_tab(
            self,
            tabs=self.tabs,
            obj_entries=obj_entries,
            pilots=pilots or [],
            voices=voices or [],
            heads=heads or [],
            bodies=bodies or [],
            archetypes=archetypes or [],
            loadouts=loadouts or [],
            factions=factions or [],
            current_name_text=current_name_text,
            current_infocard_xml=current_infocard_xml,
        )

        # ── Tab 2: Equipment (Baum + Tabelle) ──
        self.equip_tree, self.equip_table = build_base_edit_equip_tab(
            tabs=self.tabs,
            equip_groups=all_equip_groups or {},
            equip_goods=misc_goods,
        )

        # ── Tab 3: Commodities (Liste + Tabelle mit Preisen) ──
        self._commodity_prices = commodity_prices or {}
        self.comm_available, self.comm_table = build_base_edit_commodity_tab(
            tabs=self.tabs,
            commodity_prices=self._commodity_prices,
            all_nicks=all_commodity_nicks or [],
            comm_goods=comm_goods,
        )

        # ── Tab 4: Schiffe (3 Slots) ──
        assigned_ships = extract_assigned_nicknames(ship_goods)
        self._ship_market_data = build_ship_market_data_map(ship_goods)
        build_base_edit_ships_tab(
            dialog=self,
            tabs=self.tabs,
            all_ship_nicks=all_ship_nicks or [],
            assigned_ships=assigned_ships,
            ship_display_names=self._market_display_names,
        )

        # ── Button-Leiste ──
        btn_row = QHBoxLayout()
        self._delete_requested = False
        del_btn = QPushButton(tr("dlg.delete_base"))
        del_btn.setToolTip(tr("dlg.delete_base_tip"))
        del_btn.setStyleSheet("QPushButton { color: #ff6666; }")
        del_btn.clicked.connect(self._on_delete_clicked)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        btn_row.addWidget(btns)
        main_layout.addLayout(btn_row)

    @property
    def delete_requested(self) -> bool:
        return self._delete_requested

    def _on_delete_clicked(self):
        self._delete_requested = True
        self.reject()

    @staticmethod
    def _nick_from_display(raw: str) -> str:
        txt = str(raw or "").strip()
        if not txt:
            return ""
        if " - " in txt:
            return txt.split(" - ", 1)[0].strip()
        return txt

    def _on_jump_infocard_editor(self):
        cb = self._infocard_jump_cb
        if not callable(cb):
            return
        ids_info = int(self.prop_ids_info.value())
        if not can_open_infocard(ids_info):
            QMessageBox.information(self, tr("msg.error"), tr("msg.infocard_no_ids_info"))
            return
        self.reject()
        QTimer.singleShot(0, lambda: cb(ids_info))

    # ------------------------------------------------------------------
    #  Ergebnisse auslesen
    # ------------------------------------------------------------------
    def get_obj_properties(self) -> dict[str, str]:
        """Gibt die bearbeiteten Objekt-Eigenschaften zurück."""
        return build_base_edit_obj_properties(
            nickname=self.prop_nick.text().strip(),
            archetype=self.prop_arch.currentText().strip(),
            loadout=self.prop_loadout.currentText().strip(),
            reputation=self.prop_rep.currentText().strip(),
            pilot=self.prop_pilot.currentText().strip(),
            voice=self.prop_voice.currentText().strip(),
            head=self.prop_head.currentText().strip(),
            body=self.prop_body.currentText().strip(),
            ids_name=self.prop_ids_name.value(),
            ids_info=self.prop_ids_info.value(),
            behavior=self.prop_behavior.text().strip(),
            difficulty_level=self.prop_difficulty.value(),
        )

    def get_name_text(self) -> str:
        return optional_text_value(
            present=hasattr(self, "prop_name_text"),
            text=self.prop_name_text.text() if hasattr(self, "prop_name_text") else "",
        )

    def get_infocard_xml(self) -> str:
        return optional_text_value(
            present=hasattr(self, "prop_infocard_xml"),
            text=self.prop_infocard_xml.toPlainText() if hasattr(self, "prop_infocard_xml") else "",
        )

    def get_equip_nicknames(self) -> list[str]:
        """Gibt die zugewiesenen Equipment-Nicknames zurück."""
        return collect_first_column_values_from_cells(
            row_count=self.equip_table.rowCount(),
            cell_text=lambda row, col: (
                self.equip_table.item(row, col).text().strip() if self.equip_table.item(row, col) else ""
            ),
        )

    def get_commodity_nicknames(self) -> list[str]:
        """Gibt die zugewiesenen Commodity-Nicknames zurück."""
        return collect_first_column_values_from_cells(
            row_count=self.comm_table.rowCount(),
            cell_text=lambda row, col: (
                self.comm_table.item(row, col).text().strip() if self.comm_table.item(row, col) else ""
            ),
        )

    def get_ship_nicknames(self) -> list[str]:
        """Gibt die gewählten Schiffs-Nicknames zurück (max 3, leere übersprungen)."""
        values: list[str] = []
        for combo in list(getattr(self, "ship_combos", [])):
            if not isinstance(combo, QComboBox):
                continue
            text = str(combo.currentText() or "").strip()
            normalized_text = self._nick_from_display(text)
            data = str(combo.currentData() or "").strip()
            if normalized_text and normalized_text != data:
                values.append(normalized_text)
            elif data:
                values.append(data)
            elif normalized_text:
                values.append(normalized_text)
        return values

    def get_equip_market_goods(self) -> list[list[str]]:
        """Liest alle Zeilen der Equipment-Tabelle aus."""
        return collect_table_values_from_cells(
            row_count=self.equip_table.rowCount(),
            column_count=self.equip_table.columnCount(),
            cell_text=lambda row, col: (
                self.equip_table.item(row, col).text().strip() if self.equip_table.item(row, col) else ""
            ),
        )

    def get_commodity_market_goods(self) -> list[list[str]]:
        """Liest alle Zeilen der Commodity-Tabelle aus (nur die 7 MarketGood-Felder)."""
        return collect_table_values_from_cells(
            row_count=self.comm_table.rowCount(),
            column_count=7,
            cell_text=lambda row, col: (
                self.comm_table.item(row, col).text().strip() if self.comm_table.item(row, col) else ""
            ),
            max_cols=7,
        )

    def get_ship_market_goods(self) -> list[list[str]]:
        """Baut MarketGood-Zeilen für Schiffe."""
        return collect_ship_market_goods(self.get_ship_nicknames(), self._ship_market_data)


# ══════════════════════════════════════════════════════════════════════
#  Docking-Ring-Dialog  (erstellt Docking Ring + Base in einem Schritt)
# ══════════════════════════════════════════════════════════════════════

class DockingRingDialog(QDialog):
    """Kombinierter Dialog: erstellt Docking Ring UND zugehörige Base/Rooms."""

    ROOM_CHOICES = [
        ("Deck", True),
        ("Bar", True),
        ("Trader", True),
        ("Equipment", False),
        ("ShipDealer", False),
    ]

    PILOT_CHOICES = [
        "pilot_solar_easiest",
        "pilot_solar_easy",
        "pilot_solar_hard",
        "pilot_solar_hardest",
    ]

    VOICE_CHOICES = [
        "atc_leg_m01",
        "atc_leg_f01",
        "atc_leg_f01a",
        "mc_leg_m01",
    ]

    def __init__(
        self,
        parent,
        planet_nickname: str,
        base_nickname: str,
        loadouts: list[str],
        factions: list[str],
        existing_bases: list[str] | None = None,
        pilots: list[str] | None = None,
        voices: list[str] | None = None,
        *,
        needs_base: bool = True,
        default_faction: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.docking_ring"))
        self.setMinimumWidth(520)
        self._needs_base = needs_base

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QFormLayout(content)
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

        # ═══════════════════════════════════════════════════════════════
        #  Docking Ring
        # ═══════════════════════════════════════════════════════════════
        grp_ring = QGroupBox(tr("dlg.grp_docking_ring"))
        gl_ring = QFormLayout(grp_ring)

        # Nickname
        self.nick_edit = QLineEdit(f"Dock_Ring_{planet_nickname}")
        gl_ring.addRow("Nickname:", self.nick_edit)

        # Archetype
        self.arch_cb = QComboBox()
        self.arch_cb.setEditable(True)
        self.arch_cb.addItems(["dock_ring", "destructable_dock_ring"])
        gl_ring.addRow(tr("lbl.archetype"), self.arch_cb)

        # Loadout
        ring_loadouts = [l for l in loadouts if "docking_ring" in l.lower()]
        if not ring_loadouts:
            ring_loadouts = [
                "docking_ring", "docking_ring_li_01", "docking_ring_br_01",
                "docking_ring_ku_01", "docking_ring_rh_01",
                "docking_ring_co_01", "docking_ring_co_02",
                "docking_ring_co_03", "docking_ring_pi_01",
            ]
        self.loadout_cb = QComboBox()
        self.loadout_cb.setEditable(True)
        self.loadout_cb.addItems(ring_loadouts)
        gl_ring.addRow("Loadout:", self.loadout_cb)

        # Reputation
        self.faction_cb = QComboBox()
        self.faction_cb.setEditable(True)
        self.faction_cb.addItems(factions)
        configure_contains_completer(self.faction_cb)
        if str(default_faction or "").strip():
            self.faction_cb.setCurrentText(str(default_faction).strip())
        gl_ring.addRow("Reputation:", self.faction_cb)

        # Voice
        self.voice_cb = QComboBox()
        self.voice_cb.setEditable(True)
        voice_list = list(dict.fromkeys(self.VOICE_CHOICES + (voices or [])))
        self.voice_cb.addItems(voice_list)
        self.voice_cb.setCurrentText("atc_leg_m01")
        gl_ring.addRow("Voice:", self.voice_cb)

        # Space Costume
        self.costume_edit = QLineEdit("robot_body_A")
        gl_ring.addRow("Space Costume:", self.costume_edit)

        # Pilot
        self.pilot_cb = QComboBox()
        self.pilot_cb.setEditable(True)
        pilot_list = list(dict.fromkeys(self.PILOT_CHOICES + (pilots or [])))
        self.pilot_cb.addItems(pilot_list)
        self.pilot_cb.setCurrentText("pilot_solar_easiest")
        gl_ring.addRow("Pilot:", self.pilot_cb)

        # Difficulty Level
        self.diff_spin = QSpinBox()
        self.diff_spin.setRange(1, 50)
        self.diff_spin.setValue(1)
        gl_ring.addRow("Difficulty Level:", self.diff_spin)

        # IDS
        self.ids_name_edit = QLineEdit("0")
        gl_ring.addRow("ids_name:", self.ids_name_edit)
        self.ids_info_edit = QLineEdit("0")
        gl_ring.addRow("ids_info:", self.ids_info_edit)

        layout.addRow(grp_ring)

        # ═══════════════════════════════════════════════════════════════
        #  Base (nur wenn Planet noch keine Base hat)
        # ═══════════════════════════════════════════════════════════════
        if needs_base:
            grp_base = QGroupBox(tr("dlg.grp_base"))
            gl_base = QFormLayout(grp_base)

            self.base_nick_edit = QLineEdit(base_nickname)
            self.base_nick_edit.setToolTip("Base-Nickname (dock_with + base-Feld am Planeten)")
            gl_base.addRow("Base Nickname:", self.base_nick_edit)

            self.strid_name_spin = QSpinBox()
            self.strid_name_spin.setRange(0, 999999)
            self.strid_name_spin.setValue(0)
            self.strid_name_spin.setToolTip("strid_name für universe.ini")
            gl_base.addRow("strid_name:", self.strid_name_spin)

            layout.addRow(grp_base)

            # --- Rooms ---
            grp_rooms = QGroupBox(tr("dlg.grp_rooms"))
            gl_rooms = QVBoxLayout(grp_rooms)
            self.room_checks: dict[str, QCheckBox] = {}
            for room_name, default_on in self.ROOM_CHOICES:
                cb = QCheckBox(room_name)
                cb.setChecked(default_on)
                gl_rooms.addWidget(cb)
                self.room_checks[room_name] = cb

            self.start_room_cb = QComboBox()
            sr_row = QHBoxLayout()
            sr_row.addWidget(QLabel(tr("dlg.start_room")))
            sr_row.addWidget(self.start_room_cb)
            gl_rooms.addLayout(sr_row)
            for cb in self.room_checks.values():
                cb.toggled.connect(self._refresh_start_room_choices)
            self._refresh_start_room_choices(preferred="Deck")

            self.price_var_spin = QDoubleSpinBox()
            self.price_var_spin.setRange(0.0, 1.0)
            self.price_var_spin.setSingleStep(0.05)
            self.price_var_spin.setDecimals(2)
            self.price_var_spin.setValue(0.15)
            pv_row = QHBoxLayout()
            pv_row.addWidget(QLabel(tr("dlg.price_variance")))
            pv_row.addWidget(self.price_var_spin)
            gl_rooms.addLayout(pv_row)

            layout.addRow(grp_rooms)

            # --- Room-Template ---
            grp_tpl = QGroupBox(tr("dlg.grp_room_template"))
            gl_tpl = QFormLayout(grp_tpl)
            self.template_cb = QComboBox()
            self.template_cb.setEditable(True)
            self.template_cb.addItem("")
            if existing_bases:
                self.template_cb.addItems(existing_bases)
            self.template_cb.setToolTip(
                tr("dlg.copy_rooms_tip")
            )
            gl_tpl.addRow(tr("dlg.copy_rooms_from"), self.template_cb)
            layout.addRow(grp_tpl)
        else:
            # Planet hat schon eine Base – nur base_nick merken
            self._existing_base_nick = base_nickname

        # ── Buttons ──
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _refresh_start_room_choices(self, *_args, preferred: str = ""):
        if not self._needs_base or not hasattr(self, "start_room_cb"):
            return
        room_state = build_docking_ring_room_state(
            room_names=[name for name, cb in self.room_checks.items() if cb.isChecked()],
            preferred_start_room=preferred,
            current_start_room=self.start_room_cb.currentText().strip(),
        )
        self.start_room_cb.blockSignals(True)
        self.start_room_cb.clear()
        self.start_room_cb.addItems(list(room_state["rooms"]))
        if str(room_state["start_room"]):
            self.start_room_cb.setCurrentText(str(room_state["start_room"]))
        self.start_room_cb.blockSignals(False)

    def payload(self) -> dict:
        return build_docking_ring_payload(
            nickname=self.nick_edit.text().strip(),
            archetype=self.arch_cb.currentText().strip(),
            loadout=self.loadout_cb.currentText().strip(),
            faction=self.faction_cb.currentText().strip(),
            voice=self.voice_cb.currentText().strip(),
            costume=self.costume_edit.text().strip(),
            pilot=self.pilot_cb.currentText().strip(),
            difficulty=self.diff_spin.value(),
            ids_name=self.ids_name_edit.text().strip(),
            ids_info=self.ids_info_edit.text().strip(),
            needs_base=self._needs_base,
            base_nickname=self.base_nick_edit.text().strip() if self._needs_base else "",
            existing_base_nickname=getattr(self, "_existing_base_nick", ""),
            strid_name=self.strid_name_spin.value() if self._needs_base else 0,
            room_names=[name for name, cb in self.room_checks.items() if cb.isChecked()] if self._needs_base else [],
            start_room=self.start_room_cb.currentText().strip() if self._needs_base else "",
            price_variance=self.price_var_spin.value() if self._needs_base else 0.15,
            template_base=self.template_cb.currentText().strip() if self._needs_base else "",
        )
