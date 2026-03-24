from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .base_edit_logic import (
    assigned_nickname_set,
    available_equip_groups,
    available_nicknames,
    build_base_edit_property_state,
    build_commodity_market_row,
    build_default_commodity_market_row,
    build_default_equip_market_row,
    build_equip_market_row,
    preferred_equip_group_label,
    ship_slot_values,
)
from .i18n import tr
from .ui_helpers import connect_debounced_line_edit


EQUIP_COLS = [
    "Nickname",
    "Level",
    "Rep",
    "Min-Stock",
    "Max-Stock",
    tr("dlg.col_sell_buy"),
    tr("dlg.col_price_multi"),
]

COMM_COLS = [
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


def build_base_edit_properties_tab(
    dialog,
    *,
    tabs,
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
) -> None:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    layout = QFormLayout(content)
    scroll.setWidget(content)

    state = build_base_edit_property_state(obj_entries=obj_entries, pilots=pilots)
    obj_dict = dict(state["obj_dict"])

    dialog.prop_nick = QLineEdit(obj_dict.get("nickname", ""))
    layout.addRow("Nickname:", dialog.prop_nick)

    dialog.prop_arch = QComboBox()
    dialog.prop_arch.setEditable(True)
    if archetypes:
        dialog.prop_arch.addItems(archetypes)
    dialog.prop_arch.setCurrentText(obj_dict.get("archetype", ""))
    layout.addRow(tr("lbl.archetype"), dialog.prop_arch)

    dialog.prop_loadout = QComboBox()
    dialog.prop_loadout.setEditable(True)
    dialog.prop_loadout.addItem("")
    if loadouts:
        dialog.prop_loadout.addItems(loadouts)
    dialog.prop_loadout.setCurrentText(obj_dict.get("loadout", ""))
    layout.addRow("Loadout:", dialog.prop_loadout)

    dialog.prop_rep = QComboBox()
    dialog.prop_rep.setEditable(True)
    dialog.prop_rep.addItem("")
    if factions:
        dialog.prop_rep.addItems(factions)
    dialog.prop_rep.setCurrentText(obj_dict.get("reputation", ""))
    layout.addRow("Reputation:", dialog.prop_rep)

    dialog.prop_pilot = QComboBox()
    dialog.prop_pilot.setEditable(True)
    dialog.prop_pilot.addItems(list(state["pilot_choices"]))
    dialog.prop_pilot.setCurrentText(obj_dict.get("pilot", "pilot_solar_easiest"))
    layout.addRow("Pilot:", dialog.prop_pilot)

    dialog.prop_voice = QComboBox()
    dialog.prop_voice.setEditable(True)
    dialog.prop_voice.addItem("")
    if voices:
        dialog.prop_voice.addItems(voices)
    dialog.prop_voice.setCurrentText(obj_dict.get("voice", ""))
    layout.addRow("Voice:", dialog.prop_voice)

    dialog.prop_head = QComboBox()
    dialog.prop_head.setEditable(True)
    dialog.prop_head.addItem("")
    if heads:
        dialog.prop_head.addItems(heads)
    dialog.prop_head.setCurrentText(str(state["head"]))
    layout.addRow("Head:", dialog.prop_head)

    dialog.prop_body = QComboBox()
    dialog.prop_body.setEditable(True)
    dialog.prop_body.addItem("")
    if bodies:
        dialog.prop_body.addItems(bodies)
    dialog.prop_body.setCurrentText(str(state["body"]))
    layout.addRow("Body:", dialog.prop_body)

    dialog.prop_ids_name = QSpinBox()
    dialog.prop_ids_name.setRange(0, 999999)
    dialog.prop_ids_name.setValue(int(state["ids_name"]))
    layout.addRow("ids_name:", dialog.prop_ids_name)

    dialog.prop_ids_info = QSpinBox()
    dialog.prop_ids_info.setRange(0, 999999)
    dialog.prop_ids_info.setValue(int(state["ids_info"]))
    layout.addRow("ids_info:", dialog.prop_ids_info)

    dialog.prop_name_text = QLineEdit(str(current_name_text or "").strip())
    dialog.prop_name_text.setPlaceholderText("Ingame Name")
    layout.addRow("Name:", dialog.prop_name_text)

    dialog.prop_infocard_xml = QTextEdit()
    dialog.prop_infocard_xml.setAcceptRichText(False)
    dialog.prop_infocard_xml.setMinimumHeight(150)
    dialog.prop_infocard_xml.setPlainText(str(current_infocard_xml or "").strip())
    layout.addRow("Infocard XML:", dialog.prop_infocard_xml)

    jump_btn = QPushButton("InfoCard Editor öffnen")
    jump_btn.clicked.connect(dialog._on_jump_infocard_editor)
    layout.addRow("", jump_btn)

    dialog.prop_behavior = QLineEdit(obj_dict.get("behavior", "NOTHING"))
    layout.addRow("Behavior:", dialog.prop_behavior)

    dialog.prop_difficulty = QSpinBox()
    dialog.prop_difficulty.setRange(0, 100)
    dialog.prop_difficulty.setValue(int(state["difficulty_level"]))
    layout.addRow("Difficulty Level:", dialog.prop_difficulty)

    tabs.addTab(scroll, tr("dlg.tab_properties"))


def build_base_edit_equip_tab(
    *,
    tabs,
    equip_groups: dict[str, list[str]],
    equip_goods: list[list[str]],
) -> tuple[QTreeWidget, QTableWidget]:
    tab = QWidget()
    hl = QHBoxLayout(tab)

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

    right_vl = QVBoxLayout()
    right_vl.addWidget(QLabel(tr("dlg.on_this_base")))
    table = QTableWidget(0, len(EQUIP_COLS))
    table.setHorizontalHeaderLabels(EQUIP_COLS)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    right_vl.addWidget(table)

    legend = QLabel(tr("dlg.equip_legend"))
    legend.setWordWrap(True)
    right_vl.addWidget(legend)
    hl.addLayout(right_vl, 2)

    assigned_lower = assigned_nickname_set(equip_goods)
    for row in equip_goods:
        values = build_equip_market_row(row)
        if not values:
            continue
        r = table.rowCount()
        table.insertRow(r)
        for col, val in enumerate(values):
            table.setItem(r, col, QTableWidgetItem(val))

    for group_label, nicks in available_equip_groups(equip_groups, assigned_lower):
        group_item = QTreeWidgetItem(tree, [group_label])
        font = group_item.font(0)
        font.setBold(True)
        group_item.setFont(0, font)
        group_item.setFlags(group_item.flags() & ~Qt.ItemIsSelectable)
        for nick in nicks:
            child = QTreeWidgetItem(group_item, [nick])
            child.setData(0, Qt.UserRole, nick)

    def _filter_changed(text: str):
        wanted = text.lower()
        for gi in range(tree.topLevelItemCount()):
            group = tree.topLevelItem(gi)
            any_visible = False
            for ci in range(group.childCount()):
                child = group.child(ci)
                visible = wanted in child.text(0).lower()
                child.setHidden(not visible)
                if visible:
                    any_visible = True
            group.setHidden(not any_visible)
            if any_visible and wanted:
                group.setExpanded(True)

    connect_debounced_line_edit(filter_edit, lambda: _filter_changed(filter_edit.text()))

    def _move_right():
        for sel_item in tree.selectedItems():
            nick = sel_item.data(0, Qt.UserRole)
            if not nick:
                continue
            r = table.rowCount()
            table.insertRow(r)
            table.setItem(r, 0, QTableWidgetItem(nick))
            for col, val in enumerate(build_default_equip_market_row(nick)[1:], start=1):
                table.setItem(r, col, QTableWidgetItem(val))
            parent = sel_item.parent()
            if parent:
                parent.removeChild(sel_item)

    def _move_left():
        rows = sorted({idx.row() for idx in table.selectedIndexes()}, reverse=True)
        for r in rows:
            nick_item = table.item(r, 0)
            if nick_item:
                nick = nick_item.text()
                target_label = preferred_equip_group_label(nick, equip_groups)
                target_group = None
                for gi in range(tree.topLevelItemCount()):
                    group = tree.topLevelItem(gi)
                    if group.text(0) == target_label:
                        target_group = group
                        break
                if target_group is None and tree.topLevelItemCount() > 0:
                    target_group = tree.topLevelItem(0)
                if target_group is not None:
                    child = QTreeWidgetItem(target_group, [nick])
                    child.setData(0, Qt.UserRole, nick)
            table.removeRow(r)

    btn_to_right.clicked.connect(_move_right)
    btn_to_left.clicked.connect(_move_left)

    def _dbl_click(item, _col):
        nick = item.data(0, Qt.UserRole)
        if not nick:
            return
        r = table.rowCount()
        table.insertRow(r)
        table.setItem(r, 0, QTableWidgetItem(nick))
        for col, val in enumerate(build_default_equip_market_row(nick)[1:], start=1):
            table.setItem(r, col, QTableWidgetItem(val))
        parent = item.parent()
        if parent:
            parent.removeChild(item)

    tree.itemDoubleClicked.connect(_dbl_click)

    tabs.addTab(tab, "Equipment")
    return tree, table


def build_base_edit_commodity_tab(
    *,
    tabs,
    commodity_prices: dict[str, int],
    all_nicks: list[str],
    comm_goods: list[list[str]],
) -> tuple[QListWidget, QTableWidget]:
    tab = QWidget()
    hl = QHBoxLayout(tab)

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

    right_vl = QVBoxLayout()
    right_vl.addWidget(QLabel(tr("dlg.on_this_base")))
    table = QTableWidget(0, len(COMM_COLS))
    table.setHorizontalHeaderLabels(COMM_COLS)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    right_vl.addWidget(table)

    legend = QLabel(tr("dlg.comm_legend"))
    legend.setWordWrap(True)
    right_vl.addWidget(legend)
    hl.addLayout(right_vl, 2)

    def _set_price_cells(row: int, nick: str, multi_str: str):
        base_price = commodity_prices.get(nick, 0)
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
        if col == 6:
            nick_item = table.item(row, 0)
            multi_item = table.item(row, 6)
            if nick_item and multi_item:
                _set_price_cells(row, nick_item.text().strip(), multi_item.text().strip())
        elif col == 0:
            nick_item = table.item(row, 0)
            multi_item = table.item(row, 6)
            if nick_item:
                _set_price_cells(
                    row,
                    nick_item.text().strip(),
                    multi_item.text().strip() if multi_item else "1",
                )

    table.cellChanged.connect(_recalc_endpreis)

    table.blockSignals(True)
    assigned_lower = assigned_nickname_set(comm_goods)
    for row_data in comm_goods:
        values = build_commodity_market_row(row_data, commodity_prices)
        if not values:
            continue
        r = table.rowCount()
        table.insertRow(r)
        for col, val in enumerate(values):
            table.setItem(r, col, QTableWidgetItem(val))
    table.blockSignals(False)

    for nick in available_nicknames(all_nicks, assigned_lower):
        avail_list.addItem(nick)

    def _filter_changed(text: str):
        wanted = text.lower()
        for i in range(avail_list.count()):
            item = avail_list.item(i)
            item.setHidden(wanted not in item.text().lower())

    connect_debounced_line_edit(filter_edit, lambda: _filter_changed(filter_edit.text()))

    def _move_right():
        table.blockSignals(True)
        for item in avail_list.selectedItems():
            nick = item.text()
            r = table.rowCount()
            table.insertRow(r)
            for col, val in enumerate(build_default_commodity_market_row(nick, commodity_prices)):
                table.setItem(r, col, QTableWidgetItem(val))
            avail_list.takeItem(avail_list.row(item))
        table.blockSignals(False)

    def _move_left():
        rows = sorted({idx.row() for idx in table.selectedIndexes()}, reverse=True)
        for r in rows:
            nick_item = table.item(r, 0)
            if nick_item:
                avail_list.addItem(nick_item.text())
            table.removeRow(r)

    btn_to_right.clicked.connect(_move_right)
    btn_to_left.clicked.connect(_move_left)

    def _dbl_left(item):
        nick = item.text()
        table.blockSignals(True)
        r = table.rowCount()
        table.insertRow(r)
        for col, val in enumerate(build_default_commodity_market_row(nick, commodity_prices)):
            table.setItem(r, col, QTableWidgetItem(val))
        table.blockSignals(False)
        avail_list.takeItem(avail_list.row(item))

    avail_list.itemDoubleClicked.connect(_dbl_left)

    tabs.addTab(tab, "Commodities")
    return avail_list, table


def build_base_edit_ships_tab(
    *,
    dialog,
    tabs,
    all_ship_nicks: list[str],
    assigned_ships: list[str],
) -> None:
    tab = QWidget()
    vl = QVBoxLayout(tab)
    vl.addWidget(QLabel(tr("dlg.max_ships")))
    vl.addSpacing(10)

    dialog.ship_combos = []
    slot_values = ship_slot_values(all_ship_nicks, assigned_ships, slots=3)

    for slot in range(3):
        slot_hl = QHBoxLayout()
        lbl = QLabel(f"Slot {slot + 1}:")
        lbl.setFixedWidth(50)
        slot_hl.addWidget(lbl)

        combo = QComboBox()
        combo.setEditable(True)
        combo.addItem("")
        combo.addItems(sorted(all_ship_nicks, key=str.lower))
        combo.setCurrentText(slot_values[slot])
        combo.setMinimumWidth(350)
        slot_hl.addWidget(combo, 1)
        slot_hl.addStretch()
        vl.addLayout(slot_hl)
        dialog.ship_combos.append(combo)

    vl.addStretch()
    tabs.addTab(tab, "Schiffe")
