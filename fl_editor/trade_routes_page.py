from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from .ui_helpers import configure_trade_routes_table, connect_trade_route_filter_controls


def build_trade_routes_page(window, *, tr):
    page = QWidget()
    root = QVBoxLayout(page)
    root.setContentsMargins(10, 10, 10, 10)
    root.setSpacing(8)

    window.trade_title_lbl = QLabel(tr("trade.title"))
    window.trade_title_lbl.setStyleSheet("font-size: 15pt; font-weight: bold;")
    root.addWidget(window.trade_title_lbl)

    window.trade_subtitle_lbl = QLabel(tr("trade.subtitle"))
    window.trade_subtitle_lbl.setWordWrap(True)
    window.trade_subtitle_lbl.setStyleSheet("")
    root.addWidget(window.trade_subtitle_lbl)

    window.trade_content_split = QSplitter(Qt.Vertical)
    root.addWidget(window.trade_content_split, 1)

    top_panel = QWidget()
    top_l = QVBoxLayout(top_panel)
    top_l.setContentsMargins(0, 0, 0, 0)
    top_l.setSpacing(6)

    filter_row = QWidget()
    fl = QHBoxLayout(filter_row)
    fl.setContentsMargins(0, 0, 0, 0)
    fl.setSpacing(6)

    window.trade_filter_commodity_cb = QComboBox()
    window.trade_filter_commodity_cb.setEditable(True)
    window.trade_filter_commodity_cb.setMinimumWidth(230)
    window.trade_filter_commodity_lbl = QLabel(tr("trade.filter.commodity"))
    fl.addWidget(window.trade_filter_commodity_lbl)
    fl.addWidget(window.trade_filter_commodity_cb)

    window.trade_filter_min_profit = QDoubleSpinBox()
    window.trade_filter_min_profit.setRange(0.0, 1_000_000.0)
    window.trade_filter_min_profit.setDecimals(0)
    window.trade_filter_min_profit.setValue(150.0)
    window.trade_filter_min_profit.setSuffix(" cr")
    window.trade_filter_min_profit_lbl = QLabel(tr("trade.filter.min_profit"))
    fl.addWidget(window.trade_filter_min_profit_lbl)
    fl.addWidget(window.trade_filter_min_profit)

    window.trade_filter_same_system_cb = QCheckBox(tr("trade.filter.same_system"))
    fl.addWidget(window.trade_filter_same_system_cb)

    window.trade_filter_search = QLineEdit()
    window.trade_filter_search.setPlaceholderText(tr("trade.filter.search_ph"))
    window.trade_filter_search.setMinimumWidth(220)
    fl.addWidget(window.trade_filter_search, 1)

    window.trade_filter_apply_btn = QPushButton(tr("trade.filter.apply"))
    fl.addWidget(window.trade_filter_apply_btn)
    top_l.addWidget(filter_row)

    # --- Second filter row: max jumps, source/target system ---
    filter_row2 = QWidget()
    fl2 = QHBoxLayout(filter_row2)
    fl2.setContentsMargins(0, 0, 0, 0)
    fl2.setSpacing(6)

    window.trade_filter_max_jumps = QSpinBox()
    window.trade_filter_max_jumps.setRange(0, 100)
    window.trade_filter_max_jumps.setValue(0)
    window.trade_filter_max_jumps.setSpecialValueText("∞")
    window.trade_filter_max_jumps_lbl = QLabel(tr("trade.filter.max_jumps"))
    fl2.addWidget(window.trade_filter_max_jumps_lbl)
    fl2.addWidget(window.trade_filter_max_jumps)

    window.trade_filter_source_system = QComboBox()
    window.trade_filter_source_system.setEditable(True)
    window.trade_filter_source_system.setMinimumWidth(160)
    window.trade_filter_source_system_lbl = QLabel(tr("trade.filter.source_system"))
    fl2.addWidget(window.trade_filter_source_system_lbl)
    fl2.addWidget(window.trade_filter_source_system)

    window.trade_filter_target_system = QComboBox()
    window.trade_filter_target_system.setEditable(True)
    window.trade_filter_target_system.setMinimumWidth(160)
    window.trade_filter_target_system_lbl = QLabel(tr("trade.filter.target_system"))
    fl2.addWidget(window.trade_filter_target_system_lbl)
    fl2.addWidget(window.trade_filter_target_system)

    window.trade_filter_cargo_capacity = QSpinBox()
    window.trade_filter_cargo_capacity.setRange(1, 100000)
    window.trade_filter_cargo_capacity.setValue(1)
    window.trade_filter_cargo_capacity.setSuffix(" u")
    window.trade_filter_cargo_capacity_lbl = QLabel(tr("trade.filter.cargo_capacity"))
    fl2.addWidget(window.trade_filter_cargo_capacity_lbl)
    fl2.addWidget(window.trade_filter_cargo_capacity)

    fl2.addStretch(1)
    top_l.addWidget(filter_row2)

    window.trade_routes_table = QTableWidget(0, 12)
    window._retranslate_trade_route_headers()
    configure_trade_routes_table(window.trade_routes_table)
    top_l.addWidget(window.trade_routes_table, 3)

    controls = QWidget()
    bl = QHBoxLayout(controls)
    bl.setContentsMargins(0, 0, 0, 0)
    bl.setSpacing(8)
    side = QHBoxLayout()
    side.setContentsMargins(0, 0, 0, 0)
    side.setSpacing(6)
    side.addStretch(1)
    window.trade_results_lbl = QLabel(tr("trade.results_count").format(count=0))
    side.addWidget(window.trade_results_lbl)
    bl.addLayout(side, 1)
    top_l.addWidget(controls)
    window.trade_content_split.addWidget(top_panel)

    window.trade_route_scene = QGraphicsScene(window)
    window.trade_route_preview = QGraphicsView(window.trade_route_scene)
    window.trade_route_preview.setMinimumHeight(240)
    window.trade_route_preview.setRenderHint(QPainter.Antialiasing)
    window._apply_trade_preview_theme()
    window.trade_content_split.addWidget(window.trade_route_preview)
    window.trade_content_split.setStretchFactor(0, 1)
    window.trade_content_split.setStretchFactor(1, 1)
    window.trade_content_split.setSizes([500, 500])
    window.trade_content_split.splitterMoved.connect(window._on_trade_preview_splitter_moved)

    window._trade_routes_rows = []
    window._trade_route_commodity_display_map = {}
    window._trade_route_base_index = {}
    window._trade_route_system_cache = {}
    window._trade_route_universe_pos = {}
    window._trade_route_adjacency = {}
    window.trade_routes_table.itemSelectionChanged.connect(window._on_trade_route_selection_changed)
    window.trade_routes_table.customContextMenuRequested.connect(window._on_trade_routes_context_menu)
    connect_trade_route_filter_controls(
        apply_button=window.trade_filter_apply_btn,
        search_edit=window.trade_filter_search,
        commodity_combo=window.trade_filter_commodity_cb,
        min_profit_spin=window.trade_filter_min_profit,
        same_system_checkbox=window.trade_filter_same_system_cb,
        apply_filters=window._apply_trade_route_filters,
        max_jumps_spin=window.trade_filter_max_jumps,
        source_system_combo=window.trade_filter_source_system,
        target_system_combo=window.trade_filter_target_system,
        cargo_capacity_spin=window.trade_filter_cargo_capacity,
    )

    return page
