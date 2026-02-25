#!/usr/bin/env python3
"""
Freelancer System Editor v5
Neu: Universumsansicht beim Start
     - Alle Systeme als Punkte (pos aus universe.ini)
     - Verbindungslinien: Blau = Jump Gate / Nomad Gate, Gelb = Jump Hole
     - Doppelklick auf System → System-Editor öffnet sich
     - Zurück-Button zur Universumskarte
"""
import sys
import json
import shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsItem,
    QGraphicsLineItem,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QTextEdit, QLabel,
    QFileDialog, QSplitter, QGroupBox, QCheckBox, QMessageBox,
    QListWidget, QListWidgetItem, QLineEdit, QStackedWidget,
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QBrush, QColor, QPen, QFont, QPainter, QAction, QTransform


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
            json.dumps(self._d, indent=2, ensure_ascii=False), encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════
#  Case-insensitive Pfadauflösung  (Komponente für Komponente)
# ══════════════════════════════════════════════════════════════════════
def _ci_find(base: Path, name: str) -> Path | None:
    try:
        for entry in base.iterdir():
            if entry.name.lower() == name.lower():
                return entry
    except Exception:
        pass
    return None


def ci_resolve(base: Path, rel: str) -> Path | None:
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
#  universe.ini-Finder und System-Scanner
# ══════════════════════════════════════════════════════════════════════
def find_universe_ini(game_path: str) -> Path | None:
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
    Liest universe.ini → gibt alle Systeme zurück mit:
    {"nickname": str, "path": str, "pos": (x, y)}
    pos = 2D-Koordinaten aus universe.ini (x, y)
    """
    uni_ini = find_universe_ini(game_path)
    if not uni_ini:
        return []

    uni_dir  = uni_ini.parent
    data_dir = uni_dir.parent
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

        nickname = d.get("nickname", "???")
        file_rel = d["file"].strip()

        # 2D-Position aus universe.ini
        try:
            pp  = [float(c.strip()) for c in d.get("pos", "0, 0").split(",")]
            ux  = pp[0] if len(pp) > 0 else 0.0
            uy  = pp[1] if len(pp) > 1 else 0.0
        except Exception:
            ux, uy = 0.0, 0.0

        sys_path = None
        for search_base in (uni_dir, data_dir):
            resolved = ci_resolve(search_base, file_rel)
            if resolved:
                sys_path = resolved
                break

        if sys_path:
            systems.append({
                "nickname": nickname,
                "path":     str(sys_path),
                "pos":      (ux, uy),
            })

    return sorted(systems, key=lambda x: x["nickname"].lower())


# ══════════════════════════════════════════════════════════════════════
#  Schneller Jump-Scanner (liest nur archetype + goto je [Object])
# ══════════════════════════════════════════════════════════════════════
def _fast_scan_jumps(filepath: str) -> list[tuple[str, str]]:
    """
    Gibt [(archetype_lower, goto_raw), ...] für alle [Object]-Sektionen zurück.
    Schnell, weil keine vollständige Strukturierung nötig ist.
    """
    results  = []
    in_obj   = False
    arch     = ""
    goto     = ""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith(";") or line.startswith("//"):
                    continue
                if line.startswith("["):
                    if in_obj and arch and goto:
                        results.append((arch, goto))
                    in_obj = line.lower() == "[object]"
                    arch, goto = "", ""
                elif in_obj and "=" in line:
                    sem = line.find(";")
                    if sem > 0:
                        line = line[:sem].strip()
                    k, _, v = line.partition("=")
                    k = k.strip().lower()
                    if k == "archetype":
                        arch = v.strip().lower()
                    elif k == "goto":
                        goto = v.strip()
        if in_obj and arch and goto:
            results.append((arch, goto))
    except Exception:
        pass
    return results


def find_connections(systems: list[dict]) -> list[dict]:
    """
    Scannt alle Systemdateien nach Sprung-Verbindungen.
    Rückgabe: [{"from": "Li01", "to": "Li02", "type": "gate"/"hole"}, ...]
    Duplikate (A→B == B→A) werden zusammengeführt.
    """
    sys_map  = {s["nickname"].lower(): s for s in systems}
    seen     = set()
    result   = []

    for sys_info in systems:
        from_nick = sys_info["nickname"]
        jumps = _fast_scan_jumps(sys_info["path"])

        for arch, goto in jumps:
            # Typ bestimmen – HD Edition nutzt auch nomadgate
            if any(x in arch for x in ("jumphole", "jump_hole")):
                conn_type = "hole"
            elif any(x in arch for x in ("jumpgate", "nomadgate", "jump_gate", "airlockgate")):
                conn_type = "gate"
            else:
                continue

            to_nick = goto.split(",")[0].strip().lower()
            if to_nick == from_nick.lower() or to_nick not in sys_map:
                continue

            key = (min(from_nick.lower(), to_nick), max(from_nick.lower(), to_nick), conn_type)
            if key not in seen:
                seen.add(key)
                result.append({
                    "from": from_nick,
                    "to":   sys_map[to_nick]["nickname"],
                    "type": conn_type,
                })

        QApplication.processEvents()

    return result


# ══════════════════════════════════════════════════════════════════════
#  INI-Parser  (unterstützt doppelte Schlüssel)
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
#  Universumsansicht – System-Punkt
# ══════════════════════════════════════════════════════════════════════
class UniverseSystemDot(QGraphicsEllipseItem):
    R = 5

    def __init__(self, nickname: str, filepath: str):
        r = self.R
        super().__init__(-r, -r, 2*r, 2*r)
        self.nickname = nickname
        self.filepath = filepath

        self._brush_n = QBrush(QColor( 80, 160, 255))
        self._brush_h = QBrush(QColor(200, 230, 255))
        self._brush_s = QBrush(QColor(255, 200,  50))
        self.setBrush(self._brush_n)
        self.setPen(QPen(QColor(140, 190, 255, 180), 1))

        lbl = QGraphicsTextItem(nickname, self)
        lbl.setDefaultTextColor(QColor(180, 210, 255))
        lbl.setFont(QFont("Sans", 7))
        lbl.setPos(self.R + 3, -self.R)
        lbl.setAcceptedMouseButtons(Qt.NoButton)

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(2)
        self.setToolTip(f"<b>{nickname}</b><br><small>{filepath}</small>")

    def hoverEnterEvent(self, e):
        self.setBrush(self._brush_h); super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self.setBrush(self._brush_n); super().hoverLeaveEvent(e)

    def set_selected_visual(self, sel: bool):
        self.setBrush(self._brush_s if sel else self._brush_n)
        self.setPen(QPen(QColor(255, 220, 100), 2) if sel
                    else QPen(QColor(140, 190, 255, 180), 1))


# ══════════════════════════════════════════════════════════════════════
#  Universumsansicht – View  (Zoom, Pan, Doppelklick-Signal)
# ══════════════════════════════════════════════════════════════════════
class UniverseView(QGraphicsView):
    system_double_clicked = Signal(str, str)   # filepath, nickname

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(QColor(4, 4, 18)))
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self._panning   = False
        self._pan_start = QPointF()

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1/1.15
        self.scale(f, f)

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._panning, self._pan_start = True, e.position()
            self.setCursor(Qt.ClosedHandCursor); return
        super().mousePressEvent(e)

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
        if e.button() == Qt.LeftButton:
            item = self.itemAt(e.pos())
            if isinstance(item, QGraphicsTextItem):
                item = item.parentItem()
            if isinstance(item, UniverseSystemDot):
                self.system_double_clicked.emit(item.filepath, item.nickname)
                return
        super().mouseDoubleClickEvent(e)


# ══════════════════════════════════════════════════════════════════════
#  Universumsansicht – Widget  (View + Legende + Status)
# ══════════════════════════════════════════════════════════════════════
class UniverseMapWidget(QWidget):
    system_activated = Signal(str, str)   # filepath, nickname

    def __init__(self):
        super().__init__()
        self._dot_map: dict[str, UniverseSystemDot] = {}
        self._current_nick = ""
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Titelleiste
        top = QWidget(); top.setFixedHeight(32)
        tl  = QHBoxLayout(top); tl.setContentsMargins(8, 4, 8, 4)
        self.status_lbl = QLabel("🌌  Universumskarte")
        self.status_lbl.setStyleSheet("color:#99aaff; font-size:10pt;")
        tl.addWidget(self.status_lbl)
        tl.addStretch()
        hint = QLabel("Doppelklick = System bearbeiten  |  Rad = Zoom  |  Mitte = Pan")
        hint.setStyleSheet("color:#445; font-size:8pt;")
        tl.addWidget(hint)
        lay.addWidget(top)

        self.view = UniverseView()
        self.view.system_double_clicked.connect(self._on_double_click)
        lay.addWidget(self.view, stretch=1)

        # Legende
        leg = QWidget(); leg.setFixedHeight(28)
        ll  = QHBoxLayout(leg); ll.setContentsMargins(8, 4, 8, 4); ll.setSpacing(20)
        for col, txt in [
            ("#3296ff", "─── Jump Gate"),
            ("#ffd028", "- - Jump Hole"),
            ("#50a0ff", "●  System (Klick zeigt Info, Doppelklick öffnet Editor)"),
        ]:
            l = QLabel(f'<span style="color:{col}">{txt}</span>')
            l.setTextFormat(Qt.RichText); ll.addWidget(l)
        ll.addStretch()
        lay.addWidget(leg)

    def load_universe(self, systems: list[dict]):
        self._dot_map     = {}
        self._current_nick = ""
        self.view._scene.clear()

        if not systems:
            self.status_lbl.setText("⚠  Keine Systeme gefunden")
            return

        # Auto-Skalierung
        xs = [s["pos"][0] for s in systems]
        ys = [s["pos"][1] for s in systems]
        ext = max(max(abs(x) for x in xs) if xs else 1,
                  max(abs(y) for y in ys) if ys else 1, 1)
        scale = 500.0 / ext

        for s in systems:
            dot = UniverseSystemDot(s["nickname"], s["path"])
            dot.setPos(s["pos"][0] * scale, s["pos"][1] * scale)
            self.view._scene.addItem(dot)
            self._dot_map[s["nickname"].lower()] = dot

        self.status_lbl.setText(
            f"🌌  {len(systems)} Systeme geladen — scanne Verbindungen …")
        self.view.fitInView(
            self.view._scene.itemsBoundingRect().adjusted(-60,-60,60,60),
            Qt.KeepAspectRatio)
        QApplication.processEvents()

        # Verbindungen scannen
        connections = find_connections(systems)
        gate_pen = QPen(QColor( 50, 150, 255, 200), 1.2)
        hole_pen = QPen(QColor(255, 200,  40, 180), 1.2, Qt.DashLine)

        drawn = 0
        for c in connections:
            fd = self._dot_map.get(c["from"].lower())
            td = self._dot_map.get(c["to"].lower())
            if not fd or not td:
                continue
            line = QGraphicsLineItem(
                fd.pos().x(), fd.pos().y(),
                td.pos().x(), td.pos().y())
            line.setPen(gate_pen if c["type"] == "gate" else hole_pen)
            line.setZValue(0)
            line.setAcceptedMouseButtons(Qt.NoButton)
            self.view._scene.addItem(line)
            drawn += 1

        self.status_lbl.setText(
            f"🌌  {len(systems)} Systeme · {drawn} Verbindungen")
        self.view.fitInView(
            self.view._scene.itemsBoundingRect().adjusted(-60,-60,60,60),
            Qt.KeepAspectRatio)

    def highlight_system(self, nickname: str):
        if self._current_nick:
            old = self._dot_map.get(self._current_nick.lower())
            if old:
                old.set_selected_visual(False)
        self._current_nick = nickname
        dot = self._dot_map.get(nickname.lower())
        if dot:
            dot.set_selected_visual(True)

    def _on_double_click(self, filepath: str, nickname: str):
        self.highlight_system(nickname)
        self.system_activated.emit(filepath, nickname)


# ══════════════════════════════════════════════════════════════════════
#  Linkes Panel: Datenpfad + Systemliste
# ══════════════════════════════════════════════════════════════════════
class SystemBrowser(QWidget):
    system_load_requested = Signal(str)
    systems_scanned       = Signal(list)   # emittiert systems-Liste nach Scan

    def __init__(self, config: Config, parser: FLParser):
        super().__init__()
        self._config = config
        self._parser = parser
        self._build_ui()
        # Pfad vorausfüllen, aber NICHT auto-scannen
        # (MainWindow löst trigger_scan() nach Signal-Verbindung aus)
        saved = config.get("game_path", "")
        if saved:
            self.path_edit.setText(saved)

    def trigger_scan(self):
        self._scan()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        title = QLabel("⭐  System-Browser")
        title.setStyleSheet("font-weight:bold; font-size:11pt; color:#99aaff; padding:4px 0;")
        layout.addWidget(title)

        g  = QGroupBox("Freelancer-Verzeichnis")
        gl = QVBoxLayout(g); gl.setSpacing(4)

        row = QWidget()
        rl  = QHBoxLayout(row); rl.setContentsMargins(0,0,0,0); rl.setSpacing(3)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("/pfad/zu/Freelancer HD Edition/")
        self.path_edit.returnPressed.connect(self._save_and_scan)
        rl.addWidget(self.path_edit)
        browse_btn = QPushButton("📁"); browse_btn.setFixedWidth(32)
        browse_btn.clicked.connect(self._browse); rl.addWidget(browse_btn)
        gl.addWidget(row)

        scan_btn = QPushButton("🔍  Systeme einlesen")
        scan_btn.clicked.connect(self._save_and_scan); gl.addWidget(scan_btn)
        layout.addWidget(g)

        list_lbl = QLabel("Systeme  (Klick = laden):")
        list_lbl.setStyleSheet("color:#aab; font-size:9pt;")
        layout.addWidget(list_lbl)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget, stretch=1)

        self.status_lbl = QLabel("")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("color:#888; font-size:9pt; padding:2px;")
        layout.addWidget(self.status_lbl)

    def _browse(self):
        start = self.path_edit.text() or str(Path.home())
        path  = QFileDialog.getExistingDirectory(self, "Freelancer-Verzeichnis wählen", start)
        if path:
            self.path_edit.setText(path); self._save_and_scan()

    def _save_and_scan(self):
        path = self.path_edit.text().strip()
        if path:
            self._config.set("game_path", path)
        self._scan()

    def _scan(self):
        path = self.path_edit.text().strip()
        if not path:
            self.status_lbl.setText("⚠  Kein Pfad angegeben."); return

        self.status_lbl.setText("Suche …"); QApplication.processEvents()
        uni_ini = find_universe_ini(path)
        if not uni_ini:
            self.status_lbl.setText("⚠  universe.ini nicht gefunden.")
            self.list_widget.clear(); return

        systems = find_all_systems(path, self._parser)
        self.list_widget.clear()
        for s in systems:
            item = QListWidgetItem(s["nickname"])
            item.setData(Qt.UserRole, s["path"])
            item.setToolTip(s["path"])
            self.list_widget.addItem(item)

        if systems:
            self.status_lbl.setText(f"✔  {len(systems)} Systeme\n{uni_ini}")
            self.systems_scanned.emit(systems)
        else:
            self.status_lbl.setText("⚠  Keine gültigen [system]-Einträge.")

    def _on_item_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path:
            self.system_load_requested.emit(path)

    def highlight_current(self, filepath: str):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            is_c = item.data(Qt.UserRole) == filepath
            item.setBackground(QColor(40, 60, 100) if is_c else QColor(0, 0, 0, 0))
            f = item.font(); f.setBold(is_c); item.setFont(f)


# ══════════════════════════════════════════════════════════════════════
#  Zone-Item  (NUR visuell – akzeptiert keine Maus-Events)
# ══════════════════════════════════════════════════════════════════════
class ZoneItem(QGraphicsItem):
    def __init__(self, data: dict, scale: float):
        super().__init__()
        self.data     = data
        self.nickname = data.get("nickname", "")
        self.shape_t  = data.get("shape", "SPHERE").upper()

        sp = [float(s.strip()) for s in data.get("size", "1000").split(",")]
        s0 = sp[0] if len(sp)>0 else 1000.0
        s1 = sp[1] if len(sp)>1 else s0
        s2 = sp[2] if len(sp)>2 else s0

        if   self.shape_t == "SPHERE":    self.hw, self.hd = s0*scale,   s0*scale
        elif self.shape_t == "ELLIPSOID": self.hw, self.hd = s0*scale,   s2*scale
        elif self.shape_t == "BOX":       self.hw, self.hd = s0*scale/2, s2*scale/2
        elif self.shape_t == "CYLINDER":  self.hw, self.hd = s0*scale,   s1*scale/2
        else:                             self.hw, self.hd = s0*scale,   s0*scale

        pp = [float(c.strip()) for c in data.get("pos","0,0,0").split(",")]
        self.setPos((pp[0] if len(pp)>0 else 0)*scale,
                    (pp[2] if len(pp)>2 else pp[1] if len(pp)>1 else 0)*scale)
        rp = [float(r.strip()) for r in data.get("rotate","0,0,0").split(",")]
        self.setRotation(rp[1] if len(rp)>1 else 0.0)
        self._pen, self._brush = self._style()
        self._build_label()
        self.setZValue(-1)
        self.setAcceptedMouseButtons(Qt.NoButton)
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
        if any(x in n for x in ("path","vignette","exclusion","death","tradelane",
                                  "laneaccess","destroyvignette","sundeath","radiation")):
            return
        if self.hw < 8:
            return
        lbl = QGraphicsTextItem(self.nickname, self)
        lbl.setDefaultTextColor(QColor(160,160,190))
        lbl.setFont(QFont("Sans", 6))
        lbl.setPos(4, 4)
        lbl.setAcceptedMouseButtons(Qt.NoButton)

    def boundingRect(self):
        return QRectF(-self.hw-2, -self.hd-2, self.hw*2+4, self.hd*2+4)

    def paint(self, painter, option, widget=None):
        painter.setPen(self._pen); painter.setBrush(self._brush)
        r = QRectF(-self.hw, -self.hd, self.hw*2, self.hd*2)
        painter.drawRect(r) if self.shape_t in ("BOX","CYLINDER") else painter.drawEllipse(r)


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

        pp  = [float(c.strip()) for c in data.get("pos","0,0,0").split(",")]
        fx  = pp[0] if len(pp)>0 else 0.0
        fz  = pp[2] if len(pp)>2 else (pp[1] if len(pp)>1 else 0.0)
        self.setPos(fx*scale, fz*scale)

        self.nickname = data.get("nickname","???")
        arch = data.get("archetype","").lower()

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


# ══════════════════════════════════════════════════════════════════════
#  System-View  (Zoom + Pan, für den System-Editor)
# ══════════════════════════════════════════════════════════════════════
class SystemView(QGraphicsView):
    object_selected = Signal(object)

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
            if isinstance(item, QGraphicsTextItem): item = item.parentItem()
            if isinstance(item, SolarObject): self.object_selected.emit(item)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._panning:
            d = e.position()-self._pan_start; self._pan_start = e.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-int(d.x()))
            self.verticalScrollBar().setValue(  self.verticalScrollBar().value()  -int(d.y()))
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._panning = False; self.setCursor(Qt.ArrowCursor); return
        super().mouseReleaseEvent(e)


# ══════════════════════════════════════════════════════════════════════
#  Hauptfenster
# ══════════════════════════════════════════════════════════════════════
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
        self._build_ui()

        # Startet Scan wenn Pfad bereits konfiguriert
        if self._cfg.get("game_path", ""):
            self.browser.trigger_scan()

    # ── UI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        self.uni_action = QAction("🌌  Universum", self)
        self.uni_action.setToolTip("Zur Universums-Übersichtskarte")
        self.uni_action.triggered.connect(self._show_universe)
        tb.addAction(self.uni_action)

        tb.addSeparator()

        for lbl, key, slot in [
            ("📂 INI öffnen", "Ctrl+O", self._open_manual),
            ("🔍 Alles",      "Ctrl+F", self._fit),
        ]:
            a = QAction(lbl, self); a.setShortcut(key); a.triggered.connect(slot)
            tb.addAction(a)

        tb.addSeparator()

        self.move_cb = QCheckBox("✋  Move-Modus")
        self.move_cb.setToolTip("Objekte per Maus verschieben")
        self.move_cb.toggled.connect(self._toggle_move)
        tb.addWidget(self.move_cb)

        tb.addSeparator()

        self.zone_cb = QCheckBox("🗺  Zonen")
        self.zone_cb.setChecked(True)
        self.zone_cb.toggled.connect(self._toggle_zones)
        tb.addWidget(self.zone_cb)

        # Drei-Spalten-Splitter
        splitter = QSplitter(Qt.Horizontal)

        # 1. Links: Browser
        self.browser = SystemBrowser(self._cfg, self._parser)
        self.browser.system_load_requested.connect(self._load_from_browser)
        self.browser.systems_scanned.connect(self._on_systems_scanned)
        splitter.addWidget(self.browser)

        # 2. Mitte: Stack  [0=Universum | 1=System-Editor]
        self.center_stack = QStackedWidget()

        self.universe_map = UniverseMapWidget()
        self.universe_map.system_activated.connect(self._on_universe_activated)
        self.center_stack.addWidget(self.universe_map)   # Index 0

        self.view = SystemView()
        self.view.object_selected.connect(self._select)
        self.center_stack.addWidget(self.view)            # Index 1

        self.center_stack.setCurrentIndex(0)
        splitter.addWidget(self.center_stack)

        # 3. Rechts: Objekt-Editor
        right = QWidget()
        rl    = QVBoxLayout(right); rl.setContentsMargins(6,6,6,6)

        self.name_lbl = QLabel("Kein Objekt ausgewählt")
        self.name_lbl.setStyleSheet("font-weight:bold; font-size:12pt;")
        rl.addWidget(self.name_lbl)

        g  = QGroupBox("INI-Eigenschaften")
        gl = QVBoxLayout(g)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Monospace",10))
        self.editor.setPlaceholderText("Klicke auf ein Objekt …")
        gl.addWidget(self.editor)

        self.apply_btn = QPushButton("✔  Objekt-Änderungen übernehmen")
        self.apply_btn.setToolTip("Texteditor → Objektdaten (nur im Speicher)")
        self.apply_btn.clicked.connect(self._apply)
        self.apply_btn.setEnabled(False)
        gl.addWidget(self.apply_btn)

        self.write_btn = QPushButton("💾  Änderungen in Datei schreiben")
        self.write_btn.setToolTip(
            "Alle Änderungen via .tmp in Original-INI schreiben\n"
            "und Ansicht danach neu laden.")
        self.write_btn.setStyleSheet(
            "QPushButton{background:#1a3a1a;border:1px solid #2a5a2a;}"
            "QPushButton:hover{background:#245a24;}"
            "QPushButton:disabled{color:#445;background:#111;border-color:#333;}")
        self.write_btn.clicked.connect(self._write_to_file)
        self.write_btn.setEnabled(False)
        gl.addWidget(self.write_btn)
        rl.addWidget(g)

        legend = QGroupBox("Legende")
        ll = QVBoxLayout(legend)
        for col, txt in [
            ("#ffd728","☀  Stern / Sonne"),   ("#3c82dc","🪐  Planet"),
            ("#50d264","🏠  Basis / Station"), ("#d25ad2","⭕  Jumpgate / -hole"),
            ("#966e46","☄  Asteroidenfeld"),   ("#bebebe","◉  Sonstiges"),
            ("",""),
            ("#dc3232","─  Zone Death"),       ("#9650dc","─  Zone Nebula"),
            ("#b4823c","─  Zone Debris"),      ("#3cb4dc","--  Zone Tradelane"),
            ("#50a0c8","─  Zone Sonstiges"),
        ]:
            if not col: ll.addSpacing(4); continue
            lbl = QLabel(f'<span style="color:{col}">■</span>  {txt}')
            lbl.setTextFormat(Qt.RichText); ll.addWidget(lbl)
        rl.addWidget(legend)

        self.info_lbl = QLabel("Keine Datei geladen.")
        self.info_lbl.setWordWrap(True)
        rl.addWidget(self.info_lbl)
        rl.addStretch()
        splitter.addWidget(right)

        splitter.setSizes([220, 1060, 320])
        self.setCentralWidget(splitter)
        self.statusBar().showMessage("Bereit")

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
            QStackedWidget { background:#08080f; }
        """)

    # ── Universum laden (via Browser-Scan-Signal) ────────────────────
    def _on_systems_scanned(self, systems: list):
        self.statusBar().showMessage("Lade Universumskarte …")
        QApplication.processEvents()
        self.universe_map.load_universe(systems)
        self.center_stack.setCurrentIndex(0)
        self.statusBar().showMessage(
            f"🌌  {len(systems)} Systeme — Doppelklick auf System zum Bearbeiten")

    # ── Universum-Übersichtskarte anzeigen ───────────────────────────
    def _show_universe(self):
        self.center_stack.setCurrentIndex(0)
        if self._filepath:
            self.universe_map.highlight_system(Path(self._filepath).stem)

    # ── System via Universumsansicht geöffnet ────────────────────────
    def _on_universe_activated(self, filepath: str, nickname: str):
        self._filepath = filepath
        self._load(filepath)
        self.browser.highlight_current(filepath)
        self.center_stack.setCurrentIndex(1)
        self.statusBar().showMessage(
            f"✔  System {nickname} geladen — 🌌 Universum-Button für Übersicht")

    # ── System via Browser-Liste geladen ─────────────────────────────
    def _load_from_browser(self, path: str):
        self._filepath = path
        self._load(path)
        self.browser.highlight_current(path)
        self.universe_map.highlight_system(Path(path).stem)
        self.center_stack.setCurrentIndex(1)

    # ── Manuell per Dateidialog öffnen ───────────────────────────────
    def _open_manual(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Freelancer INI öffnen", "", "INI (*.ini);;Alle (*)")
        if path:
            self._filepath = path
            self._load(path)
            self.browser.highlight_current(path)
            self.universe_map.highlight_system(Path(path).stem)
            self.center_stack.setCurrentIndex(1)

    # ── Datei einlesen + Szene aufbauen ──────────────────────────────
    def _load(self, path: str, restore: QTransform | None = None):
        self._sections = self._parser.parse(path)
        raw_objs  = self._parser.get_objects(self._sections)
        raw_zones = self._parser.get_zones(self._sections)

        coords = []
        for d in raw_objs + raw_zones:
            pp = [float(c.strip()) for c in d.get("pos","0,0,0").split(",")]
            if len(pp)>0: coords.append(abs(pp[0]))
            if len(pp)>2: coords.append(abs(pp[2]))
        self._scale = 500.0 / (max(coords, default=1) or 1)

        self.view._scene.clear()
        self._objects, self._zones = [], []
        self._selected = None
        self.apply_btn.setEnabled(False)
        self.name_lbl.setText("Kein Objekt ausgewählt")
        self.editor.clear()

        for zd in raw_zones:
            try:
                zi = ZoneItem(zd, self._scale)
                self.view._scene.addItem(zi); self._zones.append(zi)
            except Exception:
                pass

        move_on = self.move_cb.isChecked()
        for od in raw_objs:
            try:
                obj = SolarObject(od, self._scale)
                obj.setFlag(QGraphicsItem.ItemIsMovable, move_on)
                self.view._scene.addItem(obj); self._objects.append(obj)
            except Exception:
                pass

        if not self.zone_cb.isChecked():
            for z in self._zones: z.setVisible(False)

        name = Path(path).stem.upper()
        self.info_lbl.setText(
            f"📄 {Path(path).name}\n"
            f"Objekte: {len(self._objects)}\n"
            f"Zonen:   {len(self._zones)}")
        self.setWindowTitle(f"Freelancer System Editor — {name}")
        self.statusBar().showMessage(
            f"✔  {name}: {len(self._objects)} Objekte · {len(self._zones)} Zonen")
        self._set_dirty(False)

        if restore:
            self.view.setTransform(restore)
        else:
            self._fit()

    # ── Objekt auswählen ────────────────────────────────────────────
    def _select(self, obj: SolarObject):
        if self._selected:
            self._selected._pos_change_cb = None
            p = self._selected.pen()
            p.setColor(QColor(255,255,255,70)); p.setWidth(1)
            self._selected.setPen(p)
        self._selected = obj
        p = obj.pen(); p.setColor(QColor(255,200,0)); p.setWidth(2)
        obj.setPen(p)
        obj._pos_change_cb = self._on_obj_moved
        self.name_lbl.setText(f"📍 {obj.nickname}")
        self.editor.setPlainText(obj.raw_text())
        self.apply_btn.setEnabled(True)
        self.statusBar().showMessage(f"Ausgewählt: {obj.nickname}")

    # ── Echtzeit pos-Update beim Verschieben ─────────────────────────
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

    # ── Texteditor → Objektdaten (Memory) ───────────────────────────
    def _apply(self):
        if not self._selected:
            return
        self._selected.apply_text(self.editor.toPlainText())
        self.name_lbl.setText(f"📍 {self._selected.nickname}")
        self._set_dirty(True)
        self.statusBar().showMessage(
            f"✔  '{self._selected.nickname}' übernommen (noch nicht gespeichert)")

    # ── Datei schreiben (.tmp → rename) + Reload ────────────────────
    def _write_to_file(self):
        if not self._filepath:
            return
        if self._selected:
            self._selected.apply_text(self.editor.toPlainText())

        for obj in self._objects:
            new_pos = obj.fl_pos_str()
            obj.data["_entries"] = [
                (k, new_pos if k.lower()=="pos" else v)
                for k, v in obj.data["_entries"]
            ]

        obj_iter = iter(self._objects)
        lines    = []
        for sec_name, entries in self._sections:
            lines.append(f"[{sec_name}]")
            if sec_name.lower() == "object":
                try:
                    o = next(obj_iter)
                    for k, v in o.data["_entries"]:
                        lines.append(f"{k} = {v}")
                except StopIteration:
                    for k, v in entries:
                        lines.append(f"{k} = {v}")
            else:
                for k, v in entries:
                    lines.append(f"{k} = {v}")
            lines.append("")

        tmp = self._filepath + ".tmp"
        try:
            Path(tmp).write_text("\n".join(lines), encoding="utf-8")
            shutil.move(tmp, self._filepath)
        except Exception as ex:
            QMessageBox.critical(self, "Fehler beim Speichern", str(ex)); return

        self.statusBar().showMessage("✔  Gespeichert · Lade neu …")
        self._load(self._filepath, restore=self.view.transform())
        self.browser.highlight_current(self._filepath)

    # ── Hilfsmethoden ─────────────────────────────────────────────────
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
            obj.setFlag(QGraphicsItem.ItemIsMovable, checked)
        self.statusBar().showMessage(
            "Move-Modus AN — Linke Maustaste zum Verschieben"
            if checked else "Move-Modus AUS")

    def _toggle_zones(self, checked: bool):
        for z in self._zones: z.setVisible(checked)

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
