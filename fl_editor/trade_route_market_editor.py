"""Market editor dialog for per-base MarketGood management."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .trade_route_market import (
    extract_base_market_goods,
    list_bases_with_commodity,
    serialize_ini_sections,
    trade_route_format_multiplier,
    trade_route_patch_marketgood_field,
    trade_route_remove_marketgood_section,
    trade_route_upsert_marketgood_section,
)


def market_editor_type_text(relation_flag: int, *, tr=None) -> str:
    if int(relation_flag) == 0:
        return tr("trade.market_editor.type_source") if tr else "Buy (Source)"
    return tr("trade.market_editor.type_sink") if tr else "Sell (Sink)"


def market_editor_effective_price(base_price: int, multiplier: float) -> int:
    if int(base_price) <= 0:
        return 0
    return int(float(base_price) * float(multiplier))


def market_editor_trade_impact_summary(
    *,
    entries: list[dict],
    current_base: str,
    relation_flag: int,
    multiplier: float,
    base_price: int,
    base_index: dict[str, dict],
    tr=None,
) -> str:
    effective_price = market_editor_effective_price(base_price, multiplier)
    current_base_low = str(current_base or "").strip().lower()
    counterpart_flag = 1 if int(relation_flag) == 0 else 0
    counterpart_entries = [
        entry for entry in entries
        if str(entry.get("base", "")).strip().lower() != current_base_low
        and int(entry.get("relation_flag", 0)) == counterpart_flag
    ]
    if not counterpart_entries:
        return tr("trade.market_editor.impact.none") if tr else "No matching counterpart base found."

    ranked = sorted(
        counterpart_entries,
        key=lambda entry: market_editor_effective_price(base_price, float(entry.get("multiplier", 0.0))),
        reverse=(counterpart_flag == 1),
    )
    best = ranked[0]
    counterpart_price = market_editor_effective_price(base_price, float(best.get("multiplier", 0.0)))
    delta = counterpart_price - effective_price if int(relation_flag) == 0 else effective_price - counterpart_price
    template = "trade.market_editor.impact.best_buyer" if int(relation_flag) == 0 else "trade.market_editor.impact.best_seller"

    base_nick = str(best.get("base", "")).strip().lower()
    info = base_index.get(base_nick, {})
    display_name = str(info.get("display_name", "") or base_nick)
    system_nick = str(info.get("system", "?") or "?")
    base_label = f"{display_name} ({base_nick})" if display_name.lower() != base_nick else base_nick

    if tr:
        return tr(template).format(
            base=base_label,
            system=system_nick,
            unit_profit=int(delta),
            price=counterpart_price,
        )
    return f"Best counterpart: {base_label} [{system_nick}] | unit profit: {int(delta)} cr | price: {counterpart_price} cr"


def open_market_editor_dialog(
    parent,
    *,
    sections: list[tuple[str, list[tuple[str, str]]]],
    base_index: dict[str, dict],
    commodity_base_prices: dict[str, int],
    commodity_display_map: dict[str, str],
    tr,
) -> tuple[list[tuple[str, list[tuple[str, str]]]] | None, bool]:
    """Open a modal dialog to view/edit MarketGood entries for a base.

    Returns ``(updated_sections_or_None, changed)``.
    """
    dlg = _MarketEditorDialog(
        parent,
        sections=sections,
        base_index=base_index,
        commodity_base_prices=commodity_base_prices,
        commodity_display_map=commodity_display_map,
        tr=tr,
    )
    if dlg.exec() == QDialog.Accepted:
        return dlg.result_sections, dlg.has_changes
    return None, False


class _MarketEditorDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        sections,
        base_index,
        commodity_base_prices,
        commodity_display_map,
        tr,
    ):
        super().__init__(parent)
        self._sections = [
            (name, list(entries)) for name, entries in sections
        ]
        self._base_index = base_index
        self._commodity_base_prices = commodity_base_prices
        self._commodity_display_map = commodity_display_map
        self._tr = tr
        self.has_changes = False
        self.result_sections = self._sections

        self.setWindowTitle(tr("trade.market_editor.title"))
        self.setMinimumSize(900, 550)

        root = QVBoxLayout(self)

        # --- Base selection ---
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel(tr("trade.market_editor.base")))
        self._base_cb = QComboBox()
        self._base_cb.setEditable(True)
        self._base_cb.setMinimumWidth(300)
        for base_nick in sorted(base_index.keys()):
            info = base_index[base_nick]
            disp = str(info.get("display_name", base_nick))
            sys_nick = str(info.get("system", ""))
            text = f"{disp} ({base_nick}) [{sys_nick}]"
            self._base_cb.addItem(text, base_nick)
        sel_row.addWidget(self._base_cb, 1)
        root.addLayout(sel_row)

        # --- MarketGood table ---
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            tr("trade.market_editor.col.commodity"),
            tr("trade.market_editor.col.type"),
            tr("trade.market_editor.col.multiplier"),
            tr("trade.market_editor.col.base_price"),
            tr("trade.market_editor.col.effective_price"),
            tr("trade.market_editor.col.stock_min"),
            tr("trade.market_editor.col.stock_max"),
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 7):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        root.addWidget(self._table, 1)

        # --- Buttons ---
        btn_row = QHBoxLayout()
        self._add_btn = QPushButton(tr("trade.market_editor.add"))
        self._remove_btn = QPushButton(tr("trade.market_editor.remove"))
        self._patch_btn = QPushButton(tr("trade.market_editor.patch"))
        btn_row.addWidget(self._add_btn)
        btn_row.addWidget(self._remove_btn)
        btn_row.addWidget(self._patch_btn)
        btn_row.addStretch(1)

        # --- Commodity matrix button ---
        self._matrix_btn = QPushButton(tr("trade.market_editor.commodity_matrix"))
        btn_row.addWidget(self._matrix_btn)
        root.addLayout(btn_row)

        # --- Dialog buttons ---
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

        # --- Connections ---
        self._base_cb.currentIndexChanged.connect(self._refresh_table)
        self._add_btn.clicked.connect(self._on_add)
        self._remove_btn.clicked.connect(self._on_remove)
        self._patch_btn.clicked.connect(self._on_patch)
        self._matrix_btn.clicked.connect(self._on_commodity_matrix)

        if self._base_cb.count() > 0:
            self._refresh_table()

    def _current_base(self) -> str:
        return str(self._base_cb.currentData() or "").strip().lower()

    def _refresh_table(self):
        base = self._current_base()
        goods = extract_base_market_goods(self._sections, base)
        self._table.setRowCount(len(goods))
        for i, g in enumerate(goods):
            commodity = g["commodity"]
            commodity_low = commodity.lower()
            disp = self._commodity_display_map.get(commodity_low, commodity)
            relation_flag = g["relation_flag"]
            multiplier = g["multiplier"]
            base_price = self._commodity_base_prices.get(commodity_low, 0)
            effective = market_editor_effective_price(base_price, multiplier)
            type_txt = market_editor_type_text(relation_flag, tr=self._tr)

            item_comm = QTableWidgetItem(f"{disp} ({commodity})")
            item_comm.setData(Qt.UserRole, g)
            item_comm.setFlags(item_comm.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(i, 0, item_comm)

            for col, val in enumerate([type_txt, f"{multiplier:.4f}", str(base_price), str(effective), str(g["stock_min"]), str(g["stock_max"])], 1):
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self._table.setItem(i, col, item)

    def _on_add(self):
        base = self._current_base()
        if not base:
            return
        add_dlg = QDialog(self)
        add_dlg.setWindowTitle(self._tr("trade.market_editor.add_title"))
        fl = QVBoxLayout(add_dlg)

        # Commodity selection
        row1 = QHBoxLayout()
        row1.addWidget(QLabel(self._tr("trade.market_editor.col.commodity")))
        comm_cb = QComboBox()
        comm_cb.setEditable(True)
        for nick, disp in sorted(self._commodity_display_map.items()):
            comm_cb.addItem(f"{disp} ({nick})", nick)
        row1.addWidget(comm_cb, 1)
        fl.addLayout(row1)

        # Type
        row2 = QHBoxLayout()
        row2.addWidget(QLabel(self._tr("trade.market_editor.col.type")))
        type_cb = QComboBox()
        type_cb.addItem(f"{market_editor_type_text(0, tr=self._tr)} - relation_flag=0", 0)
        type_cb.addItem(f"{market_editor_type_text(1, tr=self._tr)} - relation_flag=1", 1)
        row2.addWidget(type_cb, 1)
        fl.addLayout(row2)

        # Multiplier + live price preview
        row3 = QHBoxLayout()
        row3.addWidget(QLabel(self._tr("trade.market_editor.col.multiplier")))
        mult_spin = QDoubleSpinBox()
        mult_spin.setRange(0.001, 100.0)
        mult_spin.setDecimals(4)
        mult_spin.setValue(1.0)
        row3.addWidget(mult_spin)
        price_preview = QLabel("-")
        row3.addWidget(QLabel("→"))
        row3.addWidget(price_preview)
        fl.addLayout(row3)

        def _update_preview():
            nick = str(comm_cb.currentData() or "").strip().lower()
            bp = self._commodity_base_prices.get(nick, 0)
            if bp > 0:
                eff = market_editor_effective_price(bp, mult_spin.value())
                price_preview.setText(f"{eff:,} cr (base: {bp:,})")
            else:
                price_preview.setText("-")

        comm_cb.currentIndexChanged.connect(lambda _: _update_preview())
        mult_spin.valueChanged.connect(lambda _: _update_preview())
        _update_preview()

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(add_dlg.accept)
        bb.rejected.connect(add_dlg.reject)
        fl.addWidget(bb)

        if add_dlg.exec() != QDialog.Accepted:
            return

        commodity = str(comm_cb.currentData() or comm_cb.currentText()).strip()
        relation_flag = int(type_cb.currentData())
        mult_txt = trade_route_format_multiplier(mult_spin.value())

        self._sections = trade_route_upsert_marketgood_section(
            self._sections,
            base=base,
            commodity=commodity,
            relation_flag=relation_flag,
            multiplier_text=mult_txt,
        )
        self.has_changes = True
        self.result_sections = self._sections
        self._refresh_table()

    def _on_remove(self):
        row_idx = self._table.currentRow()
        if row_idx < 0:
            return
        item = self._table.item(row_idx, 0)
        if item is None:
            return
        data = item.data(Qt.UserRole)
        if not isinstance(data, dict):
            return
        commodity = data.get("commodity", "")
        base = self._current_base()
        if not base or not commodity:
            return

        reply = QMessageBox.question(
            self,
            self._tr("trade.market_editor.confirm_remove_title"),
            self._tr("trade.market_editor.confirm_remove").format(commodity=commodity, base=base),
        )
        if reply != QMessageBox.Yes:
            return

        self._sections, changed = trade_route_remove_marketgood_section(
            self._sections,
            base=base,
            commodity=commodity,
        )
        if changed:
            self.has_changes = True
            self.result_sections = self._sections
        self._refresh_table()

    def _on_patch(self):
        row_idx = self._table.currentRow()
        if row_idx < 0:
            return
        item = self._table.item(row_idx, 0)
        if item is None:
            return
        data = item.data(Qt.UserRole)
        if not isinstance(data, dict):
            return
        commodity = data.get("commodity", "")
        base = self._current_base()
        if not base or not commodity:
            return

        patch_dlg = QDialog(self)
        patch_dlg.setWindowTitle(self._tr("trade.market_editor.patch_title"))
        fl = QVBoxLayout(patch_dlg)

        commodity_low = commodity.lower()
        base_price = self._commodity_base_prices.get(commodity_low, 0)
        disp = self._commodity_display_map.get(commodity_low, commodity)
        fl.addWidget(QLabel(f"{disp} ({commodity})"))
        if base_price > 0:
            fl.addWidget(QLabel(f"Base Price: {base_price:,} cr"))

        row_t = QHBoxLayout()
        row_t.addWidget(QLabel(self._tr("trade.market_editor.col.type")))
        type_cb = QComboBox()
        type_cb.addItem(market_editor_type_text(0, tr=self._tr), 0)
        type_cb.addItem(market_editor_type_text(1, tr=self._tr), 1)
        type_cb.setCurrentIndex(0 if int(data.get("relation_flag", 0)) == 0 else 1)
        row_t.addWidget(type_cb, 1)
        fl.addLayout(row_t)

        # Multiplier
        row_m = QHBoxLayout()
        row_m.addWidget(QLabel(self._tr("trade.market_editor.col.multiplier")))
        mult_spin = QDoubleSpinBox()
        mult_spin.setRange(0.001, 100.0)
        mult_spin.setDecimals(4)
        mult_spin.setValue(data.get("multiplier", 1.0))
        row_m.addWidget(mult_spin)

        # Live price preview
        old_price = market_editor_effective_price(base_price, data.get("multiplier", 1.0))
        price_lbl = QLabel(f"→ {old_price:,} cr")
        row_m.addWidget(price_lbl)
        fl.addLayout(row_m)

        impact_lbl = QLabel("")
        impact_lbl.setWordWrap(True)
        fl.addWidget(impact_lbl)

        def _upd():
            new_p = market_editor_effective_price(base_price, mult_spin.value())
            if base_price > 0:
                price_lbl.setText(f"→ {new_p:,} cr (was {old_price:,})")
            impact_lbl.setText(
                market_editor_trade_impact_summary(
                    entries=list_bases_with_commodity(self._sections, commodity),
                    current_base=base,
                    relation_flag=int(type_cb.currentData()),
                    multiplier=float(mult_spin.value()),
                    base_price=base_price,
                    base_index=self._base_index,
                    tr=self._tr,
                )
            )

        mult_spin.valueChanged.connect(lambda _: _upd())
        type_cb.currentIndexChanged.connect(lambda _: _upd())
        _upd()

        # Stock min/max
        row_s = QHBoxLayout()
        row_s.addWidget(QLabel("Stock Min"))
        smin_spin = QSpinBox()
        smin_spin.setRange(0, 999999)
        smin_spin.setValue(data.get("stock_min", 0))
        row_s.addWidget(smin_spin)
        row_s.addWidget(QLabel("Stock Max"))
        smax_spin = QSpinBox()
        smax_spin.setRange(-1, 999999)
        smax_spin.setValue(data.get("stock_max", 0))
        row_s.addWidget(smax_spin)
        fl.addLayout(row_s)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(patch_dlg.accept)
        bb.rejected.connect(patch_dlg.reject)
        fl.addWidget(bb)

        if patch_dlg.exec() != QDialog.Accepted:
            return

        # Apply patches
        new_mult = trade_route_format_multiplier(mult_spin.value())
        self._sections, c1 = trade_route_patch_marketgood_field(
            self._sections, base=base, commodity=commodity, field_index=6, new_value=new_mult,
        )
        self._sections, c2 = trade_route_patch_marketgood_field(
            self._sections, base=base, commodity=commodity, field_index=5, new_value=str(int(type_cb.currentData())),
        )
        self._sections, c3 = trade_route_patch_marketgood_field(
            self._sections, base=base, commodity=commodity, field_index=3, new_value=str(smin_spin.value()),
        )
        self._sections, c4 = trade_route_patch_marketgood_field(
            self._sections, base=base, commodity=commodity, field_index=4, new_value=str(smax_spin.value()),
        )
        if c1 or c2 or c3 or c4:
            self.has_changes = True
            self.result_sections = self._sections
        self._refresh_table()

    def _on_commodity_matrix(self):
        """Show which bases buy/sell a selected commodity."""
        comm_dlg = QDialog(self)
        comm_dlg.setWindowTitle(self._tr("trade.market_editor.commodity_matrix"))
        comm_dlg.setMinimumSize(600, 400)
        vl = QVBoxLayout(comm_dlg)

        row_sel = QHBoxLayout()
        row_sel.addWidget(QLabel(self._tr("trade.market_editor.col.commodity")))
        comm_cb = QComboBox()
        comm_cb.setEditable(True)
        for nick, disp in sorted(self._commodity_display_map.items()):
            comm_cb.addItem(f"{disp} ({nick})", nick)
        row_sel.addWidget(comm_cb, 1)
        vl.addLayout(row_sel)

        tbl = QTableWidget(0, 4)
        tbl.setHorizontalHeaderLabels(["Base", "System", "Type", "Multiplier"])
        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        header = tbl.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, 4):
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        vl.addWidget(tbl, 1)

        def _refresh_matrix():
            nick = str(comm_cb.currentData() or "").strip().lower()
            if not nick:
                tbl.setRowCount(0)
                return
            entries = list_bases_with_commodity(self._sections, nick)
            tbl.setRowCount(len(entries))
            for i, e in enumerate(entries):
                base_nick = e["base"]
                info = self._base_index.get(base_nick, {})
                disp = info.get("display_name", base_nick)
                sys_nick = info.get("system", "?")
                rtype = market_editor_type_text(e["relation_flag"], tr=self._tr)
                tbl.setItem(i, 0, QTableWidgetItem(f"{disp} ({base_nick})"))
                tbl.setItem(i, 1, QTableWidgetItem(sys_nick))
                tbl.setItem(i, 2, QTableWidgetItem(rtype))
                tbl.setItem(i, 3, QTableWidgetItem(f"{e['multiplier']:.4f}"))

        comm_cb.currentIndexChanged.connect(lambda _: _refresh_matrix())
        if comm_cb.count() > 0:
            _refresh_matrix()

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(comm_dlg.reject)
        vl.addWidget(bb)
        comm_dlg.exec()
