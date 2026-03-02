"""Datenmodelle / 2D-Grafikelemente: ZoneItem, SolarObject, UniverseSystem."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsEllipseItem,
    QGraphicsTextItem,
)
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPen,
    QRadialGradient,
)


# ══════════════════════════════════════════════════════════════════════
#  Zone-Item  (visuell – akzeptiert nur Linksklick zur Auswahl)
# ══════════════════════════════════════════════════════════════════════

class ZoneItem(QGraphicsItem):
    """Stellt eine Freelancer-Zone (Sphere, Ellipsoid, Box, Cylinder) dar."""

    def __init__(self, data: dict, scale: float):
        super().__init__()
        self.data = data
        self._scale = float(scale)
        self.nickname = data.get("nickname", "")
        self.shape_t = "SPHERE"
        self.hw, self.hd = 0.0, 0.0
        self._pen, self._brush = QPen(Qt.NoPen), QBrush(Qt.NoBrush)
        self.label: QGraphicsTextItem | None = None
        self._label_default_visible = False
        self._refresh_visual_from_data()

        self.setZValue(-1)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setAcceptHoverEvents(False)

    # ------------------------------------------------------------------
    #  Styling
    # ------------------------------------------------------------------
    def _style(self):
        n = self.nickname.lower()
        d = self.data
        if "death" in n or "damage" in d:
            return QPen(QColor(220, 50, 50, 200), 1.5), QBrush(QColor(220, 50, 50, 20))
        if "nebula" in n or "badlands" in n:
            return QPen(QColor(150, 80, 220, 180), 1), QBrush(QColor(120, 60, 200, 18))
        if "debris" in n or "asteroid" in n:
            return QPen(QColor(180, 130, 60, 180), 1), QBrush(QColor(160, 120, 50, 18))
        if "tradelane" in n:
            return QPen(QColor(60, 180, 220, 160), 1, Qt.DashLine), QBrush(QColor(60, 180, 220, 12))
        if "jumpgate" in n or "hole" in n:
            return QPen(QColor(180, 100, 220, 200), 1.5), QBrush(QColor(160, 80, 200, 18))
        if "exclusion" in n:
            return QPen(QColor(220, 100, 50, 140), 1, Qt.DotLine), QBrush(QColor(200, 80, 40, 8))
        if "path" in n or "vignette" in n:
            return QPen(QColor(100, 100, 150, 70), 1, Qt.DotLine), QBrush(Qt.NoBrush)
        return QPen(QColor(80, 160, 200, 150), 1), QBrush(QColor(60, 140, 180, 14))

    def _build_label(self):
        n = self.nickname.lower()
        skip = any(
            x in n
            for x in (
                "path", "vignette", "exclusion", "death",
                "tradelane", "laneaccess", "destroyvignette",
                "sundeath", "radiation",
            )
        )
        self._label_default_visible = not (skip or self.hw < 8)
        if not self._label_default_visible:
            return
        self.label = QGraphicsTextItem(self.nickname, self)
        self.label.setDefaultTextColor(QColor(160, 160, 190))
        self.label.setFont(QFont("Sans", 6))
        self.label.setPos(4, 4)
        self.label.setVisible(self._label_default_visible)
        self.label.setAcceptedMouseButtons(Qt.NoButton)

    @staticmethod
    def _parse_float_list(raw: str) -> list[float]:
        out: list[float] = []
        for part in str(raw or "").split(","):
            txt = part.strip()
            if not txt:
                continue
            try:
                out.append(float(txt))
            except ValueError:
                out.append(0.0)
        return out

    def _refresh_visual_from_data(self):
        self.nickname = self.data.get("nickname", self.nickname)
        self.shape_t = str(self.data.get("shape", "SPHERE")).upper()

        sp = self._parse_float_list(self.data.get("size", "1000"))
        s0 = sp[0] if len(sp) > 0 else 1000.0
        s1 = sp[1] if len(sp) > 1 else s0
        s2 = sp[2] if len(sp) > 2 else s0

        if self.shape_t == "SPHERE":
            new_hw, new_hd = s0 * self._scale, s0 * self._scale
        elif self.shape_t == "ELLIPSOID":
            new_hw, new_hd = s0 * self._scale, s2 * self._scale
        elif self.shape_t == "BOX":
            new_hw, new_hd = s0 * self._scale / 2, s2 * self._scale / 2
        elif self.shape_t == "CYLINDER":
            new_hw, new_hd = s0 * self._scale, s1 * self._scale / 2
        else:
            new_hw, new_hd = s0 * self._scale, s0 * self._scale

        if abs(new_hw - self.hw) > 1e-9 or abs(new_hd - self.hd) > 1e-9:
            self.prepareGeometryChange()
            self.hw, self.hd = new_hw, new_hd
        else:
            self.hw, self.hd = new_hw, new_hd

        pp = self._parse_float_list(self.data.get("pos", "0,0,0"))
        px = pp[0] if len(pp) > 0 else 0.0
        pz = pp[2] if len(pp) > 2 else (pp[1] if len(pp) > 1 else 0.0)
        self.setPos(px * self._scale, pz * self._scale)

        rp = self._parse_float_list(self.data.get("rotate", "0,0,0"))
        # 2D uses X/Z projection with Qt's screen Y-axis pointing down, so FL yaw
        # must be mirrored to match the 3D orientation.
        yaw = rp[1] if len(rp) > 1 else 0.0
        self.setRotation(-yaw)

        self._pen, self._brush = self._style()

    def set_label_visibility(self, enabled: bool):
        if self.label:
            self.label.setVisible(bool(enabled) and self._label_default_visible)

    # ------------------------------------------------------------------
    #  QGraphicsItem-Interface
    # ------------------------------------------------------------------
    def boundingRect(self):
        return QRectF(-self.hw - 2, -self.hd - 2, self.hw * 2 + 4, self.hd * 2 + 4)

    def paint(self, painter, option, widget=None):
        painter.setPen(self._pen)
        painter.setBrush(self._brush)
        r = QRectF(-self.hw, -self.hd, self.hw * 2, self.hd * 2)
        if self.shape_t in ("BOX", "CYLINDER"):
            painter.drawRect(r)
        else:
            painter.drawEllipse(r)

    # ------------------------------------------------------------------
    #  Daten-Serialisierung
    # ------------------------------------------------------------------
    def raw_text(self) -> str:
        """Einträge als editierbaren Text zurückgeben."""
        return "\n".join(f"{k} = {v}" for k, v in self.data.get("_entries", []))

    def apply_text(self, text: str):
        """Editierten INI-Text auf dieses Zonenobjekt anwenden."""
        new_entries: list[tuple[str, str]] = []
        for line in text.splitlines():
            line = line.strip()
            if "=" in line:
                k, _, v = line.partition("=")
                new_entries.append((k.strip(), v.strip()))

        self.data.clear()
        self.data["_entries"] = new_entries
        for k, v in new_entries:
            if k.lower() not in self.data:
                self.data[k.lower()] = v

        old_label_visible = self.label.isVisible() if self.label is not None else None
        self._refresh_visual_from_data()

        # Label-Kinder entfernen und neu aufbauen
        try:
            for child in list(self.childItems()):
                if isinstance(child, QGraphicsTextItem):
                    child.setParentItem(None)
                    if child.scene():
                        child.scene().removeItem(child)
        except Exception:
            pass
        self._build_label()
        if old_label_visible is not None and self.label is not None:
            self.label.setVisible(bool(old_label_visible) and self._label_default_visible)
        self.update()


# ══════════════════════════════════════════════════════════════════════
#  Solar-Objekt  (Stern, Planet, Basis, Jump Gate, etc.)
# ══════════════════════════════════════════════════════════════════════

class SolarObject(QGraphicsEllipseItem):
    """2D-Darstellung eines Freelancer-Objekts mit Archetype-basiertem Styling."""

    # Farb + GrößenTabelle  → (farbe, radius, z-value, schriftgröße)
    _STYLES: list[tuple[list[str], QColor, float, int, float]] = [
        (["sun", "star"],           QColor(255, 215, 40),  9.0,  3, 8.0),
        (["planet"],                QColor(60, 130, 220),  7.0,  2, 7.0),
        (["base", "station"],       QColor(80, 210, 100),  3.5,  1, 6.0),
        (["jumpgate", "jumphole", "jump_gate", "jump_hole"],
                                    QColor(210, 90, 210),  4.0,  1, 6.0),
        (["trade_lane_ring", "tradelane_ring"],
                                    QColor(70, 140, 255),  1.2, -1, 5.0),
        (["asteroid"],              QColor(150, 110, 70),  2.0,  0, 5.0),
        (["hazard_buoy", "فانوس", "فانوس_خطر"],
                                    QColor(255, 200, 60),  1.5,  0, 5.0),
        (["wreck"],                 QColor(140, 100, 80),  2.5,  0, 5.0),
    ]

    _DEFAULT_COLOR = QColor(190, 190, 190)
    _DEFAULT_RADIUS = 2.8
    _DEFAULT_Z = 0
    _DEFAULT_FONT = 5.5

    def __init__(self, data: dict, scale: float):
        super().__init__()
        self.data = data
        self.nickname = data.get("nickname", "???")
        self._pos_change_cb = None
        self._drag_finished_cb = None
        self._drag_start_scene_pos: QPointF | None = None
        self.label: QGraphicsTextItem | None = None
        self._label_default_visible = True

        arch = data.get("archetype", "").lower()
        name = self.nickname.lower()

        # Stil bestimmen
        color, radius, z_val, font_size = (
            self._DEFAULT_COLOR, self._DEFAULT_RADIUS, self._DEFAULT_Z, self._DEFAULT_FONT
        )
        for tags, c, r, z, fs in self._STYLES:
            if any(tag in arch or tag in name for tag in tags):
                color, radius, z_val, font_size = c, r, z, fs
                break

        if arch.strip() == "dock_ring":
            color, radius, z_val, font_size = QColor(255, 150, 80), 0.9, 0, 5.0

        self.setRect(-radius, -radius, radius * 2, radius * 2)
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor(255, 255, 255, 70), 1))
        self.setZValue(z_val)

        # Position
        pp = [float(c.strip()) for c in data.get("pos", "0,0,0").split(",")]
        px = pp[0] if len(pp) > 0 else 0.0
        pz = pp[2] if len(pp) > 2 else (pp[1] if len(pp) > 1 else 0.0)
        self.setPos(px * scale, pz * scale)
        self._scale = scale

        # Label
        self.label = QGraphicsTextItem(self.nickname, self)
        self.label.setDefaultTextColor(QColor(220, 220, 230))
        self.label.setFont(QFont("Sans", font_size))
        self.label.setPos(radius + 2, -5)
        if "hazard_buoy" in arch:
            self._label_default_visible = False
        if "trade_lane_ring" in arch:
            self._label_default_visible = False
        self.label.setVisible(self._label_default_visible)
        self.label.setAcceptedMouseButtons(Qt.NoButton)

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    # ------------------------------------------------------------------
    #  Freelancer-Position  (aktuell auf dem Canvas)
    # ------------------------------------------------------------------
    def fl_pos_str(self) -> str:
        """Gibt die aktuelle Position als FL-Positionsstring zurück.

        Die X/Z-Koordinaten stammen aus der 2D-Szenenposition, die
        Y-Koordinate (Höhe) wird aus den gespeicherten Daten übernommen,
        damit sie beim Speichern nicht verloren geht.
        """
        # Y (Höhe) aus den aktuellen Objektdaten lesen
        cur_y = 0.0
        raw = self.data.get("pos", "0,0,0")
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) >= 2:
            try:
                cur_y = float(parts[1])
            except ValueError:
                pass
        return (
            f"{self.pos().x() / self._scale:.2f}, "
            f"{cur_y:.2f}, "
            f"{self.pos().y() / self._scale:.2f}"
        )

    # ------------------------------------------------------------------
    #  Daten-Serialisierung
    # ------------------------------------------------------------------
    def raw_text(self) -> str:
        return "\n".join(f"{k} = {v}" for k, v in self.data.get("_entries", []))

    def apply_text(self, text: str):
        new_entries: list[tuple[str, str]] = []
        for line in text.splitlines():
            line = line.strip()
            if "=" in line:
                k, _, v = line.partition("=")
                new_entries.append((k.strip(), v.strip()))
        self.data.clear()
        self.data["_entries"] = new_entries
        for k, v in new_entries:
            if k.lower() not in self.data:
                self.data[k.lower()] = v
        self.nickname = self.data.get("nickname", self.nickname)
        if self.label:
            self.label.setPlainText(self.nickname)

    def set_label_visibility(self, enabled: bool):
        if self.label:
            self.label.setVisible(bool(enabled) and self._label_default_visible)

    # ------------------------------------------------------------------
    #  Events  (Positionsänderung → Callback)
    # ------------------------------------------------------------------
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self._pos_change_cb:
            self._pos_change_cb(self)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_scene_pos = QPointF(self.pos())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        start_pos = self._drag_start_scene_pos
        self._drag_start_scene_pos = None
        if event.button() == Qt.LeftButton and start_pos is not None:
            end_pos = QPointF(self.pos())
            moved = abs(end_pos.x() - start_pos.x()) > 1e-4 or abs(end_pos.y() - start_pos.y()) > 1e-4
            if moved and self._drag_finished_cb:
                self._drag_finished_cb(self, start_pos, end_pos)
        super().mouseReleaseEvent(event)


# ══════════════════════════════════════════════════════════════════════
#  Universumsmarker  (System auf der Übersichtskarte)
# ══════════════════════════════════════════════════════════════════════

class UniverseSystem(SolarObject):
    """Marker für ein System in der Universumsübersicht.

    Zeichnet einen leuchtenden Punkt mit Halo-Effekt und gut lesbarem
    Label.  Beim Doppelklick wird das zugehörige System geladen.
    """

    _UNI_RADIUS = 6.0        # Kern-Radius (deutlich größer als vorher)
    _UNI_HALO   = 14.0       # Äußerer Glow-Radius

    def __init__(self, nickname: str, path: str, pos: tuple, scale: float):
        data = {"nickname": nickname, "pos": f"{pos[0]},0,{pos[1]}", "archetype": ""}
        super().__init__(data, scale)
        self.sys_path = path
        self._highlighted = False

        r = self._UNI_RADIUS
        self.setRect(-r, -r, r * 2, r * 2)

        # Leuchtender Gradient-Brush  (Kern weiß → Rand transparent Cyan)
        self._apply_brush()
        self.setPen(QPen(Qt.NoPen))
        self.setZValue(5)

        # Label aufhübschen
        if self.label:
            self.label.setDefaultTextColor(QColor(200, 220, 255))
            self.label.setFont(QFont("Sans", 7, QFont.Bold))
            self.label.setPos(r + 3, -8)

    def _apply_brush(self):
        """Gradient-Brush je nach Highlight-Zustand setzen."""
        r = self._UNI_RADIUS
        grad = QRadialGradient(0, 0, r)
        if self._highlighted:
            grad.setColorAt(0.0, QColor(255, 220, 220, 255))
            grad.setColorAt(0.55, QColor(255, 60, 60, 200))
            grad.setColorAt(1.0, QColor(220, 30, 30, 0))
        else:
            grad.setColorAt(0.0, QColor(220, 240, 255, 255))
            grad.setColorAt(0.55, QColor(100, 180, 255, 180))
            grad.setColorAt(1.0, QColor(60, 120, 220, 0))
        self.setBrush(QBrush(grad))

    def set_highlighted(self, on: bool):
        """Rot hervorheben wenn ausgewählt."""
        if self._highlighted == on:
            return
        self._highlighted = on
        self._apply_brush()
        self.update()

    # Halo als größerer, halb-transparenter Ring hinter dem Kern.
    def paint(self, painter: QPainter, option, widget=None):
        # Äußerer Halo
        h = self._UNI_HALO
        halo_grad = QRadialGradient(0, 0, h)
        if self._highlighted:
            halo_grad.setColorAt(0.0, QColor(255, 80, 80, 80))
            halo_grad.setColorAt(0.6, QColor(220, 40, 40, 35))
            halo_grad.setColorAt(1.0, QColor(180, 20, 20, 0))
        else:
            halo_grad.setColorAt(0.0, QColor(100, 160, 255, 60))
            halo_grad.setColorAt(0.6, QColor(60, 120, 220, 25))
            halo_grad.setColorAt(1.0, QColor(40, 80, 180, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(halo_grad))
        painter.drawEllipse(QRectF(-h, -h, h * 2, h * 2))
        # Kern
        super().paint(painter, option, widget)

    def boundingRect(self) -> QRectF:
        h = self._UNI_HALO + 2
        return QRectF(-h, -h, h * 2, h * 2)
        if self.label:
            self.label.setFont(QFont("Sans", 8))
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setZValue(2)
