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
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QUrl
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


# ══════════════════════════════════════════════════════════════════════
#  Connection-Dialog  (Jump Hole / Gate)
# ══════════════════════════════════════════════════════════════════════

class ConnectionDialog(QDialog):
    """Zielsystem und Typ (Jump Hole / Jump Gate) auswählen."""

    def __init__(self, parent, systems: list[tuple[str, str]]):
        super().__init__(parent)
        self.setWindowTitle("Jump Hole / Gate erstellen")
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Zielsystem:"))
        self.dest_cb = QComboBox()
        for nick, path in systems:
            self.dest_cb.addItem(nick, path)
        layout.addWidget(self.dest_cb)

        layout.addWidget(QLabel("Typ:"))
        self.type_cb = QComboBox()
        self.type_cb.addItems(["Jump Hole", "Jump Gate"])
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
        self.setWindowTitle("Gate-Parameter")
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
        self.setWindowTitle("Zone erstellen")
        self.setMinimumWidth(500)
        layout = QFormLayout(self)

        self.type_cb = QComboBox()
        self.type_cb.addItems(["Asteroid Field", "Nebula"])
        layout.addRow("Typ:", self.type_cb)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("z.B. PleioneNebula")
        layout.addRow("Zonenname:", self.name_edit)

        self.ref_cb = QComboBox()
        self.type_cb.currentTextChanged.connect(self._on_type_changed)
        self._ast_list = asteroids
        self._neb_list = nebulas
        self._on_type_changed("Asteroid Field")
        layout.addRow("Referenzdatei:", self.ref_cb)

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

        self.arch_cb = QComboBox()
        self.arch_cb.setEditable(True)
        self.arch_cb.addItems(archetypes)
        layout.addRow("Archetype:", self.arch_cb)

        burn_row = QWidget()
        burn_l = QHBoxLayout(burn_row)
        burn_l.setContentsMargins(0, 0, 0, 0)
        self.burn_btn = QPushButton("Burn Color wählen")
        self.burn_lbl = QLabel("(optional)")
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
            "archetype": self.arch_cb.currentText().strip(),
            "burn_color": self._burn_rgb,
            "radius": self.radius_spin.value(),
            "damage": self.damage_spin.value(),
            "star": self.star_cb.currentText().strip() if self.star_cb else "",
            "atmosphere_range": self.atmo_spin.value(),
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
        self.setWindowTitle("Objekt erstellen")
        layout = QFormLayout(self)

        self.nick_edit = QLineEdit()
        layout.addRow("Nickname:", self.nick_edit)

        self.arch_cb = QComboBox()
        self.arch_cb.setEditable(True)
        self.arch_cb.addItems(archetypes)
        layout.addRow("Archetype:", self.arch_cb)

        self.loadout_cb = QComboBox()
        self.loadout_cb.setEditable(True)
        self.loadout_cb.addItems(loadouts)
        layout.addRow("Loadout:", self.loadout_cb)

        self.faction_cb = QComboBox()
        self.faction_cb.setEditable(True)
        self.faction_cb.addItems(factions)
        layout.addRow("Faction:", self.faction_cb)

        self.rep_edit = QLineEdit()
        self.rep_edit.setPlaceholderText("optional")
        layout.addRow("Reputation:", self.rep_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def payload(self) -> dict:
        return {
            "nickname": self.nick_edit.text().strip(),
            "archetype": self.arch_cb.currentText().strip(),
            "loadout": self.loadout_cb.currentText().strip(),
            "faction": self.faction_cb.currentText().strip(),
            "rep": self.rep_edit.text().strip(),
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
                QLabel("Qt3D ist in dieser PySide6-Installation nicht verfügbar.")
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
        self.setWindowTitle("Neues System erstellen")
        self.setMinimumWidth(420)
        layout = QFormLayout(self)

        # 1. Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("z. B. Taharka")
        layout.addRow("System Name:", self.name_edit)

        # 2. Prefix
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("z. B. TE")
        self.prefix_edit.setMaxLength(4)
        layout.addRow("System Prefix:", self.prefix_edit)

        # 3. Größe
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1000, 10_000_000)
        self.size_spin.setValue(100000)
        layout.addRow("Systemgröße (Range):", self.size_spin)

        # 4. Space Color
        self._space_rgb = "0, 0, 0"
        space_row = QWidget()
        sl = QHBoxLayout(space_row)
        sl.setContentsMargins(0, 0, 0, 0)
        self.space_color_btn = QPushButton("Farbe wählen")
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
        self.ambient_color_btn = QPushButton("Farbe wählen")
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
        self.light_color_btn = QPushButton("Farbe wählen")
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
        space_btn = QPushButton("Farbe wählen")
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
        ambient_btn = QPushButton("Farbe wählen")
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
        self.setWindowTitle("Tradelane erstellen")
        self.setMinimumWidth(440)
        self._distance = distance

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        # Anzahl Ringe (vorberechnet, editierbar)
        self.count_spin = QSpinBox()
        self.count_spin.setRange(2, 200)
        self.count_spin.setValue(ring_count)
        form.addRow("Anzahl Ringe:", self.count_spin)

        # Abstand zwischen Ringen
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(500, 50000)
        self.spacing_spin.setSingleStep(500)
        self.spacing_spin.setValue(7500)
        self.spacing_spin.setSuffix(" Einheiten")
        self.spacing_spin.valueChanged.connect(self._on_spacing_changed)
        form.addRow("Abstand:", self.spacing_spin)

        # Startnummer
        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, 99999)
        self.start_spin.setValue(start_num)
        form.addRow("Startnummer:", self.start_spin)

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

        # ids_name
        self.ids_name_edit = QLineEdit("0")
        form.addRow("ids_name:", self.ids_name_edit)

        # tradelane_space_name Start
        self.space_name_start_edit = QLineEdit("0")
        form.addRow("space_name (Start):", self.space_name_start_edit)

        # tradelane_space_name Ende
        self.space_name_end_edit = QLineEdit("0")
        form.addRow("space_name (Ende):", self.space_name_end_edit)

        layout.addLayout(form)

        # Info-Label
        info = QLabel(
            f"System: {system_nick}  •  "
            f"Nicknames: {system_nick}_Trade_Lane_Ring_N\n"
            f"Abstand zwischen Ringen: ~7.500 Einheiten"
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
        self.setWindowTitle("Tradelane-Routen bearbeiten")
        self.setMinimumWidth(520)
        self.setMinimumHeight(360)
        self._chains = chains
        self._action: str | None = None
        self._selected_chain_idx: int = -1

        layout = QVBoxLayout(self)

        info = QLabel(f"{len(chains)} Tradelane-Route(n) erkannt:")
        info.setStyleSheet("font-weight:bold; margin-bottom:4px;")
        layout.addWidget(info)

        self.chain_list = QListWidget()
        for i, chain in enumerate(chains):
            first = chain[0]["nickname"]
            last = chain[-1]["nickname"]
            count = len(chain)
            item_text = f"Route {i+1}:  {first}  →  {last}   ({count} Ringe)"
            item = QListWidgetItem(item_text)
            item.setData(256, i)
            self.chain_list.addItem(item)
        self.chain_list.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self.chain_list)

        # Detail-Box
        self.detail_grp = QGroupBox("Details")
        dl = QVBoxLayout(self.detail_grp)
        self.detail_lbl = QLabel("Wähle eine Route aus der Liste.")
        self.detail_lbl.setWordWrap(True)
        self.detail_lbl.setStyleSheet("font-size:9pt;")
        dl.addWidget(self.detail_lbl)

        btn_row = QHBoxLayout()
        self.delete_btn = QPushButton("🗑  Route löschen")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self.delete_btn)

        self.reposition_btn = QPushButton("📐  Start-/Endpunkt neu setzen")
        self.reposition_btn.setEnabled(False)
        self.reposition_btn.clicked.connect(self._on_reposition)
        btn_row.addWidget(self.reposition_btn)
        dl.addLayout(btn_row)

        layout.addWidget(self.detail_grp)

        # Schließen
        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def _on_selection_changed(self, row: int):
        self._selected_chain_idx = row
        enabled = (0 <= row < len(self._chains))
        self.delete_btn.setEnabled(enabled)
        self.reposition_btn.setEnabled(enabled)
        if enabled:
            chain = self._chains[row]
            first = chain[0]
            last = chain[-1]
            self.detail_lbl.setText(
                f"Start: {first['nickname']}  pos=({first.get('pos', '?')})\n"
                f"Ende:  {last['nickname']}  pos=({last.get('pos', '?')})\n"
                f"Ringe: {len(chain)}   "
                f"Loadout: {first.get('loadout', '?')}   "
                f"Rotation: {first.get('rotate', '?')}"
            )

    def _on_delete(self):
        self._action = "delete"
        self.accept()

    def _on_reposition(self):
        self._action = "reposition"
        self.accept()

    @property
    def action(self) -> str | None:
        return self._action

    @property
    def selected_chain_index(self) -> int:
        return self._selected_chain_idx
