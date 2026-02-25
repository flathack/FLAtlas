# main.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Dict, Tuple

from PySide6 import QtWidgets, QtCore, QtGui

from flpaths import make_paths, FLPaths, resolve_path_case_insensitive
from workspace import SystemDoc
from flini import IniBlock, parse_blocks
from view3d import System3DView
from assets_db import list_factions, list_loadouts, list_archetypes

SETTINGS_FILE = Path.home() / ".fle_like_settings.json"


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8", errors="ignore"))
    return {}


def save_settings(d: dict):
    SETTINGS_FILE.write_text(json.dumps(d, indent=2), encoding="utf-8", errors="ignore")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FLE-like (Prototype)")
        self.resize(1350, 820)

        self.settings = load_settings()
        self.fl: Optional[FLPaths] = None

        self.doc: Optional[SystemDoc] = None
        self.obj_index_by_id: Dict[str, int] = {}  # obj nickname -> block index

        self._build_ui()
        self._build_menu()

        # If we already have a saved path, load it
        inst = self.settings.get("freelancer_install")
        if inst:
            self.set_install(Path(inst))
        else:
            self.statusBar().showMessage("Freelancer-Pfad setzen über: Einstellungen → Freelancer-Pfad setzen…")

    # ---------- UI ----------
    def _build_ui(self):
        splitter = QtWidgets.QSplitter()
        self.setCentralWidget(splitter)

        # Left: stacked (Universe list / System editor)
        self.stack = QtWidgets.QStackedWidget()
        splitter.addWidget(self.stack)

        # Universe page
        uni_page = QtWidgets.QWidget()
        uni_lay = QtWidgets.QVBoxLayout(uni_page)

        top = QtWidgets.QHBoxLayout()
        self.lbl_install = QtWidgets.QLabel("Freelancer-Pfad: (nicht gesetzt)")
        self.btn_setpath = QtWidgets.QPushButton("Pfad setzen…")
        self.btn_setpath.clicked.connect(self.pick_install)
        self.btn_reload = QtWidgets.QPushButton("Universe neu laden")
        self.btn_reload.clicked.connect(self.load_universe_view)

        top.addWidget(self.lbl_install, 1)
        top.addWidget(self.btn_setpath)
        top.addWidget(self.btn_reload)
        uni_lay.addLayout(top)

        self.universe_list = QtWidgets.QListWidget()
        self.universe_list.itemDoubleClicked.connect(self.open_system_from_universe)
        uni_lay.addWidget(self.universe_list, 1)

        self.stack.addWidget(uni_page)

        # System page
        sys_page = QtWidgets.QWidget()
        sys_lay = QtWidgets.QVBoxLayout(sys_page)

        bar = QtWidgets.QHBoxLayout()
        self.btn_back = QtWidgets.QPushButton("← Universe")
        self.btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.chk_move = QtWidgets.QCheckBox("Move Modus")
        self.btn_save = QtWidgets.QPushButton("Änderungen schreiben")
        self.btn_save.clicked.connect(self.commit)

        self.chk_move.toggled.connect(self.on_move_mode)

        bar.addWidget(self.btn_back)
        bar.addWidget(self.chk_move)
        bar.addStretch(1)
        bar.addWidget(self.btn_save)
        sys_lay.addLayout(bar)

        self.system_view = System3DView(on_pick=self.on_pick_obj)
        sys_lay.addWidget(self.system_view, 1)

        self.stack.addWidget(sys_page)

        splitter.setStretchFactor(0, 3)

        # Right sidebar
        right = QtWidgets.QWidget()
        rlay = QtWidgets.QVBoxLayout(right)

        self.lbl_selected = QtWidgets.QLabel("Kein Objekt ausgewählt.")
        rlay.addWidget(self.lbl_selected)

        form = QtWidgets.QFormLayout()
        self.cmb_rep = QtWidgets.QComboBox()
        self.cmb_loadout = QtWidgets.QComboBox()
        self.cmb_arch = QtWidgets.QComboBox()
        self.cmb_rep.currentTextChanged.connect(lambda v: self.update_selected_kv("reputation", v))
        self.cmb_loadout.currentTextChanged.connect(lambda v: self.update_selected_kv("loadout", v))
        self.cmb_arch.currentTextChanged.connect(lambda v: self.update_selected_kv("archetype", v))
        form.addRow("Reputation", self.cmb_rep)
        form.addRow("Loadout", self.cmb_loadout)
        form.addRow("Archetype", self.cmb_arch)
        rlay.addLayout(form)

        rlay.addWidget(QtWidgets.QLabel("Zonen (nicht klickbar, Auswahl hier):"))
        self.cmb_zone = QtWidgets.QComboBox()
        self.cmb_zone.currentIndexChanged.connect(self.on_zone_select)
        rlay.addWidget(self.cmb_zone)

        self.ini_editor = QtWidgets.QPlainTextEdit()
        self.ini_editor.setPlaceholderText("INI-Block (Objekt oder Zone) erscheint hier…")
        rlay.addWidget(self.ini_editor, 1)

        splitter.addWidget(right)
        splitter.setStretchFactor(1, 2)

    def _build_menu(self):
        m = self.menuBar().addMenu("Einstellungen")

        act_set = QtGui.QAction("Freelancer-Pfad setzen…", self)
        act_set.triggered.connect(self.pick_install)
        m.addAction(act_set)

        act_reload = QtGui.QAction("Universe neu laden", self)
        act_reload.triggered.connect(self.load_universe_view)
        m.addAction(act_reload)

    # ---------- Actions ----------
    def on_move_mode(self, enabled: bool):
        self.system_view.set_move_mode(enabled)
        self.statusBar().showMessage("Move Modus aktiv" if enabled else "Move Modus aus")

    def pick_install(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Freelancer Installationsordner wählen (muss DATA/UNIVERSE/universe.ini enthalten)",
        )
        if not d:
            return

        p = Path(d)
        uni = p / "DATA" / "UNIVERSE" / "universe.ini"
        if not uni.exists():
            QtWidgets.QMessageBox.warning(
                self,
                "Pfad stimmt nicht",
                f"Ich finde keine universe.ini unter:\n{uni}\n\n"
                "Bitte wähle den Freelancer-Root-Ordner (dort wo der DATA-Ordner liegt).",
            )
            return

        self.settings["freelancer_install"] = str(p)
        save_settings(self.settings)

        self.set_install(p)
        self.load_universe_view()
        self.stack.setCurrentIndex(0)

    def set_install(self, install: Path):
        self.fl = make_paths(install)
        self.lbl_install.setText(f"Freelancer-Pfad: {install}")

        # Populate dropdowns (best-effort)
        try:
            self.cmb_rep.blockSignals(True)
            self.cmb_rep.clear()
            self.cmb_rep.addItems([""] + list_factions(self.fl.initialworld))
        finally:
            self.cmb_rep.blockSignals(False)

        try:
            self.cmb_loadout.blockSignals(True)
            self.cmb_loadout.clear()
            self.cmb_loadout.addItems([""] + list_loadouts(self.fl.loadouts))
        finally:
            self.cmb_loadout.blockSignals(False)

        try:
            self.cmb_arch.blockSignals(True)
            self.cmb_arch.clear()
            self.cmb_arch.addItems([""] + list_archetypes(self.fl.solararch))
        finally:
            self.cmb_arch.blockSignals(False)

        self.statusBar().showMessage("Freelancer-Pfad gesetzt. Universe kann geladen werden.")

    # ---------- Universe loading ----------
    def load_universe_view(self):
        if not self.fl:
            QtWidgets.QMessageBox.information(self, "Info", "Bitte zuerst den Freelancer-Pfad setzen.")
            return

        uni = self.fl.universe / "universe.ini"
        if not uni.exists():
            QtWidgets.QMessageBox.warning(self, "Fehler", f"universe.ini nicht gefunden:\n{uni}")
            return

        text = uni.read_text(encoding="utf-8", errors="ignore")
        _, blocks = parse_blocks(text)

        self.universe_list.clear()

        count = 0
        missing = 0
        for b in blocks:
            if b.name.lower() != "system":
                continue

            nick = b.get1("nickname") or "(no nickname)"
            rel = (b.get1("file") or "").strip()
            if not rel:
                continue

            # file paths in Freelancer INIs are usually Windows-style (backslashes)
            sys_ini = resolve_path_case_insensitive(self.fl.universe, rel)


            item = QtWidgets.QListWidgetItem(f"{nick}  →  {rel_norm}")
            item.setData(QtCore.Qt.UserRole, sys_ini)

            if not sys_ini.exists():
                item.setForeground(QtCore.Qt.gray)
                missing += 1

            self.universe_list.addItem(item)
            count += 1

        self.statusBar().showMessage(f"Universe geladen: {count} Systeme ({missing} fehlen auf Disk).")

    def open_system_from_universe(self, item: QtWidgets.QListWidgetItem):
        p: Path = item.data(QtCore.Qt.UserRole)
        if not p or not Path(p).exists():
            QtWidgets.QMessageBox.warning(self, "Fehler", f"System-INI nicht gefunden:\n{p}")
            return
        self.open_system(Path(p))

    # ---------- System loading ----------
    def open_system(self, system_ini: Path):
        self.doc = SystemDoc.load(system_ini)
        self.obj_index_by_id.clear()

        self.system_view.clear_scene()
        self.cmb_zone.blockSignals(True)
        self.cmb_zone.clear()
        self.cmb_zone.addItem("(keine)")
        self.cmb_zone.blockSignals(False)

        # Objects
        for bi, b in self.doc.get_object_blocks():
            nick = b.get1("nickname") or f"obj_{bi}"
            pos = b.get1("pos")
            if not pos:
                continue

            try:
                x, y, z = [float(t.strip()) for t in pos.split(",")]
            except Exception:
                continue

            arch = (b.get1("archetype") or "").strip()
            is_tl = arch.lower() == "trade_lane_ring"  # tradelanes as dot/no name

            self.obj_index_by_id[nick] = bi
            self.system_view.add_object(nick, (x, y, z), label=nick, is_tradelane=is_tl)

        # Zones (visual only, not clickable)
        zones = self.doc.get_zone_blocks()
        self.cmb_zone.blockSignals(True)
        for bi, b in zones:
            zn = b.get1("nickname") or f"zone_{bi}"
            self.cmb_zone.addItem(zn, (bi, zn))

            # MVP: render a sphere if pos + size/radius exist
            pos = b.get1("pos")
            rad = b.get1("size") or b.get1("radius")
            if pos and rad:
                try:
                    x, y, z = [float(t.strip()) for t in pos.split(",")]
                    r = float(rad.split(",")[0].strip())
                    self.system_view.add_zone_visual((x, y, z), radius=r)
                except Exception:
                    pass
        self.cmb_zone.blockSignals(False)

        self.stack.setCurrentIndex(1)
        self.statusBar().showMessage(f"System geladen: {system_ini}")

    # ---------- Picking / Sidebar ----------
    def on_pick_obj(self, pick):
        if not self.doc:
            return

        obj_id = pick.obj_id
        self.lbl_selected.setText(f"Ausgewählt: {obj_id}")

        bi = self.obj_index_by_id.get(obj_id)
        if bi is None:
            return

        block = self.doc.modified.get(bi, self.doc.blocks[bi])

        # show block text
        text = "\n".join([f"[{block.name}]"] + [f"{k} = {v}" for k, v in block.items])
        self.ini_editor.setPlainText(text)

        # sync dropdowns to current values
        def set_combo(cmb: QtWidgets.QComboBox, val: str):
            old = cmb.blockSignals(True)
            idx = cmb.findText(val)
            cmb.setCurrentIndex(idx if idx >= 0 else 0)
            cmb.blockSignals(old)

        set_combo(self.cmb_rep, block.get1("reputation") or "")
        set_combo(self.cmb_loadout, block.get1("loadout") or "")
        set_combo(self.cmb_arch, block.get1("archetype") or "")

    def update_selected_kv(self, key: str, value: str):
        if not self.doc:
            return

        sel_text = self.lbl_selected.text()
        if not sel_text.startswith("Ausgewählt: "):
            return
        sel = sel_text.replace("Ausgewählt: ", "").strip()

        bi = self.obj_index_by_id.get(sel)
        if bi is None:
            return

        block = self.doc.modified.get(bi, self.doc.blocks[bi])
        nb = IniBlock(block.name, block.start_line, block.end_line, list(block.items))

        if value:
            nb.set1(key, value)
            self.doc.update_block(bi, nb)
            self.on_pick_obj(type("P", (), {"obj_id": sel})())

    def on_zone_select(self, idx: int):
        if not self.doc:
            return
        if idx <= 0:
            return

        data = self.cmb_zone.itemData(idx)
        if not data:
            return
        bi, _zn = data

        block = self.doc.modified.get(bi, self.doc.blocks[bi])
        text = "\n".join([f"[{block.name}]"] + [f"{k} = {v}" for k, v in block.items])
        self.lbl_selected.setText(f"Zone: {block.get1('nickname') or bi}")
        self.ini_editor.setPlainText(text)

    # ---------- Save ----------
    def commit(self):
        if not self.doc:
            return
        if not self.doc.is_dirty():
            QtWidgets.QMessageBox.information(self, "Info", "Keine Änderungen.")
            return

        self.doc.commit_to_disk()
        QtWidgets.QMessageBox.information(self, "OK", "System-INI wurde geschrieben.")

        # reload current system to reflect disk (and clear dirty state in view)
        try:
            self.open_system(self.doc.path)
        except Exception:
            pass


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    w = MainWindow()
    w.show()
    app.exec()
