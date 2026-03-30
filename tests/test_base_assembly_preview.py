from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QVector3D

from fl_editor.base_assembly_preview import BaseAssemblyPreviewView


def test_base_assembly_preview_retries_scene_data_after_initial_none():
    view = BaseAssemblyPreviewView.__new__(BaseAssemblyPreviewView)
    target = object()
    calls: list[object] = []
    payload = object()

    def _resolver(obj):
        calls.append(obj)
        return None if len(calls) == 1 else payload

    view._native_scene_overrides = {}
    view._native_scene_resolver = _resolver
    view._obj_key = lambda obj: 123

    assert view._scene_data_for_object(target) is None
    assert view._scene_data_for_object(target) is payload
    assert calls == [target, target]
    assert view._native_scene_overrides[123] is payload


def test_set_selected_native_scene_data_none_clears_override():
    view = BaseAssemblyPreviewView.__new__(BaseAssemblyPreviewView)
    target = object()
    payload = object()
    view._native_scene_overrides = {123: payload}
    view._obj_key = lambda obj: 123

    view.set_selected_native_scene_data(target, None)

    assert 123 not in view._native_scene_overrides


def test_base_assembly_preview_picker_click_emits_selected_object():
    view = BaseAssemblyPreviewView.__new__(BaseAssemblyPreviewView)
    target = object()
    selected_calls: list[object] = []
    menu_calls: list[tuple[object, object]] = []

    class _SignalStub:
        def __init__(self, sink):
            self._sink = sink

        def emit(self, *args):
            self._sink.append(args if len(args) != 1 else args[0])

    class _PickEvent:
        def button(self):
            return Qt.LeftButton

    view.object_selected = _SignalStub(selected_calls)
    view.context_menu_requested = _SignalStub(menu_calls)
    view._suppress_next_pick = False

    view._handle_object_picker_clicked(target, _PickEvent())

    assert selected_calls == [target]
    assert menu_calls == []


def test_base_assembly_preview_camera_state_roundtrip_preserves_zoom_scaled_distance():
    class _FakeCamera:
        def __init__(self):
            self._center = QVector3D(0.0, 0.0, 0.0)
            self._position = QVector3D(5.0, 0.0, 10.0)

        def viewCenter(self):
            return self._center

        def position(self):
            return self._position

        def setViewCenter(self, center):
            self._center = center

        def setPosition(self, position):
            self._position = position

    source = BaseAssemblyPreviewView.__new__(BaseAssemblyPreviewView)
    source._camera = _FakeCamera()
    source._preview_zoom_factor = 2.0
    source._camera_distance = 22.360679774997898

    state = source.get_camera_state()

    target = BaseAssemblyPreviewView.__new__(BaseAssemblyPreviewView)
    target._camera = _FakeCamera()
    target._preview_zoom_factor = 2.0
    target._max_orbit_distance_scene = 3500.0
    target._camera_distance = 0.0
    target._camera_yaw_deg = 0.0
    target._camera_pitch_deg = 0.0
    target.set_camera_state(state)

    assert round(float(target._camera.position().x()), 4) == 5.0
    assert round(float(target._camera.position().z()), 4) == 10.0
    assert round(float(target._camera_distance), 4) == round(float(state["orbit_distance"]), 4)


def test_base_assembly_preview_refresh_gizmo_state_tracks_selection_and_axis():
    class _EntityStub:
        def __init__(self):
            self.enabled = None

        def setEnabled(self, value):
            self.enabled = bool(value)

    class _MaterialStub:
        def __init__(self):
            self.diffuse = None

        def setDiffuse(self, value):
            self.diffuse = value

        def setAmbient(self, _value):
            return None

    item_selected = type("Item", (), {"gizmo_entities": {}})()
    item_other = type("Item", (), {"gizmo_entities": {}})()
    for item in (item_selected, item_other):
        for axis in ("x", "y", "z"):
            item.gizmo_entities[axis] = _EntityStub()
            item.gizmo_entities[f"{axis}_material"] = _MaterialStub()

    view = BaseAssemblyPreviewView.__new__(BaseAssemblyPreviewView)
    view._items_by_key = {1: item_selected, 2: item_other}
    view._selected_key = 1
    view._interaction_mode = "move"
    view._transform_axis = "y"

    view._refresh_gizmo_state()

    # 3D gizmo entities are always disabled (replaced by 2D overlay)
    assert item_selected.gizmo_entities["x"].enabled is False
    assert item_selected.gizmo_entities["y"].enabled is False
    assert item_other.gizmo_entities["x"].enabled is False


def test_base_assembly_preview_event_filter_accepts_qt3d_window_events(monkeypatch):
    view = BaseAssemblyPreviewView.__new__(BaseAssemblyPreviewView)
    window = object()
    container = object()
    called: list[str] = []
    view._view3d = window
    view._container = container

    monkeypatch.setattr("fl_editor.base_assembly_preview.QT3D_AVAILABLE", True)
    monkeypatch.setattr(view, "_handle_wheel", lambda event: called.append("wheel") or True)

    class _WheelEvent:
        def type(self):
            return QEvent.Wheel

    assert view.eventFilter(window, _WheelEvent()) is True
    assert called == ["wheel"]


def test_base_assembly_preview_orbit_drag_keeps_horizontal_and_flips_vertical_to_natural_direction():
    view = BaseAssemblyPreviewView.__new__(BaseAssemblyPreviewView)
    view._camera_yaw_deg = 0.0
    view._camera_pitch_deg = 0.0
    applied: list[tuple[float, float]] = []
    view._apply_camera_pose = lambda: applied.append((view._camera_yaw_deg, view._camera_pitch_deg))

    view._orbit_camera(-10.0, -10.0)

    assert round(float(view._camera_yaw_deg), 3) == 3.5
    assert round(float(view._camera_pitch_deg), 3) == -2.5
    assert applied == [(view._camera_yaw_deg, view._camera_pitch_deg)]