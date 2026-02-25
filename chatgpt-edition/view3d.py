# view3d.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Tuple
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl

@dataclass
class PickResult:
    obj_id: str

class System3DView(gl.GLViewWidget):
    def __init__(self, on_pick: Callable[[PickResult], None]):
        super().__init__()
        self.on_pick = on_pick
        self.move_mode = False
        self._obj_items: Dict[str, gl.GLGraphicsItem] = {}
        self._obj_pos: Dict[str, np.ndarray] = {}
        self._obj_meta: Dict[str, dict] = {}
        self._selected: Optional[str] = None

        grid = gl.GLGridItem()
        grid.scale(1000, 1000, 1000)
        self.addItem(grid)

        self.setCameraPosition(distance=80000)

    def set_move_mode(self, enabled: bool):
        self.move_mode = enabled

    def clear_scene(self):
        for it in list(self._obj_items.values()):
            self.removeItem(it)
        self._obj_items.clear()
        self._obj_pos.clear()
        self._obj_meta.clear()
        self._selected = None

    def add_object(self, obj_id: str, pos_xyz: Tuple[float,float,float], label: str, is_tradelane: bool):
        pos = np.array(pos_xyz, dtype=float)
        self._obj_pos[obj_id] = pos
        self._obj_meta[obj_id] = {"label": label, "is_tradelane": is_tradelane}

        if is_tradelane:
            # kleiner blauer Punkt, kein Name
            pts = np.array([pos], dtype=float)
            item = gl.GLScatterPlotItem(pos=pts, size=6, color=(0.2, 0.5, 1.0, 1.0))
            self.addItem(item)
            self._obj_items[obj_id] = item
        else:
            pts = np.array([pos], dtype=float)
            item = gl.GLScatterPlotItem(pos=pts, size=10, color=(0.9, 0.9, 0.9, 1.0))
            self.addItem(item)
            self._obj_items[obj_id] = item
            # Label in 3D ist in pyqtgraph eher aufwändig; erstmal in Sidebar/Statusbar anzeigen.

    def add_zone_visual(self, center_xyz: Tuple[float,float,float], radius: float):
        # visuell, aber nicht pickbar: wir speichern keine obj_id dafür
        md = gl.MeshData.sphere(rows=10, cols=20, radius=radius)
        m = gl.GLMeshItem(meshdata=md, smooth=True, color=(1.0, 0.3, 0.7, 0.12), shader="shaded", drawEdges=False)
        m.translate(center_xyz[0], center_xyz[1], center_xyz[2])
        self.addItem(m)

    def mousePressEvent(self, ev):
        # Sehr vereinfachtes Picking: wir nehmen den nächstliegenden Punkt zur Kamera-Ray Projektion NICHT korrekt.
        # Für echtes Picking: Raycast im View + Distanz zu Punkten. Hier MVP: click toggles selection by proximity on screen.
        if ev.button() == pg.QtCore.Qt.LeftButton:
            pos = ev.position()
            picked = self._pick_nearest(pos.x(), pos.y())
            if picked:
                self._selected = picked
                self.on_pick(PickResult(obj_id=picked))
        super().mousePressEvent(ev)

    def _pick_nearest(self, x: float, y: float) -> Optional[str]:
        # crude heuristic: project 3D->2D using camera transform is non-trivial here; keep placeholder
        # Return first object deterministically to keep it running; replace with real picking later.
        return next(iter(self._obj_items.keys()), None)

    def move_selected(self, dx: float, dy: float, dz: float):
        if not self.move_mode or not self._selected:
            return
        obj_id = self._selected
        self._obj_pos[obj_id] = self._obj_pos[obj_id] + np.array([dx, dy, dz], dtype=float)
        # update visual
        it = self._obj_items[obj_id]
        pts = np.array([self._obj_pos[obj_id]], dtype=float)
        if isinstance(it, gl.GLScatterPlotItem):
            it.setData(pos=pts)
