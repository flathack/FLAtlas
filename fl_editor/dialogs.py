"""Dialoge für den Freelancer System Editor.

Enthält:
- ConnectionDialog       – Zielsystem und Typ wählen (Jump Hole/Gate)
- GateInfoDialog         – Zusätzliche Gate-Parameter
- ZoneCreationDialog     – Zonentyp, Name und Referenzdatei
- SolarCreationDialog    – Sonne / Planet erstellen
- ObjectCreationDialog   – Beliebiges Objekt erstellen
- MeshPreviewDialog      – 3D-Vorschau eines Archetype-Modells
- SystemCreationDialog   – Neues Sternensystem erstellen
- SystemSettingsDialog   – System-Metadaten bearbeiten
- TradeLaneDialog        – Tradelane-Parameter eingeben
- TradeLaneEditDialog    – Tradelane-Routen bearbeiten/löschen
- ZonePopulationDialog   – Zone-Population bearbeiten (Encounter/Factions)
- SimpleZoneDialog       – Einfache Zone erstellen (Pop-Zone)
- BaseCreationDialog     – Neue Base erstellen
- BaseEditDialog         – Base-Attribute und Market bearbeiten
- DockingRingDialog      – Docking Ring + Base in einem Schritt erstellen
"""

from __future__ import annotations

from pathlib import Path
from struct import pack

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
from PySide6.QtCore import Qt, QUrl, QSize, QTimer, QByteArray
from PySide6.QtGui import QFont, QVector3D

from .cmp_loader import build_native_model_debug_rows
from .freelancer_mesh_data import FreelancerMeshData
from .native_preview_geometry import (
    aggregate_native_preview_bounds,
    decode_native_preview_geometries,
)
from .qt3d_compat import (
    QT3D_AVAILABLE,
    QAttribute3D,
    QBuffer3D,
    QCuboidMesh3D,
    QDirectionalLight3D,
    QEntity3D,
    QGeometry3D,
    QGeometryRenderer3D,
    QMesh3D,
    QOrbitCameraController3D,
    QPhongMaterial3D,
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
#  Connection-Dialog  (Jump Hole / Gate)
# ══════════════════════════════════════════════════════════════════════

class ConnectionDialog(QDialog):
    """Zielsystem und Typ (Jump Hole / Jump Gate) auswählen."""

    def __init__(self, parent, systems: list[tuple[str, str]]):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.connection_title"))
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(tr("dlg.target_system")))
        self.dest_cb = QComboBox()
        for nick, path in systems:
            self.dest_cb.addItem(nick, path)
        layout.addWidget(self.dest_cb)

        layout.addWidget(QLabel(tr("dlg.type")))
        self.type_cb = QComboBox()
        self.type_cb.addItems(["Jump Hole", "Jump Gate", "Nomad Gate"])
        layout.addWidget(self.type_cb)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)


# ══════════════════════════════════════════════════════════════════════
#  Gate-Info-Dialog
# ══════════════════════════════════════════════════════════════════════

class GateInfoDialog(QDialog):
    """Zusätzliche Parameter für ein Jump-Gate sammeln."""

    def __init__(self, parent, loadouts: list[str], factions: list[str]):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.gate_params"))
        layout = QFormLayout(self)

        self.behavior_edit = QLineEdit("NOTHING")
        layout.addRow("behavior:", self.behavior_edit)

        self.difficulty_spin = QSpinBox()
        self.difficulty_spin.setRange(0, 10)
        self.difficulty_spin.setValue(1)
        layout.addRow("difficulty:", self.difficulty_spin)

        self.loadout_cb = QComboBox()
        self.loadout_cb.addItems(loadouts)
        layout.addRow("loadout:", self.loadout_cb)

        self.pilot_edit = QLineEdit("pilot_solar_hardest")
        layout.addRow("pilot:", self.pilot_edit)

        self.rep_cb = QComboBox()
        self.rep_cb.setEditable(True)
        self.rep_cb.addItems(factions)
        layout.addRow("reputation:", self.rep_cb)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)


# ══════════════════════════════════════════════════════════════════════
#  Zone-Erstellungsdialog
# ══════════════════════════════════════════════════════════════════════

class ZoneCreationDialog(QDialog):
    """Zonentyp, Name und Referenzdatei wählen."""

    def __init__(self, parent, asteroids: list[str], nebulas: list[str]):
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
        self._on_type_changed("Asteroid Field")
        layout.addRow(tr("dlg.ref_file"), self.ref_cb)

        self.damage_spin = QSpinBox()
        self.damage_spin.setRange(0, 2_000_000)
        self.damage_spin.setValue(0)
        layout.addRow("Damage:", self.damage_spin)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _on_type_changed(self, typ: str):
        self.ref_cb.clear()
        if typ == "Asteroid Field":
            self.ref_cb.addItems(self._ast_list)
        else:
            self.ref_cb.addItems(self._neb_list)


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
        self.sort_spin.setValue(76)
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
        self.toughness_spin.setValue(19)
        layout.addRow("Toughness:", self.toughness_spin)

        self.density_spin = QSpinBox()
        self.density_spin.setRange(0, 100)
        self.density_spin.setValue(10)
        layout.addRow("Density:", self.density_spin)

        self.repop_spin = QSpinBox()
        self.repop_spin.setRange(0, 10_000)
        self.repop_spin.setValue(90)
        layout.addRow("Repop Time:", self.repop_spin)

        self.battle_spin = QSpinBox()
        self.battle_spin.setRange(0, 10_000)
        self.battle_spin.setValue(10)
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
        if self.encounter_cb.count() > 0:
            self.encounter_cb.setCurrentIndex(0)
        self.encounter_cb.setCurrentText(self.encounter_cb.currentText() or "patrolp_assault")
        layout.addRow("Encounter:", self.encounter_cb)

        self.faction_cb = QComboBox()
        self.faction_cb.setEditable(True)
        self.faction_cb.addItems(factions or [])
        layout.addRow("Faction:", self.faction_cb)

        self.levels_edit = QLineEdit("2,5,8,11,14,17,19")
        layout.addRow("Encounter Levels:", self.levels_edit)

        self.chance_spin = QSpinBox()
        self.chance_spin.setRange(0, 100)
        self.chance_spin.setValue(70)
        layout.addRow("Encounter Chance:", self.chance_spin)

        self.last_diff_cb = QCheckBox("Use lower chance for last level")
        self.last_diff_cb.setChecked(True)
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
        return ["attack_patrol", "field_patrol", "lane_patrol", "mining_path", "scavenger_path"]

    def _apply_pop_type_items(self, usage: str):
        current = self.pop_type_cb.currentText().strip() if hasattr(self, "pop_type_cb") else ""
        items = self._pop_types_for_usage(usage)
        self.pop_type_cb.clear()
        self.pop_type_cb.addItems(items)
        if current:
            self.pop_type_cb.setCurrentText(current)
        else:
            self.pop_type_cb.setCurrentText(items[0] if items else "")

    def _on_usage_changed(self, usage: str):
        self._apply_pop_type_items(usage)

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
            default_chance=self.chance_spin.value(),
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
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.exclusion_create"))
        self.setMinimumWidth(460)
        layout = QFormLayout(self)

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

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def get_data(self) -> dict:
        return build_exclusion_zone_data(
            nickname=self.nick_edit.text(),
            shape=self.shape_cb.currentText(),
            comment=self.comment_edit.text(),
            sort=self.sort_spin.value(),
            link_to_field_zone=self.link_cb.isChecked(),
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
        self.voice_cb.setCurrentText("mc_leg_m01")
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
            table.setItem(ridx, 0, QTableWidgetItem(nick))
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
        )

    def _faction_nick_from_display(self, raw: str) -> str:
        return faction_nick_from_display(raw)

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
        completer = QCompleter(cb.model(), cb)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        cb.setCompleter(completer)
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
            change_state = build_template_change_state(
                template_value=str(self.template_cb.currentData() or self.template_cb.currentText() or "").strip(),
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
        self.atmo_spin.setValue(2000)
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

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

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
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(900, 700)
        layout = QVBoxLayout(self)

        if not QT3D_AVAILABLE:
            layout.addWidget(
                QLabel(tr("dlg.qt3d_not_available"))
            )
            return

        if info_text:
            info_lbl = QLabel(info_text)
            info_lbl.setWordWrap(True)
            layout.addWidget(info_lbl)

        content_row = QHBoxLayout()
        layout.addLayout(content_row)

        self._view3d = Qt3DWindow3D()
        container = QWidget.createWindowContainer(self._view3d)
        content_row.addWidget(container, 1)

        self._root = QEntity3D()
        self._mesh_entity = QEntity3D(self._root)
        self._mesh_transform = QTransform3D(self._root)
        self._native_mesh_entities: list[object] = []

        native_geometries = decode_native_preview_geometries(native_model) if native_model is not None else ()
        native_geometry = native_geometries[0] if native_geometries else None
        native_geometry_bounds = aggregate_native_preview_bounds(native_geometries)

        if mesh_path is not None:
            self._mesh = QMesh3D()
            self._mesh.setSource(QUrl.fromLocalFile(str(mesh_path)))
            self._mesh_entity.addComponent(self._mesh)
        elif native_geometry is not None and all((QGeometryRenderer3D, QGeometry3D, QAttribute3D, QBuffer3D)):
            self._mesh_entity.addComponent(self._build_native_geometry_renderer(native_geometry))
            for extra_geometry in native_geometries[1:]:
                ent = QEntity3D(self._root)
                renderer = self._build_native_geometry_renderer(extra_geometry, entity=ent)
                transform = QTransform3D(ent)
                material = QPhongMaterial3D(ent)
                ent.addComponent(renderer)
                ent.addComponent(transform)
                ent.addComponent(material)
                self._native_mesh_entities.append(ent)
        else:
            prim = (primitive or "cube").lower()
            native_bounds = native_model.bounds if native_model is not None else None
            if prim == "sphere":
                pm = QSphereMesh3D()
                pm.setRadius(max(native_bounds.radius if native_bounds and native_bounds.radius else 35.0, 1.0))
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
            self._mesh_entity.addComponent(pm)

        self._material = QPhongMaterial3D(self._root)
        self._mesh_entity.addComponent(self._material)
        self._mesh_entity.addComponent(self._mesh_transform)

        self._light_entity = QEntity3D(self._root)
        self._light = QDirectionalLight3D(self._light_entity)
        self._light.setWorldDirection(QVector3D(-0.7, -1.0, -0.5))
        self._light_entity.addComponent(self._light)

        cam = self._view3d.camera()
        cam.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 50000.0)
        cam.setPosition(QVector3D(0.0, 0.0, 120.0))
        cam.setViewCenter(QVector3D(0.0, 0.0, 0.0))
        preview_bounds = None
        if native_geometry_bounds is not None:
            preview_bounds = native_geometry_bounds
        elif native_geometry is not None:
            preview_bounds = native_geometry.bounds
        elif native_model is not None:
            preview_bounds = native_model.bounds
        if preview_bounds is not None:
            self._apply_native_preview_bounds(cam, preview_bounds)

        self._cam_controller = QOrbitCameraController3D(self._root)
        self._cam_controller.setLinearSpeed(100.0)
        self._cam_controller.setLookSpeed(180.0)
        self._cam_controller.setCamera(cam)

        self._view3d.setRootEntity(self._root)

        if native_model is not None:
            panel = self._build_native_model_panel(native_model)
            panel.setMinimumWidth(280)
            content_row.addWidget(panel)

    def _build_native_model_panel(self, native_model: FreelancerMeshData) -> QWidget:
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

        if native_model.cmp_fix_records:
            fix_grp = QGroupBox("CMP Fix Records")
            fix_layout = QVBoxLayout(fix_grp)
            fix_list = QListWidget(fix_grp)
            fix_list.setObjectName("native_cmp_fix_list")
            for record in native_model.cmp_fix_records[:40]:
                item_text = record.part_name
                item_text += f" | rec={record.record_index}"
                item_text += f" | bytes={record.record_size}"
                item_text += f" | f32={record.float_count}"
                if record.first_f32:
                    item_text += " | first=" + ",".join(f"{value:.3f}" for value in record.first_f32[:4])
                fix_list.addItem(item_text)
            fix_layout.addWidget(fix_list)
            panel_layout.addWidget(fix_grp)

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

    def _build_native_geometry_renderer(self, native_geometry, entity=None) -> object:
        target_entity = entity or self._mesh_entity
        geometry = QGeometry3D(target_entity)

        vertex_blob = QByteArray()
        for x, y, z in native_geometry.positions:
            vertex_blob.append(pack("<3f", x, y, z))
        vertex_buffer = QBuffer3D(geometry)
        vertex_buffer.setData(vertex_blob)

        position_attr = QAttribute3D(geometry)
        position_attr.setName(QAttribute3D.defaultPositionAttributeName())
        position_attr.setAttributeType(QAttribute3D.VertexAttribute)
        position_attr.setVertexBaseType(QAttribute3D.Float)
        position_attr.setVertexSize(3)
        position_attr.setByteStride(12)
        position_attr.setCount(len(native_geometry.positions))
        position_attr.setBuffer(vertex_buffer)

        index_blob = QByteArray()
        if native_geometry.index_size == 2:
            for index in native_geometry.indices:
                index_blob.append(pack("<H", index))
            index_type = QAttribute3D.UnsignedShort
        else:
            for index in native_geometry.indices:
                index_blob.append(pack("<I", index))
            index_type = QAttribute3D.UnsignedInt
        index_buffer = QBuffer3D(geometry)
        index_buffer.setData(index_blob)

        index_attr = QAttribute3D(geometry)
        index_attr.setAttributeType(QAttribute3D.IndexAttribute)
        index_attr.setVertexBaseType(index_type)
        index_attr.setCount(len(native_geometry.indices))
        index_attr.setBuffer(index_buffer)

        geometry.addAttribute(position_attr)
        geometry.addAttribute(index_attr)

        renderer = QGeometryRenderer3D(target_entity)
        renderer.setGeometry(geometry)
        renderer.setPrimitiveType(QGeometryRenderer3D.Triangles)
        renderer.setVertexCount(len(native_geometry.indices))
        return renderer

    def _apply_native_preview_bounds(self, camera, bounds) -> None:
        min_x, min_y, min_z = bounds.min_xyz
        max_x, max_y, max_z = bounds.max_xyz
        center = QVector3D(
            (min_x + max_x) * 0.5,
            (min_y + max_y) * 0.5,
            (min_z + max_z) * 0.5,
        )
        radius = max(bounds.radius or 0.0, 1.0)
        camera.setViewCenter(center)
        camera.setPosition(center + QVector3D(0.0, 0.0, radius * 3.0))


# ══════════════════════════════════════════════════════════════════════
#  System-Erstellungsdialog
# ══════════════════════════════════════════════════════════════════════

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

        lay = QVBoxLayout(self)

        # ── Population-Parameter ──────────────────────────────────────
        pop_grp = QGroupBox(tr("dlg.grp_pop_params"))
        form = QFormLayout(pop_grp)

        self.toughness_spin = QSpinBox()
        self.toughness_spin.setRange(0, 100)
        self.toughness_spin.setValue(self._int(pop.get("toughness", "19")))
        form.addRow("Toughness:", self.toughness_spin)

        self.density_spin = QSpinBox()
        self.density_spin.setRange(0, 100)
        self.density_spin.setValue(self._int(pop.get("density", "5")))
        form.addRow("Density:", self.density_spin)

        self.repop_spin = QSpinBox()
        self.repop_spin.setRange(0, 9999)
        self.repop_spin.setValue(self._int(pop.get("repop_time", "20")))
        form.addRow("Repop Time:", self.repop_spin)

        self.battle_spin = QSpinBox()
        self.battle_spin.setRange(0, 100)
        self.battle_spin.setValue(self._int(pop.get("max_battle_size", "10")))
        form.addRow("Max Battle Size:", self.battle_spin)

        self.pop_type_combo = QComboBox()
        self.pop_type_combo.setEditable(True)
        pop_types = [
            "lootable_field", "field", "attack_patrol",
            "trade_lane", "mining_field",
        ]
        self.pop_type_combo.addItems(pop_types)
        cur_pt = pop.get("pop_type", "")
        if cur_pt:
            idx = self.pop_type_combo.findText(cur_pt)
            if idx >= 0:
                self.pop_type_combo.setCurrentIndex(idx)
            else:
                self.pop_type_combo.setCurrentText(cur_pt)
        form.addRow("Pop Type:", self.pop_type_combo)

        self.relief_spin = QSpinBox()
        self.relief_spin.setRange(0, 9999)
        self.relief_spin.setValue(self._int(pop.get("relief_time", "35")))
        form.addRow("Relief Time:", self.relief_spin)

        lay.addWidget(pop_grp)

        # ── Density Restrictions ──────────────────────────────────────
        dr_grp = QGroupBox(tr("dlg.grp_density"))
        dr_lay = QVBoxLayout(dr_grp)
        self.dr_list = QListWidget()
        self.dr_list.setMaximumHeight(120)
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

        self.enc_tree = QTreeWidget()
        self.enc_tree.setHeaderLabels(["Name", "Anzahl / Gewicht", "Chance"])
        self.enc_tree.setColumnWidth(0, 300)
        self.enc_tree.setColumnWidth(1, 120)
        self.enc_tree.setColumnWidth(2, 80)
        self.enc_tree.setAlternatingRowColors(True)

        for enc in encs:
            enc_item = QTreeWidgetItem([enc["name"], enc["count"], enc["chance"]])
            enc_item.setFlags(enc_item.flags() | Qt.ItemIsEditable)
            for fac in enc["factions"]:
                fac_item = QTreeWidgetItem([fac["name"], fac["weight"], ""])
                fac_item.setFlags(fac_item.flags() | Qt.ItemIsEditable)
                enc_item.addChild(fac_item)
            self.enc_tree.addTopLevelItem(enc_item)
            enc_item.setExpanded(True)

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
                    "chance": parts[2] if len(parts) > 2 else "100",
                    "factions": [],
                }
                encs.append(current_enc)
            elif kl == "faction" and current_enc is not None:
                parts = [p.strip() for p in v.split(",")]
                current_enc["factions"].append({
                    "name": parts[0] if parts else "",
                    "weight": parts[1] if len(parts) > 1 else "1",
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

        enc_item = QTreeWidgetItem([name, "1", "100"])
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

        fac_item = QTreeWidgetItem([name, "1", ""])
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
                result.append(("encounter", f"{name}, {count}, {chance}"))
                for j in range(enc_item.childCount()):
                    fac_item = enc_item.child(j)
                    fname = fac_item.text(0).strip()
                    fweight = fac_item.text(1).strip()
                    if fname:
                        result.append(("faction", f"{fname}, {fweight}"))

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
        return collect_non_empty_combo_texts(combos=self.ship_combos)

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
        gl_ring.addRow("Reputation:", self.faction_cb)

        # Voice
        self.voice_cb = QComboBox()
        self.voice_cb.setEditable(True)
        voice_list = list(dict.fromkeys(self.VOICE_CHOICES + (voices or [])))
        self.voice_cb.addItems(voice_list)
        self.voice_cb.setCurrentText("atc_leg_f01a")
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
