#!/usr/bin/env python3
"""
Freelancer System Editor v4.1
- Persistente Config (~/.config/fl_editor/config.json)
- Systemliste aus universe.ini
- Vollständig case-insensitive Pfadauflösung (Linux/Wine)
- Zonen-Rendering (SPHERE, ELLIPSOID, BOX, CYLINDER)
- Move-Modus per Checkbox
- Echtzeit pos-Update beim Verschieben
- Zweistufiger Save-Workflow (Memory → .tmp → Datei → Reload)
"""
import sys
import json
import shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsItem, QGraphicsPolygonItem,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QTextEdit, QLabel,
    QFileDialog, QSplitter, QGroupBox, QCheckBox, QMessageBox,
    QListWidget, QListWidgetItem, QLineEdit, QComboBox, QDialog,
    QDialogButtonBox, QFormLayout, QSpinBox
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QBrush, QColor, QPen, QFont, QPainter, QAction, QTransform, QPolygonF


CONFIG_PATH = Path.home() / ".config" / "fl_editor" / "config.json"


# ══════════════════════════════════════════════════════════════════════
#  Persistente Konfiguration
# ══════════════════════════════════════════════════════════════════════
class Config:
    def __init__(self):
        self._d: dict = {}
        if CONFIG_PATH.exists():
            try:
                self._d = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass

    def get(self, key: str, default=None):
        return self._d.get(key, default)

    def set(self, key: str, value):
        self._d[key] = value
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(self._d, indent=2, ensure_ascii=False),
            encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════
#  Case-insensitive Pfadauflösung  (Komponente für Komponente)
# ══════════════════════════════════════════════════════════════════════
def _ci_find(base: Path, name: str) -> Path | None:
    """Findet einen Eintrag in base unabhängig von Groß-/Kleinschreibung."""
    try:
        for entry in base.iterdir():
            if entry.name.lower() == name.lower():
                return entry
    except Exception:
        pass
    return None


def ci_resolve(base: Path, rel: str) -> Path | None:
    """
    Löst einen relativen Pfad (Backslash ODER Slash) von base aus
    vollständig case-insensitiv auf – Komponente für Komponente.

    Beispiel:
      base = /DATA/UNIVERSE/
      rel  = systems\\ST04\\ST04.ini
      →     /DATA/UNIVERSE/SYSTEMS/ST04/ST04.ini   (echter Pfad auf Disk)
    """
    parts   = rel.replace("\\", "/").split("/")
    current = base
    for part in parts:
        if not part:
            continue
        found = _ci_find(current, part)
        if found is None:
            return None
        current = found
    return current if current.is_file() else None


# ══════════════════════════════════════════════════════════════════════
#  System-Finder  (universe.ini → alle System-INIs)
# ══════════════════════════════════════════════════════════════════════
def find_universe_ini(game_path: str) -> Path | None:
    """
    Sucht universe.ini ab dem angegebenen Pfad – vollständig case-insensitiv.
    Unterstützte Strukturen:
      <path>/DATA/UNIVERSE/universe.ini   ← Standard
      <path>/UNIVERSE/universe.ini
      <path>/universe.ini
    """
    base = Path(game_path)
    if not base.exists():
        return None
    for components in [
        ["DATA", "UNIVERSE", "universe.ini"],
        ["UNIVERSE",         "universe.ini"],
        [                    "universe.ini"],
    ]:
        result = ci_resolve(base, "/".join(components))
        if result:
            return result
    return None


def find_all_systems(game_path: str, parser) -> list[dict]:
    """
    Liest universe.ini und gibt alle [system]-Einträge mit aufgelöstem
    absolutem Dateipfad zurück.
    Pfade in universe.ini sind relativ zu DATA/UNIVERSE/ angegeben,
    z. B.:  file = systems\\ST04\\ST04.ini
    Optional enthält jede Sektion ein `pos`-Feld (Navmap-Koordinaten).
    Diese werden als Tupel (x,y) zurückgegeben und dienen der
    Universumsübersicht.    """
    uni_ini = find_universe_ini(game_path)
    if not uni_ini:
        return []

    uni_dir  = uni_ini.parent   # …/DATA/UNIVERSE/
    data_dir = uni_dir.parent   # …/DATA/

    sections = parser.parse(str(uni_ini))
    systems  = []

    for sec_name, entries in sections:
        if sec_name.lower() != "system":
            continue
        d: dict = {}
        for k, v in entries:
            if k.lower() not in d:
                d[k.lower()] = v
        if "file" not in d:
            continue

        nickname = d.get("nickname", "???:?")
        file_rel = d["file"].strip()   # z. B.  systems\ST04\ST04.ini

        # navmap positionen aus universe.ini (x,y)
        pos = (0.0, 0.0)
        if "pos" in d:
            parts = [p.strip() for p in d["pos"].split(",")]
            try:
                x = float(parts[0]) if len(parts) >= 1 and parts[0] else 0.0
                y = float(parts[1]) if len(parts) >= 2 and parts[1] else 0.0
                pos = (x, y)
            except ValueError:
                pass

        sys_path = None
        for search_base in (uni_dir, data_dir):
            resolved = ci_resolve(search_base, file_rel)
            if resolved:
                sys_path = resolved
                break

        if sys_path:
            systems.append({"nickname": nickname, "path": str(sys_path), "pos": pos})

    return sorted(systems, key=lambda x: x["nickname"].lower())


# ══════════════════════════════════════════════════════════════════════
#  INI-Parser  (unterstützt doppelte Schlüssel – Freelancer-Eigenheit)
# ══════════════════════════════════════════════════════════════════════
class FLParser:
    def parse(self, filepath: str) -> list[tuple[str, list[tuple[str, str]]]]:
        sections, cur_name, cur_entries = [], None, []
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith(";") or line.startswith("//"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    if cur_name is not None:
                        sections.append((cur_name, cur_entries))
                    cur_name, cur_entries = line[1:-1].strip(), []
                elif "=" in line and cur_name is not None:
                    sem = line.find(";")
                    if sem > 0:
                        line = line[:sem].strip()
                    k, _, v = line.partition("=")
                    cur_entries.append((k.strip(), v.strip()))
        if cur_name is not None:
            sections.append((cur_name, cur_entries))
        return sections

    def _build(self, entries):
        d = {"_entries": list(entries)}
        for k, v in entries:
            if k.lower() not in d:
                d[k.lower()] = v
        return d

    def get_objects(self, sections):
        return [self._build(e) for n, e in sections if n.lower() == "object"]

    def get_zones(self, sections):
        return [self._build(e) for n, e in sections if n.lower() == "zone"]


# ══════════════════════════════════════════════════════════════════════
#  Linkes Panel: Datenpfad + Systemliste
# ══════════════════════════════════════════════════════════════════════
class SystemBrowser(QWidget):
    system_load_requested = Signal(str)
    path_updated = Signal(str)            # Neues Signal: Pfad wurde gespeichert/gescannt

    def __init__(self, config: Config, parser: FLParser):
        super().__init__()
        self._config = config
        self._parser = parser
        self._build_ui()
        saved = config.get("game_path", "")
        if saved:
            self.path_edit.setText(saved)
            self._scan()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        title = QLabel("⭐  System-Browser")
        title.setStyleSheet(
            "font-weight:bold; font-size:11pt; color:#99aaff; padding:4px 0;")
        layout.addWidget(title)

        # ── Pfad-Gruppe ──────────────────────────────────────────────
        g  = QGroupBox("Freelancer-Verzeichnis")
        gl = QVBoxLayout(g)
        gl.setSpacing(4)

        row = QWidget()
        rl  = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(3)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("/pfad/zu/Freelancer HD Edition/")
        self.path_edit.setToolTip(
            "Basis-Verzeichnis des Spiels.\n"
            "Erwartet: <pfad>/DATA/UNIVERSE/universe.ini")
        self.path_edit.returnPressed.connect(self._save_and_scan)
        rl.addWidget(self.path_edit)

        browse_btn = QPushButton("📁")
        browse_btn.setFixedWidth(32)
        browse_btn.setToolTip("Verzeichnis auswählen")
        browse_btn.clicked.connect(self._browse)
        rl.addWidget(browse_btn)
        gl.addWidget(row)

        scan_btn = QPushButton("🔍  Systeme einlesen")
        scan_btn.clicked.connect(self._save_and_scan)
        gl.addWidget(scan_btn)
        layout.addWidget(g)

        # ── Systemliste ──────────────────────────────────────────────
        list_lbl = QLabel("Systeme  (Klick zum Laden):")
        list_lbl.setStyleSheet("color:#aab; font-size:9pt;")
        layout.addWidget(list_lbl)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setToolTip("System anklicken um es zu laden")
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget, stretch=1)

        self.status_lbl = QLabel("")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("color:#888; font-size:9pt; padding:2px;")
        layout.addWidget(self.status_lbl)

    def _browse(self):
        start = self.path_edit.text() or str(Path.home())
        path  = QFileDialog.getExistingDirectory(
            self, "Freelancer-Verzeichnis wählen", start)
        if path:
            self.path_edit.setText(path)
            self._save_and_scan()

    def _save_and_scan(self):
        path = self.path_edit.text().strip()
        if path:
            self._config.set("game_path", path)
            self.path_updated.emit(path)
        self._scan()

    def _scan(self):
        path = self.path_edit.text().strip()
        if not path:
            self.status_lbl.setText("⚠  Kein Pfad angegeben.")
            return

        self.status_lbl.setText("Suche …")
        QApplication.processEvents()

        uni_ini = find_universe_ini(path)
        if not uni_ini:
            self.status_lbl.setText(
                "⚠  universe.ini nicht gefunden.\n"
                "Erwartet: <pfad>/DATA/UNIVERSE/universe.ini")
            self.list_widget.clear()
            return

        systems = find_all_systems(path, self._parser)
        self.list_widget.clear()

        for s in systems:
            item = QListWidgetItem(s["nickname"])
            item.setData(Qt.UserRole, s["path"])
            item.setToolTip(s["path"])
            self.list_widget.addItem(item)

        if systems:
            self.status_lbl.setText(
                f"✔  {len(systems)} Systeme\n{uni_ini}")
        else:
            self.status_lbl.setText(
                "⚠  universe.ini gefunden,\naber keine gültigen [system]-Pfade.")

    def _on_item_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path:
            self.system_load_requested.emit(path)

    def highlight_current(self, filepath: str):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            is_cur = item.data(Qt.UserRole) == filepath
            item.setBackground(QColor(40, 60, 100) if is_cur else QColor(0, 0, 0, 0))
            f = item.font()
            f.setBold(is_cur)
            item.setFont(f)


# ══════════════════════════════════════════════════════════════════════
#  Zone-Item  (NUR visuell – akzeptiert KEINE Maus-Events)
# ══════════════════════════════════════════════════════════════════════
class ZoneItem(QGraphicsItem):
    def __init__(self, data: dict, scale: float):
        super().__init__()
        self.data     = data
        self.nickname = data.get("nickname", "")
        self.shape_t  = data.get("shape", "SPHERE").upper()

        sp = [float(s.strip()) for s in data.get("size", "1000").split(",")]
        s0 = sp[0] if len(sp) > 0 else 1000.0
        s1 = sp[1] if len(sp) > 1 else s0
        s2 = sp[2] if len(sp) > 2 else s0

        if   self.shape_t == "SPHERE":    self.hw, self.hd = s0*scale,     s0*scale
        elif self.shape_t == "ELLIPSOID": self.hw, self.hd = s0*scale,     s2*scale
        elif self.shape_t == "BOX":       self.hw, self.hd = s0*scale/2,   s2*scale/2
        elif self.shape_t == "CYLINDER":  self.hw, self.hd = s0*scale,     s1*scale/2
        else:                             self.hw, self.hd = s0*scale,     s0*scale

        pp = [float(c.strip()) for c in data.get("pos", "0,0,0").split(",")]
        px = pp[0] if len(pp) > 0 else 0.0
        pz = pp[2] if len(pp) > 2 else (pp[1] if len(pp) > 1 else 0.0)
        self.setPos(px * scale, pz * scale)

        rp = [float(r.strip()) for r in data.get("rotate", "0,0,0").split(",")]
        self.setRotation(rp[1] if len(rp) > 1 else 0.0)

        self._pen, self._brush = self._style()
        self._build_label()

        self.setZValue(-1)
        # allow left-click to trigger zone_clicked signal; no dragging/hovering
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable,    False)
        self.setAcceptHoverEvents(False)

    def _style(self):
        n, d = self.nickname.lower(), self.data
        if "death"     in n or "damage"   in d: return QPen(QColor(220, 50, 50,200),1.5), QBrush(QColor(220, 50, 50, 20))
        if "nebula"    in n or "badlands" in n:  return QPen(QColor(150, 80,220,180),1),   QBrush(QColor(120, 60,200, 18))
        if "debris"    in n or "asteroid" in n:  return QPen(QColor(180,130, 60,180),1),   QBrush(QColor(160,120, 50, 18))
        if "tradelane" in n:                     return QPen(QColor( 60,180,220,160),1,Qt.DashLine), QBrush(QColor(60,180,220,12))
        if "jumpgate"  in n or "hole"     in n:  return QPen(QColor(180,100,220,200),1.5), QBrush(QColor(160, 80,200, 18))
        if "exclusion" in n:                     return QPen(QColor(220,100, 50,140),1,Qt.DotLine),  QBrush(QColor(200, 80, 40,  8))
        if "path"      in n or "vignette" in n:  return QPen(QColor(100,100,150, 70),1,Qt.DotLine),  QBrush(Qt.NoBrush)
        return QPen(QColor(80,160,200,150),1), QBrush(QColor(60,140,180,14))

    def _build_label(self):
        n = self.nickname.lower()
        skip = any(x in n for x in ("path","vignette","exclusion","death",
                                     "tradelane","laneaccess","destroyvignette",
                                     "sundeath","radiation"))
        if skip or self.hw < 8:
            return
        lbl = QGraphicsTextItem(self.nickname, self)
        lbl.setDefaultTextColor(QColor(160,160,190))
        lbl.setFont(QFont("Sans", 6))
        lbl.setPos(4, 4)
        lbl.setAcceptedMouseButtons(Qt.NoButton)

    def boundingRect(self):
        return QRectF(-self.hw-2, -self.hd-2, self.hw*2+4, self.hd*2+4)

    def paint(self, painter, option, widget=None):
        painter.setPen(self._pen)
        painter.setBrush(self._brush)
        r = QRectF(-self.hw, -self.hd, self.hw*2, self.hd*2)
        painter.drawRect(r) if self.shape_t in ("BOX","CYLINDER") else painter.drawEllipse(r)

    def raw_text(self) -> str:
        """Return entries as text for editing."""
        return "\n".join(f"{k} = {v}" for k, v in self.data.get("_entries", []))

    def apply_text(self, text: str):
        """Apply edited INI-style text back to this zone's data."""
        new_entries = []
        for line in text.splitlines():
            line = line.strip()
            if "=" in line:
                k, _, v = line.partition("=")
                new_entries.append((k.strip(), v.strip()))
        # update internal data structure
        self.data.clear()
        self.data["_entries"] = new_entries
        for k, v in new_entries:
            if k.lower() not in self.data:
                self.data[k.lower()] = v
        # update nickname and rebuild label
        self.nickname = self.data.get("nickname", self.nickname)
        # remove existing text children (labels) and rebuild
        try:
            for child in list(self.childItems()):
                if isinstance(child, QGraphicsTextItem):
                    child.setParentItem(None)
                    if child.scene():
                        child.scene().removeItem(child)
        except Exception:
            pass
        self._build_label()
        self.update()


# ══════════════════════════════════════════════════════════════════════
#  Solar-Objekt
# ══════════════════════════════════════════════════════════════════════
class SolarObject(QGraphicsEllipseItem):
    BASE_R = 8

    def __init__(self, data: dict, scale: float):
        r = self.BASE_R
        super().__init__(-r, -r, 2*r, 2*r)
        self.data           = data
        self.scale          = scale
        self._pos_change_cb = None

        # pos = x, y_hoch, z  →  Szene: x=x, y=z
        pp  = [float(c.strip()) for c in data.get("pos","0,0,0").split(",")]
        fx  = pp[0] if len(pp)>0 else 0.0
        fz  = pp[2] if len(pp)>2 else (pp[1] if len(pp)>1 else 0.0)
        self.setPos(fx*scale, fz*scale)

        self.nickname = data.get("nickname","???")
        arch = data.get("archetype","").lower()

        # Trade lane ring hat spezielles Aussehen: kleiner blauer Punkt ohne Label
        if "trade_lane_ring" in arch:
            color = QColor(60,130,220)
            r = 4
            self.setRect(-r, -r, 2*r, 2*r)
            self._brush_n = QBrush(color)
            self._brush_h = QBrush(color.lighter(160))
            self.setBrush(self._brush_n)
            self.setPen(QPen(QColor(255,255,255,70), 1))
            self.label = None
            self.setFlag(QGraphicsItem.ItemIsSelectable, False)
            self.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.setAcceptHoverEvents(False)
            self.setZValue(1)
            return
        # Hazard-Buoy: gelbes Dreieck, keine Beschriftung
        if "hazard_buoy" in self.nickname.lower():
            self.setBrush(Qt.NoBrush)
            self.setPen(Qt.NoPen)
            self.label = None
            self.setFlag(QGraphicsItem.ItemIsSelectable, False)
            self.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.setAcceptHoverEvents(False)
            pts = QPolygonF([QPointF(0,-r), QPointF(r,r), QPointF(-r,r)])
            tri = QGraphicsPolygonItem(pts, self)
            tri.setBrush(QBrush(QColor(255,255,0)))
            tri.setPen(QPen(QColor(0,0,0)))
            tri.setZValue(1)
            return

        if any(x in arch for x in ("sun","star")):
            color = QColor(255,215,40); r=14; self.setRect(-r,-r,2*r,2*r)
        elif "planet"  in arch:                           color = QColor( 60,130,220)
        elif any(x in arch for x in ("base","station")):  color = QColor( 80,210,100)
        elif any(x in arch for x in ("jump","gate")):     color = QColor(210, 90,210)
        elif any(x in arch for x in ("asteroid","field","debris")): color = QColor(150,110,70)
        else:                                             color = QColor(190,190,190)

        self._brush_n = QBrush(color)
        self._brush_h = QBrush(color.lighter(160))
        self.setBrush(self._brush_n)
        self.setPen(QPen(QColor(255,255,255,70), 1))

        if "tradelane" not in self.nickname.lower():
            self.label = QGraphicsTextItem(self.nickname, self)
            self.label.setDefaultTextColor(QColor(220,220,220))
            self.label.setFont(QFont("Sans",7))
            self.label.setPos(self.BASE_R+3, -self.BASE_R)
            self.label.setAcceptedMouseButtons(Qt.NoButton)
        else:
            self.label = None

        self.setFlag(QGraphicsItem.ItemIsMovable,            False)
        self.setFlag(QGraphicsItem.ItemIsSelectable,         True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

    def hoverEnterEvent(self, e): self.setBrush(self._brush_h); super().hoverEnterEvent(e)
    def hoverLeaveEvent(self, e): self.setBrush(self._brush_n); super().hoverLeaveEvent(e)

    def itemChange(self, change, value):
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
                and self._pos_change_cb):
            self._pos_change_cb(self)
        return super().itemChange(change, value)

    def fl_pos_str(self) -> str:
        sp   = self.pos()
        orig = [p.strip() for p in self.data.get("pos","0,0,0").split(",")]
        fy   = orig[1] if len(orig)>1 else "0"
        return f"{sp.x()/self.scale:.2f}, {fy}, {sp.y()/self.scale:.2f}"

    def raw_text(self) -> str:
        return "\n".join(f"{k} = {v}" for k,v in self.data["_entries"])

    def apply_text(self, text: str):
        new_entries = []
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


class UniverseSystem(SolarObject):
    """Kleiner Marker für ein System im Universum. Beim Doppelklick
    wird das zugehörige INI-System geladen (sys_path).
    """
    def __init__(self, nickname: str, path: str, pos: tuple, scale: float):
        # `SolarObject` versteht datums mit einer `pos`-Zeichenkette
        data = {"nickname": nickname, "pos": f"{pos[0]},0,{pos[1]}", "archetype": ""}
        super().__init__(data, scale)
        self.sys_path = path
        # weiße Markierung und etwas größere Beschriftung
        self.setBrush(QBrush(QColor(255,255,255)))
        self.setPen(QPen(QColor(255,255,255,200), 1))
        if self.label:
            self.label.setFont(QFont("Sans", 8))
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setZValue(2)
# ══════════════════════════════════════════════════════════════════════
#  System-View  (Zoom + Pan)
# ══════════════════════════════════════════════════════════════════════
class SystemView(QGraphicsView):
    object_selected = Signal(object)
    background_clicked = Signal(QPointF)
    zone_clicked = Signal(object)  # emitted when a zone is clicked
    system_double_clicked = Signal(str)  # Pfad des Systems bei Doppelklick

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(QColor(6,6,20)))
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self._panning   = False
        self._pan_start = QPointF()

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y()>0 else 1/1.15
        self.scale(f, f)

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._panning, self._pan_start = True, e.position()
            self.setCursor(Qt.ClosedHandCursor); return
        if e.button() == Qt.LeftButton:
            item = self.itemAt(e.pos())
            if isinstance(item, QGraphicsTextItem):
                item = item.parentItem()
            if isinstance(item, ZoneItem):
                self.zone_clicked.emit(item)
            elif isinstance(item, SolarObject):
                self.object_selected.emit(item)
            else:
                # click on empty space
                self.background_clicked.emit(self.mapToScene(e.pos()))
        super().mousePressEvent(e)   # Muss aufgerufen werden für ItemIsMovable

    def mouseMoveEvent(self, e):
        if self._panning:
            d = e.position() - self._pan_start; self._pan_start = e.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-int(d.x()))
            self.verticalScrollBar().setValue(  self.verticalScrollBar().value()  -int(d.y()))
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._panning = False; self.setCursor(Qt.ArrowCursor); return
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        # Öffne System, falls ein Marker auf der Universumsübersicht getroffen wird
        if e.button() == Qt.LeftButton:
            item = self.itemAt(e.pos())
            if isinstance(item, QGraphicsTextItem):
                item = item.parentItem()
            # Marker haben ein `sys_path`-Attribut
            if item and hasattr(item, "sys_path"):
                self.system_double_clicked.emit(item.sys_path)
                return
        super().mouseDoubleClickEvent(e)


# ══════════════════════════════════════════════════════════════════════
#  Hauptfenster
# ══════════════════════════════════════════════════════════════════════

# Dialog zum Auswählen des Zielsystems und des Typs
class ConnectionDialog(QDialog):
    def __init__(self, parent, systems: list[tuple[str,str]]):
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

# Dialog für zusätzliche Gate-Parameter
class GateInfoDialog(QDialog):
    def __init__(self, parent, loadouts, factions):
        super().__init__(parent)
        self.setWindowTitle("Gate-Parameter")
        layout = QFormLayout(self)
        # behaviour and difficulty
        self.behavior_edit = QLineEdit("NOTHING")
        layout.addRow("behavior:", self.behavior_edit)
        self.difficulty_spin = QSpinBox()
        self.difficulty_spin.setRange(0, 10)
        self.difficulty_spin.setValue(1)
        layout.addRow("difficulty:", self.difficulty_spin)
        # loadout combo
        self.loadout_cb = QComboBox()
        self.loadout_cb.addItems(loadouts)
        layout.addRow("loadout:", self.loadout_cb)
        # pilot
        self.pilot_edit = QLineEdit("pilot_solar_hardest")
        layout.addRow("pilot:", self.pilot_edit)
        # reputation (faction)
        self.rep_cb = QComboBox()
        self.rep_cb.setEditable(True)
        self.rep_cb.addItems(factions)
        layout.addRow("reputation:", self.rep_cb)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

# Dialog für Zone-Erstellung
class ZoneCreationDialog(QDialog):
    def __init__(self, parent, asteroids: list, nebulas: list):
        super().__init__(parent)
        self.setWindowTitle("Zone erstellen")
        self.setMinimumWidth(500)
        layout = QFormLayout(self)
        # Type selector
        self.type_cb = QComboBox()
        self.type_cb.addItems(["Asteroid Field", "Nebula"])
        layout.addRow("Typ:", self.type_cb)
        # Name input
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("z.B. Zone_ST04_field_01")
        layout.addRow("Zonenname:", self.name_edit)
        # Reference file selector
        self.ref_cb = QComboBox()
        self.type_cb.currentTextChanged.connect(self._on_type_changed)
        self._ast_list = asteroids
        self._neb_list = nebulas
        self._on_type_changed("Asteroid Field")
        layout.addRow("Referenzdatei:", self.ref_cb)
        # dialog buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _on_type_changed(self, typ):
        self.ref_cb.clear()
        if typ == "Asteroid Field":
            self.ref_cb.addItems(self._ast_list)
        else:
            self.ref_cb.addItems(self._neb_list)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Freelancer System Editor")
        self.resize(1600, 900)
        self._cfg      = Config()
        self._parser   = FLParser()
        self._sections : list[tuple[str,list]] = []
        self._objects  : list[SolarObject]     = []
        self._zones    : list[ZoneItem]        = []
        self._selected : SolarObject | None    = None
        self._scale    = 1.0
        self._filepath : str | None            = None
        self._dirty    = False
        self._ed_busy  = False
        self._pending_conn = None   # state for connection tool
        self._pending_snapshots : list[tuple[str, list, list]] = []
        self._pending_zone = None   # state for zone creation
        self._build_ui()

    # ── UI aufbauen ───────────────────────────────────────────────────
    def _build_ui(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        for lbl, key, slot in [
            ("📂 INI öffnen", "Ctrl+O", self._open_manual),
            ("🌐 Universum",  "Ctrl+U", self._load_universe_action),
            ("🔍 Alles",      "Ctrl+F", self._fit),
        ]:
            a = QAction(lbl, self); a.setShortcut(key); a.triggered.connect(slot)
            tb.addAction(a)

        tb.addSeparator()

        self.move_cb = QCheckBox("✋  Move-Modus")
        self.move_cb.setToolTip("Objekte per Maus verschieben (Linksklick + Ziehen)")
        self.move_cb.toggled.connect(self._toggle_move)
        tb.addWidget(self.move_cb)

        tb.addSeparator()

        self.zone_cb = QCheckBox("🗺  Zonen")
        self.zone_cb.setChecked(True)
        self.zone_cb.toggled.connect(self._toggle_zones)
        tb.addWidget(self.zone_cb)

        # ── Drei-Spalten-Splitter ─────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)

        # 1. Links: System-Browser
        self.browser = SystemBrowser(self._cfg, self._parser)
        self.browser.system_load_requested.connect(self._load_from_browser)
        # when the game path changes we can refresh the dropdown lists too
        self.browser.path_updated.connect(self._populate_quick_editor_options)
        self.browser.path_updated.connect(self._load_universe)
        splitter.addWidget(self.browser)


        # 2. Mitte: Kartenansicht
        self.view = SystemView()
        self.view.object_selected.connect(self._select)
        self.view.zone_clicked.connect(self._select_zone)
        self.view.background_clicked.connect(self._on_background_click)
        self.view.system_double_clicked.connect(self._load_from_browser)
        splitter.addWidget(self.view)

        # 3. Rechts: Objekt-Editor + Schnell-Editor
        right = QWidget()
        self.right_panel = right
        rl    = QVBoxLayout(right)
        rl.setContentsMargins(6,6,6,6)

        self.name_lbl = QLabel("Kein Objekt ausgewählt")
        self.name_lbl.setStyleSheet("font-weight:bold; font-size:12pt;")
        rl.addWidget(self.name_lbl)

        # ── Dropdown zur Auswahl von Objekten und Zonen ──────────────────
        self.obj_combo = QComboBox()
        self.obj_combo.setToolTip("Alle Objekte und Zonen – wählen Sie aus, um zu bearbeiten")
        self.obj_combo.currentIndexChanged.connect(self._on_obj_combo_changed)
        rl.addWidget(self.obj_combo)

        # ── Schnellzugriff für häufige Werte ─────────────────────────────
        quick = QGroupBox("Schnell-Editor")
        ql = QVBoxLayout(quick)
        ql.setSpacing(4)

        # Archetype
        row = QWidget(); rowl = QHBoxLayout(row); rowl.setContentsMargins(0,0,0,0)
        rowl.addWidget(QLabel("Archetype:"))
        self.arch_cb = QComboBox(); self.arch_cb.setEditable(True)
        self.arch_cb.setToolTip("Archetype ändern")
        self.arch_cb.currentTextChanged.connect(lambda t: self._update_editor_field("archetype", t))
        rowl.addWidget(self.arch_cb)
        ql.addWidget(row)

        # Loadout
        row = QWidget(); rowl = QHBoxLayout(row); rowl.setContentsMargins(0,0,0,0)
        rowl.addWidget(QLabel("Loadout:"))
        self.loadout_cb = QComboBox(); self.loadout_cb.setEditable(True)
        self.loadout_cb.setToolTip("Loadout ändern")
        self.loadout_cb.currentTextChanged.connect(lambda t: self._update_editor_field("loadout", t))
        rowl.addWidget(self.loadout_cb)
        ql.addWidget(row)

        # Reputation
        row = QWidget(); rowl = QHBoxLayout(row); rowl.setContentsMargins(0,0,0,0)
        rowl.addWidget(QLabel("Faction:"))
        self.faction_cb = QComboBox(); self.faction_cb.setEditable(True)
        self.faction_cb.setToolTip("Fraktionsfeld für Rep")
        self.faction_cb.currentTextChanged.connect(self._on_faction_changed)
        rowl.addWidget(self.faction_cb)
        rowl.addWidget(QLabel("Rep:"))
        self.rep_edit = QLineEdit()
        self.rep_edit.setMaximumWidth(60)
        self.rep_edit.setToolTip("Reputation-Wert")
        self.rep_edit.editingFinished.connect(self._on_rep_changed)
        rowl.addWidget(self.rep_edit)
        ql.addWidget(row)

        # Suche / neues Objekt
        row = QWidget(); rowl = QHBoxLayout(row); rowl.setContentsMargins(0,0,0,0)
        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText("Nickname suchen")
        self.search_edit.returnPressed.connect(self._search_nickname)
        rowl.addWidget(self.search_edit)
        self.new_obj_btn = QPushButton("➕ Neues Objekt")
        self.new_obj_btn.clicked.connect(self._create_new_object)
        rowl.addWidget(self.new_obj_btn)
        ql.addWidget(row)

        rl.addWidget(quick)

        g  = QGroupBox("INI-Eigenschaften")
        gl = QVBoxLayout(g)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Monospace",10))
        self.editor.setPlaceholderText("Klicke auf ein Objekt …")
        gl.addWidget(self.editor)

        self.apply_btn = QPushButton("✔  Objekt-Änderungen übernehmen")
        self.apply_btn.setToolTip("Texteditor → Objektdaten (nur im Speicher).")
        self.apply_btn.clicked.connect(self._apply)
        self.apply_btn.setEnabled(False)
        gl.addWidget(self.apply_btn)

        self.delete_btn = QPushButton("🗑  Objekt löschen")
        self.delete_btn.setToolTip("Das aktuell ausgewählte Objekt entfernen.")
        self.delete_btn.clicked.connect(self._delete_object)
        self.delete_btn.setEnabled(False)
        gl.addWidget(self.delete_btn)

        self.write_btn = QPushButton("💾  Änderungen in Datei schreiben")
        self.write_btn.setToolTip(
            "Alle Änderungen via .tmp-Datei in die Original-INI schreiben\n"
            "und Ansicht anschließend neu laden.")
        self.write_btn.setStyleSheet(
            "QPushButton{background:#1a3a1a;border:1px solid #2a5a2a;}"
            "QPushButton:hover{background:#245a24;}"
            "QPushButton:disabled{color:#445;background:#111;border-color:#333;}")
        self.write_btn.clicked.connect(self._write_to_file)
        self.write_btn.setEnabled(False)
        gl.addWidget(self.write_btn)
        rl.addWidget(g)
        # Bereich für Zusatzfunktionen unterhalb der INI-Eigenschaften
        btns = QWidget(); bl = QHBoxLayout(btns); bl.setContentsMargins(0,0,0,0); bl.setSpacing(4)
        self.create_conn_btn = QPushButton("Jump Hole / Gate erstellen")
        self.create_conn_btn.clicked.connect(self._start_connection_dialog)
        bl.addWidget(self.create_conn_btn)
        self.save_conn_btn = QPushButton("💾 Verbindungen speichern")
        self.save_conn_btn.setVisible(False)
        self.save_conn_btn.clicked.connect(self._save_pending_connections)
        bl.addWidget(self.save_conn_btn)
        self.create_zone_btn = QPushButton("📍 Zone erstellen")
        self.create_zone_btn.clicked.connect(self._start_zone_creation)
        bl.addWidget(self.create_zone_btn)
        # drei Platzhalter
        for _ in range(3):
            pb = QPushButton("…"); pb.setEnabled(False); bl.addWidget(pb)
        rl.addWidget(btns)

        # (die Legende wird nun unterhalb der Hauptansicht als einzelne
        # Zeile angezeigt – siehe weiter unten beim Erzeugen des Hauptlayout)
        # wir legen nur die Daten hier vor, das Widget wird später erzeugt
        self._legend_entries = [
            ("#ffd728","☀  Stern / Sonne"),   ("#3c82dc","🪐  Planet"),
            ("#50d264","🏠  Basis / Station"), ("#d25ad2","⭕  Jumpgate / -hole"),
            ("#966e46","☄  Asteroidenfeld"),   ("#bebebe","◉  Sonstiges"),
            ("#0000ff","─  Jumpgate-Verbindung"), ("#ffff00","─  Jumphole-Verbindung"),
            ("",""),
            ("#dc3232","─  Zone Death"),       ("#9650dc","─  Zone Nebula"),
            ("#b4823c","─  Zone Debris"),      ("#3cb4dc","--  Zone Tradelane"),
            ("#50a0c8","─  Zone Sonstiges"),
        ]
        # Platzhalter damit das rechte Panel weiterhin korrekt aufgebaut wird
        self.legend_box = None

        self.info_lbl = QLabel("Keine Datei geladen.")
        self.info_lbl.setWordWrap(True)
        rl.addWidget(self.info_lbl)
        rl.addStretch()
        splitter.addWidget(right)

        splitter.setSizes([220, 1060, 320])
        # stelle splitter plus Legende in einem vertikalen Container zusammen
        central = QWidget()
        cl = QVBoxLayout(central)
        cl.setContentsMargins(0,0,0,0)
        cl.addWidget(splitter)
        # erzeugen der Legendenzeile
        self.legend_box = QGroupBox("Legende")
        ll = QHBoxLayout(self.legend_box)
        ll.setSpacing(8)
        for col, txt in self._legend_entries:
            if not col:
                ll.addSpacing(12)
                continue
            lbl = QLabel(f'<span style="color:{col}">■</span> {txt}')
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet("font-size:8pt;")
            ll.addWidget(lbl)
        cl.addWidget(self.legend_box)
        # shrink legend vertically to content
        self.legend_box.setMaximumHeight(self.legend_box.sizeHint().height())
        self.setCentralWidget(central)
        self.statusBar().showMessage("Bereit — Pfad eingeben oder INI öffnen")

        # wenn ein Spielpfad in der Konfiguration hinterlegt ist, gleich
        # die Universumsübersicht laden
        saved = self._cfg.get("game_path", "")
        if saved:
            self._load_universe(saved)

        self.setStyleSheet("""
            * { background:#12122a; color:#dde; }
            QGroupBox { border:1px solid #334; margin-top:10px;
                        padding:5px; border-radius:4px; }
            QGroupBox::title { color:#99aaff; }
            QPushButton { background:#1e1e50; border:1px solid #446;
                          padding:4px 8px; border-radius:3px; }
            QPushButton:hover    { background:#2a2a70; }
            QPushButton:disabled { color:#445; }
            QTextEdit  { background:#08080f; border:1px solid #334; }
            QLineEdit  { background:#0d0d22; border:1px solid #446;
                         padding:3px; border-radius:2px; }
            QListWidget { background:#0a0a1e; border:1px solid #334;
                          alternate-background-color:#0d0d25; }
            QListWidget::item:hover    { background:#1e2050; }
            QListWidget::item:selected { background:#2a3070; color:#fff; }
            QToolBar   { background:#0e0e28; border-bottom:1px solid #334;
                         spacing:4px; padding:2px; }
            QStatusBar { background:#0e0e28; color:#99aaff; }
            QSplitter::handle { background:#224; width:3px; }
            QCheckBox  { color:#dde; spacing:5px; }
            QCheckBox::indicator { width:14px; height:14px;
                                   border:1px solid #556; border-radius:2px;
                                   background:#1e1e50; }
            QCheckBox::indicator:checked { background:#5060c0; }
            QScrollBar:vertical   { background:#0a0a1e; width:10px; }
            QScrollBar::handle:vertical { background:#334; border-radius:4px; }
        """)

    # ── Laden via Browser-Klick ────────────────────────────────────────
    def _load_from_browser(self, path: str):
        self._filepath = path
        # ensure dropdowns contain data for this game path before adding new object
        self._populate_quick_editor_options()
        self._load(path)
        self.browser.highlight_current(path)

    def _load_universe_action(self):
        """Handler für Toolbar-Knopf: Universumsübersicht laden."""
        path = self.browser.path_edit.text().strip()
        if path:
            self._load_universe(path)
        else:
            QMessageBox.warning(self, "Kein Pfad",
                                "Bitte zuerst Pfad eingeben und Systeme einlesen.")

    def _load_universe(self, game_path: str):
        """Zeigt alle Systeme als Punkte aus universe.ini an und zeichnet
        Verbindungen durch Sprunglöcher/-tore.
        """
        # make sure our dropdowns know about the current game path
        self._populate_quick_editor_options(game_path)
        uni_ini = find_universe_ini(game_path)
        if not uni_ini:
            QMessageBox.warning(self, "Fehler", "universe.ini nicht gefunden.")
            return

        systems = find_all_systems(game_path, self._parser)
        if not systems:
            QMessageBox.warning(self, "Fehler",
                                "Keine Systeme in universe.ini gefunden.")
            return

        # Maßstab anhand der Systemkoordinaten ermitteln
        coords = []
        for s in systems:
            x, y = s.get("pos", (0.0, 0.0))
            coords.append(abs(x)); coords.append(abs(y))
        self._scale = 500.0 / (max(coords, default=1) or 1)

        # Szene zurücksetzen
        self.view._scene.clear()
        self._objects = []
        self._zones = []
        self._selected = None
        self.apply_btn.setEnabled(False)
        self.write_btn.setEnabled(False)
        self.name_lbl.setText("Universumsübersicht")
        self.editor.clear()
        self._filepath = None

        coord_map = {}
        for s in systems:
            x, y = s.get("pos", (0.0, 0.0))
            # use uppercase nicknames for consistency with edge keys
            coord_map[s["nickname"].upper()] = (x * self._scale, y * self._scale)

        # Systeme als Marker hinzufügen
        for s in systems:
            sys_item = UniverseSystem(s["nickname"], s["path"], s.get("pos", (0.0, 0.0)), self._scale)
            self.view._scene.addItem(sys_item)
            self._objects.append(sys_item)

        # Verbindungen analysieren (Objekte mit jumpgate/jumphole)
        edges = {}
        import re
        for s in systems:
            src = s["nickname"]
            try:
                secs = self._parser.parse(s["path"])
            except Exception:
                continue
            objs = self._parser.get_objects(secs)
            for o in objs:
                arch = o.get("archetype", "").lower()
                # nur richtige Archetypen betrachten
                if "jumpgate" in arch or "nomad_gate" in arch:
                    typ = "gate"
                elif arch.startswith("jumphole"):
                    typ = "hole"
                else:
                    continue

                # Ziel aus goto ziehen, falls angegeben
                dest = None
                goto = o.get("goto", "")
                if goto:
                    dest = goto.split(",")[0].strip()
                if not dest:
                    # Fallback: aus nickname extrahieren
                    m = re.search(r"to_([A-Za-z0-9]+)", o.get("nickname", ""), re.IGNORECASE)
                    if m:
                        dest = m.group(1)
                if not dest or dest.upper() == src.upper():
                    continue

                key = frozenset({src.upper(), dest.upper()})
                existing = edges.get(key)
                if existing is None or (existing == "hole" and typ == "gate"):
                    edges[key] = typ

        # Linien zeichnen
        for key, typ in edges.items():
            a, b = list(key)
            if a not in coord_map or b not in coord_map:
                continue
            ax, ay = coord_map[a]
            bx, by = coord_map[b]
            col = QColor(0, 0, 255) if typ == "gate" else QColor(255, 255, 0)
            pen = QPen(col, 1.5)
            line = self.view._scene.addLine(ax, ay, bx, by, pen)
            line.setZValue(-2)

        self.info_lbl.setText(f"🌐 Universum: {len(systems)} Systeme")
        self.setWindowTitle("Freelancer System Editor — Universum")
        self.statusBar().showMessage(f"✔  Universum geladen: {len(systems)} Systeme")
        # rechte Spalte und Legende ausblenden
        if hasattr(self, 'right_panel'):
            self.right_panel.setVisible(False)
        if hasattr(self, 'legend_box'):
            self.legend_box.setVisible(False)
        self._fit()

    # ── Manuell öffnen ─────────────────────────────────────────────────
    def _open_manual(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Freelancer INI öffnen", "", "INI (*.ini);;Alle (*)")
        if path:
            self._filepath = path
            self._load(path)
            self.browser.highlight_current(path)

    # ── Datei einlesen und Szene aufbauen ──────────────────────────────
    def _load(self, path: str, restore: QTransform | None = None):
        # clear any in-progress connection when switching systems
        self._pending_conn = None
        # remember current file for save/new-object operations
        self._filepath = path
        self._sections = self._parser.parse(path)
        raw_objs  = self._parser.get_objects(self._sections)
        raw_zones = self._parser.get_zones(self._sections)

        coords = []
        # also compute radius to display system boundary
        rmax = 0.0
        for d in raw_objs + raw_zones:
            pp = [float(c.strip()) for c in d.get("pos","0,0,0").split(",")]
            if len(pp)>0: coords.append(abs(pp[0]))
            if len(pp)>2: coords.append(abs(pp[2]))
            # distance from origin
            fx = pp[0] if len(pp)>0 else 0.0
            fz = pp[2] if len(pp)>2 else (pp[1] if len(pp)>1 else 0.0)
            dist = (fx*fx + fz*fz)**0.5
            sz = 0.0
            if "size" in d:
                try:
                    sz = float(d["size"].split(",")[0])
                except Exception:
                    sz = 0.0
            rmax = max(rmax, dist + sz)
        self._scale = 500.0 / (max(coords, default=1) or 1)

        # if we computed a radius, draw a thin circle later once scene exists
        boundary_radius = rmax

        self.view._scene.clear()
        self._objects, self._zones = [], []
        self._selected = None
        self.apply_btn.setEnabled(False)
        self.name_lbl.setText("Kein Objekt ausgewählt")
        self.editor.clear()

        for zd in raw_zones:
            try:
                zi = ZoneItem(zd, self._scale)
                self.view._scene.addItem(zi)
                self._zones.append(zi)
            except Exception:
                pass

        move_on = self.move_cb.isChecked()
        for od in raw_objs:
            try:
                obj = SolarObject(od, self._scale)
                obj.setFlag(QGraphicsItem.ItemIsMovable, move_on)
                self.view._scene.addItem(obj)
                self._objects.append(obj)
            except Exception:
                pass

        # after placing everything, draw system boundary if computed
        if boundary_radius and boundary_radius > 0:
            pen = QPen(QColor(200,200,200,120))
            pen.setWidthF(0.5)
            r = boundary_radius * self._scale
            circ = QGraphicsEllipseItem(-r, -r, 2*r, 2*r)
            circ.setPen(pen)
            circ.setBrush(Qt.NoBrush)
            circ.setZValue(-1)
            self.view._scene.addItem(circ)

        if not self.zone_cb.isChecked():
            for z in self._zones:
                z.setVisible(False)

        name = Path(path).stem.upper()
        self.info_lbl.setText(
            f"📄 {Path(path).name}\n"
            f"Objekte: {len(self._objects)}\n"
            f"Zonen:   {len(self._zones)}")
        # rebuild the object/zone combobox
        self._rebuild_object_combo()
        self.setWindowTitle(f"Freelancer System Editor — {name}")
        self.statusBar().showMessage(
            f"✔  {name}: {len(self._objects)} Objekte · {len(self._zones)} Zonen")
        # rechte Spalte und Legende wieder einblenden
        if hasattr(self, 'right_panel'):
            self.right_panel.setVisible(True)
        if hasattr(self, 'legend_box'):
            self.legend_box.setVisible(True)
        self._set_dirty(False)

        if restore:
            self.view.setTransform(restore)
        else:
            self._fit()
        # after loading a system, make sure our quick-editor list values exist
        self._populate_quick_editor_options()

    # ── Objekt anklicken ────────────────────────────────────────────────
    def _select(self, obj: SolarObject):
        # wenn ein Universumsmarker angeklickt wird, nur Nachricht anzeigen
        if hasattr(obj, "sys_path"):
            self.statusBar().showMessage(f"System: {obj.nickname}")
            return

        if self._selected:
            self._selected._pos_change_cb = None
            # only change pen color if it's a SolarObject (has pen() method)
            if hasattr(self._selected, 'setPen') and hasattr(self._selected, 'pen'):
                p = self._selected.pen()
                p.setColor(QColor(255,255,255,70)); p.setWidth(1)
                self._selected.setPen(p)
        self._selected = obj
        # only highlight if it's a SolarObject
        if hasattr(obj, 'setPen') and hasattr(obj, 'pen'):
            p = obj.pen()
            p.setColor(QColor(255,200,0)); p.setWidth(2)
            obj.setPen(p)
            obj._pos_change_cb = self._on_obj_moved
        self.name_lbl.setText(f"📍 {obj.nickname}")
        self.editor.setPlainText(obj.raw_text())
        self.apply_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.statusBar().showMessage(f"Ausgewählt: {obj.nickname}")
        # sync combo to this object
        self._sync_obj_combo_to_selection()
        # fill quick-editor controls with current values
        self.arch_cb.setCurrentText(obj.data.get("archetype", ""))
        self.loadout_cb.setCurrentText(obj.data.get("loadout", ""))
        rep_val = obj.data.get("reputation", "")
        if rep_val:
            parts = [p.strip() for p in rep_val.split(",")]
            self.faction_cb.setCurrentText(parts[0] if parts else "")
            self.rep_edit.setText(parts[1] if len(parts) > 1 else "")
        else:
            self.faction_cb.setCurrentText("")
            self.rep_edit.clear()

    # ── Echtzeit pos-Update beim Verschieben ────────────────────────────
    def _on_obj_moved(self, obj: SolarObject):
        if self._ed_busy or obj is not self._selected:
            return
        new_pos = obj.fl_pos_str()
        updated = []
        for line in self.editor.toPlainText().splitlines():
            if line.partition("=")[0].strip().lower() == "pos":
                updated.append(f"pos = {new_pos}")
            else:
                updated.append(line)
        self._ed_busy = True
        cur = self.editor.textCursor().position()
        self.editor.setPlainText("\n".join(updated))
        tc = self.editor.textCursor()
        tc.setPosition(min(cur, len(self.editor.toPlainText())))
        self.editor.setTextCursor(tc)
        self._ed_busy = False
        self._set_dirty(True)

    # ── Helfer zum Füllen der Comboboxen ──────────────────────────────
    def _populate_quick_editor_options(self, game_path: str | None = None):
        """Lädt Fraktionen, Loadouts und Archetypen in die Dropdowns.

        Wenn *game_path* übergeben wird, wird dieser verwendet; sonst
        wird der aktuelle Pfad aus dem Browserfeld genommen.  Diese Methode
        wird beim Ändern des Pfads oder beim Laden eines Systems aufgerufen.
        """
        if game_path is None:
            game_path = self.browser.path_edit.text().strip()
        if not game_path:
            return

        base = Path(game_path)

        # --- Fraktionen aus initialworld.ini --------------------------------
        self.faction_cb.clear()
        iw_file = ci_resolve(base, "DATA/initialworld.ini")
        factions = []
        if iw_file and iw_file.exists():
            try:
                secs = self._parser.parse(str(iw_file))
                for name, entries in secs:
                    if name.lower() == "group":
                        for k, v in entries:
                            if k.lower() == "nickname" and v not in factions:
                                factions.append(v)
            except Exception:
                pass
        factions.sort(key=str.lower)
        self.faction_cb.addItems(factions)

        # --- Loadouts aus DATA/SOLAR/loadouts.ini -----------------------------
        self.loadout_cb.clear()
        ld_file = ci_resolve(base, "DATA/SOLAR/loadouts.ini")
        loadouts = []
        if ld_file and ld_file.exists():
            try:
                secs = self._parser.parse(str(ld_file))
                for name, entries in secs:
                    if name.lower() == "loadout":
                        for k, v in entries:
                            if k.lower() == "nickname" and v not in loadouts:
                                loadouts.append(v)
            except Exception:
                pass
        loadouts.sort(key=str.lower)
        self.loadout_cb.addItems(loadouts)

        # --- Archetypen aller Systeme (analyse universe.ini) ------------------
        self.arch_cb.clear()
        archs = set()
        try:
            systems = find_all_systems(game_path, self._parser)
            for s in systems:
                try:
                    secs = self._parser.parse(s["path"])
                except Exception:
                    continue
                objs = self._parser.get_objects(secs)
                for o in objs:
                    a = o.get("archetype", "")
                    if a:
                        archs.add(a)
        except Exception:
            pass
        for item in sorted(archs, key=str.lower):
            self.arch_cb.addItem(item)

    # ── Editor-Feld aktualisieren ───────────────────────────────────────
    def _update_editor_field(self, key: str, value: str):
        """Setzt, ändert oder entfernt eine Zeile `<key> = <value>` im Texteditor.

        Wenn *value* leer ist, wird der Eintrag komplett gelöscht (statt
        `key = ` als leere Zeile einzufügen)."""
        if not self._selected:
            return
        updated = []
        found = False
        lc_key = key.lower()
        for line in self.editor.toPlainText().splitlines():
            if line.partition("=")[0].strip().lower() == lc_key:
                if value.strip():
                    updated.append(f"{key} = {value}")
                # else: drop the line entirely
                found = True
            else:
                updated.append(line)
        if not found and value.strip():
            updated.append(f"{key} = {value}")
        self._ed_busy = True
        cur = self.editor.textCursor().position()
        self.editor.setPlainText("\n".join(updated))
        tc = self.editor.textCursor()
        tc.setPosition(min(cur, len(self.editor.toPlainText())))
        self.editor.setTextCursor(tc)
        self._ed_busy = False
        self._set_dirty(True)

    def _on_faction_changed(self, text: str):
        # wenn Fraktion ausgewählt wird, aktualisiere das reputation-Feld
        if not text:
            return
        rep_val = self.rep_edit.text().strip()
        if rep_val:
            self._update_editor_field("reputation", f"{text},{rep_val}")
        else:
            self._update_editor_field("reputation", text)

    def _on_rep_changed(self):
        if not self.faction_cb.currentText():
            return
        val = self.rep_edit.text().strip()
        if val:
            self._update_editor_field("reputation",
                                      f"{self.faction_cb.currentText()},{val}")
        else:
            # nur Fraktion ohne Wert
            self._update_editor_field("reputation", self.faction_cb.currentText())

    def _delete_object(self):
        if not self._selected:
            return
        obj = self._selected
        nick = obj.nickname.lower()
        arch = obj.data.get("archetype", "").lower()
        # check if this is a jumpgate or jumphole that has a counterpart
        is_gate = "jumpgate" in arch
        is_hole = "jumphole" in arch
        counterpart_nick = None
        counterpart_file = None
        if is_gate or is_hole:
            # Parse the 'goto' field to find the actual counterpart nickname.
            # Format may be: "ST04, ST04_to_FP7_SYSTEM_jumphole, gate_tunnel_bretonia"
            goto_val = obj.data.get("goto", "").strip()
            if goto_val:
                tokens = [t.strip() for t in goto_val.split(",") if t.strip()]
                if len(tokens) >= 2:
                    counterpart_sys = tokens[0]
                    counterpart_nick = tokens[1]
                    # try to find other system's file
                    try:
                        systems = find_all_systems(self.browser.path_edit.text().strip(), self._parser)
                        for sys in systems:
                            if sys.get("nickname", "").upper() == counterpart_sys.upper():
                                counterpart_file = sys.get("path")
                                break
                    except Exception:
                        pass
        # confirm deletion
        msg = f"Objekt '{obj.nickname}' wirklich löschen?"
        if counterpart_nick and counterpart_file:
            msg += f"\n\nDas Gegenstück '{counterpart_nick}'\nim anderen System wird automatisch gelöscht."
            ret = QMessageBox.warning(self, "Löschen bestätigen", msg,
                                       QMessageBox.Ok | QMessageBox.Cancel)
            if ret != QMessageBox.Ok:
                return
        elif counterpart_nick and not counterpart_file:
            # counterpart info present in goto but system file not found -> warn and require explicit confirmation
            err = (f"Gegenstück '{counterpart_nick}' wurde anhand des 'goto'-Feldes erkannt,\n"
                   f"die zugehörige Systemdatei ('{counterpart_sys}') wurde jedoch nicht in der Systemliste gefunden.\n\n"
                   "Soll trotzdem gelöscht werden?")
            ans = QMessageBox.question(self, "Gegenstück nicht gefunden", err,
                                       QMessageBox.Yes | QMessageBox.No)
            if ans != QMessageBox.Yes:
                return
        # remove from scene and objects list
        # determine object index so we can remove the corresponding [Object] section
        obj_idx = None
        try:
            obj_idx = self._objects.index(obj)
        except ValueError:
            obj_idx = None
        # remove corresponding section from self._sections (nth [Object])
        if obj_idx is not None:
            count = 0
            for i, (sec_name, entries) in enumerate(list(self._sections)):
                if sec_name.lower() == "object":
                    if count == obj_idx:
                        # remove this section
                        self._sections.pop(i)
                        break
                    count += 1
        # finally remove from scene and objects list
        self.view._scene.removeItem(obj)
        if obj in self._objects:
            self._objects.remove(obj)
        self._rebuild_object_combo()
        self._selected = None
        self.name_lbl.setText("Kein Objekt ausgewählt")
        self.editor.clear()
        self.apply_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self._set_dirty(True)
        # persist deletion immediately
        self._write_to_file(reload=False)
        # if there's a counterpart, delete it too
        if counterpart_nick and counterpart_file:
            try:
                self._delete_counterpart(counterpart_file, counterpart_nick)
            except Exception as ex:
                QMessageBox.warning(self, "Gegenpart-Löschung",
                                   f"Konnte Gegenstück nicht löschen:\n{ex}")
        self.statusBar().showMessage(f"✓  Objekt '{nick}' gelöscht")

    def _delete_counterpart(self, filepath: str, nick_to_delete: str):
        """Delete a counterpart object from another system file."""
        secs = self._parser.parse(filepath)
        objs = self._parser.get_objects(secs)
        # find the object with matching nickname
        obj_idx = -1
        for i, o in enumerate(objs):
            if o.get("nickname", "").lower() == nick_to_delete.lower():
                obj_idx = i
                break
        if obj_idx < 0:
            return  # object not found
        # find and remove the corresponding [Object] section
        obj_count = 0
        new_secs = []
        for sec_name, entries in secs:
            if sec_name.lower() == "object":
                if obj_count == obj_idx:
                    # skip this section
                    obj_count += 1
                    continue
                obj_count += 1
            new_secs.append((sec_name, entries))
        # write back
        lines = []
        for sec_name, entries in new_secs:
            lines.append(f"[{sec_name}]")
            for k, v in entries:
                lines.append(f"{k} = {v}")
            lines.append("")
        # overwrite the target INI directly so the counterpart removal takes effect immediately
        try:
            Path(filepath).write_text("\n".join(lines), encoding="utf-8")
        except Exception:
            # fallback: write tmp and try move
            tmp = str(filepath) + ".tmp"
            Path(tmp).write_text("\n".join(lines), encoding="utf-8")
            try:
                shutil.move(tmp, filepath)
            except Exception:
                pass
        shutil.move(tmp, filepath)

    def _select_zone(self, zone):
        """Called when a zone is clicked -- edit it."""
        # only allow zone selection if the zone editing checkbox is enabled
        if not self.zone_cb.isChecked():
            return
        self.name_lbl.setText(f"📍 {zone.nickname}")
        self.editor.setPlainText(zone.raw_text())
        self.apply_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.statusBar().showMessage(f"Zone ausgewählt: {zone.nickname}")
        self._selected = zone
        # sync combo to this zone
        self._sync_obj_combo_to_selection()

    def _rebuild_object_combo(self):
        """Regenerate the object/zone combobox from current _objects and _zones."""
        self.obj_combo.blockSignals(True)
        self.obj_combo.clear()
        for obj in self._objects:
            self.obj_combo.addItem(f"[OBJ] {obj.nickname}", obj)
        for zone in self._zones:
            self.obj_combo.addItem(f"[ZONE] {zone.nickname}", zone)
        if len(self._objects) == 0 and len(self._zones) == 0:
            self.obj_combo.addItem("(keine Objekte/Zonen)")
        self.obj_combo.blockSignals(False)

    def _sync_obj_combo_to_selection(self):
        """Set the combobox selection to the current _selected object/zone."""
        if not self._selected:
            self.obj_combo.setCurrentIndex(-1)
            return
        for i in range(self.obj_combo.count()):
            if self.obj_combo.itemData(i) is self._selected:
                self.obj_combo.blockSignals(True)
                self.obj_combo.setCurrentIndex(i)
                self.obj_combo.blockSignals(False)
                return
        self.obj_combo.setCurrentIndex(-1)

    def _on_obj_combo_changed(self, index):
        """Handle combobox selection change."""
        if index < 0:
            return
        item_data = self.obj_combo.itemData(index)
        if item_data is None:
            return
        # Determine if it's a SolarObject or ZoneItem and call appropriate handler
        if isinstance(item_data, self.view._scene.itemsBoundingRect().__class__.__bases__[0]):
            # Try to identify by class name
            if item_data.__class__.__name__ == "ZoneItem":
                self._select_zone(item_data)
            elif item_data.__class__.__name__ == "SolarObject":
                self._select(item_data)
        else:
            # Fallback: check if it has apply_text (SolarObject) or raw_text (ZoneItem)
            if hasattr(item_data, 'apply_text'):
                self._select(item_data)
            elif hasattr(item_data, 'raw_text'):
                self._select_zone(item_data)

    def _start_zone_creation(self):
        """Start workflow to create a new zone (asteroid field or nebula)."""
        if not self._filepath:
            QMessageBox.warning(self, "Kein System",
                                "Bitte zuerst ein System laden.")
            return
        # probe for available asteroids and nebulas
        game_path = self.browser.path_edit.text().strip()
        if not game_path:
            QMessageBox.warning(self, "Kein Spielpfad",
                                "Bitte zuerst Spielpfad konfigurieren.")
            return
        base = Path(game_path)
        # Look for DATA directory if game_path doesn't point to it
        if not (base / "solar").exists() and not (base / "SOLAR").exists():
            data_dir = _ci_find(base, "DATA")
            if data_dir and data_dir.is_dir():
                base = data_dir
        # use _ci_find to navigate to directories (case-insensitive)
        solar_dir = _ci_find(base, "solar")
        if not solar_dir or not solar_dir.is_dir():
            QMessageBox.warning(self, "Fehler", 
                               f"solar-Verzeichnis nicht gefunden in {base}")
            return
        ast_dir = _ci_find(solar_dir, "asteroids")
        neb_dir = _ci_find(solar_dir, "nebula")
        asteroids = []
        nebulas = []
        if ast_dir and ast_dir.is_dir():
            asteroids = sorted([f.name for f in ast_dir.glob("*.ini")])
        if neb_dir and neb_dir.is_dir():
            nebulas = sorted([f.name for f in neb_dir.glob("*.ini")])
        # present dialog to choose type and reference file
        dlg = ZoneCreationDialog(self, asteroids, nebulas)
        if dlg.exec() != QDialog.Accepted:
            return
        zone_type = dlg.type_cb.currentText()  # "Asteroid Field" or "Nebula"
        ref_file = dlg.ref_cb.currentText()
        zone_name = dlg.name_edit.text().strip()
        if not zone_name or not ref_file:
            QMessageBox.warning(self, "Unvollständig",
                                "Bitte Name und Referenzdatei angeben.")
            return
        # switch to zone click mode
        self.statusBar().showMessage(
            f"Klicke auf die Karte, um die neue Zone '{zone_name}' zu platzieren")
        self._pending_zone = {
            "type": zone_type,
            "ref_file": ref_file,
            "name": zone_name,
            "game_path": game_path
        }

    def _start_connection_dialog(self):
        """Start workflow to create a jump hole/gate connection."""
        # beginne den Workflow zum Erstellen einer Jump-Hole/Gate-Verbindung
        if not self._filepath:
            QMessageBox.warning(self, "Kein System",
                                "Bitte zuerst ein System laden.")
            return
        if self._pending_snapshots:
            QMessageBox.warning(self, "Offene Änderungen",
                                "Bitte vorhandene Verbindungen zuerst speichern.")
            return
        # erhalte Liste der Systeme aus dem Browser
        systems = []
        for i in range(self.browser.list_widget.count()):
            item = self.browser.list_widget.item(i)
            systems.append((item.text(), item.data(Qt.UserRole)))
        dlg = ConnectionDialog(self, systems)
        if dlg.exec() != QDialog.Accepted:
            return
        dest_path = dlg.dest_cb.currentData()
        typ = dlg.type_cb.currentText()
        origin = self._filepath
        if not origin:
            # sanity check, should never happen since we require a loaded system
            QMessageBox.warning(self, "Kein System",
                                "Bitte zuerst ein System laden.")
            return
        origin_nick = Path(origin).stem.upper()
        # if this is a gate we need additional parameters from the user
        gate_info: dict | None = None
        if typ == "Jump Gate":
            # collect available loadouts and factions
            loads = [self.loadout_cb.itemText(i)
                     for i in range(self.loadout_cb.count())
                     if "jumpgate" in self.loadout_cb.itemText(i).lower()]
            facts = [self.faction_cb.itemText(i)
                     for i in range(self.faction_cb.count())]
            gdlg = GateInfoDialog(self, loads, facts)
            if gdlg.exec() != QDialog.Accepted:
                return
            gate_info = {
                "behavior": gdlg.behavior_edit.text().strip(),
                "difficulty": gdlg.difficulty_spin.value(),
                "loadout": gdlg.loadout_cb.currentText().strip(),
                "pilot": gdlg.pilot_edit.text().strip(),
                "reputation": gdlg.rep_cb.currentText().strip(),
            }
        # we will first let the user place the connection in the current
        # (origin) system; after the click we automatically switch to the
        # destination and ask for the counterpart.
        self._pending_conn = {"origin": origin,
                              "origin_nick": origin_nick,
                              "type": typ,
                              "dest": dest_path,
                              "step": 1,
                              "gate_info": gate_info}
        self.statusBar().showMessage(
            "Klicke im aktuellen System, um das erste Verbindungsobjekt zu platzieren")

    def _on_background_click(self, pos: QPointF):
        # zone creation takes priority
        if self._pending_zone:
            self._create_zone_at_pos(pos)
            return
        if not self._pending_conn:
            return
        step = self._pending_conn.get("step", 1)
        orig = self._pending_conn["origin_nick"]
        typ = self._pending_conn["type"]
        arch = "jumpgate" if "Gate" in typ else "jumphole"
        # helper to turn current sections+objects into a lightweight snapshot
        def _snapshot():
            fp = self._filepath
            secs = [(n, list(e)) for n, e in self._sections]
            objs = []
            for o in self._objects:
                d = {k: v for k, v in o.data.items() if k != "_entries"}
                ents = list(o.data.get("_entries", []))
                d["_entries"] = ents
                objs.append(d)
            return (fp, secs, objs)
        # helper to create object (with optional extras) and return it
        def make_obj(nick, goto_val, extras=None):
            entries = [("nickname", nick),
                       ("pos", f"{pos.x()/self._scale:.2f}, 0, {pos.y()/self._scale:.2f}"),
                       ("archetype", arch),
                       ("goto", goto_val)]
            if extras:
                entries.extend(extras)
            data = {"_entries": entries}
            for k, v in entries:
                if k.lower() not in data:
                    data[k.lower()] = v
            obj = SolarObject(data, self._scale)
            obj.setFlag(QGraphicsItem.ItemIsMovable, self.move_cb.isChecked())
            self.view._scene.addItem(obj)
            self._objects.append(obj)
            self._select(obj)
            self._set_dirty(True)
            return obj
        if step == 1:
            # place the object in the origin system; goto points to destination
            destnick = Path(self._pending_conn["dest"]).stem.upper()
            nick = f"{orig}_to_{destnick}_{arch}"
            goto_str = f"{destnick}, {destnick}_to_{orig}_{arch}, gate_tunnel_bretonia"
            # extras depending on type
            extras = [("rotate", "0,0,0"),
                      ("ids_name", "0"),
                      ("ids_info", "66145" if arch=="jumpgate" else "66146"),
                      ("msg_id_prefix", f"gcs_refer_system_{destnick}")]
            if arch == "jumpgate":
                info = self._pending_conn.get("gate_info", {}) or {}
                extras += [("behavior", info.get("behavior", "NOTHING")),
                           ("difficulty_level", str(info.get("difficulty", 1))),
                           ("loadout", info.get("loadout", "")),
                           ("pilot", info.get("pilot", "pilot_solar_hardest")),
                           ("reputation", info.get("reputation", ""))]
            make_obj(nick, goto_str, extras)
            # remember snapshot of origin (including new object)
            self._pending_snapshots.append(_snapshot())
            # prepare for second step and remember destination path
            dest_path = self._pending_conn["dest"]
            self._pending_conn["step"] = 2
            # load target system; _load clears pending_conn, so stash and
            # restore afterwards
            pending = self._pending_conn
            self._load(dest_path)
            self._pending_conn = pending
            self.browser.highlight_current(dest_path)
            self.statusBar().showMessage(
                "Origin platziert – klicke im Zielsystem, um Gegenstück zu setzen")
        else:
            # second click: create counterpart in dest system
            destnick = Path(self._filepath).stem.upper()
            nick = f"{destnick}_to_{orig}_{arch}"
            goto_str = f"{orig}, {orig}_to_{destnick}_{arch}, gate_tunnel_bretonia"
            extras = [("rotate", "0,0,0"),
                      ("ids_name", "0"),
                      ("ids_info", "66145" if arch=="jumpgate" else "66146"),
                      ("msg_id_prefix", f"gcs_refer_system_{orig}")]
            if arch == "jumpgate":
                info = self._pending_conn.get("gate_info", {}) or {}
                extras += [("behavior", info.get("behavior", "NOTHING")),
                           ("difficulty_level", str(info.get("difficulty", 1))),
                           ("loadout", info.get("loadout", "")),
                           ("pilot", info.get("pilot", "pilot_solar_hardest")),
                           ("reputation", info.get("reputation", ""))]
            make_obj(nick, goto_str, extras)
            # remember snapshot of destination (including new object)
            self._pending_snapshots.append(_snapshot())
            # after second object, show save button and clear pending state
            self.save_conn_btn.setVisible(True)
            self.create_conn_btn.setEnabled(False)
            self._pending_conn = None
            self.statusBar().showMessage("Ziel erstellt – bitte Verbindungen speichern")

    def _create_zone_at_pos(self, pos: QPointF):
        """Create a zone at the clicked position."""
        if not self._pending_zone:
            return
        pz = self._pending_zone
        zone_type = pz["type"]  # "Asteroid Field" or "Nebula"
        ref_file = pz["ref_file"]
        zone_name = pz["name"]
        game_path = pz["game_path"]
        
        # determine source directory and section names
        if zone_type == "Asteroid Field":
            src_dir_name = "solar\\asteroids"
            src_dir_rel = "solar/asteroids"
            section_name = "Asteroids"
            ids_info = "66146"  # asteroids
        else:
            src_dir_name = "solar\\nebula"
            src_dir_rel = "solar/nebula"
            section_name = "Nebula"
            ids_info = "66146"  # nebulas use same value
        
        base = Path(game_path)
        # Look for DATA directory if game_path doesn't point to it
        if not (base / "solar").exists() and not (base / "SOLAR").exists():
            data_dir = _ci_find(base, "DATA")
            if data_dir and data_dir.is_dir():
                base = data_dir
        # use _ci_find for case-insensitive directory resolution
        solar_dir = _ci_find(base, "solar")
        if not solar_dir or not solar_dir.is_dir():
            QMessageBox.warning(self, "Fehler", 
                               f"solar-Verzeichnis nicht gefunden in {base}")
            return
        if zone_type == "Asteroid Field":
            src_dir = _ci_find(solar_dir, "asteroids")
        else:
            src_dir = _ci_find(solar_dir, "nebula")
        if not src_dir or not src_dir.is_dir():
            QMessageBox.warning(self, "Fehler", f"Verzeichnis {src_dir_rel} nicht gefunden.")
            return
        
        src_file = src_dir / ref_file
        if not src_file.exists():
            QMessageBox.warning(self, "Fehler", f"Referenzdatei nicht gefunden: {src_file}")
            return
        
        # create a copy in the same directory
        sys_name = Path(self._filepath).stem.upper()
        # determine next sequential number and safe filename
        # turn spaces into underscores and remove unsafe characters
        tmp_name = zone_name.replace(' ', '_')
        safe_zone_name = "".join(ch for ch in tmp_name if ch.isalnum() or ch in ('_', '-'))
        existing = list(src_dir.glob(f"{sys_name}_{safe_zone_name}_*.ini"))
        next_num = len(existing) + 1
        # filename: {SYS}_{Name}_{N}.ini per user request
        new_zone_file = f"{sys_name}_{safe_zone_name}_{next_num}.ini"
        new_zone_path = src_dir / new_zone_file
        
        # copy file and remove exclusion zones
        try:
            content = src_file.read_text(encoding="utf-8")
            # remove [Exclusion Zones] sections
            lines = content.split("\n")
            new_lines = []
            skip_section = False
            for line in lines:
                l_lower = line.strip().lower()
                if l_lower == "[exclusion zones]":
                    skip_section = True
                elif l_lower.startswith("[") and skip_section:
                    skip_section = False
                if not skip_section:
                    new_lines.append(line)
            # append comment
            new_lines.append(f"\n; Copied by FLeditor from file: {src_dir_name}\\{ref_file}")
            new_zone_path.write_text("\n".join(new_lines), encoding="utf-8")
        except Exception as ex:
            QMessageBox.critical(self, "Fehler beim Kopieren", str(ex))
            return
        
        # create zone entry in sections and zone data
        zone_nick = f"Zone_{sys_name}_{safe_zone_name}_{next_num}"
        zone_entries = [
            ("nickname", zone_nick),
            ("ids_name", "0"),
            ("pos", f"{pos.x()/self._scale:.2f}, 0, {pos.y()/self._scale:.2f}"),
            ("rotate", "0, 0, 0"),
            ("shape", "ELLIPSOID"),
            ("size", "1000, 1000, 1000"),
            ("property_flags", "0"),
            ("ids_info", ids_info),
            ("visit", "0"),
            ("damage", "0"),
        ]
        zone_data = {"_entries": zone_entries}
        for k, v in zone_entries:
            zone_data[k.lower()] = v

        zone = ZoneItem(zone_data, self._scale)
        self.view._scene.addItem(zone)
        self._zones.append(zone)
        self._rebuild_object_combo()
        self._select_zone(zone)

        # add a new [Zone] section to the system INI (will be written on save)
        # append to self._sections so it's included when writing the main INI
        try:
            self._sections.append(("Zone", list(zone_entries)))
        except Exception:
            # on any failure, fall back to appending at end
            self._sections.append(("Zone", list(zone_entries)))

        # also add [Asteroids]/[Nebula] section to the main INI
        # path relative to game directory
        rel_path = f"{src_dir_name}\\{new_zone_file}"
        entry = (section_name, [("file", rel_path), ("zone", zone_nick)])
        # Insert the new section under [Music] if present, otherwise append at end
        insert_idx = None
        for i, (sec_name, _) in enumerate(self._sections):
            if sec_name.lower() == "music":
                insert_idx = i + 1
                break
        if insert_idx is not None:
            self._sections.insert(insert_idx, entry)
        else:
            self._sections.append(entry)
        
        self._set_dirty(True)
        self._pending_zone = None
        self.statusBar().showMessage(f"✓  Zone '{zone_name}' erstellt")

    def _extract_nickname_from_entries(self, entries):
        """Extract the 'nickname' value from a list of (key, value) tuples."""
        for k, v in entries:
            if k.lower() == "nickname":
                return v
        return None

    def _search_nickname(self):
        term = self.search_edit.text().strip().lower()
        if not term:
            return
        for o in self._objects:
            if o.nickname.lower() == term:
                self.view.centerOn(o)
                self._select(o)
                return
        QMessageBox.information(self, "Nicht gefunden",
                                f"Kein Objekt mit Nickname '{term}'")

    def _create_new_object(self):
        if not self._filepath:
            QMessageBox.warning(self, "Kein System",
                                "Bitte zuerst ein System laden.")
            return
        nickname = self.search_edit.text().strip() or f"new_obj_{len(self._objects)+1}"
        entries = [("nickname", nickname), ("pos", "0,0,0"),
                   ("ids_name", "0"), ("ids_info", "0"),
                   ("rotate", "0,0,0")]
        arch = self.arch_cb.currentText().strip()
        if arch:
            entries.append(("archetype", arch))
        loadout = self.loadout_cb.currentText().strip()
        if loadout:
            entries.append(("loadout", loadout))
        faction = self.faction_cb.currentText().strip()
        if faction:
            rep_val = self.rep_edit.text().strip()
            if rep_val:
                entries.append(("reputation", f"{faction},{rep_val}"))
            else:
                entries.append(("reputation", faction))
        data = {"_entries": entries}
        for k, v in entries:
            if k.lower() not in data:
                data[k.lower()] = v
        obj = SolarObject(data, self._scale)
        obj.setFlag(QGraphicsItem.ItemIsMovable, self.move_cb.isChecked())
        self.view._scene.addItem(obj)
        self._objects.append(obj)
        self._rebuild_object_combo()
        self._select(obj)
        self._set_dirty(True)

    # ── Texteditor → Objektdaten (Memory) ───────────────────────────────
    def _apply(self):
        if not self._selected:
            return
        self._selected.apply_text(self.editor.toPlainText())
        self.name_lbl.setText(f"📍 {self._selected.nickname}")
        self._set_dirty(True)
        self.statusBar().showMessage(
            f"✔  '{self._selected.nickname}' übernommen (noch nicht gespeichert)")

    # ── In Datei schreiben (.tmp → rename) + Reload ──────────────────────
    def _write_to_file(self, reload: bool = True):
        if not self._filepath:
            return
        if self._selected:
            self._selected.apply_text(self.editor.toPlainText())

        # Szenen-Positionen → pos-Einträge aktualisieren (objects und zones)
        for obj in self._objects:
            new_pos = obj.fl_pos_str()
            obj.data["_entries"] = [
                (k, new_pos if k.lower()=="pos" else v)
                for k, v in obj.data["_entries"]
            ]
        for zone in self._zones:
            # zones don't move, but update their _entries if edited
            # (no position update needed unlike objects)
            pass

        # INI-Text rekonstruieren – vorhandene Sektionen mit den aktuell
        # geladenen Objekten UND Zonen abgleichen
        obj_idx = 0
        zone_idx = 0
        remaining_objs = []  # for objects that have no corresponding section
        remaining_zones = []  # for zones that have no corresponding section
        lines = []
        
        for sec_name, entries in self._sections:
            lines.append(f"[{sec_name}]")
            if sec_name.lower() == "object":
                if obj_idx < len(self._objects):
                    o = self._objects[obj_idx]
                    for k, v in o.data["_entries"]:
                        lines.append(f"{k} = {v}")
                    obj_idx += 1
                else:
                    # original section exists but no new object – keep old lines
                    for k, v in entries:
                        lines.append(f"{k} = {v}")
            elif sec_name.lower() == "zone":
                # Finde die entsprechende Zone anhand des Namens
                found = False
                for i, z in enumerate(self._zones[zone_idx:], start=zone_idx):
                    if z.nickname == self._extract_nickname_from_entries(entries):
                        for k, v in z.data["_entries"]:
                            lines.append(f"{k} = {v}")
                        zone_idx = i + 1
                        found = True
                        break
                if not found:
                    # Zone nicht gefunden, alte Einträge behalten
                    for k, v in entries:
                        lines.append(f"{k} = {v}")
            else:
                for k, v in entries:
                    lines.append(f"{k} = {v}")
            lines.append("")
        
        # falls noch zusätzliche Objekte in _objects verbleiben
        for o in self._objects[obj_idx:]:
            lines.append("[Object]")
            for k, v in o.data["_entries"]:
                lines.append(f"{k} = {v}")
            lines.append("")
        
        # falls noch zusätzliche Zonen in _zones verbleiben
        for z in self._zones[zone_idx:]:
            lines.append("[Zone]")
            for k, v in z.data["_entries"]:
                lines.append(f"{k} = {v}")
            lines.append("")

        tmp = self._filepath + ".tmp"
        try:
            Path(tmp).write_text("\n".join(lines), encoding="utf-8")
            shutil.move(tmp, self._filepath)
        except Exception as ex:
            QMessageBox.critical(self, "Fehler beim Speichern", str(ex))
            return

        if reload:
            self.statusBar().showMessage(f"✔  Gespeichert · Lade neu …")
            self._load(self._filepath, restore=self.view.transform())
            self.browser.highlight_current(self._filepath)
        else:
            # just notify, keep current scene and pending state intact
            self.statusBar().showMessage("✔  Gespeichert")

    # helper used by connection workflow to write a snapshot tuple
    def _write_snapshot(self, snapshot):
        filepath, sections, objs = snapshot
        lines = []
        obj_iter = iter(objs)
        for sec_name, entries in sections:
            lines.append(f"[{sec_name}]")
            if sec_name.lower() == "object":
                try:
                    o = next(obj_iter)
                    for k, v in o.get("_entries", []):
                        lines.append(f"{k} = {v}")
                except StopIteration:
                    for k, v in entries:
                        lines.append(f"{k} = {v}")
            else:
                for k, v in entries:
                    lines.append(f"{k} = {v}")
            lines.append("")
        for o in obj_iter:
            lines.append("[Object]")
            for k, v in o.get("_entries", []):
                lines.append(f"{k} = {v}")
            lines.append("")
        tmp = filepath + ".tmp"
        try:
            Path(tmp).write_text("\n".join(lines), encoding="utf-8")
            shutil.move(tmp, filepath)
        except Exception as ex:
            QMessageBox.critical(self, "Fehler beim Speichern", str(ex))

    def _save_pending_connections(self):
        # write all queued snapshots to disk
        for snap in list(self._pending_snapshots):
            self._write_snapshot(snap)
        self._pending_snapshots.clear()
        self.save_conn_btn.setVisible(False)
        self.create_conn_btn.setEnabled(True)
        self._set_dirty(False)
        self.statusBar().showMessage("✔  Verbindungen gespeichert")

    # ── Dirty-Flag ──────────────────────────────────────────────────────
    def _set_dirty(self, d: bool):
        self._dirty = d
        self.write_btn.setEnabled(bool(self._filepath) and d)
        t = self.windowTitle()
        if d and not t.startswith("*"):
            self.setWindowTitle("* " + t)
        elif not d and t.startswith("* "):
            self.setWindowTitle(t[2:])

    def _toggle_move(self, checked: bool):
        for obj in self._objects:
            # Universum-Marker dürfen nie verschoben werden
            if hasattr(obj, "sys_path"):
                continue
            obj.setFlag(QGraphicsItem.ItemIsMovable, checked)
        self.statusBar().showMessage(
            "Move-Modus AN — Linke Maustaste zum Verschieben"
            if checked else "Move-Modus AUS")

    def _toggle_zones(self, checked: bool):
        for z in self._zones:
            z.setVisible(checked)

    def _fit(self):
        r = self.view._scene.itemsBoundingRect()
        self.view.fitInView(r.adjusted(-80,-80,80,80), Qt.KeepAspectRatio)


# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
