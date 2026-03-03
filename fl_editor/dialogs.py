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

from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
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
from PySide6.QtCore import Qt, QUrl, QSize, QTimer
from PySide6.QtGui import QFont, QVector3D

from .qt3d_compat import (
    QT3D_AVAILABLE,
    QCuboidMesh3D,
    QDirectionalLight3D,
    QEntity3D,
    QMesh3D,
    QOrbitCameraController3D,
    QPhongMaterial3D,
    QSphereMesh3D,
    Qt3DWindow3D,
)
from .i18n import tr


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
        self.type_cb.addItems(["Jump Hole", "Jump Gate"])
        layout.addWidget(self.type_cb)

        layout.addWidget(QLabel("Ingame Name (optional):"))
        self.ids_name_edit = QLineEdit()
        self.ids_name_edit.setPlaceholderText("e.g. Jump Gate to New London or Jump to {system}")
        layout.addWidget(self.ids_name_edit)

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
        levels: list[int] = []
        for token in self.levels_edit.text().split(","):
            t = token.strip()
            if not t:
                continue
            try:
                n = int(t)
                if n > 0:
                    levels.append(n)
            except ValueError:
                continue
        if not levels:
            levels = [2, 5, 8, 11, 14, 17, 19]

        default_chance = int(self.chance_spin.value())
        last_chance = int(self.last_chance_spin.value())
        pairs: list[tuple[int, int]] = []
        for i, lvl in enumerate(levels):
            chance = default_chance
            if self.last_diff_cb.isChecked() and i == len(levels) - 1:
                chance = last_chance
            pairs.append((lvl, chance))

        return {
            "name": self.name_edit.text().strip(),
            "usage": self.usage_cb.currentText().strip().lower() or "patrol",
            "comment": self.comment_edit.text().strip(),
            "sort": int(self.sort_spin.value()),
            "radius": int(self.radius_spin.value()),
            "damage": int(self.damage_spin.value()),
            "toughness": int(self.toughness_spin.value()),
            "density": int(self.density_spin.value()),
            "repop_time": int(self.repop_spin.value()),
            "max_battle_size": int(self.battle_spin.value()),
            "pop_type": self.pop_type_cb.currentText().strip() or "attack_patrol",
            "relief_time": int(self.relief_spin.value()),
            "path_label": self.path_name_edit.text().strip(),
            "path_index": int(self.path_index_spin.value()),
            "encounter": self.encounter_cb.currentText().strip(),
            "faction": self.faction_cb.currentText().strip(),
            "encounter_pairs": pairs,
            "mission_eligible": bool(self.mission_eligible_cb.isChecked()),
        }


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
        return {
            "nickname": self.nick_edit.text().strip(),
            "shape": self.shape_cb.currentText().strip().upper(),
            "comment": self.comment_edit.text().strip(),
            "sort": self.sort_spin.value(),
            "link_to_field_zone": self.link_cb.isChecked(),
        }


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

    STATION_ARCHETYPES = [
        "largestation1", "largestation2", "largestation3",
        "mediumstation1", "mediumstation2", "mediumstation3",
        "smallstation1", "smallstation2", "smallstation3",
        "outpost", "mining01", "research01",
        "factory01", "depot01", "warehouse01",
    ]

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
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.base_create"))
        self.setMinimumWidth(560)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QFormLayout(content)
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

        self.ids_info_spin = QSpinBox()
        self.ids_info_spin.setRange(0, 999999)
        self.ids_info_spin.setValue(0)
        gl_base.addRow("ids_info:", self.ids_info_spin)

        layout.addRow(grp_base)

        # --- Objekt-Parameter ---
        grp_obj = QGroupBox(tr("dlg.grp_space_object"))
        gl_obj = QFormLayout(grp_obj)

        all_archs = list(dict.fromkeys(self.STATION_ARCHETYPES + archetypes))
        self.arch_cb = QComboBox()
        self.arch_cb.setEditable(True)
        self.arch_cb.addItems(all_archs)
        gl_obj.addRow(tr("lbl.archetype"), self.arch_cb)

        self.loadout_cb = QComboBox()
        self.loadout_cb.setEditable(True)
        self.loadout_cb.addItem("")
        self.loadout_cb.addItems(loadouts)
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
        costume_layout.addRow("Head:", self.head_cb)

        self.body_cb = QComboBox()
        self.body_cb.setEditable(True)
        self.body_cb.addItem("")
        if bodies:
            self.body_cb.addItems(bodies)
        else:
            self.body_cb.addItems(["benchmark_male_body", "benchmark_female_body"])
        costume_layout.addRow("Body:", self.body_cb)
        gl_obj.addRow(costume_grp)

        layout.addRow(grp_obj)

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
        self.start_room_cb.addItems([r for r, _ in self.ROOM_CHOICES])
        self.start_room_cb.setCurrentText("Deck")
        sr_row = QHBoxLayout()
        sr_row.addWidget(QLabel(tr("dlg.start_room")))
        sr_row.addWidget(self.start_room_cb)
        gl_rooms.addLayout(sr_row)

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

        # --- Template-Quelle ---
        grp_tpl = QGroupBox(tr("dlg.grp_room_template"))
        gl_tpl = QFormLayout(grp_tpl)
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
        self.template_cb.setToolTip(
            tr("dlg.copy_rooms_tip")
        )
        gl_tpl.addRow(tr("dlg.copy_rooms_from"), self.template_cb)
        layout.addRow(grp_tpl)

        # --- Universe ---
        grp_uni = QGroupBox(tr("dlg.grp_universe_registry"))
        gl_uni = QFormLayout(grp_uni)
        self.bgcs_edit = QLineEdit()
        self.bgcs_edit.setPlaceholderText("z.B. W02bF35")
        gl_uni.addRow("BGCS_base_run_by:", self.bgcs_edit)
        layout.addRow(grp_uni)

        # --- Buttons ---
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def payload(self) -> dict:
        rooms = [name for name, cb in self.room_checks.items() if cb.isChecked()]
        head = self.head_cb.currentText().strip()
        body = self.body_cb.currentText().strip()
        if head and body:
            costume = f"{head}, {body}"
        elif head:
            costume = head
        elif body:
            costume = body
        else:
            costume = ""
        return {
            "base_nickname": self.base_nick_edit.text().strip(),
            "obj_nickname": self.obj_nick_edit.text().strip(),
            "ids_name_text": self.ids_name_edit.text().strip(),
            "ids_info": self.ids_info_spin.value(),
            "archetype": self.arch_cb.currentText().strip(),
            "loadout": self.loadout_cb.currentText().strip(),
            "reputation": self.faction_cb.currentText().strip(),
            "pilot": self.pilot_cb.currentText().strip(),
            "voice": self.voice_cb.currentText().strip(),
            "space_costume": costume,
            "rooms": rooms,
            "start_room": self.start_room_cb.currentText().strip(),
            "price_variance": self.price_var_spin.value(),
            "template_base": str(self.template_cb.currentData() or self.template_cb.currentText()).strip(),
            "bgcs_base_run_by": self.bgcs_edit.text().strip(),
        }


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
        return {
            "nickname": self.nick_edit.text().strip(),
            "ids_name_text": self.ids_name_edit.text().strip(),
            "archetype": self.arch_cb.currentText().strip(),
            "burn_color": self._burn_rgb,
            "radius": self.radius_spin.value(),
            "damage": self.damage_spin.value(),
            "star": self.star_cb.currentText().strip() if self.star_cb else "",
            "atmosphere_range": self.atmo_spin.value(),
        }


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
        return {
            "nickname": self.nick_edit.text().strip(),
            "type": self.type_cb.currentText().strip().upper(),
            "color": self._color_rgb,
            "range": self.range_spin.value(),
            "atten_curve": self.atten_cb.currentText().strip(),
        }


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
        self.loadout_cb.addItems(loadouts)
        layout.addRow("Loadout:", self.loadout_cb)

        self.faction_cb = QComboBox()
        self.faction_cb.setEditable(True)
        self.faction_cb.addItems(factions)
        layout.addRow("Reputation:", self.faction_cb)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def payload(self) -> dict:
        return {
            "nickname": self.nick_edit.text().strip(),
            "ids_name_text": self.ids_name_edit.text().strip(),
            "archetype": self.arch_cb.currentText().strip(),
            "loadout": self.loadout_cb.currentText().strip(),
            "faction": self.faction_cb.currentText().strip(),
        }



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
        self.loadout_cb.addItems(loadouts)
        layout.addRow(tr("lbl.loadout"), self.loadout_cb)

        self.faction_cb = None
        self.rep_edit = None
        if show_reputation and factions:
            self.faction_cb = QComboBox()
            self.faction_cb.setEditable(True)
            self.faction_cb.addItems(factions)
            layout.addRow(tr("lbl.faction"), self.faction_cb)
            self.rep_edit = QLineEdit()
            self.rep_edit.setPlaceholderText("optional")
            layout.addRow(tr("lbl.reputation"), self.rep_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def payload(self) -> dict:
        out = {
            "archetype": self.arch_cb.currentText().strip(),
            "ids_name_text": self.ids_name_edit.text().strip(),
            "loadout": self.loadout_cb.currentText().strip(),
        }
        if self.faction_cb:
            out["faction"] = self.faction_cb.currentText().strip()
        if self.rep_edit:
            out["rep"] = self.rep_edit.text().strip()
        return out


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
        self.count_spin.setRange(2, 128)
        self.count_spin.setValue(8)
        layout.addRow(tr("dlg.count"), self.count_spin)

        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(100, 100000)
        self.spacing_spin.setValue(3000)
        layout.addRow(tr("dlg.spacing_line"), self.spacing_spin)

        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(100, 200000)
        self.radius_spin.setValue(12000)
        layout.addRow(tr("dlg.radius_circle"), self.radius_spin)

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
        self.spacing_spin.setVisible(line_mode)
        self.radius_spin.setVisible(circle_mode)
        self.count_spin.setEnabled(not single_mode)
        if single_mode:
            self.count_spin.setValue(1)
        elif self.count_spin.value() < 2:
            self.count_spin.setValue(2)

    def payload(self) -> dict:
        pat = self.pattern_cb.currentText().strip().upper()
        return {
            "buoy_type": self.type_cb.currentText().strip(),
            "pattern": pat,
            "count": 1 if pat == "SINGLE" else self.count_spin.value(),
            "spacing": self.spacing_spin.value(),
            "radius": self.radius_spin.value(),
        }


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

        self._view3d = Qt3DWindow3D()
        container = QWidget.createWindowContainer(self._view3d)
        layout.addWidget(container)

        self._root = QEntity3D()
        self._mesh_entity = QEntity3D(self._root)

        if mesh_path is not None:
            self._mesh = QMesh3D()
            self._mesh.setSource(QUrl.fromLocalFile(str(mesh_path)))
            self._mesh_entity.addComponent(self._mesh)
        else:
            prim = (primitive or "cube").lower()
            if prim == "sphere":
                pm = QSphereMesh3D()
                pm.setRadius(35.0)
            else:
                pm = QCuboidMesh3D()
            self._mesh_entity.addComponent(pm)

        self._material = QPhongMaterial3D(self._root)
        self._mesh_entity.addComponent(self._material)

        self._light_entity = QEntity3D(self._root)
        self._light = QDirectionalLight3D(self._light_entity)
        self._light.setWorldDirection(QVector3D(-0.7, -1.0, -0.5))
        self._light_entity.addComponent(self._light)

        cam = self._view3d.camera()
        cam.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 50000.0)
        cam.setPosition(QVector3D(0.0, 0.0, 120.0))
        cam.setViewCenter(QVector3D(0.0, 0.0, 0.0))

        self._cam_controller = QOrbitCameraController3D(self._root)
        self._cam_controller.setLinearSpeed(100.0)
        self._cam_controller.setLookSpeed(180.0)
        self._cam_controller.setCamera(cam)

        self._view3d.setRootEntity(self._root)


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
        return {
            "name": self.name_edit.text().strip(),
            "prefix": self.prefix_edit.text().strip().upper(),
            "size": self.size_spin.value(),
            "space_color": self._space_rgb,
            "music_space": self.music_space_cb.currentText().strip(),
            "music_danger": self.music_danger_cb.currentText().strip(),
            "music_battle": self.music_battle_cb.currentText().strip(),
            "ambient_color": self._ambient_rgb,
            "bg_basic": self.bg_basic_cb.currentText().strip(),
            "bg_complex": self.bg_complex_cb.currentText().strip(),
            "bg_nebulae": self.bg_nebulae_cb.currentText().strip(),
            "light_color": self._light_rgb,
            "local_faction": self.faction_cb.currentText().strip(),
        }


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
        return {
            "music_space": self.music_space_cb.currentText().strip(),
            "music_danger": self.music_danger_cb.currentText().strip(),
            "music_battle": self.music_battle_cb.currentText().strip(),
            "space_color": self._space_rgb,
            "local_faction": self.local_faction_cb.currentText().strip(),
            "ambient_color": self._ambient_rgb,
            "dust": self.dust_cb.currentText().strip(),
            "bg_basic": self.bg_basic_cb.currentText().strip(),
            "bg_complex": self.bg_complex_cb.currentText().strip(),
            "bg_nebulae": self.bg_nebulae_cb.currentText().strip(),
        }


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
        return {
            "ring_count": self.count_spin.value(),
            "spacing": self.spacing_spin.value(),
            "start_num": self.start_spin.value(),
            "loadout": self.loadout_cb.currentText().strip(),
            "reputation": self.reputation_cb.currentText().strip(),
            "difficulty_level": self.diff_spin.value(),
            "pilot": self.pilot_cb.currentText().strip(),
            "ids_name": self.ids_name_edit.text().strip() or "0",
            "space_name_start": self.space_name_start_edit.text().strip() or "0",
            "space_name_end": self.space_name_end_edit.text().strip() or "0",
        }


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
        self._build_properties_tab(
            obj_entries, pilots or [], voices or [],
            heads or [], bodies or [],
            archetypes or [], loadouts or [], factions or [],
            current_name_text=current_name_text,
            current_infocard_xml=current_infocard_xml,
        )

        # ── Tab 2: Equipment (Baum + Tabelle) ──
        self.equip_tree, self.equip_table = self._build_equip_tab(
            all_equip_groups or {}, misc_goods,
        )

        # ── Tab 3: Commodities (Liste + Tabelle mit Preisen) ──
        self._commodity_prices = commodity_prices or {}
        self.comm_available, self.comm_table = self._build_commodity_tab(
            all_commodity_nicks or [], comm_goods,
        )

        # ── Tab 4: Schiffe (3 Slots) ──
        assigned_ships = [row[0].strip() for row in ship_goods if row]
        self._ship_market_data: dict[str, list[str]] = {}
        for row in ship_goods:
            if row:
                self._ship_market_data[row[0].strip().lower()] = row
        self._build_ships_tab(all_ship_nicks or [], assigned_ships)

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

    # ------------------------------------------------------------------
    #  Tab: Eigenschaften
    # ------------------------------------------------------------------
    def _build_properties_tab(
        self,
        obj_entries: list[tuple[str, str]],
        pilots: list[str],
        voices: list[str],
        heads: list[str],
        bodies: list[str],
        archetypes: list[str],
        loadouts: list[str],
        factions: list[str],
        current_name_text: str = "",
        current_infocard_xml: str = "",
    ):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QFormLayout(content)
        scroll.setWidget(content)

        obj_dict: dict[str, str] = {}
        for k, v in obj_entries:
            obj_dict.setdefault(k.lower(), v)

        self.prop_nick = QLineEdit(obj_dict.get("nickname", ""))
        layout.addRow("Nickname:", self.prop_nick)

        self.prop_arch = QComboBox()
        self.prop_arch.setEditable(True)
        if archetypes:
            self.prop_arch.addItems(archetypes)
        self.prop_arch.setCurrentText(obj_dict.get("archetype", ""))
        layout.addRow(tr("lbl.archetype"), self.prop_arch)

        self.prop_loadout = QComboBox()
        self.prop_loadout.setEditable(True)
        self.prop_loadout.addItem("")
        if loadouts:
            self.prop_loadout.addItems(loadouts)
        self.prop_loadout.setCurrentText(obj_dict.get("loadout", ""))
        layout.addRow("Loadout:", self.prop_loadout)

        self.prop_rep = QComboBox()
        self.prop_rep.setEditable(True)
        self.prop_rep.addItem("")
        if factions:
            self.prop_rep.addItems(factions)
        self.prop_rep.setCurrentText(obj_dict.get("reputation", ""))
        layout.addRow("Reputation:", self.prop_rep)

        self.prop_pilot = QComboBox()
        self.prop_pilot.setEditable(True)
        pilot_list = list(dict.fromkeys(
            ["pilot_solar_easiest", "pilot_solar_easy",
             "pilot_solar_hard", "pilot_solar_hardest"] + pilots
        ))
        pilot_list = [p for p in pilot_list if p.lower().startswith("pilot_solar")]
        self.prop_pilot.addItems(pilot_list)
        self.prop_pilot.setCurrentText(obj_dict.get("pilot", "pilot_solar_easiest"))
        layout.addRow("Pilot:", self.prop_pilot)

        self.prop_voice = QComboBox()
        self.prop_voice.setEditable(True)
        self.prop_voice.addItem("")
        if voices:
            self.prop_voice.addItems(voices)
        self.prop_voice.setCurrentText(obj_dict.get("voice", ""))
        layout.addRow("Voice:", self.prop_voice)

        # Space Costume
        costume_val = obj_dict.get("space_costume", "")
        c_parts = [p.strip() for p in costume_val.split(",", 1)] if costume_val else ["", ""]
        if len(c_parts) < 2:
            c_parts.append("")

        self.prop_head = QComboBox()
        self.prop_head.setEditable(True)
        self.prop_head.addItem("")
        if heads:
            self.prop_head.addItems(heads)
        self.prop_head.setCurrentText(c_parts[0])
        layout.addRow("Head:", self.prop_head)

        self.prop_body = QComboBox()
        self.prop_body.setEditable(True)
        self.prop_body.addItem("")
        if bodies:
            self.prop_body.addItems(bodies)
        self.prop_body.setCurrentText(c_parts[1])
        layout.addRow("Body:", self.prop_body)

        self.prop_ids_name = QSpinBox()
        self.prop_ids_name.setRange(0, 999999)
        self.prop_ids_name.setValue(int(obj_dict.get("ids_name", "0") or 0))
        layout.addRow("ids_name:", self.prop_ids_name)

        self.prop_ids_info = QSpinBox()
        self.prop_ids_info.setRange(0, 999999)
        self.prop_ids_info.setValue(int(obj_dict.get("ids_info", "0") or 0))
        layout.addRow("ids_info:", self.prop_ids_info)

        self.prop_name_text = QLineEdit(str(current_name_text or "").strip())
        self.prop_name_text.setPlaceholderText("Ingame Name")
        layout.addRow("Name:", self.prop_name_text)

        self.prop_infocard_xml = QTextEdit()
        self.prop_infocard_xml.setAcceptRichText(False)
        self.prop_infocard_xml.setMinimumHeight(150)
        self.prop_infocard_xml.setPlainText(str(current_infocard_xml or "").strip())
        layout.addRow("Infocard XML:", self.prop_infocard_xml)

        jump_btn = QPushButton("InfoCard Editor öffnen")
        jump_btn.clicked.connect(self._on_jump_infocard_editor)
        layout.addRow("", jump_btn)

        self.prop_behavior = QLineEdit(obj_dict.get("behavior", "NOTHING"))
        layout.addRow("Behavior:", self.prop_behavior)

        self.prop_difficulty = QSpinBox()
        self.prop_difficulty.setRange(0, 100)
        self.prop_difficulty.setValue(int(obj_dict.get("difficulty_level", "1") or 1))
        layout.addRow("Difficulty Level:", self.prop_difficulty)

        self.tabs.addTab(scroll, tr("dlg.tab_properties"))

    def _on_jump_infocard_editor(self):
        cb = self._infocard_jump_cb
        if not callable(cb):
            return
        ids_info = int(self.prop_ids_info.value())
        if ids_info <= 0:
            QMessageBox.information(self, tr("msg.error"), tr("msg.infocard_no_ids_info"))
            return
        self.reject()
        QTimer.singleShot(0, lambda: cb(ids_info))

    # ------------------------------------------------------------------
    #  Tab: Dual-List  (Equipment / Commodities)
    # ------------------------------------------------------------------
    def _build_dual_list_tab(
        self,
        label: str,
        all_nicks: list[str],
        assigned_nicks: list[str],
    ) -> tuple[QListWidget, QListWidget]:
        """Erstellt einen Tab mit zwei Listen und Verschiebe-Buttons.

        Linke Liste = alle verfügbaren Einträge (abzüglich zugewiesener).
        Rechte Liste = der Base zugewiesene Einträge.
        """
        tab = QWidget()
        hl = QHBoxLayout(tab)

        # ── Linke Spalte: Verfügbar ──
        left_vl = QVBoxLayout()
        left_vl.addWidget(QLabel(tr("dlg.available")))
        filter_edit = QLineEdit()
        filter_edit.setPlaceholderText("Filter …")
        left_vl.addWidget(filter_edit)
        avail_list = QListWidget()
        avail_list.setSelectionMode(QListWidget.ExtendedSelection)
        avail_list.setSortingEnabled(True)
        left_vl.addWidget(avail_list)
        hl.addLayout(left_vl, 1)

        # ── Mitte: Buttons ──
        mid_vl = QVBoxLayout()
        mid_vl.addStretch()
        btn_to_right = QPushButton("→")
        btn_to_right.setFixedWidth(40)
        btn_to_left = QPushButton("←")
        btn_to_left.setFixedWidth(40)
        mid_vl.addWidget(btn_to_right)
        mid_vl.addWidget(btn_to_left)
        mid_vl.addStretch()
        hl.addLayout(mid_vl)

        # ── Rechte Spalte: Zugewiesen ──
        right_vl = QVBoxLayout()
        right_vl.addWidget(QLabel(tr("dlg.on_this_base")))
        assigned_list = QListWidget()
        assigned_list.setSelectionMode(QListWidget.ExtendedSelection)
        assigned_list.setSortingEnabled(True)
        right_vl.addWidget(assigned_list)
        hl.addLayout(right_vl, 1)

        # Listen befüllen
        assigned_lower = {n.strip().lower() for n in assigned_nicks}
        for nick in sorted(all_nicks, key=str.lower):
            if nick.strip().lower() not in assigned_lower:
                avail_list.addItem(nick)
        for nick in assigned_nicks:
            assigned_list.addItem(nick.strip())

        # Filter-Logik
        def _filter_changed(text: str):
            t = text.lower()
            for i in range(avail_list.count()):
                item = avail_list.item(i)
                item.setHidden(t not in item.text().lower())

        filter_edit.textChanged.connect(_filter_changed)

        # Verschieben → (verfügbar → zugewiesen)
        def _move_right():
            for item in avail_list.selectedItems():
                assigned_list.addItem(item.text())
                avail_list.takeItem(avail_list.row(item))

        # Verschieben ← (zugewiesen → verfügbar)
        def _move_left():
            for item in assigned_list.selectedItems():
                avail_list.addItem(item.text())
                assigned_list.takeItem(assigned_list.row(item))

        btn_to_right.clicked.connect(_move_right)
        btn_to_left.clicked.connect(_move_left)

        # Doppelklick = sofort verschieben
        avail_list.itemDoubleClicked.connect(
            lambda it: (assigned_list.addItem(it.text()),
                        avail_list.takeItem(avail_list.row(it)))
        )
        assigned_list.itemDoubleClicked.connect(
            lambda it: (avail_list.addItem(it.text()),
                        assigned_list.takeItem(assigned_list.row(it)))
        )

        self.tabs.addTab(tab, label)
        return avail_list, assigned_list

    # ------------------------------------------------------------------
    #  Tab: Equipment  (Gruppierter Baum + Tabelle mit Parametern)
    # ------------------------------------------------------------------
    _EQUIP_COLS = ["Nickname", "Level", "Rep", "Min-Stock", "Max-Stock",
                   tr("dlg.col_sell_buy"), tr("dlg.col_price_multi")]

    def _build_equip_tab(
        self,
        equip_groups: dict[str, list[str]],
        equip_goods: list[list[str]],
    ) -> tuple[QTreeWidget, QTableWidget]:
        """Erstellt den Equipment-Tab.

        Links: QTreeWidget mit Gruppen (Waffen, Schilde, …).
        Rechts: QTableWidget mit den der Base zugewiesenen Einträgen.
        """
        tab = QWidget()
        hl = QHBoxLayout(tab)

        # ── Linke Spalte: Gruppierter Baum ──
        left_vl = QVBoxLayout()
        left_vl.addWidget(QLabel(tr("dlg.available")))
        filter_edit = QLineEdit()
        filter_edit.setPlaceholderText("Filter …")
        left_vl.addWidget(filter_edit)
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        left_vl.addWidget(tree)
        hl.addLayout(left_vl, 1)

        # ── Mitte: Buttons ──
        mid_vl = QVBoxLayout()
        mid_vl.addStretch()
        btn_to_right = QPushButton("→")
        btn_to_right.setFixedWidth(40)
        btn_to_left = QPushButton("←")
        btn_to_left.setFixedWidth(40)
        mid_vl.addWidget(btn_to_right)
        mid_vl.addWidget(btn_to_left)
        mid_vl.addStretch()
        hl.addLayout(mid_vl)

        # ── Rechte Spalte: Tabelle ──
        right_vl = QVBoxLayout()
        right_vl.addWidget(QLabel(tr("dlg.on_this_base")))
        table = QTableWidget(0, len(self._EQUIP_COLS))
        table.setHorizontalHeaderLabels(self._EQUIP_COLS)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        table.setSelectionBehavior(QTableWidget.SelectRows)
        right_vl.addWidget(table)

        legend = QLabel(tr("dlg.equip_legend"))
        legend.setWordWrap(True)
        right_vl.addWidget(legend)
        hl.addLayout(right_vl, 2)

        # ── Tabelle befüllen (vorhandene Einträge) ──
        assigned_lower: set[str] = set()
        for row in equip_goods:
            if not row:
                continue
            nick = row[0].strip()
            assigned_lower.add(nick.lower())
            r = table.rowCount()
            table.insertRow(r)
            table.setItem(r, 0, QTableWidgetItem(nick))
            defaults = ["0", "-1", "10", "10", "0", "1"]
            for col in range(1, len(self._EQUIP_COLS)):
                val = row[col].strip() if col < len(row) else defaults[col - 1]
                table.setItem(r, col, QTableWidgetItem(val))

        # ── Baum befüllen (gruppiert) ──
        for group_label, nicks in equip_groups.items():
            group_item = QTreeWidgetItem(tree, [group_label])
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            group_item.setFlags(
                group_item.flags() & ~Qt.ItemIsSelectable
            )
            for nick in nicks:
                if nick.strip().lower() not in assigned_lower:
                    child = QTreeWidgetItem(group_item, [nick])
                    child.setData(0, Qt.UserRole, nick)

        # ── Filter ──
        def _filter_changed(text: str):
            t = text.lower()
            for gi in range(tree.topLevelItemCount()):
                group = tree.topLevelItem(gi)
                any_visible = False
                for ci in range(group.childCount()):
                    child = group.child(ci)
                    vis = t in child.text(0).lower()
                    child.setHidden(not vis)
                    if vis:
                        any_visible = True
                group.setHidden(not any_visible)
                if any_visible and t:
                    group.setExpanded(True)

        filter_edit.textChanged.connect(_filter_changed)

        # ── Verschieben → (Baum → Tabelle) ──
        def _move_right():
            for sel_item in tree.selectedItems():
                nick = sel_item.data(0, Qt.UserRole)
                if not nick:
                    continue  # Gruppe ignorieren
                r = table.rowCount()
                table.insertRow(r)
                table.setItem(r, 0, QTableWidgetItem(nick))
                for col, val in enumerate(
                    ["0", "-1", "10", "10", "0", "1"], start=1
                ):
                    table.setItem(r, col, QTableWidgetItem(val))
                parent = sel_item.parent()
                if parent:
                    parent.removeChild(sel_item)

        # ── Verschieben ← (Tabelle → Baum) ──
        def _move_left():
            rows = sorted(
                {idx.row() for idx in table.selectedIndexes()},
                reverse=True,
            )
            for r in rows:
                nick_item = table.item(r, 0)
                if nick_item:
                    nick = nick_item.text()
                    # In passende Gruppe einfügen (oder erste)
                    inserted = False
                    for gi in range(tree.topLevelItemCount()):
                        group = tree.topLevelItem(gi)
                        # Suche ob Nick ursprünglich zu dieser Gruppe gehörte
                        grp_label = group.text(0)
                        if grp_label in equip_groups:
                            nicks_in_grp = [n.lower() for n in equip_groups[grp_label]]
                            if nick.lower() in nicks_in_grp:
                                child = QTreeWidgetItem(group, [nick])
                                child.setData(0, Qt.UserRole, nick)
                                inserted = True
                                break
                    if not inserted and tree.topLevelItemCount() > 0:
                        group = tree.topLevelItem(0)
                        child = QTreeWidgetItem(group, [nick])
                        child.setData(0, Qt.UserRole, nick)
                table.removeRow(r)

        btn_to_right.clicked.connect(_move_right)
        btn_to_left.clicked.connect(_move_left)

        # Doppelklick auf Blatt = sofort verschieben
        def _dbl_click(item, _col):
            nick = item.data(0, Qt.UserRole)
            if not nick:
                return
            r = table.rowCount()
            table.insertRow(r)
            table.setItem(r, 0, QTableWidgetItem(nick))
            for col, val in enumerate(
                ["0", "-1", "10", "10", "0", "1"], start=1
            ):
                table.setItem(r, col, QTableWidgetItem(val))
            parent = item.parent()
            if parent:
                parent.removeChild(item)

        tree.itemDoubleClicked.connect(_dbl_click)

        self.tabs.addTab(tab, "Equipment")
        return tree, table

    # ------------------------------------------------------------------
    #  Tab: Commodities  (Liste + Tabelle mit Parametern + Preisberechnung)
    # ------------------------------------------------------------------
    _COMM_COLS = ["Nickname", "Level", "Rep", "Min-Stock", "Max-Stock",
                  tr("dlg.col_sell_buy"), tr("dlg.col_price_multi"), tr("dlg.col_base_price"), tr("dlg.col_end_price")]

    def _build_commodity_tab(
        self,
        all_nicks: list[str],
        comm_goods: list[list[str]],
    ) -> tuple[QListWidget, QTableWidget]:
        """Erstellt den Commodities-Tab.

        Links: QListWidget mit allen verfügbaren Commodity-Nicknames.
        Rechts: QTableWidget mit den der Base zugewiesenen Commodities
                samt editierbaren Parametern und berechneter Preisanzeige.
        """
        tab = QWidget()
        hl = QHBoxLayout(tab)

        # ── Linke Spalte: Verfügbar ──
        left_vl = QVBoxLayout()
        left_vl.addWidget(QLabel(tr("dlg.available")))
        filter_edit = QLineEdit()
        filter_edit.setPlaceholderText("Filter …")
        left_vl.addWidget(filter_edit)
        avail_list = QListWidget()
        avail_list.setSelectionMode(QListWidget.ExtendedSelection)
        avail_list.setSortingEnabled(True)
        left_vl.addWidget(avail_list)
        hl.addLayout(left_vl, 1)

        # ── Mitte: Buttons ──
        mid_vl = QVBoxLayout()
        mid_vl.addStretch()
        btn_to_right = QPushButton("→")
        btn_to_right.setFixedWidth(40)
        btn_to_left = QPushButton("←")
        btn_to_left.setFixedWidth(40)
        mid_vl.addWidget(btn_to_right)
        mid_vl.addWidget(btn_to_left)
        mid_vl.addStretch()
        hl.addLayout(mid_vl)

        # ── Rechte Spalte: Tabelle mit Parametern ──
        right_vl = QVBoxLayout()
        right_vl.addWidget(QLabel(tr("dlg.on_this_base")))
        table = QTableWidget(0, len(self._COMM_COLS))
        table.setHorizontalHeaderLabels(self._COMM_COLS)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        table.setSelectionBehavior(QTableWidget.SelectRows)
        right_vl.addWidget(table)

        # Legende
        legend = QLabel(tr("dlg.comm_legend"))
        legend.setWordWrap(True)
        right_vl.addWidget(legend)
        hl.addLayout(right_vl, 2)

        # Preislookup
        prices = self._commodity_prices

        def _set_price_cells(row: int, nick: str, multi_str: str):
            """Setzt Base-Preis (readonly) und berechnet Endpreis."""
            base_price = prices.get(nick, 0)
            bp_item = QTableWidgetItem(str(base_price))
            bp_item.setFlags(bp_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 7, bp_item)
            try:
                multi = float(multi_str)
            except (ValueError, TypeError):
                multi = 1.0
            end_price = round(base_price * multi)
            ep_item = QTableWidgetItem(str(end_price))
            ep_item.setFlags(ep_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 8, ep_item)

        def _recalc_endpreis(row: int, col: int):
            """Wird aufgerufen wenn eine Zelle geändert wird."""
            if col == 6:  # Preis-Multi geändert
                nick_item = table.item(row, 0)
                multi_item = table.item(row, 6)
                if nick_item and multi_item:
                    _set_price_cells(row, nick_item.text().strip(),
                                     multi_item.text().strip())
            elif col == 0:  # Nickname geändert → Base-Preis aktualisieren
                nick_item = table.item(row, 0)
                multi_item = table.item(row, 6)
                if nick_item:
                    _set_price_cells(
                        row, nick_item.text().strip(),
                        multi_item.text().strip() if multi_item else "1"
                    )

        table.cellChanged.connect(_recalc_endpreis)

        # ── Listen befüllen ──
        assigned_lower: set[str] = set()
        table.blockSignals(True)
        for row_data in comm_goods:
            if not row_data:
                continue
            nick = row_data[0].strip()
            assigned_lower.add(nick.lower())
            r = table.rowCount()
            table.insertRow(r)
            table.setItem(r, 0, QTableWidgetItem(nick))
            defaults = ["0", "-1", "0", "0", "0", "1"]
            for col in range(1, 7):
                val = row_data[col].strip() if col < len(row_data) else defaults[col - 1]
                table.setItem(r, col, QTableWidgetItem(val))
            multi_str = row_data[6].strip() if len(row_data) > 6 else "1"
            _set_price_cells(r, nick, multi_str)
        table.blockSignals(False)

        for nick in sorted(all_nicks, key=str.lower):
            if nick.strip().lower() not in assigned_lower:
                avail_list.addItem(nick)

        # ── Filter ──
        def _filter_changed(text: str):
            t = text.lower()
            for i in range(avail_list.count()):
                item = avail_list.item(i)
                item.setHidden(t not in item.text().lower())

        filter_edit.textChanged.connect(_filter_changed)

        # ── Verschieben → (Liste → Tabelle) ──
        def _move_right():
            table.blockSignals(True)
            for item in avail_list.selectedItems():
                nick = item.text()
                r = table.rowCount()
                table.insertRow(r)
                table.setItem(r, 0, QTableWidgetItem(nick))
                for col, val in enumerate(
                    ["0", "-1", "0", "0", "0", "1"], start=1
                ):
                    table.setItem(r, col, QTableWidgetItem(val))
                _set_price_cells(r, nick, "1")
                avail_list.takeItem(avail_list.row(item))
            table.blockSignals(False)

        # ── Verschieben ← (Tabelle → Liste) ──
        def _move_left():
            rows = sorted(
                {idx.row() for idx in table.selectedIndexes()},
                reverse=True,
            )
            for r in rows:
                nick_item = table.item(r, 0)
                if nick_item:
                    avail_list.addItem(nick_item.text())
                table.removeRow(r)

        btn_to_right.clicked.connect(_move_right)
        btn_to_left.clicked.connect(_move_left)

        # Doppelklick links = sofort in Tabelle
        def _dbl_left(it):
            nick = it.text()
            table.blockSignals(True)
            r = table.rowCount()
            table.insertRow(r)
            table.setItem(r, 0, QTableWidgetItem(nick))
            for col, val in enumerate(
                ["0", "-1", "0", "0", "0", "1"], start=1
            ):
                table.setItem(r, col, QTableWidgetItem(val))
            _set_price_cells(r, nick, "1")
            table.blockSignals(False)
            avail_list.takeItem(avail_list.row(it))

        avail_list.itemDoubleClicked.connect(_dbl_left)

        self.tabs.addTab(tab, "Commodities")
        return avail_list, table

    # ------------------------------------------------------------------
    #  Tab: Schiffe  (3 Slot-Boxen)
    # ------------------------------------------------------------------
    def _build_ships_tab(
        self,
        all_ship_nicks: list[str],
        assigned_ships: list[str],
    ):
        tab = QWidget()
        vl = QVBoxLayout(tab)
        vl.addWidget(QLabel(tr("dlg.max_ships")))
        vl.addSpacing(10)

        self.ship_combos: list[QComboBox] = []

        for slot in range(3):
            slot_hl = QHBoxLayout()
            lbl = QLabel(f"Slot {slot + 1}:")
            lbl.setFixedWidth(50)
            slot_hl.addWidget(lbl)

            combo = QComboBox()
            combo.setEditable(True)
            combo.addItem("")  # leer = kein Schiff
            combo.addItems(sorted(all_ship_nicks, key=str.lower))
            # Vorhandenes Schiff setzen
            if slot < len(assigned_ships) and assigned_ships[slot]:
                combo.setCurrentText(assigned_ships[slot])
            else:
                combo.setCurrentText("")
            combo.setMinimumWidth(350)
            slot_hl.addWidget(combo, 1)
            slot_hl.addStretch()
            vl.addLayout(slot_hl)
            self.ship_combos.append(combo)

        vl.addStretch()
        self.tabs.addTab(tab, "Schiffe")

    # ------------------------------------------------------------------
    #  Ergebnisse auslesen
    # ------------------------------------------------------------------
    def get_obj_properties(self) -> dict[str, str]:
        """Gibt die bearbeiteten Objekt-Eigenschaften zurück."""
        head = self.prop_head.currentText().strip()
        body = self.prop_body.currentText().strip()
        if head and body:
            costume = f"{head}, {body}"
        elif head:
            costume = head
        elif body:
            costume = body
        else:
            costume = ""
        return {
            "nickname": self.prop_nick.text().strip(),
            "archetype": self.prop_arch.currentText().strip(),
            "loadout": self.prop_loadout.currentText().strip(),
            "reputation": self.prop_rep.currentText().strip(),
            "pilot": self.prop_pilot.currentText().strip(),
            "voice": self.prop_voice.currentText().strip(),
            "space_costume": costume,
            "ids_name": str(self.prop_ids_name.value()),
            "ids_info": str(self.prop_ids_info.value()),
            "behavior": self.prop_behavior.text().strip(),
            "difficulty_level": str(self.prop_difficulty.value()),
        }

    def get_name_text(self) -> str:
        return self.prop_name_text.text().strip() if hasattr(self, "prop_name_text") else ""

    def get_infocard_xml(self) -> str:
        return self.prop_infocard_xml.toPlainText().strip() if hasattr(self, "prop_infocard_xml") else ""

    def get_equip_nicknames(self) -> list[str]:
        """Gibt die zugewiesenen Equipment-Nicknames zurück."""
        result: list[str] = []
        for r in range(self.equip_table.rowCount()):
            item = self.equip_table.item(r, 0)
            if item and item.text().strip():
                result.append(item.text().strip())
        return result

    def get_commodity_nicknames(self) -> list[str]:
        """Gibt die zugewiesenen Commodity-Nicknames zurück."""
        result: list[str] = []
        for r in range(self.comm_table.rowCount()):
            item = self.comm_table.item(r, 0)
            if item and item.text().strip():
                result.append(item.text().strip())
        return result

    def get_ship_nicknames(self) -> list[str]:
        """Gibt die gewählten Schiffs-Nicknames zurück (max 3, leere übersprungen)."""
        result: list[str] = []
        for combo in self.ship_combos:
            nick = combo.currentText().strip()
            if nick:
                result.append(nick)
        return result

    def get_equip_market_goods(self) -> list[list[str]]:
        """Liest alle Zeilen der Equipment-Tabelle aus."""
        result: list[list[str]] = []
        for r in range(self.equip_table.rowCount()):
            fields: list[str] = []
            for c in range(self.equip_table.columnCount()):
                item = self.equip_table.item(r, c)
                fields.append(item.text().strip() if item else "")
            if fields[0]:  # Nickname muss vorhanden sein
                result.append(fields)
        return result

    def get_commodity_market_goods(self) -> list[list[str]]:
        """Liest alle Zeilen der Commodity-Tabelle aus (nur die 7 MarketGood-Felder)."""
        result: list[list[str]] = []
        for r in range(self.comm_table.rowCount()):
            fields: list[str] = []
            for c in range(7):  # nur Nickname..Preis-Multi, nicht Base-Preis/Endpreis
                item = self.comm_table.item(r, c)
                fields.append(item.text().strip() if item else "")
            if fields[0]:  # Nickname muss vorhanden sein
                result.append(fields)
        return result

    def get_ship_market_goods(self) -> list[list[str]]:
        """Baut MarketGood-Zeilen für Schiffe."""
        nicks = self.get_ship_nicknames()
        result: list[list[str]] = []
        for nick in nicks:
            existing = self._ship_market_data.get(nick.strip().lower())
            if existing:
                result.append(existing)
            else:
                result.append([nick, "1", "-1", "1", "1", "0", "1", "1"])
        return result


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
            self.start_room_cb.addItems([r for r, _ in self.ROOM_CHOICES])
            self.start_room_cb.setCurrentText("Deck")
            sr_row = QHBoxLayout()
            sr_row.addWidget(QLabel(tr("dlg.start_room")))
            sr_row.addWidget(self.start_room_cb)
            gl_rooms.addLayout(sr_row)

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

    def payload(self) -> dict:
        result: dict = {
            "nickname": self.nick_edit.text().strip(),
            "archetype": self.arch_cb.currentText().strip(),
            "loadout": self.loadout_cb.currentText().strip(),
            "faction": self.faction_cb.currentText().strip(),
            "voice": self.voice_cb.currentText().strip(),
            "costume": self.costume_edit.text().strip(),
            "pilot": self.pilot_cb.currentText().strip(),
            "difficulty": self.diff_spin.value(),
            "ids_name": self.ids_name_edit.text().strip(),
            "ids_info": self.ids_info_edit.text().strip(),
        }
        if self._needs_base:
            rooms = [name for name, cb in self.room_checks.items() if cb.isChecked()]
            result.update({
                "base_nickname": self.base_nick_edit.text().strip(),
                "strid_name": self.strid_name_spin.value(),
                "rooms": rooms,
                "start_room": self.start_room_cb.currentText().strip(),
                "price_variance": self.price_var_spin.value(),
                "template_base": self.template_cb.currentText().strip(),
            })
        else:
            result["base_nickname"] = self._existing_base_nick
        return result
