"""Dialoge für den Freelancer System Editor.

Enthält:
- ConnectionDialog       – Zielsystem und Typ wählen (Jump Hole/Gate)
- GateInfoDialog         – Zusätzliche Gate-Parameter
- ZoneCreationDialog     – Zonentyp, Name und Referenzdatei
- SolarCreationDialog    – Sonne / Planet erstellen
- ObjectCreationDialog   – Beliebiges Objekt erstellen
- MeshPreviewDialog      – 3D-Vorschau eines Archetype-Modells
- SystemCreationDialog   – Neues Sternensystem erstellen
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
        self.name_edit.setPlaceholderText("z.B. Zone_ST04_field_01")
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
