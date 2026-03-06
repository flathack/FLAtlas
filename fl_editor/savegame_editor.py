"""Savegame editor module for FL Atlas.

This module can be used from MainWindow integration and can also be started standalone.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGraphicsScene,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSizePolicy,
    QSpinBox,
    QDoubleSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from .i18n import tr
except Exception:  # pragma: no cover
    _this_dir = Path(__file__).resolve().parent
    _parent = str(_this_dir.parent)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)
    from fl_editor.i18n import tr  # type: ignore


def _resolve_map_view_cls():
    try:
        from .main_window import _SavegameKnownMapView
    except Exception:  # pragma: no cover
        _this_dir = Path(__file__).resolve().parent
        _parent = str(_this_dir.parent)
        if _parent not in sys.path:
            sys.path.insert(0, _parent)
        from fl_editor.main_window import _SavegameKnownMapView  # type: ignore
    return _SavegameKnownMapView


def open_savegame_editor(self):
    _SavegameKnownMapView = _resolve_map_view_cls()
    default_dir = self._default_savegame_editor_dir()
    default_game_path = self._default_savegame_editor_game_path()
    game_path = str(default_game_path or self._primary_game_path() or self._fallback_game_path() or "").strip()
    faction_labels = self._savegame_editor_load_faction_labels(game_path)
    templates = self._savegame_editor_collect_rep_templates(game_path)
    nickname_labels = self._savegame_editor_collect_nickname_labels(game_path)
    numeric_id_map = self._savegame_editor_collect_numeric_id_map(game_path)
    system_label_by_nick: dict[str, str] = {}
    system_to_bases: dict[str, list[dict[str, str]]] = {}
    if game_path:
        try:
            for row in self._npc_collect_bases(game_path):
                base_nick = str(row.get("nickname", "")).strip()
                base_disp = str(row.get("display", "")).strip() or base_nick
                sys_nick = str(row.get("system", "")).strip()
                if not base_nick or not sys_nick:
                    continue
                sys_name = self._system_display_name(sys_nick).strip() or sys_nick
                sys_label = f"{sys_nick} - {sys_name}" if sys_name.lower() != sys_nick.lower() else sys_nick
                system_label_by_nick[sys_nick] = sys_label
                system_to_bases.setdefault(sys_nick, []).append({"nickname": base_nick, "display": base_disp})
        except Exception:
            system_label_by_nick = {}
            system_to_bases = {}
    for sys_nick, rows in system_to_bases.items():
        rows.sort(key=lambda r: str(r.get("display", "")).lower())

    dlg = QDialog(self)
    dlg.resize(1120, 800)
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(10, 10, 10, 10)
    lay.setSpacing(8)
    menu_bar = QMenuBar(dlg)
    menu_bar.setNativeMenuBar(False)
    menu_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    menu_bar.setFixedHeight(28)
    menu_host = QWidget(dlg)
    menu_host_l = QHBoxLayout(menu_host)
    menu_host_l.setContentsMargins(0, 0, 0, 0)
    menu_host_l.setSpacing(0)
    menu_host_l.addWidget(menu_bar, 1)
    lay.addWidget(menu_host)
    file_menu = menu_bar.addMenu(tr("savegame_editor.menu.file"))
    settings_menu = menu_bar.addMenu(tr("savegame_editor.menu.settings"))

    def _set_editor_title(path: Path | None = None) -> None:
        base = tr("savegame_editor.title")
        if isinstance(path, Path):
            dlg.setWindowTitle(f"{base} -> {path.name}")
        else:
            dlg.setWindowTitle(base)

    _set_editor_title(None)

    save_dir_edit = QLineEdit(str(default_dir))
    game_path_edit = QLineEdit(game_path)

    select_row = QHBoxLayout()
    select_row.addWidget(QLabel(tr("savegame_editor.select")))
    savegame_cb = QComboBox(dlg)
    savegame_cb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    select_row.addWidget(savegame_cb, 1)
    lay.addLayout(select_row)

    actions_row = QHBoxLayout()
    actions_row.addStretch(1)
    refresh_btn = QPushButton(tr("savegame_editor.refresh_list"), dlg)
    actions_row.addWidget(refresh_btn)
    load_btn = QPushButton(tr("savegame_editor.load_selected"), dlg)
    actions_row.addWidget(load_btn)
    open_btn = QPushButton(tr("savegame_editor.open"), dlg)
    actions_row.addWidget(open_btn)

    reload_btn = QPushButton(tr("savegame_editor.reload"), dlg)
    actions_row.addWidget(reload_btn)
    lay.addLayout(actions_row)

    info_lbl = QLabel(tr("savegame_editor.no_file"))
    info_lbl.setWordWrap(True)
    lay.addWidget(info_lbl)
    load_progress = QProgressBar(dlg)
    load_progress.setVisible(False)
    lay.addWidget(load_progress)

    tabs = QTabWidget(dlg)
    tab_general = QWidget(dlg)
    tab_reputation = QWidget(dlg)
    tab_ship = QWidget(dlg)
    general_l = QVBoxLayout(tab_general)
    general_l.setContentsMargins(8, 8, 8, 8)
    general_l.setSpacing(8)
    rep_l = QVBoxLayout(tab_reputation)
    rep_l.setContentsMargins(8, 8, 8, 8)
    rep_l.setSpacing(8)
    ship_tab_l = QVBoxLayout(tab_ship)
    ship_tab_l.setContentsMargins(8, 8, 8, 8)
    ship_tab_l.setSpacing(8)
    tabs.addTab(tab_general, tr("savegame_editor.tab.general"))
    tabs.addTab(tab_reputation, tr("savegame_editor.tab.reputation"))
    tabs.addTab(tab_ship, tr("savegame_editor.tab.ship"))
    lay.addWidget(tabs, 1)

    form = QFormLayout()
    rank_spin = QSpinBox(dlg)
    rank_spin.setRange(0, 100)
    money_spin = QSpinBox(dlg)
    money_spin.setRange(0, 999_999_999)
    rep_group_cb = QComboBox(dlg)
    rep_group_cb.setEditable(True)
    for nick in sorted(self._cached_factions, key=str.lower):
        label = faction_labels.get(str(nick).strip().lower(), self._faction_ui_label(nick) or str(nick))
        rep_group_cb.addItem(label, str(nick))
    system_cb = QComboBox(dlg)
    system_cb.setEditable(True)
    for sys_nick in sorted(system_to_bases.keys(), key=lambda s: str(system_label_by_nick.get(s, s)).lower()):
        system_cb.addItem(system_label_by_nick.get(sys_nick, sys_nick), sys_nick)
    base_cb = QComboBox(dlg)
    base_cb.setEditable(True)
    form.addRow(tr("savegame_editor.rank"), rank_spin)
    form.addRow(tr("savegame_editor.money"), money_spin)
    form.addRow(tr("savegame_editor.rep_group"), rep_group_cb)
    form.addRow(tr("savegame_editor.system"), system_cb)
    form.addRow(tr("savegame_editor.base"), base_cb)
    story_lock_lbl = QLabel("", dlg)
    story_lock_lbl.setWordWrap(True)
    story_lock_lbl.setVisible(False)
    story_lock_lbl.setStyleSheet("color: #9aa0a6;")
    form.addRow("", story_lock_lbl)
    general_l.addLayout(form)
    ids_box = QGroupBox(tr("savegame_editor.ids_group"), dlg)
    ids_l = QVBoxLayout(ids_box)
    ids_l.setContentsMargins(8, 8, 8, 8)
    ids_l.setSpacing(6)
    map_tabs = QTabWidget(ids_box)
    locked_map_page = QWidget(ids_box)
    locked_map_l = QVBoxLayout(locked_map_page)
    locked_map_l.setContentsMargins(0, 0, 0, 0)
    locked_map_l.setSpacing(6)
    locked_scene = QGraphicsScene(ids_box)
    locked_view = _SavegameKnownMapView(locked_scene, ids_box)
    locked_view.setRenderHint(QPainter.Antialiasing, True)
    locked_view.setMinimumHeight(240)
    locked_view.setStyleSheet("QGraphicsView { border: 1px solid palette(mid); }")
    locked_map_l.addWidget(locked_view, 1)
    unlock_all_btn = QPushButton(tr("savegame_editor.unlock_all"), ids_box)
    locked_map_l.addWidget(unlock_all_btn, 0, Qt.AlignRight)
    visited_map_page = QWidget(ids_box)
    visited_map_l = QVBoxLayout(visited_map_page)
    visited_map_l.setContentsMargins(0, 0, 0, 0)
    visited_map_l.setSpacing(6)
    visited_scene = QGraphicsScene(ids_box)
    visited_view = _SavegameKnownMapView(visited_scene, ids_box)
    visited_view.setRenderHint(QPainter.Antialiasing, True)
    visited_view.setMinimumHeight(240)
    visited_view.setStyleSheet("QGraphicsView { border: 1px solid palette(mid); }")
    visited_map_l.addWidget(visited_view, 1)
    visit_unlock_all_btn = QPushButton(tr("savegame_editor.visit_unlock_all"), ids_box)
    visited_map_l.addWidget(visit_unlock_all_btn, 0, Qt.AlignRight)
    map_tabs.addTab(locked_map_page, tr("savegame_editor.map_tab.locked"))
    map_tabs.addTab(visited_map_page, tr("savegame_editor.map_tab.visited"))
    ids_l.addWidget(map_tabs, 1)
    general_l.addWidget(ids_box)

    tpl_row = QHBoxLayout()
    tpl_row.addWidget(QLabel(tr("savegame_editor.template")))
    template_cb = QComboBox(dlg)
    for tpl in templates:
        template_cb.addItem(str(tpl.get("name") or ""), tpl)
    template_cb.setEnabled(bool(templates))
    template_cb.setCurrentIndex(-1)
    tpl_row.addWidget(template_cb, 1)
    apply_template_btn = QPushButton(tr("savegame_editor.template_apply"), dlg)
    apply_template_btn.setEnabled(bool(templates))
    tpl_row.addWidget(apply_template_btn)
    rep_l.addLayout(tpl_row)

    item_data = self._savegame_editor_collect_item_data(game_path)
    item_name_map: dict[str, str] = dict(item_data.get("item_name_map", {}) or {})
    ship_nicks: list[str] = list(item_data.get("ship_nicks", []) or [])
    equip_nicks: list[str] = list(item_data.get("equip_nicks", []) or [])
    ship_hardpoints_by_nick: dict[str, list[str]] = {
        str(k): list(v) for k, v in dict(item_data.get("ship_hardpoints_by_nick", {}) or {}).items()
    }
    ship_hp_types_by_hardpoint_by_nick: dict[str, dict[str, list[str]]] = {
        str(k): {str(hk): list(hv) for hk, hv in dict(hmap).items()}
        for k, hmap in dict(item_data.get("ship_hp_types_by_hardpoint_by_nick", {}) or {}).items()
    }
    equip_type_by_nick: dict[str, str] = {
        str(k): str(v) for k, v in dict(item_data.get("equip_type_by_nick", {}) or {}).items()
    }
    equip_hp_types_by_nick: dict[str, list[str]] = {
        str(k): list(v) for k, v in dict(item_data.get("equip_hp_types_by_nick", {}) or {}).items()
    }
    hash_to_nick: dict[int, str] = {int(k): str(v) for k, v in dict(item_data.get("hash_to_nick", {}) or {}).items()}
    jump_data = self._savegame_editor_collect_jump_connections(game_path)

    ship_box = QGroupBox(tr("savegame_editor.ship_group"), dlg)
    ship_l = QVBoxLayout(ship_box)
    ship_l.setContentsMargins(8, 8, 8, 8)
    ship_l.setSpacing(6)
    ship_form = QFormLayout()
    ship_archetype_cb = QComboBox(dlg)
    ship_archetype_cb.setEditable(True)
    ship_form.addRow(tr("savegame_editor.ship_archetype"), ship_archetype_cb)
    ship_l.addLayout(ship_form)
    hardpoint_hint_lbl = QLabel("", dlg)
    hardpoint_hint_lbl.setWordWrap(True)
    ship_l.addWidget(hardpoint_hint_lbl)

    equip_lbl = QLabel(tr("savegame_editor.equip"), dlg)
    ship_l.addWidget(equip_lbl)
    equip_tbl = QTableWidget(0, 2, dlg)
    equip_tbl.setHorizontalHeaderLabels([tr("savegame_editor.col.item"), tr("savegame_editor.col.hardpoint")])
    eh = equip_tbl.horizontalHeader()
    eh.setSectionResizeMode(0, QHeaderView.Stretch)
    eh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
    equip_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
    equip_tbl.setSelectionMode(QAbstractItemView.SingleSelection)
    equip_tbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    ship_l.addWidget(equip_tbl, 1)
    equip_btn_row = QHBoxLayout()
    equip_add_btn = QPushButton(tr("savegame_editor.btn.add_equip"), dlg)
    equip_del_btn = QPushButton(tr("savegame_editor.btn.remove_selected"), dlg)
    equip_btn_row.addWidget(equip_add_btn)
    equip_btn_row.addWidget(equip_del_btn)
    equip_btn_row.addStretch(1)
    ship_l.addLayout(equip_btn_row)

    cargo_lbl = QLabel(tr("savegame_editor.cargo"), dlg)
    ship_l.addWidget(cargo_lbl)
    cargo_tbl = QTableWidget(0, 2, dlg)
    cargo_tbl.setHorizontalHeaderLabels([tr("savegame_editor.col.item"), tr("savegame_editor.col.amount")])
    ch = cargo_tbl.horizontalHeader()
    ch.setSectionResizeMode(0, QHeaderView.Stretch)
    ch.setSectionResizeMode(1, QHeaderView.ResizeToContents)
    cargo_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
    cargo_tbl.setSelectionMode(QAbstractItemView.SingleSelection)
    cargo_tbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    ship_l.addWidget(cargo_tbl, 1)
    cargo_btn_row = QHBoxLayout()
    cargo_add_btn = QPushButton(tr("savegame_editor.btn.add_cargo"), dlg)
    cargo_del_btn = QPushButton(tr("savegame_editor.btn.remove_selected"), dlg)
    cargo_btn_row.addWidget(cargo_add_btn)
    cargo_btn_row.addWidget(cargo_del_btn)
    cargo_btn_row.addStretch(1)
    ship_l.addLayout(cargo_btn_row)
    ship_tab_l.addWidget(ship_box, 1)

    houses_lbl = QLabel(tr("savegame_editor.houses"))
    rep_l.addWidget(houses_lbl)
    houses_tbl = QTableWidget(0, 3, dlg)
    houses_tbl.setHorizontalHeaderLabels(
        [tr("savegame_editor.col.faction"), tr("savegame_editor.col.rep"), tr("savegame_editor.col.slider")]
    )
    hh = houses_tbl.horizontalHeader()
    hh.setSectionResizeMode(0, QHeaderView.Stretch)
    hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
    hh.setSectionResizeMode(2, QHeaderView.Stretch)
    houses_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
    houses_tbl.setSelectionMode(QAbstractItemView.SingleSelection)
    rep_l.addWidget(houses_tbl, 1)

    bottom_row = QHBoxLayout()
    bottom_row.addStretch(1)
    save_btn = QPushButton(tr("savegame_editor.save"), dlg)
    close_btn = QPushButton(tr("dlg.close"), dlg)
    bottom_row.addWidget(save_btn)
    bottom_row.addWidget(close_btn)
    lay.addLayout(bottom_row)

    state: dict[str, object] = {
        "path": None,
        "updating_savegame_cb": False,
        "locked_ids": set(),
        "visit_ids": set(),
        "visit_line_by_id": {},
        "story_locked": False,
    }
    map_state: dict[str, object] = {"locked_ids": set(), "visit_ids": set()}

    def _set_loading(active: bool) -> None:
        load_progress.setVisible(active)
        if active:
            load_progress.setRange(0, 0)
            load_progress.setFormat(tr("savegame_editor.loading"))
        else:
            load_progress.setRange(0, 1)
            load_progress.setValue(0)
        QApplication.processEvents()

    def _save_dir() -> Path:
        txt = save_dir_edit.text().strip()
        if txt:
            return Path(txt)
        return default_dir

    def _fmt_rep(v: float) -> str:
        return f"{float(v):.6f}".rstrip("0").rstrip(".")

    def _resolve_item_nick(raw_nick: str) -> str:
        raw = str(raw_nick or "").strip()
        if not raw:
            return ""
        if raw.isdigit():
            try:
                hid = int(raw)
            except Exception:
                hid = 0
            if hid > 0:
                mapped = str(hash_to_nick.get(hid, "") or "").strip()
                if mapped:
                    return mapped
        return raw

    def _item_ui_label(nick: str) -> str:
        raw = _resolve_item_nick(str(nick or "").strip())
        if not raw:
            return ""
        if raw.isdigit():
            try:
                mapped = str(numeric_id_map.get(int(raw), "") or "").strip()
            except Exception:
                mapped = ""
            if mapped:
                raw = mapped
        disp = str(item_name_map.get(raw.lower(), "") or "").strip()
        if not disp:
            fac_disp = str(nickname_labels.get(raw.lower(), "") or "").strip()
            if " - " in fac_disp:
                disp = fac_disp.split(" - ", 1)[1].strip()
        if disp and disp.lower() != raw.lower():
            return f"{raw} - {disp}"
        return raw

    def _item_from_ui(raw: str) -> str:
        txt = str(raw or "").strip()
        if not txt:
            return ""
        if " - " in txt:
            return txt.split(" - ", 1)[0].strip()
        return txt

    def _setup_item_combo(cb: QComboBox, nicks: list[str]) -> None:
        cb.setEditable(True)
        for nick in nicks:
            cb.addItem(_item_ui_label(nick), nick)

    def _set_item_combo_value(cb: QComboBox, nick: str) -> None:
        val = _resolve_item_nick(str(nick or "").strip())
        if not val:
            cb.setCurrentText("")
            return
        idx = cb.findData(val)
        if idx >= 0:
            cb.setCurrentIndex(idx)
            return
        cb.addItem(_item_ui_label(val), val)
        cb.setCurrentIndex(cb.count() - 1)

    def _combo_item_nick(cb: QComboBox) -> str:
        data = str(cb.currentData() or "").strip()
        if data:
            return _resolve_item_nick(data)
        return _resolve_item_nick(_item_from_ui(cb.currentText()))

    def _item_token_for_save(nick: str) -> str:
        raw = _resolve_item_nick(str(nick or "").strip())
        if not raw:
            return ""
        hid = int(self._fl_hash_nickname(raw))
        if hid > 0:
            return str(hid)
        return raw

    def _current_ship_nick() -> str:
        return _combo_item_nick(ship_archetype_cb)

    def _ship_hardpoints(ship_nick: str) -> list[str]:
        return list(ship_hardpoints_by_nick.get(str(ship_nick or "").strip().lower(), []))

    def _equip_type(nick: str) -> str:
        return str(equip_type_by_nick.get(str(nick or "").strip().lower(), "") or "").strip().lower()

    def _equip_hp_types(nick: str) -> set[str]:
        vals = list(equip_hp_types_by_nick.get(str(nick or "").strip().lower(), []) or [])
        return {str(v).strip().lower() for v in vals if str(v).strip()}

    def _typed_filter_for_hardpoint(hardpoint: str, candidates: list[str]) -> list[str]:
        hp = str(hardpoint or "").strip().lower()
        if not hp:
            return list(candidates)
        out = list(candidates)
        if hp.startswith("hpshield"):
            out = [n for n in out if _equip_type(n) == "shieldgenerator"]
        elif hp.startswith("hpthruster"):
            out = [n for n in out if _equip_type(n) == "thruster"]
        elif hp.startswith("hpcountermeasure") or hp.startswith("hpcm"):
            out = [n for n in out if _equip_type(n) == "countermeasuredropper"]
        elif hp.startswith("hpmine"):
            out = [n for n in out if _equip_type(n) == "minedropper"]
        elif hp.startswith("hptorpedo"):
            out = [n for n in out if _equip_type(n) in {"gun", "cgun"}]
        return out

    def _ship_hp_types_for_hardpoint(ship_nick: str, hardpoint: str) -> set[str]:
        sn = str(ship_nick or "").strip().lower()
        hp = str(hardpoint or "").strip().lower()
        if not sn or not hp:
            return set()
        by_hp = dict(ship_hp_types_by_hardpoint_by_nick.get(sn, {}) or {})
        vals = list(by_hp.get(hp, []) or [])
        return {str(v).strip().lower() for v in vals if str(v).strip()}

    def _compatible_equip_nicks_for_hardpoint(hardpoint: str) -> list[str]:
        hp = str(hardpoint or "").strip().lower()
        if not hp:
            return list(equip_nicks)
        ship_types = _ship_hp_types_for_hardpoint(_current_ship_nick(), hp)
        if ship_types:
            by_type = []
            for n in equip_nicks:
                item_types = _equip_hp_types(n)
                if item_types and (item_types & ship_types):
                    by_type.append(n)
            by_type = _typed_filter_for_hardpoint(hp, by_type)
            if by_type:
                return by_type
        by_hpname = [n for n in equip_nicks if hp in _equip_hp_types(n)]
        by_hpname = _typed_filter_for_hardpoint(hp, by_hpname)
        if by_hpname:
            return by_hpname
        return _typed_filter_for_hardpoint(hp, list(equip_nicks))

    def _set_hardpoint_combo_value(cb: QComboBox, hardpoint: str) -> None:
        val = str(hardpoint or "").strip()
        if not val:
            idx_empty = cb.findData("")
            if idx_empty >= 0:
                cb.setCurrentIndex(idx_empty)
            else:
                cb.setCurrentIndex(-1)
                cb.setEditText("")
            return
        idx = cb.findData(val)
        if idx < 0:
            cb.addItem(val, val)
            idx = cb.count() - 1
        cb.setCurrentIndex(idx)

    def _hardpoint_from_widget(w: QWidget | None) -> str:
        if isinstance(w, QComboBox):
            return str(w.currentText() or "").strip()
        if isinstance(w, QLineEdit):
            return str(w.text() or "").strip()
        return ""

    def _table_row_for_widget(tbl: QTableWidget, w: QWidget | None, col: int) -> int:
        if w is None:
            return -1
        for r in range(tbl.rowCount()):
            if tbl.cellWidget(r, col) is w:
                return r
        return -1

    def _refresh_hardpoint_hint() -> None:
        ship_nick = _current_ship_nick()
        hp_all = _ship_hardpoints(ship_nick)
        if not hp_all:
            hardpoint_hint_lbl.setText(tr("savegame_editor.hardpoints_none"))
            return
        used: set[str] = set()
        for r in range(equip_tbl.rowCount()):
            hp = _hardpoint_from_widget(equip_tbl.cellWidget(r, 1))
            if hp:
                used.add(hp.lower())
        free = [hp for hp in hp_all if hp.lower() not in used]
        hardpoint_hint_lbl.setText(
            tr("savegame_editor.hardpoints_info").format(total=len(hp_all), used=len(used), free=max(0, len(free)))
            + " "
            + tr("savegame_editor.hardpoints_free_list").format(items=", ".join(free[:20]) if free else "-")
        )

    _setup_item_combo(ship_archetype_cb, ship_nicks)

    def _update_rep_color(spin: QDoubleSpinBox, value: float) -> None:
        if value < -0.61:
            spin.setStyleSheet("color: #d33f49; font-weight: 700;")
        elif value > 0.61:
            spin.setStyleSheet("color: #2f9e44; font-weight: 700;")
        else:
            spin.setStyleSheet("")

    def _insert_house_row(faction: str, rep: float) -> None:
        row = houses_tbl.rowCount()
        houses_tbl.insertRow(row)
        faction_nick = str(faction or "").strip()
        faction_label = faction_labels.get(faction_nick.lower(), self._faction_ui_label(faction_nick) or faction_nick)
        fac_item = QTableWidgetItem(faction_label)
        fac_item.setData(Qt.UserRole, faction_nick)
        fac_item.setFlags((fac_item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled) & ~Qt.ItemIsEditable)
        houses_tbl.setItem(row, 0, fac_item)

        rep_spin = QDoubleSpinBox(dlg)
        rep_spin.setDecimals(3)
        rep_spin.setRange(-1.0, 1.0)
        rep_spin.setSingleStep(0.01)
        rep_spin.setValue(float(rep))
        _update_rep_color(rep_spin, float(rep))
        houses_tbl.setCellWidget(row, 1, rep_spin)

        rep_slider = QSlider(Qt.Horizontal, dlg)
        rep_slider.setRange(-100, 100)
        rep_slider.setSingleStep(1)
        rep_slider.setPageStep(5)
        rep_slider.setValue(int(round(float(rep) * 100.0)))
        houses_tbl.setCellWidget(row, 2, rep_slider)

        sync = {"busy": False}

        def _from_spin(v: float) -> None:
            if sync["busy"]:
                return
            sync["busy"] = True
            rep_slider.setValue(int(round(v * 100.0)))
            _update_rep_color(rep_spin, float(v))
            sync["busy"] = False

        def _from_slider(v: int) -> None:
            if sync["busy"]:
                return
            sync["busy"] = True
            rep_val = float(v) / 100.0
            rep_spin.setValue(rep_val)
            _update_rep_color(rep_spin, rep_val)
            sync["busy"] = False

        rep_spin.valueChanged.connect(_from_spin)
        rep_slider.valueChanged.connect(_from_slider)

    def _set_houses(rows: list[tuple[str, float]]) -> None:
        houses_tbl.setRowCount(0)
        for faction, rep in rows:
            _insert_house_row(faction, rep)

    def _locked_gate_ids_from_lines(lines: list[str]) -> set[int]:
        out: set[int] = set()
        for raw_line in lines:
            line = str(raw_line or "")
            core = line.split(";", 1)[0].strip()
            if not core or "=" not in core:
                continue
            key, value = core.split("=", 1)
            k = str(key or "").strip().lower()
            if k not in {"locked_gate", "npc_locked_gate"}:
                continue
            first = str(value or "").split(",", 1)[0].strip()
            try:
                hid = int(first)
            except Exception:
                continue
            if hid > 0:
                out.add(int(hid))
        return out

    def _visit_ids_from_lines(lines: list[str]) -> set[int]:
        out: set[int] = set()
        for raw_line in lines:
            line = str(raw_line or "")
            core = line.split(";", 1)[0].strip()
            if not core or "=" not in core:
                continue
            key, value = core.split("=", 1)
            if str(key or "").strip().lower() != "visit":
                continue
            first = str(value or "").split(",", 1)[0].strip()
            try:
                hid = int(first)
            except Exception:
                continue
            if hid > 0:
                out.add(int(hid))
        return out

    def _visit_line_map_from_lines(lines: list[str]) -> dict[int, str]:
        out: dict[int, str] = {}
        for raw_line in lines:
            line = str(raw_line or "")
            core = line.split(";", 1)[0].strip()
            if not core or "=" not in core:
                continue
            key, value = core.split("=", 1)
            if str(key or "").strip().lower() != "visit":
                continue
            raw_v = str(value or "").strip()
            first = raw_v.split(",", 1)[0].strip()
            try:
                hid = int(first)
            except Exception:
                continue
            if hid > 0 and hid not in out:
                out[int(hid)] = raw_v
        return out

    def _render_known_objects_map(locked_ids: set[int]) -> None:
        locked_scene.clear()
        systems_obj = dict(jump_data.get("systems", {}) or {})
        edges = list(jump_data.get("edges", []) or [])
        if not systems_obj or not edges:
            locked_scene.addText(tr("savegame_editor.ids_none"))
            locked_view.set_base_rect(locked_scene.itemsBoundingRect().adjusted(-12, -12, 12, 12))
            return
        positions: dict[str, tuple[float, float]] = {}
        xs: list[float] = []
        ys: list[float] = []
        for key, row in systems_obj.items():
            x = float(row.get("x", 0.0) or 0.0)
            y = float(row.get("y", 0.0) or 0.0)
            positions[str(key).upper()] = (x, y)
            xs.append(x)
            ys.append(y)
        if not xs or not ys:
            locked_scene.addText(tr("savegame_editor.ids_none"))
            return
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        w = max(1.0, max_x - min_x)
        h = max(1.0, max_y - min_y)
        scale = min(900.0 / w, 520.0 / h)
        node_pos: dict[str, QPointF] = {}
        for key, (x, y) in positions.items():
            sx = (x - min_x) * scale
            sy = (y - min_y) * scale
            node_pos[key] = QPointF(sx, sy)

        locked_systems: set[str] = set()
        for edge in edges:
            ids = [int(v) for v in list(edge.get("ids", []) or []) if int(v) > 0]
            if any(i in locked_ids for i in ids):
                locked_systems.add(str(edge.get("a", "")).upper())
                locked_systems.add(str(edge.get("b", "")).upper())

        for edge in edges:
            a = str(edge.get("a", "")).upper()
            b = str(edge.get("b", "")).upper()
            if a not in node_pos or b not in node_pos:
                continue
            ids = [int(v) for v in list(edge.get("ids", []) or []) if int(v) > 0]
            is_locked = any(i in locked_ids for i in ids)
            typ = str(edge.get("type", "hole") or "hole").lower()
            if is_locked:
                col = QColor("#d33f49")
                width = 2.4
            else:
                col = QColor("#8a8a8a")
                width = 1.3
            pen = QPen(col, width)
            pen.setCosmetic(True)
            locked_scene.addLine(node_pos[a].x(), node_pos[a].y(), node_pos[b].x(), node_pos[b].y(), pen)

        for key, pt in node_pos.items():
            row = dict(systems_obj.get(key, {}) or {})
            nick = str(row.get("nickname", key) or key)
            disp = str(row.get("display", nick) or nick)
            r = 7.0 if key in locked_systems else 5.0
            fill = QColor("#d33f49") if key in locked_systems else QColor("#9aa0a6")
            pen = QPen(QColor("#202020"), 1.0)
            pen.setCosmetic(True)
            node = locked_scene.addEllipse(pt.x() - r, pt.y() - r, r * 2.0, r * 2.0, pen, QBrush(fill))
            node.setData(0, key)
            label = locked_scene.addText(disp)
            label.setDefaultTextColor(QColor("#ffd5d8") if key in locked_systems else QColor("#a7a7a7"))
            label.setPos(pt.x() + 8.0, pt.y() - 10.0)
            label.setData(0, key)

        rect = locked_scene.itemsBoundingRect().adjusted(-24, -24, 24, 24)
        locked_scene.setSceneRect(rect)
        locked_view.set_base_rect(rect)
        map_state["locked_ids"] = set(int(v) for v in locked_ids if int(v) > 0)

    def _render_visited_map(visit_ids: set[int]) -> None:
        visited_scene.clear()
        systems_obj = dict(jump_data.get("systems", {}) or {})
        edges = list(jump_data.get("edges", []) or [])
        if not systems_obj:
            visited_scene.addText(tr("savegame_editor.ids_none"))
            visited_view.set_base_rect(visited_scene.itemsBoundingRect().adjusted(-12, -12, 12, 12))
            return
        positions: dict[str, tuple[float, float]] = {}
        hash_by_sys: dict[str, int] = {}
        xs: list[float] = []
        ys: list[float] = []
        for key, row in systems_obj.items():
            x = float(row.get("x", 0.0) or 0.0)
            y = float(row.get("y", 0.0) or 0.0)
            sk = str(key).upper()
            positions[sk] = (x, y)
            nick = str(row.get("nickname", sk) or sk)
            hash_by_sys[sk] = int(self._fl_hash_nickname(nick))
            xs.append(x)
            ys.append(y)
        if not xs or not ys:
            visited_scene.addText(tr("savegame_editor.ids_none"))
            return
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        w = max(1.0, max_x - min_x)
        h = max(1.0, max_y - min_y)
        scale = min(900.0 / w, 520.0 / h)
        node_pos: dict[str, QPointF] = {}
        for key, (x, y) in positions.items():
            node_pos[key] = QPointF((x - min_x) * scale, (y - min_y) * scale)
        visited_systems: set[str] = {k for k, hv in hash_by_sys.items() if hv in visit_ids}
        for edge in edges:
            a = str(edge.get("a", "")).upper()
            b = str(edge.get("b", "")).upper()
            if a not in node_pos or b not in node_pos:
                continue
            edge_ids = [int(v) for v in list(edge.get("ids", []) or []) if int(v) > 0]
            edge_visited = any(v in visit_ids for v in edge_ids)
            if not edge_visited:
                edge_visited = (
                    hash_by_sys.get(a, 0) in visit_ids and hash_by_sys.get(b, 0) in visit_ids
                )
            if edge_visited:
                visited_systems.add(a)
                visited_systems.add(b)
            pen = QPen(QColor("#3c82dc") if edge_visited else QColor("#8a8a8a"), 2.0 if edge_visited else 1.2)
            pen.setCosmetic(True)
            visited_scene.addLine(node_pos[a].x(), node_pos[a].y(), node_pos[b].x(), node_pos[b].y(), pen)
        for key, pt in node_pos.items():
            row = dict(systems_obj.get(key, {}) or {})
            disp = str(row.get("display", key) or key)
            is_visited = key in visited_systems
            r = 7.0 if is_visited else 5.0
            fill = QColor("#2f9e44") if is_visited else QColor("#9aa0a6")
            pen = QPen(QColor("#202020"), 1.0)
            pen.setCosmetic(True)
            node = visited_scene.addEllipse(pt.x() - r, pt.y() - r, r * 2.0, r * 2.0, pen, QBrush(fill))
            node.setData(0, key)
            label = visited_scene.addText(disp)
            label.setDefaultTextColor(QColor("#d8d8d8") if is_visited else QColor("#a7a7a7"))
            label.setPos(pt.x() + 8.0, pt.y() - 10.0)
            label.setData(0, key)
        rect = visited_scene.itemsBoundingRect().adjusted(-24, -24, 24, 24)
        visited_scene.setSceneRect(rect)
        visited_view.set_base_rect(rect)
        map_state["visit_ids"] = set(int(v) for v in visit_ids if int(v) > 0)

    def _set_pending_locked_ids(locked_ids: set[int]) -> None:
        clean = set(int(v) for v in locked_ids if int(v) > 0)
        state["locked_ids"] = clean
        _render_known_objects_map(clean)

    def _set_pending_visit_ids(visit_ids: set[int]) -> None:
        clean = set(int(v) for v in visit_ids if int(v) > 0)
        state["visit_ids"] = clean
        _render_visited_map(clean)

    def _refresh_equip_row_filters(row: int) -> None:
        if row < 0 or row >= equip_tbl.rowCount():
            return
        item_cb = equip_tbl.cellWidget(row, 0)
        hp_cb = equip_tbl.cellWidget(row, 1)
        if not isinstance(item_cb, QComboBox) or not isinstance(hp_cb, QComboBox):
            return
        ship_hp_opts = _ship_hardpoints(_current_ship_nick())
        cur_item = _combo_item_nick(item_cb)
        cur_hp = _hardpoint_from_widget(hp_cb)
        hp_cb.blockSignals(True)
        hp_cb.clear()
        hp_cb.addItem("", "")
        for hp in ship_hp_opts:
            hp_cb.addItem(hp, hp)
        _set_hardpoint_combo_value(hp_cb, cur_hp)
        hp_cb.blockSignals(False)
        selected_hp = _hardpoint_from_widget(hp_cb)
        opts = _compatible_equip_nicks_for_hardpoint(selected_hp)
        item_cb.blockSignals(True)
        item_cb.clear()
        _setup_item_combo(item_cb, opts)
        if cur_item:
            _set_item_combo_value(item_cb, cur_item)
        else:
            item_cb.setCurrentIndex(-1)
            item_cb.setEditText("")
        item_cb.blockSignals(False)

    def _refresh_equip_row_filters_for_widget(w: QWidget | None) -> None:
        row = _table_row_for_widget(equip_tbl, w, 0)
        if row >= 0:
            _refresh_equip_row_filters(row)
            _refresh_hardpoint_hint()

    def _refresh_equip_row_filters_for_hp_widget(w: QWidget | None) -> None:
        row = _table_row_for_widget(equip_tbl, w, 1)
        if row >= 0:
            _refresh_equip_row_filters(row)
            _refresh_hardpoint_hint()

    def _add_equip_row(item_nick: str = "", hardpoint: str = "", extra: str = "") -> None:
        row = equip_tbl.rowCount()
        equip_tbl.insertRow(row)
        item_cb = QComboBox(dlg)
        _setup_item_combo(item_cb, equip_nicks)
        item_cb.setProperty("fl_extra", str(extra or "").strip())
        equip_tbl.setCellWidget(row, 0, item_cb)
        hp_cb = QComboBox(dlg)
        hp_cb.setEditable(False)
        hp_cb.addItem("", "")
        for hp in _ship_hardpoints(_current_ship_nick()):
            hp_cb.addItem(hp, hp)
        equip_tbl.setCellWidget(row, 1, hp_cb)
        if hardpoint:
            _set_hardpoint_combo_value(hp_cb, hardpoint)
        hp_cb.currentIndexChanged.connect(lambda _idx, w=hp_cb: _refresh_equip_row_filters_for_hp_widget(w))
        hp_cb.currentTextChanged.connect(lambda _txt, w=hp_cb: _refresh_equip_row_filters_for_hp_widget(w))
        _refresh_equip_row_filters(row)
        if item_nick:
            _set_item_combo_value(item_cb, item_nick)
            _refresh_equip_row_filters(row)
        _refresh_hardpoint_hint()

    def _add_cargo_row(item_nick: str = "", amount: int = 1, extra: str = ", , 0") -> None:
        row = cargo_tbl.rowCount()
        cargo_tbl.insertRow(row)
        item_cb = QComboBox(dlg)
        _setup_item_combo(item_cb, equip_nicks)
        _set_item_combo_value(item_cb, item_nick)
        item_cb.setProperty("fl_extra", str(extra or "").strip())
        cargo_tbl.setCellWidget(row, 0, item_cb)
        amt_spin = QSpinBox(dlg)
        amt_spin.setRange(0, 1_000_000)
        amt_spin.setValue(max(0, int(amount)))
        cargo_tbl.setCellWidget(row, 1, amt_spin)

    def _equip_rows() -> list[tuple[str, str, str]]:
        out: list[tuple[str, str, str]] = []
        for r in range(equip_tbl.rowCount()):
            item_cb = equip_tbl.cellWidget(r, 0)
            hp_w = equip_tbl.cellWidget(r, 1)
            if not isinstance(item_cb, QComboBox):
                continue
            nick = _combo_item_nick(item_cb)
            if not nick:
                continue
            hp = _hardpoint_from_widget(hp_w)
            extra = str(item_cb.property("fl_extra") or "").strip()
            out.append((nick, hp, extra))
        return out

    def _cargo_rows() -> list[tuple[str, int, str]]:
        out: list[tuple[str, int, str]] = []
        for r in range(cargo_tbl.rowCount()):
            item_cb = cargo_tbl.cellWidget(r, 0)
            amt_spin = cargo_tbl.cellWidget(r, 1)
            if not isinstance(item_cb, QComboBox):
                continue
            nick = _combo_item_nick(item_cb)
            if not nick:
                continue
            amount = int(amt_spin.value()) if isinstance(amt_spin, QSpinBox) else 0
            extra = str(item_cb.property("fl_extra") or "").strip()
            out.append((nick, amount, extra))
        return out

    def _refresh_equip_hardpoint_choices() -> None:
        for r in range(equip_tbl.rowCount()):
            _refresh_equip_row_filters(r)
        _refresh_hardpoint_hint()

    def _current_system_nick() -> str:
        data = str(system_cb.currentData() or "").strip()
        if data:
            return data
        txt = str(system_cb.currentText() or "").strip()
        if " - " in txt:
            txt = txt.split(" - ", 1)[0].strip()
        return txt

    def _current_base_nick() -> str:
        data = str(base_cb.currentData() or "").strip()
        if data:
            return data
        txt = str(base_cb.currentText() or "").strip()
        m = re.match(r"^.*\(([^()]+)\)\s*$", txt)
        if m:
            inner = m.group(1).strip()
            if inner:
                return inner
        return txt

    def _set_story_lock_ui(active: bool, mission_num: int = 0) -> None:
        locked = bool(active)
        state["story_locked"] = locked
        system_cb.setEnabled(not locked)
        base_cb.setEnabled(not locked)
        if locked:
            story_lock_lbl.setText(
                f"Story mission detected (MissionNum = {int(mission_num)}). "
                "System/Base editing is locked for this savegame."
            )
            story_lock_lbl.setVisible(True)
        else:
            story_lock_lbl.setText("")
            story_lock_lbl.setVisible(False)

    def _ensure_system_item(system_nick: str) -> None:
        sys_nick = str(system_nick or "").strip()
        if not sys_nick:
            return
        idx = system_cb.findData(sys_nick)
        if idx >= 0:
            system_cb.setCurrentIndex(idx)
            return
        sys_name = self._system_display_name(sys_nick).strip() or sys_nick
        sys_label = f"{sys_nick} - {sys_name}" if sys_name.lower() != sys_nick.lower() else sys_nick
        system_cb.addItem(sys_label, sys_nick)
        system_cb.setCurrentIndex(system_cb.count() - 1)

    def _rebuild_base_combo(system_nick: str, preferred_base: str = "") -> None:
        pref = str(preferred_base or "").strip()
        base_cb.blockSignals(True)
        base_cb.clear()
        for row in system_to_bases.get(str(system_nick or "").strip(), []):
            bnick = str(row.get("nickname", "")).strip()
            bdisp = str(row.get("display", "")).strip() or bnick
            if not bnick:
                continue
            label = f"{bdisp} ({bnick})" if bdisp.lower() != bnick.lower() else bnick
            base_cb.addItem(label, bnick)
        if pref:
            idx = base_cb.findData(pref)
            if idx >= 0:
                base_cb.setCurrentIndex(idx)
            else:
                base_cb.addItem(pref, pref)
                base_cb.setCurrentIndex(base_cb.count() - 1)
        elif base_cb.count() > 0:
            base_cb.setCurrentIndex(0)
        base_cb.blockSignals(False)

    def _set_rep_group_value(rep_group: str) -> None:
        rep = str(rep_group or "").strip()
        if not rep:
            rep_group_cb.setCurrentText("")
            return
        idx = rep_group_cb.findData(rep)
        if idx >= 0:
            rep_group_cb.setCurrentIndex(idx)
            return
        label = faction_labels.get(rep.lower(), self._faction_ui_label(rep) or rep)
        rep_group_cb.addItem(label, rep)
        rep_group_cb.setCurrentIndex(rep_group_cb.count() - 1)

    def _current_rep_group_nick() -> str:
        data = str(rep_group_cb.currentData() or "").strip()
        if data:
            return data
        raw = str(rep_group_cb.currentText() or "").strip()
        return self._faction_from_ui(raw) or raw

    def _current_houses() -> list[tuple[str, float]]:
        out: list[tuple[str, float]] = []
        for r in range(houses_tbl.rowCount()):
            item = houses_tbl.item(r, 0)
            if item is None:
                continue
            faction = str(item.data(Qt.UserRole) or "").strip()
            spin = houses_tbl.cellWidget(r, 1)
            if not faction or not isinstance(spin, QDoubleSpinBox):
                continue
            out.append((faction, float(spin.value())))
        return out

    def _parse_savegame(path: Path) -> tuple[bool, str]:
        try:
            raw = self._read_text_best_effort(path)
        except Exception as exc:
            return False, str(exc)
        lines = raw.splitlines()
        bounds = self._find_ini_section_bounds(lines, "Player", None)
        if bounds is None:
            return False, tr("savegame_editor.player_missing")
        s, e = bounds
        player_lines = lines[s:e]

        rank = 0
        money = 0
        rep_group = ""
        system = ""
        base = ""
        ship_archetype = ""
        equip_rows: list[tuple[str, str, str]] = []
        cargo_rows: list[tuple[str, int, str]] = []
        houses: list[tuple[str, float]] = []
        for raw_line in player_lines[1:]:
            line = str(raw_line).strip()
            if not line or line.startswith(";") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            k = key.strip().lower()
            v = val.strip()
            if k == "rank":
                try:
                    rank = int(float(v))
                except Exception:
                    rank = 0
            elif k == "money":
                try:
                    money = int(float(v))
                except Exception:
                    money = 0
            elif k == "rep_group":
                rep_group = v
            elif k == "system":
                system = v
            elif k == "base":
                base = v
            elif k == "ship_archetype":
                ship_archetype = v
            elif k == "equip":
                parts = [x.strip() for x in v.split(",")]
                if parts and parts[0]:
                    hardpoint = parts[1] if len(parts) > 1 else ""
                    if hardpoint and re.match(r"^[+-]?\d+(\.\d+)?$", hardpoint):
                        hardpoint = ""
                    extra = ", ".join(parts[2:]).strip() if len(parts) > 2 else "1"
                    equip_rows.append((parts[0], hardpoint, extra))
            elif k == "cargo":
                parts = [x.strip() for x in v.split(",")]
                if not parts or not parts[0]:
                    continue
                amount = 0
                for p in parts[1:]:
                    if not p:
                        continue
                    try:
                        amount = int(float(p))
                        break
                    except Exception:
                        continue
                extra = ", ".join(parts[2:]).strip() if len(parts) > 2 else ", , 0"
                cargo_rows.append((parts[0], amount, extra))
            elif k == "house":
                parts = [x.strip() for x in v.split(",", 1)]
                if len(parts) < 2:
                    continue
                try:
                    rep = float(parts[0])
                except Exception:
                    continue
                faction = parts[1]
                if faction:
                    houses.append((faction, rep))

        rank_spin.setValue(max(rank_spin.minimum(), min(rank_spin.maximum(), rank)))
        money_spin.setValue(max(money_spin.minimum(), min(money_spin.maximum(), money)))
        _set_rep_group_value(rep_group)
        _set_item_combo_value(ship_archetype_cb, ship_archetype)
        equip_tbl.setRowCount(0)
        for item_nick, hp, extra in equip_rows:
            _add_equip_row(item_nick, hp, extra)
        cargo_tbl.setRowCount(0)
        for item_nick, amount, extra in cargo_rows:
            _add_cargo_row(item_nick, amount, extra)
        _ensure_system_item(system)
        _rebuild_base_combo(system, preferred_base=base)
        houses.sort(key=lambda x: x[0].lower())
        _set_houses(houses)
        locked_ids = _locked_gate_ids_from_lines(player_lines)
        visit_ids = _visit_ids_from_lines(player_lines)
        state["locked_ids"] = set(locked_ids)
        state["visit_ids"] = set(visit_ids)
        state["visit_line_by_id"] = _visit_line_map_from_lines(player_lines)
        _set_pending_locked_ids(set(locked_ids))
        _set_pending_visit_ids(set(visit_ids))
        story_mission_num = 0
        story_bounds = self._find_ini_section_bounds(lines, "StoryInfo", None)
        if story_bounds is not None:
            ss, se = story_bounds
            for ln in lines[ss + 1:se]:
                core = str(ln or "").split(";", 1)[0].strip()
                if not core or "=" not in core:
                    continue
                k, v = core.split("=", 1)
                if str(k or "").strip().lower() != "missionnum":
                    continue
                try:
                    story_mission_num = int(float(str(v or "").strip()))
                except Exception:
                    story_mission_num = 0
                break
        _set_story_lock_ui(1 <= int(story_mission_num) <= 12, story_mission_num)
        _set_editor_title(path)
        info_lbl.setText(tr("savegame_editor.loaded").format(file=path.name, count=len(locked_ids)))
        state["path"] = path
        return True, ""

    def _parse_with_loading(path: Path) -> tuple[bool, str]:
        _set_loading(True)
        try:
            return _parse_savegame(path)
        finally:
            _set_loading(False)

    def _decode_savegame_player_name(raw_name: str) -> str:
        txt = str(raw_name or "").strip()
        if not txt:
            return ""
        if re.fullmatch(r"[0-9A-Fa-f]+", txt) and len(txt) % 2 == 0:
            try:
                blob = bytes.fromhex(txt)
            except Exception:
                blob = b""
            if blob:
                for enc in ("utf-16-be", "utf-16-le", "utf-8", "cp1252", "latin1"):
                    try:
                        val = blob.decode(enc, errors="ignore").replace("\x00", "").strip()
                    except Exception:
                        val = ""
                    if val:
                        return val
        return txt

    def _read_savegame_player_name(path: Path) -> str:
        try:
            raw = self._read_text_best_effort(path)
        except Exception:
            return ""
        lines = raw.splitlines()
        bounds = self._find_ini_section_bounds(lines, "Player", None)
        if bounds is None:
            return ""
        s, e = bounds
        player_values: dict[str, str] = {}
        for raw_line in lines[s + 1:e]:
            line = str(raw_line or "").strip()
            if not line or line.startswith(";") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            k = str(key or "").strip().lower()
            if not k:
                continue
            if k not in player_values:
                player_values[k] = str(val or "").strip()
        if str(player_values.get("description", "")).strip():
            return _decode_savegame_player_name(str(player_values.get("description", "")))
        if str(player_values.get("name", "")).strip():
            return _decode_savegame_player_name(str(player_values.get("name", "")))
        return ""

    def _refresh_savegame_list(*, select_path: Path | None = None, auto_load: bool = False) -> None:
        save_dir = _save_dir()
        files: list[Path] = []
        if save_dir.exists() and save_dir.is_dir():
            try:
                files = sorted(
                    [p for p in save_dir.iterdir() if p.is_file() and p.suffix.lower() == ".fl"],
                    key=lambda p: p.name.lower(),
                )
            except Exception:
                files = []
        state["updating_savegame_cb"] = True
        savegame_cb.clear()
        for fp in files:
            ingame_name = _read_savegame_player_name(fp)
            label = f"{fp.name} - {ingame_name}" if ingame_name else fp.name
            savegame_cb.addItem(label, str(fp))
        state["updating_savegame_cb"] = False
        if not files:
            savegame_cb.setCurrentIndex(-1)
            _set_story_lock_ui(False, 0)
            return
        target = None
        if select_path is not None:
            target = str(select_path)
        elif isinstance(state.get("path"), Path):
            target = str(state.get("path"))
        selected = False
        if target:
            idx = savegame_cb.findData(target)
            if idx >= 0:
                savegame_cb.setCurrentIndex(idx)
                selected = True
        if not selected:
            savegame_cb.setCurrentIndex(-1)
        if auto_load and savegame_cb.currentIndex() >= 0:
            _load_selected()

    def _load_selected() -> None:
        chosen = str(savegame_cb.currentData() or "").strip()
        if not chosen:
            return
        ok, msg = _parse_with_loading(Path(chosen))
        if not ok:
            QMessageBox.warning(dlg, tr("savegame_editor.title"), msg)

    def _apply_save_dir() -> None:
        path = _save_dir()
        self._cfg.set("settings.savegame_path", str(path))
        if hasattr(self, "gs_savegame_path_edit"):
            self.gs_savegame_path_edit.setText(str(path))
        self.statusBar().showMessage(tr("savegame_editor.path_saved").format(path=str(path)))
        _refresh_savegame_list(auto_load=False)

    def _apply_game_path() -> None:
        nonlocal game_path, faction_labels, templates, nickname_labels, numeric_id_map
        nonlocal item_name_map, ship_nicks, equip_nicks, ship_hardpoints_by_nick
        nonlocal ship_hp_types_by_hardpoint_by_nick
        nonlocal equip_type_by_nick, equip_hp_types_by_nick, hash_to_nick
        nonlocal jump_data, system_label_by_nick, system_to_bases
        game_path = str(game_path_edit.text() or "").strip()
        self._cfg.set("settings.savegame_game_path", game_path)
        if hasattr(self, "gs_savegame_game_path_edit"):
            self.gs_savegame_game_path_edit.setText(game_path)
        faction_labels = self._savegame_editor_load_faction_labels(game_path)
        templates = self._savegame_editor_collect_rep_templates(game_path)
        nickname_labels = self._savegame_editor_collect_nickname_labels(game_path)
        numeric_id_map = self._savegame_editor_collect_numeric_id_map(game_path)
        system_label_by_nick = {}
        system_to_bases = {}
        if game_path:
            try:
                for row in self._npc_collect_bases(game_path):
                    base_nick = str(row.get("nickname", "")).strip()
                    base_disp = str(row.get("display", "")).strip() or base_nick
                    sys_nick = str(row.get("system", "")).strip()
                    if not base_nick or not sys_nick:
                        continue
                    sys_name = self._system_display_name(sys_nick).strip() or sys_nick
                    sys_label = f"{sys_nick} - {sys_name}" if sys_name.lower() != sys_nick.lower() else sys_nick
                    system_label_by_nick[sys_nick] = sys_label
                    system_to_bases.setdefault(sys_nick, []).append({"nickname": base_nick, "display": base_disp})
            except Exception:
                system_label_by_nick = {}
                system_to_bases = {}
        for sys_nick, rows in system_to_bases.items():
            rows.sort(key=lambda r: str(r.get("display", "")).lower())
        item_data_new = self._savegame_editor_collect_item_data(game_path)
        item_name_map = dict(item_data_new.get("item_name_map", {}) or {})
        ship_nicks = list(item_data_new.get("ship_nicks", []) or [])
        equip_nicks = list(item_data_new.get("equip_nicks", []) or [])
        ship_hardpoints_by_nick = {
            str(k): list(v) for k, v in dict(item_data_new.get("ship_hardpoints_by_nick", {}) or {}).items()
        }
        ship_hp_types_by_hardpoint_by_nick = {
            str(k): {str(hk): list(hv) for hk, hv in dict(hmap).items()}
            for k, hmap in dict(item_data_new.get("ship_hp_types_by_hardpoint_by_nick", {}) or {}).items()
        }
        equip_type_by_nick = {
            str(k): str(v) for k, v in dict(item_data_new.get("equip_type_by_nick", {}) or {}).items()
        }
        equip_hp_types_by_nick = {
            str(k): list(v) for k, v in dict(item_data_new.get("equip_hp_types_by_nick", {}) or {}).items()
        }
        hash_to_nick = {int(k): str(v) for k, v in dict(item_data_new.get("hash_to_nick", {}) or {}).items()}
        jump_data = self._savegame_editor_collect_jump_connections(game_path)
        rep_group_cb.blockSignals(True)
        rep_group_cb.clear()
        for nick in sorted(self._cached_factions, key=str.lower):
            label = faction_labels.get(str(nick).strip().lower(), self._faction_ui_label(nick) or str(nick))
            rep_group_cb.addItem(label, str(nick))
        rep_group_cb.blockSignals(False)
        template_cb.blockSignals(True)
        template_cb.clear()
        for tpl in templates:
            template_cb.addItem(str(tpl.get("name") or ""), tpl)
        template_cb.setEnabled(bool(templates))
        apply_template_btn.setEnabled(bool(templates))
        template_cb.setCurrentIndex(-1)
        template_cb.blockSignals(False)
        cur_sys = _current_system_nick()
        system_cb.blockSignals(True)
        system_cb.clear()
        for sys_nick in sorted(system_to_bases.keys(), key=lambda s: str(system_label_by_nick.get(s, s)).lower()):
            system_cb.addItem(system_label_by_nick.get(sys_nick, sys_nick), sys_nick)
        if cur_sys:
            idx = system_cb.findData(cur_sys)
            if idx >= 0:
                system_cb.setCurrentIndex(idx)
            elif system_cb.count() > 0:
                system_cb.setCurrentIndex(0)
        system_cb.blockSignals(False)
        _rebuild_base_combo(_current_system_nick(), _current_base_nick())
        ship_archetype_cb.blockSignals(True)
        ship_archetype_cb.clear()
        _setup_item_combo(ship_archetype_cb, ship_nicks)
        ship_archetype_cb.blockSignals(False)
        _refresh_equip_hardpoint_choices()
        cur_path = state.get("path")
        if isinstance(cur_path, Path):
            ok, msg = _parse_with_loading(cur_path)
            if not ok:
                QMessageBox.warning(dlg, tr("savegame_editor.title"), msg)
        self.statusBar().showMessage(tr("savegame_editor.game_path_saved").format(path=game_path))

    def _open_path_settings() -> None:
        pd = QDialog(dlg)
        pd.setWindowTitle(tr("savegame_editor.path_settings"))
        pd.resize(760, 180)
        pl = QVBoxLayout(pd)
        form = QFormLayout()
        sg_row = QWidget(pd)
        sg_l = QHBoxLayout(sg_row)
        sg_l.setContentsMargins(0, 0, 0, 0)
        sg_l.setSpacing(6)
        sg_edit = QLineEdit(save_dir_edit.text().strip(), pd)
        sg_l.addWidget(sg_edit, 1)
        sg_browse = QPushButton(tr("welcome.browse"), pd)
        sg_l.addWidget(sg_browse)
        form.addRow(tr("savegame_editor.path_dir"), sg_row)
        gm_row = QWidget(pd)
        gm_l = QHBoxLayout(gm_row)
        gm_l.setContentsMargins(0, 0, 0, 0)
        gm_l.setSpacing(6)
        gm_edit = QLineEdit(game_path_edit.text().strip(), pd)
        gm_l.addWidget(gm_edit, 1)
        gm_browse = QPushButton(tr("welcome.browse"), pd)
        gm_l.addWidget(gm_browse)
        form.addRow(tr("savegame_editor.game_path"), gm_row)
        pl.addLayout(form)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        ok_btn = QPushButton(tr("savegame_editor.path_apply"), pd)
        cancel_btn = QPushButton(tr("dlg.cancel"), pd)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        pl.addLayout(btn_row)

        def _browse_save_path() -> None:
            start = sg_edit.text().strip() or str(Path.home())
            chosen = QFileDialog.getExistingDirectory(pd, tr("welcome.browse_title"), start)
            if chosen:
                sg_edit.setText(chosen)

        def _browse_game_path() -> None:
            start = gm_edit.text().strip() or str(Path.home())
            chosen = QFileDialog.getExistingDirectory(pd, tr("welcome.browse_title"), start)
            if chosen:
                gm_edit.setText(chosen)

        def _accept() -> None:
            save_dir_edit.setText(sg_edit.text().strip())
            game_path_edit.setText(gm_edit.text().strip())
            _apply_save_dir()
            _apply_game_path()
            pd.accept()

        sg_browse.clicked.connect(_browse_save_path)
        gm_browse.clicked.connect(_browse_game_path)
        ok_btn.clicked.connect(_accept)
        cancel_btn.clicked.connect(pd.reject)
        pd.exec()

    def _unlock_all_connections() -> None:
        cur = state.get("path")
        if not isinstance(cur, Path):
            QMessageBox.information(dlg, tr("savegame_editor.title"), tr("savegame_editor.no_file"))
            return
        _set_pending_locked_ids(set())
        info_lbl.setText(tr("savegame_editor.unlocked_all").format(count=0))
        self.statusBar().showMessage(tr("savegame_editor.pending_changes"))

    def _unlock_system_connections(system_key: str) -> None:
        cur = state.get("path")
        if not isinstance(cur, Path):
            return
        skey = str(system_key or "").strip().upper()
        if not skey:
            return
        ids: set[int] = set()
        for edge in list(jump_data.get("edges", []) or []):
            a = str(edge.get("a", "")).upper()
            b = str(edge.get("b", "")).upper()
            if skey not in {a, b}:
                continue
            for v in list(edge.get("ids", []) or []):
                try:
                    hid = int(v)
                except Exception:
                    hid = 0
                if hid > 0:
                    ids.add(hid)
        current_locked = set(int(v) for v in set(state.get("locked_ids", set()) or set()) if int(v) > 0)
        if not ids or not current_locked:
            return
        new_locked = set(current_locked)
        new_locked.difference_update(ids)
        removed = max(0, len(current_locked) - len(new_locked))
        if removed <= 0:
            return
        _set_pending_locked_ids(new_locked)
        sys_row = dict(dict(jump_data.get("systems", {}) or {}).get(skey, {}) or {})
        disp = str(sys_row.get("display", skey) or skey)
        info_lbl.setText(tr("savegame_editor.unlocked_system").format(system=disp, count=removed))
        self.statusBar().showMessage(tr("savegame_editor.pending_changes"))

    def _visit_unlock_all_connections() -> None:
        cur = state.get("path")
        if not isinstance(cur, Path):
            QMessageBox.information(dlg, tr("savegame_editor.title"), tr("savegame_editor.no_file"))
            return
        gate_ids = sorted(int(v) for v in set(jump_data.get("all_gate_ids", set()) or set()) if int(v) > 0)
        if not gate_ids:
            QMessageBox.information(dlg, tr("savegame_editor.title"), tr("savegame_editor.ids_none"))
            return
        system_ids: set[int] = set()
        for row in dict(jump_data.get("systems", {}) or {}).values():
            sys_nick = str(dict(row or {}).get("nickname", "") or "").strip()
            if not sys_nick:
                continue
            hid = int(self._fl_hash_nickname(sys_nick))
            if hid > 0:
                system_ids.add(hid)
        all_ids = sorted(set(gate_ids) | system_ids)
        current_visit = set(int(v) for v in set(state.get("visit_ids", set()) or set()) if int(v) > 0)
        merged = set(current_visit)
        merged.update(int(v) for v in all_ids)
        _set_pending_visit_ids(merged)
        info_lbl.setText(
            tr("savegame_editor.visited_all").format(count=len(all_ids))
            + f" (JH/JG: {len(gate_ids)}, Systems: {len(system_ids)})"
        )
        self.statusBar().showMessage(tr("savegame_editor.pending_changes"))

    def _pick_file() -> None:
        cur = state.get("path")
        if isinstance(cur, Path):
            start_dir = str(cur.parent)
        else:
            start_dir = str(_save_dir())
        chosen, _flt = QFileDialog.getOpenFileName(
            dlg,
            tr("savegame_editor.open"),
            start_dir,
            "Freelancer Savegame (*.fl);;All files (*)",
        )
        if not chosen:
            return
        chosen_path = Path(chosen)
        save_dir_edit.setText(str(chosen_path.parent))
        _apply_save_dir()
        ok, msg = _parse_with_loading(chosen_path)
        if not ok:
            QMessageBox.warning(dlg, tr("savegame_editor.title"), msg)
            return
        _refresh_savegame_list(select_path=chosen_path, auto_load=False)

    def _reload() -> None:
        cur = state.get("path")
        if not isinstance(cur, Path):
            QMessageBox.information(dlg, tr("savegame_editor.title"), tr("savegame_editor.no_file"))
            return
        ok, msg = _parse_with_loading(cur)
        if not ok:
            QMessageBox.warning(dlg, tr("savegame_editor.title"), msg)

    def _apply_template() -> None:
        tpl = template_cb.currentData()
        if not isinstance(tpl, dict):
            return
        houses_obj = tpl.get("houses")
        if not isinstance(houses_obj, dict) or not houses_obj:
            return
        try:
            houses_in = {str(k).strip(): float(v) for k, v in houses_obj.items() if str(k).strip()}
        except Exception:
            return
        template_faction = str(tpl.get("faction") or "").strip()
        rows: list[tuple[str, float]] = []
        for fac, val in houses_in.items():
            rep = float(val)
            rep = max(-0.91, min(0.91, rep))
            rows.append((fac, rep))
        rows.sort(key=lambda x: x[0].lower())
        _set_houses(rows)
        if template_faction:
            _set_rep_group_value(template_faction)
        info_lbl.setText(
            tr("savegame_editor.template_applied").format(
                template=str(tpl.get("name") or ""),
                faction=self._faction_ui_label(template_faction) or template_faction or tr("savegame_editor.template_none"),
            )
        )

    def _save() -> None:
        cur = state.get("path")
        if not isinstance(cur, Path):
            QMessageBox.information(dlg, tr("savegame_editor.title"), tr("savegame_editor.no_file"))
            return
        try:
            raw = self._read_text_best_effort(cur)
        except Exception as exc:
            QMessageBox.critical(dlg, tr("msg.save_error"), tr("savegame_editor.save_failed").format(error=exc))
            return
        newline = "\r\n" if "\r\n" in raw else "\n"
        lines = raw.splitlines()
        bounds = self._find_ini_section_bounds(lines, "Player", None)
        if bounds is None:
            QMessageBox.warning(dlg, tr("savegame_editor.title"), tr("savegame_editor.player_missing"))
            return
        s, e = bounds
        player = list(lines[s:e])
        orig_system = ""
        orig_base = ""
        for ln in player[1:]:
            core = str(ln or "").split(";", 1)[0].strip()
            if not core or "=" not in core:
                continue
            k, v = core.split("=", 1)
            kl = str(k or "").strip().lower()
            vv = str(v or "").strip()
            if kl == "system" and not orig_system:
                orig_system = vv
            elif kl == "base" and not orig_base:
                orig_base = vv

        new_system = _current_system_nick()
        new_base = _current_base_nick()

        # Freelancer can crash when moving system/base in an active story mission save.
        story_mission_num = 0
        story_bounds = self._find_ini_section_bounds(lines, "StoryInfo", None)
        if story_bounds is not None:
            ss, se = story_bounds
            for ln in lines[ss + 1:se]:
                core = str(ln or "").split(";", 1)[0].strip()
                if not core or "=" not in core:
                    continue
                k, v = core.split("=", 1)
                if str(k or "").strip().lower() != "missionnum":
                    continue
                try:
                    story_mission_num = int(float(str(v or "").strip()))
                except Exception:
                    story_mission_num = 0
                break
        story_active = 1 <= int(story_mission_num) <= 12
        if story_active:
            changed_system = bool(orig_system and new_system) and (orig_system.strip().lower() != new_system.strip().lower())
            changed_base = bool(orig_base and new_base) and (orig_base.strip().lower() != new_base.strip().lower())
            if changed_system or changed_base:
                QMessageBox.warning(
                    dlg,
                    tr("savegame_editor.title"),
                    (
                        "Active story mission detected (MissionNum = {mn}). "
                        "Changing system/base is blocked to prevent savegame crashes.\n\n"
                        "Restore the backup or keep original system/base for story saves."
                    ).format(mn=story_mission_num),
                )
                return

        player, _ = self._set_single_key_line_in_section(player, "rank", f"rank = {int(rank_spin.value())}")
        player, _ = self._set_single_key_line_in_section(player, "money", f"money = {int(money_spin.value())}")
        player, _ = self._set_single_key_line_in_section(player, "rep_group", f"rep_group = {_current_rep_group_nick()}")
        player, _ = self._set_single_key_line_in_section(player, "system", f"system = {new_system}")
        player, _ = self._set_single_key_line_in_section(player, "base", f"base = {new_base}")
        ship_token = _item_token_for_save(_combo_item_nick(ship_archetype_cb))
        player, _ = self._set_single_key_line_in_section(player, "ship_archetype", f"ship_archetype = {ship_token}")

        house_lines: list[str] = []
        for faction, rep in _current_houses():
            house_lines.append(f"house = {_fmt_rep(rep)}, {faction}")

        equip_lines: list[str] = []
        for item_nick, hardpoint, extra in _equip_rows():
            item_token = _item_token_for_save(item_nick)
            if not item_token:
                continue
            tail = str(extra or "").strip()
            if not tail:
                tail = "1"
            if hardpoint:
                equip_lines.append(f"equip = {item_token}, {hardpoint}, {tail}")
            else:
                equip_lines.append(f"equip = {item_token}, , {tail}")

        cargo_lines: list[str] = []
        for item_nick, amount, extra in _cargo_rows():
            item_token = _item_token_for_save(item_nick)
            if not item_token:
                continue
            tail = str(extra or "").strip()
            if not tail:
                tail = ", , 0"
            cargo_lines.append(f"cargo = {item_token}, {int(amount)}, {tail}")

        def _line_key(raw_line: str) -> str:
            core = str(raw_line or "").split(";", 1)[0].strip()
            if not core or "=" not in core:
                return ""
            return str(core.split("=", 1)[0] or "").strip().lower()

        def _replace_key_block(
            section_lines: list[str], keys: set[str], replacement_lines: list[str]
        ) -> list[str]:
            if not section_lines:
                return []
            header = section_lines[0]
            body = list(section_lines[1:])
            first_idx: int | None = None
            kept: list[str] = []
            for ln in body:
                if _line_key(ln) in keys:
                    if first_idx is None:
                        first_idx = len(kept)
                    continue
                kept.append(ln)
            if replacement_lines:
                ins = first_idx if first_idx is not None else len(kept)
                kept = kept[:ins] + list(replacement_lines) + kept[ins:]
            return [header] + kept

        pending_locked = sorted(int(v) for v in set(state.get("locked_ids", set()) or set()) if int(v) > 0)
        pending_visit = sorted(int(v) for v in set(state.get("visit_ids", set()) or set()) if int(v) > 0)
        visit_line_by_id = dict(state.get("visit_line_by_id", {}) or {})
        lock_lines = [f"locked_gate = {hid}" for hid in pending_locked]
        visit_lines: list[str] = []
        for hid in pending_visit:
            raw_v = str(visit_line_by_id.get(int(hid), "") or "").strip()
            if not raw_v:
                raw_v = f"{int(hid)}, 1"
            visit_lines.append(f"visit = {raw_v}")
        player = _replace_key_block(player, {"locked_gate", "npc_locked_gate"}, lock_lines)
        player = _replace_key_block(player, {"visit"}, visit_lines)
        player = _replace_key_block(player, {"equip"}, equip_lines)
        player = _replace_key_block(player, {"cargo"}, cargo_lines)
        player = _replace_key_block(player, {"house"}, house_lines)
        out_lines = lines[:s] + player + lines[e:]

        backup = cur.with_name(f"{cur.name}.FLAtlasBAK")
        try:
            shutil.copy2(str(cur), str(backup))
            text = newline.join(out_lines)
            if not text.endswith(newline):
                text += newline
            try:
                cur.write_text(text, encoding="cp1252")
            except UnicodeEncodeError:
                cur.write_text(text, encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(dlg, tr("msg.save_error"), tr("savegame_editor.save_failed").format(error=exc))
            return
        self.statusBar().showMessage(tr("savegame_editor.saved").format(path=str(cur), backup=str(backup)))
        info_lbl.setText(tr("savegame_editor.saved").format(path=str(cur), backup=str(backup)))

    act_file_open = file_menu.addAction(tr("savegame_editor.open"))
    act_file_reload = file_menu.addAction(tr("savegame_editor.reload"))
    act_file_save = file_menu.addAction(tr("savegame_editor.save"))
    file_menu.addSeparator()
    act_file_close = file_menu.addAction(tr("dlg.close"))
    act_settings_paths = settings_menu.addAction(tr("savegame_editor.path_settings"))

    refresh_btn.clicked.connect(lambda: _refresh_savegame_list(auto_load=False))
    load_btn.clicked.connect(_load_selected)
    ship_archetype_cb.currentIndexChanged.connect(lambda _idx: _refresh_equip_hardpoint_choices())
    ship_archetype_cb.currentTextChanged.connect(lambda _txt: _refresh_equip_hardpoint_choices())
    system_cb.currentIndexChanged.connect(lambda _idx: _rebuild_base_combo(_current_system_nick(), _current_base_nick()))
    system_cb.currentTextChanged.connect(lambda _txt: _rebuild_base_combo(_current_system_nick(), _current_base_nick()))
    equip_add_btn.clicked.connect(lambda: _add_equip_row("", ""))
    equip_del_btn.clicked.connect(
        lambda: (equip_tbl.removeRow(equip_tbl.currentRow()), _refresh_hardpoint_hint()) if equip_tbl.currentRow() >= 0 else None
    )
    cargo_add_btn.clicked.connect(lambda: _add_cargo_row("", 1))
    cargo_del_btn.clicked.connect(lambda: cargo_tbl.removeRow(cargo_tbl.currentRow()) if cargo_tbl.currentRow() >= 0 else None)
    savegame_cb.currentIndexChanged.connect(
        lambda _idx: _load_selected() if not bool(state.get("updating_savegame_cb")) else None
    )
    open_btn.clicked.connect(_pick_file)
    reload_btn.clicked.connect(_reload)
    unlock_all_btn.clicked.connect(_unlock_all_connections)
    visit_unlock_all_btn.clicked.connect(_visit_unlock_all_connections)
    apply_template_btn.clicked.connect(_apply_template)
    save_btn.clicked.connect(_save)
    close_btn.clicked.connect(dlg.reject)
    act_file_open.triggered.connect(_pick_file)
    act_file_reload.triggered.connect(_reload)
    act_file_save.triggered.connect(_save)
    act_file_close.triggered.connect(dlg.reject)
    act_settings_paths.triggered.connect(_open_path_settings)
    locked_view.on_system_click = _unlock_system_connections

    _refresh_savegame_list(auto_load=False)
    _render_known_objects_map(set())
    _render_visited_map(set())
    locked_view.reset_zoom()
    visited_view.reset_zoom()
    _refresh_hardpoint_hint()
    dlg.exec()


def run_standalone() -> int:
    try:
        from .main_window import MainWindow
    except Exception:  # pragma: no cover
        _this_dir = Path(__file__).resolve().parent
        _parent = str(_this_dir.parent)
        if _parent not in sys.path:
            sys.path.insert(0, _parent)
        from fl_editor.main_window import MainWindow  # type: ignore

    class _SavegameEditorHost(MainWindow):
        def _startup_update_check(self):  # type: ignore[override]
            return

    app = QApplication.instance() or QApplication(sys.argv)
    host = _SavegameEditorHost()
    host.hide()
    open_savegame_editor(host)
    host.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_standalone())
