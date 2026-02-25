#!/usr/bin/env python3
"""
Freelancer System Editor v3
Fixes: Move-Modus (ZoneItem blockiert keine Events mehr), Save-Workflow,
       Echtzeit-pos-Update, Reload nach Schreiben
"""
import sys
import shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView,
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsItem,
    QVBoxLayout, QWidget, QPushButton, QTextEdit, QLabel,
    QFileDialog, QSplitter, QGroupBox, QCheckBox, QMessageBox,
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QBrush, QColor, QPen, QFont, QPainter, QAction, QTransform


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

        if   self.shape_t == "SPHERE":    self.hw, self.hd = s0 * scale, s0 * scale
        elif self.shape_t == "ELLIPSOID": self.hw, self.hd = s0 * scale, s2 * scale
        elif self.shape_t == "BOX":       self.hw, self.hd = s0 * scale / 2, s2 * scale / 2
        elif self.shape_t == "CYLINDER":  self.hw, self.hd = s0 * scale, s1 * scale / 2
        else:                             self.hw, self.hd = s0 * scale, s0 * scale

        pp = [float(c.strip()) for c in data.get("pos", "0,0,0").split(",")]
        px = pp[0] if len(pp) > 0 else 0.0
        pz = pp[2] if len(pp) > 2 else (pp[1] if len(pp) > 1 else 0.0)
        self.setPos(px * scale, pz * scale)

        rp = [float(r.strip()) for r in data.get("rotate", "0,0,0").split(",")]
        self.setRotation(rp[1] if len(rp) > 1 else 0.0)

        self._pen, self._brush = self._style()
        self._build_label()

        self.setZValue(-1)

        # ══ KRITISCH: ZoneItems dürfen KEINE Maus-Events abfangen ══
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable,    False)
        self.setAcceptHoverEvents(False)

    def _style(self):
        n = self.nickname.lower()
        d = self.data
        if "death"   in n or "damage"   in d: return QPen(QColor(220, 50,  50, 200), 1.5), QBrush(QColor(220, 50,  50,  20))
        if "nebula"  in n or "badlands" in n:  return QPen(QColor(150, 80, 220, 180), 1),   QBrush(QColor(120, 60, 200,  18))
        if "debris"  in n or "asteroid" in n:  return QPen(QColor(180,130,  60, 180), 1),   QBrush(QColor(160,120,  50,  18))
        if "tradelane" in n:                   return QPen(QColor( 60,180, 220, 160), 1, Qt.DashLine), QBrush(QColor(60,180,220, 12))
        if "jumpgate" in n or "hole" in n:     return QPen(QColor(180,100, 220, 200), 1.5), QBrush(QColor(160, 80, 200,  18))
        if "exclusion" in n:                   return QPen(QColor(220,100,  50, 140), 1, Qt.DotLine),  QBrush(QColor(200, 80,  40,   8))
        if "path" in n or "vignette" in n:     return QPen(QColor(100,100, 150,  70), 1, Qt.DotLine),  QBrush(Qt.NoBrush)
        return QPen(QColor(80, 160, 200, 150), 1), QBrush(QColor(60, 140, 180, 14))

    def _build_label(self):
        n = self.nickname.lower()
        skip = any(x in n for x in ("path", "vignette", "exclusion", "death",
                                     "tradelane", "laneaccess", "destroyvignette",
                                     "sundeath", "radiation"))
        if not skip and self.hw > 8:
            lbl = QGraphicsTextItem(self.nickname, self)
            lbl.setDefaultTextColor(QColor(160, 160, 190))
            lbl.setFont(QFont("Sans", 6))
            lbl.setPos(4, 4)
            # Labels dürfen auch keine Events abfangen
            lbl.setAcceptedMouseButtons(Qt.NoButton)

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


# ══════════════════════════════════════════════════════════════════════
#  Solar-Objekt
# ══════════════════════════════════════════════════════════════════════
class SolarObject(QGraphicsEllipseItem):
    BASE_R = 8

    def __init__(self, data: dict, scale: float):
        r = self.BASE_R
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.data             = data
        self.scale            = scale
        self._pos_change_cb   = None

        # pos = x, y_hoch, z  →  Szene: x=x, y=z
        pp  = [float(c.strip()) for c in data.get("pos", "0,0,0").split(",")]
        fx  = pp[0] if len(pp) > 0 else 0.0
        fz  = pp[2] if len(pp) > 2 else (pp[1] if len(pp) > 1 else 0.0)
        self.setPos(fx * scale, fz * scale)

        self.nickname = data.get("nickname", "???")

        arch = data.get("archetype", "").lower()
        if any(x in arch for x in ("sun", "star")):
            color = QColor(255, 215, 40);  r = 14;  self.setRect(-r, -r, 2*r, 2*r)
        elif "planet"  in arch:                          color = QColor( 60, 130, 220)
        elif any(x in arch for x in ("base","station")): color = QColor( 80, 210, 100)
        elif any(x in arch for x in ("jump","gate")):    color = QColor(210,  90, 210)
        elif any(x in arch for x in ("asteroid","field","debris")): color = QColor(150, 110, 70)
        else:                                            color = QColor(190, 190, 190)

        self._brush_n = QBrush(color)
        self._brush_h = QBrush(color.lighter(160))
        self.setBrush(self._brush_n)
        self.setPen(QPen(QColor(255, 255, 255, 70), 1))

        if "tradelane" not in self.nickname.lower():
            self.label = QGraphicsTextItem(self.nickname, self)
            self.label.setDefaultTextColor(QColor(220, 220, 220))
            self.label.setFont(QFont("Sans", 7))
            self.label.setPos(self.BASE_R + 3, -self.BASE_R)
            self.label.setAcceptedMouseButtons(Qt.NoButton)
        else:
            self.label = None

        # ItemIsMovable startet AUS – wird per Checkbox aktiviert
        self.setFlag(QGraphicsItem.ItemIsMovable,            False)
        self.setFlag(QGraphicsItem.ItemIsSelectable,         True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

    def hoverEnterEvent(self, e):
        self.setBrush(self._brush_h); super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self.setBrush(self._brush_n); super().hoverLeaveEvent(e)

    # Echtzeit-Callback beim Verschieben
    def itemChange(self, change, value):
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
                and self._pos_change_cb):
            self._pos_change_cb(self)
        return super().itemChange(change, value)

    def fl_pos_str(self) -> str:
        """Szenenposition → Freelancer pos-String  (x, y_hoch, z)"""
        sp   = self.pos()
        fx   = sp.x() / self.scale
        fz   = sp.y() / self.scale
        orig = [p.strip() for p in self.data.get("pos", "0,0,0").split(",")]
        fy   = orig[1] if len(orig) > 1 else "0"
        return f"{fx:.2f}, {fy}, {fz:.2f}"

    def raw_text(self) -> str:
        return "\n".join(f"{k} = {v}" for k, v in self.data["_entries"])

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
#  System-View  (Zoom + Pan)
# ══════════════════════════════════════════════════════════════════════
class SystemView(QGraphicsView):
    object_selected = Signal(object)

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(QColor(6, 6, 20)))
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self._panning   = False
        self._pan_start = QPointF()

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.scale(f, f)

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._panning, self._pan_start = True, e.position()
            self.setCursor(Qt.ClosedHandCursor)
            return
        if e.button() == Qt.LeftButton:
            item = self.itemAt(e.pos())
            if isinstance(item, QGraphicsTextItem):
                item = item.parentItem()
            if isinstance(item, SolarObject):
                self.object_selected.emit(item)
        super().mousePressEvent(e)   # ← MUSS aufgerufen werden für ItemIsMovable

    def mouseMoveEvent(self, e):
        if self._panning:
            d = e.position() - self._pan_start
            self._pan_start = e.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(d.x()))
            self.verticalScrollBar().setValue(  self.verticalScrollBar().value()   - int(d.y()))
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            return
        super().mouseReleaseEvent(e)


# ══════════════════════════════════════════════════════════════════════
#  Hauptfenster
# ══════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Freelancer System Editor")
        self.resize(1440, 880)
        self._parser   = FLParser()
        self._sections : list[tuple[str, list]] = []
        self._objects  : list[SolarObject]      = []
        self._zones    : list[ZoneItem]         = []
        self._selected : SolarObject | None     = None
        self._scale    = 1.0
        self._filepath : str | None             = None
        self._dirty    = False
        self._ed_busy  = False
        self._build_ui()

    # ── UI aufbauen ──────────────────────────────────────────────────
    def _build_ui(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        for lbl, key, slot in [
            ("📂 Öffnen", "Ctrl+O", self._open),
            ("🔍 Alles",  "Ctrl+F", self._fit),
        ]:
            a = QAction(lbl, self); a.setShortcut(key); a.triggered.connect(slot)
            tb.addAction(a)

        tb.addSeparator()

        # ── Move-Modus  (toggled → bool, kein Enum-Vergleich nötig) ──
        self.move_cb = QCheckBox("✋  Move-Modus")
        self.move_cb.setToolTip("Aktiviert das Verschieben von Objekten per Maus")
        self.move_cb.toggled.connect(self._toggle_move)   # ← toggled statt stateChanged
        tb.addWidget(self.move_cb)

        tb.addSeparator()

        self.zone_cb = QCheckBox("🗺  Zonen")
        self.zone_cb.setChecked(True)
        self.zone_cb.toggled.connect(self._toggle_zones)
        tb.addWidget(self.zone_cb)

        # ── Splitter ────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        self.view = SystemView()
        self.view.object_selected.connect(self._select)
        splitter.addWidget(self.view)

        panel = QWidget()
        pl    = QVBoxLayout(panel)
        pl.setContentsMargins(6, 6, 6, 6)

        self.name_lbl = QLabel("Kein Objekt ausgewählt")
        self.name_lbl.setStyleSheet("font-weight:bold; font-size:12pt;")
        pl.addWidget(self.name_lbl)

        g  = QGroupBox("INI-Eigenschaften")
        gl = QVBoxLayout(g)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Monospace", 10))
        self.editor.setPlaceholderText("Klicke auf ein Objekt …")
        gl.addWidget(self.editor)

        # Button 1: Änderungen in Objekt-Daten übernehmen (in Memory)
        self.apply_btn = QPushButton("✔  Objekt-Änderungen übernehmen")
        self.apply_btn.setToolTip("Schreibt den Texteditor-Inhalt ins Objekt (nur im Speicher).")
        self.apply_btn.clicked.connect(self._apply)
        self.apply_btn.setEnabled(False)
        gl.addWidget(self.apply_btn)

        # Button 2: Alles in Original-Datei schreiben + Ansicht neu laden
        self.write_btn = QPushButton("💾  Änderungen in Datei schreiben")
        self.write_btn.setToolTip(
            "Schreibt ALLE Änderungen in die Original-INI (via temp-Datei)\n"
            "und lädt die Ansicht anschließend neu.")
        self.write_btn.setStyleSheet(
            "QPushButton { background:#1a3a1a; border:1px solid #2a5a2a; }"
            "QPushButton:hover    { background:#245a24; }"
            "QPushButton:disabled { color:#445; background:#111; border-color:#333; }")
        self.write_btn.clicked.connect(self._write_to_file)
        self.write_btn.setEnabled(False)
        gl.addWidget(self.write_btn)

        pl.addWidget(g)

        # Legende
        legend = QGroupBox("Legende")
        ll = QVBoxLayout(legend)
        for col, txt in [
            ("#ffd728", "☀  Stern / Sonne"),
            ("#3c82dc", "🪐  Planet"),
            ("#50d264", "🏠  Basis / Station"),
            ("#d25ad2", "⭕  Jumpgate / -hole"),
            ("#966e46", "☄  Asteroidenfeld"),
            ("#bebebe", "◉  Sonstiges"),
            ("",        ""),
            ("#dc3232", "─  Zone Death/Damage"),
            ("#9650dc", "─  Zone Nebula"),
            ("#b4823c", "─  Zone Debris/Asteroids"),
            ("#3cb4dc", "--  Zone Tradelane"),
            ("#50a0c8", "─  Zone Sonstiges"),
        ]:
            if not col:
                ll.addSpacing(4); continue
            lbl = QLabel(f'<span style="color:{col}">■</span>  {txt}')
            lbl.setTextFormat(Qt.RichText)
            ll.addWidget(lbl)
        pl.addWidget(legend)

        self.info_lbl = QLabel("Keine Datei geladen.")
        self.info_lbl.setWordWrap(True)
        pl.addWidget(self.info_lbl)
        pl.addStretch()

        splitter.addWidget(panel)
        splitter.setSizes([1050, 380])
        self.setCentralWidget(splitter)
        self.statusBar().showMessage("Bereit — INI-Datei öffnen")

        self.setStyleSheet("""
            * { background:#12122a; color:#dde; }
            QGroupBox { border:1px solid #334; margin-top:10px;
                        padding:5px; border-radius:4px; }
            QGroupBox::title { color:#99aaff; }
            QPushButton { background:#1e1e50; border:1px solid #446;
                          padding:4px 8px; border-radius:3px; }
            QPushButton:hover    { background:#2a2a70; }
            QPushButton:disabled { color:#445; }
            QTextEdit   { background:#08080f; border:1px solid #334; }
            QToolBar    { background:#0e0e28; border-bottom:1px solid #334;
                          spacing:4px; padding:2px; }
            QStatusBar  { background:#0e0e28; color:#99aaff; }
            QSplitter::handle { background:#224; width:3px; }
            QCheckBox   { color:#dde; spacing:5px; }
            QCheckBox::indicator { width:14px; height:14px;
                                   border:1px solid #556; border-radius:2px;
                                   background:#1e1e50; }
            QCheckBox::indicator:checked { background:#5060c0; }
        """)

    # ── Öffnen ───────────────────────────────────────────────────────
    def _open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Freelancer INI öffnen", "", "INI (*.ini);;Alle (*)")
        if path:
            self._filepath = path
            self._load(path)

    # ── Laden  (optional: Transform nach Reload wiederherstellen) ────
    def _load(self, path: str, restore: QTransform | None = None):
        self._sections = self._parser.parse(path)
        raw_objs  = self._parser.get_objects(self._sections)
        raw_zones = self._parser.get_zones(self._sections)

        coords = []
        for d in raw_objs + raw_zones:
            pp = [float(c.strip()) for c in d.get("pos", "0,0,0").split(",")]
            if len(pp) > 0: coords.append(abs(pp[0]))
            if len(pp) > 2: coords.append(abs(pp[2]))
        self._scale = 500.0 / (max(coords, default=1) or 1)

        self.view._scene.clear()
        self._objects, self._zones = [], []
        self._selected = None
        self.apply_btn.setEnabled(False)
        self.name_lbl.setText("Kein Objekt ausgewählt")
        self.editor.clear()

        # Zonen zuerst (z=-1, hinter Objekten)
        for zd in raw_zones:
            try:
                zi = ZoneItem(zd, self._scale)
                self.view._scene.addItem(zi)
                self._zones.append(zi)
            except Exception:
                pass

        # Objekte (z=1)
        move_on = self.move_cb.isChecked()
        for od in raw_objs:
            try:
                obj = SolarObject(od, self._scale)
                obj.setFlag(QGraphicsItem.ItemIsMovable, move_on)
                self.view._scene.addItem(obj)
                self._objects.append(obj)
            except Exception:
                pass

        # Zonen-Checkbox-Zustand anwenden
        if not self.zone_cb.isChecked():
            for z in self._zones:
                z.setVisible(False)

        self.info_lbl.setText(
            f"📄 {Path(path).name}\n"
            f"Objekte: {len(self._objects)}\n"
            f"Zonen:   {len(self._zones)}")
        self.setWindowTitle(f"Freelancer System Editor — {Path(path).name}")
        self.statusBar().showMessage(
            f"✔  {len(self._objects)} Objekte · {len(self._zones)} Zonen geladen")
        self._set_dirty(False)

        if restore:
            self.view.setTransform(restore)
        else:
            self._fit()

    # ── Objekt auswählen ─────────────────────────────────────────────
    def _select(self, obj: SolarObject):
        if self._selected:
            self._selected._pos_change_cb = None
            p = self._selected.pen()
            p.setColor(QColor(255, 255, 255, 70)); p.setWidth(1)
            self._selected.setPen(p)

        self._selected = obj
        p = obj.pen()
        p.setColor(QColor(255, 200, 0)); p.setWidth(2)
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

    # ── Button 1: Texteditor → Objekt-Daten (nur Memory) ────────────
    def _apply(self):
        if not self._selected:
            return
        self._selected.apply_text(self.editor.toPlainText())
        self.name_lbl.setText(f"📍 {self._selected.nickname}")
        self._set_dirty(True)
        self.statusBar().showMessage(
            f"✔  '{self._selected.nickname}' übernommen  "
            f"(noch nicht in Datei geschrieben)")

    # ── Button 2: In Datei schreiben (via .tmp) + Ansicht neu laden ──
    def _write_to_file(self):
        if not self._filepath:
            return

        # Noch offene Texteditor-Änderungen zuerst übernehmen
        if self._selected:
            self._selected.apply_text(self.editor.toPlainText())

        # Szenen-Positionen → pos-Einträge aller Objekte aktualisieren
        for obj in self._objects:
            new_pos = obj.fl_pos_str()
            obj.data["_entries"] = [
                (k, new_pos if k.lower() == "pos" else v)
                for k, v in obj.data["_entries"]
            ]

        # INI-Text rekonstruieren
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

        # Erst in .tmp schreiben, dann umbenennen (atomar)
        tmp = self._filepath + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            shutil.move(tmp, self._filepath)
        except Exception as ex:
            QMessageBox.critical(self, "Fehler beim Speichern", str(ex))
            return

        self.statusBar().showMessage(f"✔  Gespeichert: {self._filepath} — Ansicht wird neu geladen …")

        # Ansicht mit gleichem Zoom/Pan neu laden
        self._load(self._filepath, restore=self.view.transform())

    # ── Dirty-Flag ───────────────────────────────────────────────────
    def _set_dirty(self, d: bool):
        self._dirty = d
        self.write_btn.setEnabled(bool(self._filepath) and d)
        t = self.windowTitle()
        if d and not t.startswith("*"):
            self.setWindowTitle("* " + t)
        elif not d and t.startswith("* "):
            self.setWindowTitle(t[2:])

    # ── Move-Modus  (checked ist bereits bool – kein Enum-Problem) ───
    def _toggle_move(self, checked: bool):
        for obj in self._objects:
            obj.setFlag(QGraphicsItem.ItemIsMovable, checked)
        msg = "Move-Modus AN — Linke Maustaste zum Verschieben" if checked else "Move-Modus AUS"
        self.statusBar().showMessage(msg)

    def _toggle_zones(self, checked: bool):
        for z in self._zones:
            z.setVisible(checked)

    def _fit(self):
        r = self.view._scene.itemsBoundingRect()
        self.view.fitInView(r.adjusted(-80, -80, 80, 80), Qt.KeepAspectRatio)


# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
