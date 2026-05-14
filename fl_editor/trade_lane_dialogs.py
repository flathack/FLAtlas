"""Trade lane dialog widgets used by the dialog facade."""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .i18n import tr
from .simple_dialog_logic import build_trade_lane_payload
from .ui_helpers import configure_contains_completer


class TradeLaneDialog(QDialog):
    """Dialog zum Konfigurieren einer neuen Tradelane zwischen zwei Punkten."""

    # Bekannte Loadouts
    _LOADOUTS = [
        "trade_lane_ring_li_01", "trade_lane_ring_li_02",
        "trade_lane_ring_li_03", "trade_lane_ring_br_01",
        "trade_lane_ring_br_02", "trade_lane_ring_co_01",
        "trade_lane_ring_ku_01", "trade_lane_ring_rh_01",
    ]
    _PILOTS = [
        "pilot_solar_easiest", "pilot_solar_easy", "pilot_solar_hard",
    ]

    def __init__(self, parent, *,
                 system_nick: str,
                 start_num: int,
                 ring_count: int,
                 distance: float,
                 factions: list[str],
                 extra_loadouts: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.tradelane_create"))
        self.setMinimumWidth(440)
        self._distance = distance

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        # Anzahl Ringe (vorberechnet, editierbar)
        self.count_spin = QSpinBox()
        self.count_spin.setRange(2, 200)
        self.count_spin.setValue(ring_count)
        form.addRow(tr("dlg.ring_count"), self.count_spin)

        # Abstand zwischen Ringen
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(500, 50000)
        self.spacing_spin.setSingleStep(500)
        self.spacing_spin.setValue(7500)
        self.spacing_spin.setSuffix(tr("dlg.units"))
        self.spacing_spin.valueChanged.connect(self._on_spacing_changed)
        form.addRow(tr("dlg.spacing"), self.spacing_spin)

        # Startnummer
        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, 99999)
        self.start_spin.setValue(start_num)
        form.addRow(tr("dlg.start_number"), self.start_spin)

        # Loadout
        loadouts = list(self._LOADOUTS)
        if extra_loadouts:
            for lo in extra_loadouts:
                if lo not in loadouts:
                    loadouts.append(lo)
        loadouts.sort(key=str.lower)
        self.loadout_cb = QComboBox()
        self.loadout_cb.setEditable(True)
        self.loadout_cb.addItems(loadouts)
        self.loadout_cb.setCurrentText(loadouts[0] if loadouts else "")
        form.addRow("Loadout:", self.loadout_cb)

        # Reputation
        self.reputation_cb = QComboBox()
        self.reputation_cb.setEditable(True)
        self.reputation_cb.addItems(factions)
        configure_contains_completer(self.reputation_cb)
        form.addRow("Reputation:", self.reputation_cb)

        # Difficulty
        self.diff_spin = QSpinBox()
        self.diff_spin.setRange(1, 7)
        self.diff_spin.setValue(1)
        form.addRow("Difficulty Level:", self.diff_spin)

        # Pilot
        self.pilot_cb = QComboBox()
        self.pilot_cb.setEditable(True)
        self.pilot_cb.addItems(self._PILOTS)
        self.pilot_cb.setCurrentText("pilot_solar_easiest")
        form.addRow("Pilot:", self.pilot_cb)

        # Anzeigename
        self.ids_name_edit = QLineEdit("")
        self.ids_name_edit.setPlaceholderText(tr("dlg.tradelane_name_ph"))
        form.addRow(tr("dlg.tradelane_name"), self.ids_name_edit)

        # tradelane_space_name Start
        self.space_name_start_edit = QLineEdit("")
        self.space_name_start_edit.setPlaceholderText(tr("dlg.tradelane_start_name_ph"))
        form.addRow(tr("dlg.tradelane_start_name"), self.space_name_start_edit)

        # tradelane_space_name Ende
        self.space_name_end_edit = QLineEdit("")
        self.space_name_end_edit.setPlaceholderText(tr("dlg.tradelane_end_name_ph"))
        form.addRow(tr("dlg.tradelane_end_name"), self.space_name_end_edit)

        layout.addLayout(form)

        # Info-Label
        info = QLabel(
            f"System: {system_nick}  •  "
            f"Nicknames: {system_nick}_Trade_Lane_Ring_N\n"
            f"{tr('dlg.spacing_info')}"
        )
        info.setStyleSheet("color:#999; font-size:8pt; margin-top:6px;")
        layout.addWidget(info)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_spacing_changed(self, val: int):
        if val > 0 and self._distance > 0:
            count = max(2, round(self._distance / val) + 1)
            self.count_spin.setValue(count)

    def payload(self) -> dict:
        return build_trade_lane_payload(
            ring_count=self.count_spin.value(),
            spacing=self.spacing_spin.value(),
            start_num=self.start_spin.value(),
            loadout=self.loadout_cb.currentText(),
            reputation=self.reputation_cb.currentText(),
            difficulty_level=self.diff_spin.value(),
            pilot=self.pilot_cb.currentText(),
            ids_name=self.ids_name_edit.text(),
            space_name_start=self.space_name_start_edit.text(),
            space_name_end=self.space_name_end_edit.text(),
        )


# ══════════════════════════════════════════════════════════════════════
#  TradeLaneEditDialog – Bestehende Tradelane-Routen bearbeiten
# ══════════════════════════════════════════════════════════════════════

class TradeLaneEditDialog(QDialog):
    """Dialog zum Verwalten bestehender Tradelane-Routen.

    Zeigt alle erkannten Routen als Liste.  Der User kann:
    - Eine Route komplett löschen
    - Start-/Endpunkt einer Route neu setzen (Positionen verschieben)
    """

    def __init__(self, parent, *, chains: list[list[dict]]):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg.tradelane_edit"))
        self.setMinimumWidth(520)
        self.setMinimumHeight(360)
        self._chains = chains
        self._action: str | None = None
        self._selected_chain_idx: int = -1

        layout = QVBoxLayout(self)

        info = QLabel(tr("dlg.routes_found").format(count=len(chains)))
        info.setStyleSheet("font-weight:bold; margin-bottom:4px;")
        layout.addWidget(info)

        self.chain_list = QListWidget()
        for i, chain in enumerate(chains):
            first = chain[0]["nickname"]
            last = chain[-1]["nickname"]
            count = len(chain)
            route_name = str(chain[0].get("route_name", "") or "").strip() or "-"
            start_name = str(chain[0].get("start_name", "") or "").strip() or "-"
            end_name = str(chain[0].get("end_name", "") or "").strip() or "-"
            item_text = (
                f"Route {i+1}: {first} → {last} ({count} Ringe)\n"
                f"{tr('dlg.tradelane_name')} {route_name} | "
                f"{tr('dlg.tradelane_start_name')} {start_name} | "
                f"{tr('dlg.tradelane_end_name')} {end_name}"
            )
            item = QListWidgetItem(item_text)
            hint = item.sizeHint()
            item.setSizeHint(QSize(hint.width(), hint.height() + 18))
            item.setData(256, i)
            self.chain_list.addItem(item)
        self.chain_list.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self.chain_list)

        # Detail-Box
        self.detail_grp = QGroupBox(tr("dlg.grp_details"))
        dl = QVBoxLayout(self.detail_grp)
        self.detail_lbl = QLabel(tr("dlg.select_route"))
        self.detail_lbl.setWordWrap(True)
        self.detail_lbl.setStyleSheet("font-size:9pt;")
        dl.addWidget(self.detail_lbl)

        name_form = QFormLayout()
        self.route_name_edit = QLineEdit()
        self.start_name_edit = QLineEdit()
        self.end_name_edit = QLineEdit()
        self.route_name_edit.setPlaceholderText(tr("dlg.tradelane_name_ph"))
        self.start_name_edit.setPlaceholderText(tr("dlg.tradelane_start_name_ph"))
        self.end_name_edit.setPlaceholderText(tr("dlg.tradelane_end_name_ph"))
        name_form.addRow(tr("dlg.tradelane_name"), self.route_name_edit)
        name_form.addRow(tr("dlg.tradelane_start_name"), self.start_name_edit)
        name_form.addRow(tr("dlg.tradelane_end_name"), self.end_name_edit)
        dl.addLayout(name_form)

        self.save_names_btn = QPushButton(tr("btn.save"))
        self.save_names_btn.setEnabled(False)
        self.save_names_btn.clicked.connect(self._on_save_names)
        dl.addWidget(self.save_names_btn)

        btn_row = QHBoxLayout()
        self.delete_btn = QPushButton(tr("dlg.delete_route"))
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self.delete_btn)

        self.reposition_btn = QPushButton(tr("dlg.reposition_route"))
        self.reposition_btn.setEnabled(False)
        self.reposition_btn.clicked.connect(self._on_reposition)
        btn_row.addWidget(self.reposition_btn)
        dl.addLayout(btn_row)

        layout.addWidget(self.detail_grp)

        # Schließen
        close_btn = QPushButton(tr("dlg.close"))
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def _on_selection_changed(self, row: int):
        self._selected_chain_idx = row
        enabled = (0 <= row < len(self._chains))
        self.delete_btn.setEnabled(enabled)
        self.reposition_btn.setEnabled(enabled)
        self.save_names_btn.setEnabled(enabled)
        if enabled:
            chain = self._chains[row]
            first = chain[0]
            last = chain[-1]
            route_name = str(first.get("route_name", "") or "").strip() or "-"
            start_name = str(first.get("start_name", "") or "").strip() or "-"
            end_name = str(first.get("end_name", "") or "").strip() or "-"
            self.route_name_edit.setText("" if route_name == "-" else route_name)
            self.start_name_edit.setText("" if start_name == "-" else start_name)
            self.end_name_edit.setText("" if end_name == "-" else end_name)
            self.detail_lbl.setText(
                f"Start: {first['nickname']}  pos=({first.get('pos', '?')})\n"
                f"Ende:  {last['nickname']}  pos=({last.get('pos', '?')})\n"
                f"{tr('dlg.tradelane_name')} {route_name}\n"
                f"{tr('dlg.tradelane_start_name')} {start_name}\n"
                f"{tr('dlg.tradelane_end_name')} {end_name}\n"
                f"Ringe: {len(chain)}   "
                f"Loadout: {first.get('loadout', '?')}   "
                f"Rotation: {first.get('rotate', '?')}"
            )
        else:
            self.route_name_edit.clear()
            self.start_name_edit.clear()
            self.end_name_edit.clear()
            self.detail_lbl.setText(tr("dlg.select_route"))

    def _on_delete(self):
        self._action = "delete"
        self.accept()

    def _on_reposition(self):
        self._action = "reposition"
        self.accept()

    def _on_save_names(self):
        self._action = "update_names"
        self.accept()

    @property
    def action(self) -> str | None:
        return self._action

    @property
    def selected_chain_index(self) -> int:
        return self._selected_chain_idx

    @property
    def edited_names(self) -> tuple[str, str, str]:
        return (
            self.route_name_edit.text().strip(),
            self.start_name_edit.text().strip(),
            self.end_name_edit.text().strip(),
        )


# ══════════════════════════════════════════════════════════════════════
#  ZonePopulationDialog – Zone Population bearbeiten
# ══════════════════════════════════════════════════════════════════════
