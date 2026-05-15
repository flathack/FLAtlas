from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QVector3D

from fl_editor.base_assembly_preview import (
    BaseAssemblyPreviewView,
    _base_assembly_render_scene_data,
    _base_assembly_should_build_wireframes,
)
from fl_editor.freelancer_mesh_data import FreelancerBounds
from fl_editor.native_preview_scene_data import NativePreviewSceneData


@dataclass(frozen=True)
class _FakeNativeGeometry:
    model_name: str
    level_name: str | None
    part_name: str | None
    group_start: int
    group_count: int
    positions: tuple[tuple[float, float, float], ...]
    indices: tuple[int, ...]
    vertex_stride: int
    index_size: int
    confidence: str
    bounds: FreelancerBounds


def _fake_geometry(
    *,
    level_name: str = "Level0",
    part_name: str = "Part_Test",
    radius: float = 1.0,
    positions: tuple[tuple[float, float, float], ...] | None = None,
    indices: tuple[int, ...] | None = None,
) -> _FakeNativeGeometry:
    return _FakeNativeGeometry(
        model_name=f"{part_name.lower()}_{level_name.lower()}.3db",
        level_name=level_name,
        part_name=part_name,
        group_start=0,
        group_count=1,
        positions=positions or ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=indices or (0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(-radius, -radius, -radius), max_xyz=(radius, radius, radius), radius=radius),
    )


def _scene_data(
    geometries: tuple[_FakeNativeGeometry, ...],
    *,
    all_geometries: tuple[_FakeNativeGeometry, ...] = (),
) -> NativePreviewSceneData:
    bounds = geometries[0].bounds if geometries else FreelancerBounds(
        min_xyz=(-1.0, -1.0, -1.0),
        max_xyz=(1.0, 1.0, 1.0),
        radius=1.0,
    )
    return NativePreviewSceneData(
        geometries=geometries,
        primary_geometry=geometries[0] if geometries else None,
        bounds=bounds,
        part_names=tuple(geometry.part_name or geometry.model_name for geometry in geometries),
        texture_path=None,
        geometry_texture_paths=tuple(None for _geometry in geometries),
        all_geometries=all_geometries,
        all_geometry_texture_paths=tuple(None for _geometry in all_geometries),
    )


def test_base_assembly_preview_uses_coarsest_lod_for_native_scene_data():
    fine = _fake_geometry(level_name="Level0", radius=10.0)
    coarse = _fake_geometry(level_name="Level2", radius=10.0)
    scene_data = _scene_data((fine,), all_geometries=(fine, coarse))

    render_data, skip_reason = _base_assembly_render_scene_data(scene_data)

    assert skip_reason is None
    assert render_data is not None
    assert render_data.geometries == (coarse,)


def test_base_assembly_preview_uses_bounds_proxy_when_native_geometry_exceeds_budget(monkeypatch):
    import fl_editor.base_assembly_preview as preview_mod

    monkeypatch.setattr(preview_mod, "_BASE_ASSEMBLY_MAX_NATIVE_GEOMETRIES", 1)
    monkeypatch.setattr(preview_mod, "_BASE_ASSEMBLY_MAX_NATIVE_VERTICES", 2)
    monkeypatch.setattr(preview_mod, "_BASE_ASSEMBLY_MAX_NATIVE_INDICES", 2)
    geometry = _fake_geometry(
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        indices=(0, 1, 2, 0, 2, 3),
    )
    scene_data = _scene_data((geometry,))

    render_data, skip_reason = _base_assembly_render_scene_data(scene_data)

    assert skip_reason is not None
    assert render_data is not None
    assert render_data.geometries == ()
    assert render_data.bounds == scene_data.bounds


def test_base_assembly_preview_simplifies_oversized_geometry_instead_of_using_proxy(monkeypatch):
    import fl_editor.base_assembly_preview as preview_mod

    monkeypatch.setattr(preview_mod, "_BASE_ASSEMBLY_MAX_NATIVE_GEOMETRIES", 1)
    monkeypatch.setattr(preview_mod, "_BASE_ASSEMBLY_MAX_NATIVE_VERTICES", 3)
    monkeypatch.setattr(preview_mod, "_BASE_ASSEMBLY_MAX_NATIVE_INDICES", 3)
    geometry = _fake_geometry(
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        indices=(0, 1, 2, 0, 2, 3),
    )
    scene_data = _scene_data((geometry,))

    render_data, skip_reason = _base_assembly_render_scene_data(scene_data)

    assert skip_reason is None
    assert render_data is not None
    assert len(render_data.geometries) == 1
    assert len(render_data.geometries[0].positions) == 3
    assert len(render_data.geometries[0].indices) == 3
    assert render_data.bounds == scene_data.bounds


def test_base_assembly_preview_skips_wireframes_when_index_budget_is_exceeded(monkeypatch):
    import fl_editor.base_assembly_preview as preview_mod

    monkeypatch.setattr(preview_mod, "_BASE_ASSEMBLY_MAX_WIREFRAME_INDICES", 5)
    geometry = _fake_geometry(indices=(0, 1, 2, 0, 2, 1))

    assert _base_assembly_should_build_wireframes((geometry,)) is False


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


def test_base_assembly_preview_uses_prepared_payload_before_scene_resolver():
    view = BaseAssemblyPreviewView.__new__(BaseAssemblyPreviewView)
    target = object()
    payload_scene_data = object()
    resolver_calls: list[object] = []

    class _Payload:
        scene_data = payload_scene_data

    view._native_scene_overrides = {}
    view._native_scene_prepared_payload_resolver = lambda obj: _Payload()
    view._native_scene_resolver = lambda obj: resolver_calls.append(obj) or None
    view._obj_key = lambda obj: 123

    assert view._scene_data_for_object(target) is payload_scene_data
    assert resolver_calls == []
    assert view._native_scene_overrides[123] is payload_scene_data


def test_set_selected_native_scene_data_none_clears_override():
    view = BaseAssemblyPreviewView.__new__(BaseAssemblyPreviewView)
    target = object()
    payload = object()
    view._native_scene_overrides = {123: payload}
    view._obj_key = lambda obj: 123

    view.set_selected_native_scene_data(target, None)

    assert 123 not in view._native_scene_overrides


def test_base_assembly_preview_clear_retains_qt3d_entities_until_widget_teardown():
    class _EntityStub:
        def __init__(self):
            self.enabled = True
            self.delete_later_calls = 0
            self.set_parent_calls = 0

        def setEnabled(self, value):
            self.enabled = bool(value)

        def deleteLater(self):
            self.delete_later_calls += 1

        def setParent(self, _parent):
            self.set_parent_calls += 1

    root = _EntityStub()
    wire = _EntityStub()
    grid = _EntityStub()
    axis = _EntityStub()
    item = type("Item", (), {"root_entity": root})()

    view = BaseAssemblyPreviewView.__new__(BaseAssemblyPreviewView)
    view._items_by_key = {1: item}
    view._wireframe_entities = [wire]
    view._ground_grid_entity = grid
    view._axis_indicator_entity = axis
    view._pending_deletions = []

    view._clear_item_entities()

    assert root.enabled is False
    assert wire.enabled is False
    assert grid.enabled is False
    assert axis.enabled is False
    assert view._pending_deletions == [grid, axis, root]
    assert root.delete_later_calls == 0
    assert grid.delete_later_calls == 0
    assert axis.delete_later_calls == 0
    assert root.set_parent_calls == 0


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
