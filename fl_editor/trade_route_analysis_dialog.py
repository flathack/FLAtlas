"""Dialogs for trade-route market analysis and validation."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .trade_route_analysis import (
    find_best_buyers,
    find_best_sellers,
    find_commodities_without_sink,
    validate_market_sections,
)


def open_trade_route_analysis_dialog(
    parent,
    *,
    sections: list[tuple[str, list[tuple[str, str]]]],
    base_index: dict[str, dict],
    commodity_base_prices: dict[str, int],
    commodity_display_map: dict[str, str],
    tr,
    initial_commodity: str = "",
) -> None:
    dlg = _TradeRouteAnalysisDialog(
        parent,
        sections=sections,
        base_index=base_index,
        commodity_base_prices=commodity_base_prices,
        commodity_display_map=commodity_display_map,
        tr=tr,
        initial_commodity=initial_commodity,
    )
    dlg.exec()


class _TradeRouteAnalysisDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        sections,
        base_index,
        commodity_base_prices,
        commodity_display_map,
        tr,
        initial_commodity,
    ):
        super().__init__(parent)
        self._sections = sections
        self._base_index = base_index
        self._commodity_base_prices = {
            str(key).strip().lower(): int(value)
            for key, value in dict(commodity_base_prices).items()
            if str(key).strip()
        }
        self._commodity_display_map = {
            str(key).strip().lower(): str(value)
            for key, value in dict(commodity_display_map).items()
            if str(key).strip()
        }
        self._tr = tr

        self.setWindowTitle(tr("trade.analysis.title"))
        self.resize(980, 640)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        subtitle = QLabel(tr("trade.analysis.subtitle"))
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        tabs = QTabWidget()
        root.addWidget(tabs, 1)

        tabs.addTab(self._build_validation_tab(), tr("trade.analysis.tab.validation"))
        tabs.addTab(self._build_commodity_tab(initial_commodity), tr("trade.analysis.tab.commodity"))
        tabs.addTab(self._build_coverage_tab(), tr("trade.analysis.tab.coverage"))

        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def _commodity_label(self, commodity: str) -> str:
        key = str(commodity or "").strip().lower()
        return self._commodity_display_map.get(key, commodity)

    def _base_label(self, base_nick: str) -> str:
        info = self._base_index.get(str(base_nick or "").strip().lower(), {})
        disp = str(info.get("display_name", "") or "").strip()
        nick = str(base_nick or "").strip().lower()
        if disp and disp.lower() != nick:
            return f"{disp} ({nick})"
        return nick

    def _base_system(self, base_nick: str) -> str:
        info = self._base_index.get(str(base_nick or "").strip().lower(), {})
        return str(info.get("system", "?") or "?")

    def _all_known_commodities(self) -> list[str]:
        known = {
            str(key).strip().lower()
            for key in self._commodity_base_prices.keys()
            if str(key).strip()
        }
        known.update(
            str(key).strip().lower()
            for key in self._commodity_display_map.keys()
            if str(key).strip()
        )
        return sorted(known)

    def _build_validation_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        issues = validate_market_sections(
            self._sections,
            known_bases=set(self._base_index.keys()),
            known_commodities=set(self._all_known_commodities()),
        )
        error_count = sum(1 for issue in issues if str(issue.get("severity")) == "error")
        warning_count = sum(1 for issue in issues if str(issue.get("severity")) == "warning")

        summary = QLabel(
            self._tr("trade.analysis.validation.summary").format(
                total=len(issues),
                errors=error_count,
                warnings=warning_count,
            )
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(
            [
                self._tr("trade.analysis.col.severity"),
                self._tr("trade.analysis.col.base"),
                self._tr("trade.analysis.col.commodity"),
                self._tr("trade.analysis.col.message"),
            ]
        )
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setRowCount(len(issues))
        for row_index, issue in enumerate(issues):
            table.setItem(row_index, 0, QTableWidgetItem(str(issue.get("severity", ""))))
            table.setItem(row_index, 1, QTableWidgetItem(self._base_label(str(issue.get("base", "")))))
            commodity = str(issue.get("commodity", "") or "")
            table.setItem(row_index, 2, QTableWidgetItem(self._commodity_label(commodity) if commodity else ""))
            table.setItem(row_index, 3, QTableWidgetItem(str(issue.get("message", ""))))
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table, 1)
        return panel

    def _build_commodity_tab(self, initial_commodity: str) -> QWidget:
        from PySide6.QtWidgets import QComboBox

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        select_row = QHBoxLayout()
        select_row.addWidget(QLabel(self._tr("trade.analysis.commodity_picker")))
        commodity_combo = QComboBox()
        commodity_combo.setEditable(True)
        commodities = self._all_known_commodities()
        for commodity in commodities:
            label = self._commodity_label(commodity)
            text = f"{label} ({commodity})" if label.lower() != commodity.lower() else label
            commodity_combo.addItem(text, commodity)
        select_row.addWidget(commodity_combo, 1)
        layout.addLayout(select_row)

        summary = QLabel("")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        split = QSplitter(Qt.Horizontal)
        layout.addWidget(split, 1)

        sellers_table = QTableWidget(0, 4)
        sellers_table.setHorizontalHeaderLabels(
            [
                self._tr("trade.analysis.col.base"),
                self._tr("trade.analysis.col.system"),
                self._tr("trade.analysis.col.effective_price"),
                self._tr("trade.analysis.col.multiplier"),
            ]
        )
        buyers_table = QTableWidget(0, 4)
        buyers_table.setHorizontalHeaderLabels(
            [
                self._tr("trade.analysis.col.base"),
                self._tr("trade.analysis.col.system"),
                self._tr("trade.analysis.col.effective_price"),
                self._tr("trade.analysis.col.multiplier"),
            ]
        )
        for table in (sellers_table, buyers_table):
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.horizontalHeader().setStretchLastSection(True)

        sellers_panel = QWidget()
        sellers_layout = QVBoxLayout(sellers_panel)
        sellers_layout.setContentsMargins(0, 0, 0, 0)
        sellers_layout.setSpacing(6)
        sellers_layout.addWidget(QLabel(self._tr("trade.analysis.best_sellers")))
        sellers_layout.addWidget(sellers_table, 1)

        buyers_panel = QWidget()
        buyers_layout = QVBoxLayout(buyers_panel)
        buyers_layout.setContentsMargins(0, 0, 0, 0)
        buyers_layout.setSpacing(6)
        buyers_layout.addWidget(QLabel(self._tr("trade.analysis.best_buyers")))
        buyers_layout.addWidget(buyers_table, 1)

        split.addWidget(sellers_panel)
        split.addWidget(buyers_panel)
        split.setSizes([480, 480])

        def _populate_price_table(table: QTableWidget, rows: list[dict]) -> None:
            table.setRowCount(len(rows))
            for row_index, item in enumerate(rows):
                base = str(item.get("base", ""))
                table.setItem(row_index, 0, QTableWidgetItem(self._base_label(base)))
                table.setItem(row_index, 1, QTableWidgetItem(self._base_system(base)))
                table.setItem(row_index, 2, QTableWidgetItem(str(item.get("effective_price", 0))))
                table.setItem(row_index, 3, QTableWidgetItem(f"{float(item.get('multiplier', 0.0)):.4f}"))

        def _refresh() -> None:
            commodity = str(commodity_combo.currentData() or commodity_combo.currentText() or "").strip().lower()
            if not commodity:
                summary.setText(self._tr("trade.analysis.commodity.empty"))
                sellers_table.setRowCount(0)
                buyers_table.setRowCount(0)
                return
            sellers = find_best_sellers(
                self._sections,
                commodity,
                commodity_base_prices=self._commodity_base_prices,
                known_bases=set(self._base_index.keys()),
            )
            buyers = find_best_buyers(
                self._sections,
                commodity,
                commodity_base_prices=self._commodity_base_prices,
                known_bases=set(self._base_index.keys()),
            )
            summary.setText(
                self._tr("trade.analysis.commodity.summary").format(
                    commodity=self._commodity_label(commodity),
                    sellers=len(sellers),
                    buyers=len(buyers),
                )
            )
            _populate_price_table(sellers_table, sellers)
            _populate_price_table(buyers_table, buyers)

        commodity_combo.currentIndexChanged.connect(lambda _index: _refresh())
        if initial_commodity:
            match_index = commodity_combo.findData(str(initial_commodity).strip().lower())
            if match_index >= 0:
                commodity_combo.setCurrentIndex(match_index)
        _refresh()
        return panel

    def _build_coverage_tab(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        orphaned = find_commodities_without_sink(
            self._sections,
            set(self._all_known_commodities()),
            known_bases=set(self._base_index.keys()),
            commodity_base_prices=self._commodity_base_prices,
        )
        summary = QLabel(
            self._tr("trade.analysis.coverage.summary").format(count=len(orphaned))
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(
            [
                self._tr("trade.analysis.col.commodity"),
                self._tr("trade.analysis.col.message"),
            ]
        )
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setRowCount(len(orphaned))
        for row_index, commodity in enumerate(orphaned):
            table.setItem(row_index, 0, QTableWidgetItem(f"{self._commodity_label(commodity)} ({commodity})"))
            table.setItem(row_index, 1, QTableWidgetItem(self._tr("trade.analysis.coverage.no_sink")))
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table, 1)
        return panel
