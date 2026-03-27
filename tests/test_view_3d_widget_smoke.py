from __future__ import annotations

from dataclasses import dataclass
import pytest
from PySide6.QtGui import QColor

from fl_editor.freelancer_mesh_data import FreelancerBounds
from fl_editor.native_preview_qt3d import QPhongMaterial3D, QTextureMaterial3D
from fl_editor.native_preview_scene_data import NativePreviewSceneData
from fl_editor.qt3d_compat import QT3D_AVAILABLE
from fl_editor.view_3d import System3DView


class _DummySceneItem:
    def __init__(self, nickname: str, data: dict[str, str]):
        self.nickname = nickname
        self.data = data


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


def _dummy_object(nickname: str, **data):
    payload = {
        "pos": "0,0,0",
        "rotate": "0,0,0",
        "archetype": "space_police01",
    }
    payload.update(data)
    return _DummySceneItem(nickname, payload)


def _dummy_zone(nickname: str, **data):
    payload = {
        "pos": "10,0,0",
        "rotate": "0,0,0",
        "size": "1000",
        "shape": "SPHERE",
    }
    payload.update(data)
    return _DummySceneItem(nickname, payload)


def test_system3dview_smoke_builds_scene_and_clears(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station")
    zone = _dummy_zone("zone_li01")

    view.set_data([obj], [zone], 0.01)

    assert obj in view._obj_map
    assert zone in view._zone_map
    assert view._system_radius > 0.0

    view.set_selected(obj)
    assert view._selected_obj is obj

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )
    view.set_selected_native_scene_data(obj, scene_data)
    assert view.get_selected_native_scene_data() is scene_data
    assert view._selected_native_detail_entity is not None
    assert view._obj_sphere_ent[obj].isEnabled() is False
    cached_entity = view._selected_native_detail_entity
    view.center_on_item(obj)
    assert (view._cam_target.x(), view._cam_target.y(), view._cam_target.z()) == (0.5, 0.5, 0.0)
    assert view._cam_distance == 120.0

    other = _dummy_object("li01_station_other")
    view.set_selected_native_scene_data(other, scene_data)
    assert view.get_selected_native_scene_data() is None
    assert view._selected_native_detail_entity is None
    assert view._obj_sphere_ent[obj].isEnabled() is True
    assert scene_data in view._native_detail_entity_cache

    view.set_selected_native_scene_data(obj, scene_data)
    assert view.get_selected_native_scene_data() is scene_data
    assert view._selected_native_detail_entity is cached_entity
    assert scene_data not in view._native_detail_entity_cache

    view.clear_scene()
    assert view._obj_map == {}
    assert view._zone_map == {}


def test_system3dview_common_placeholder_proxies_build_without_errors(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    jumpgate = _dummy_object("li01_jumpgate", archetype="jumpgate_li01")
    buoy = _dummy_object("li01_nav", archetype="nav_buoy")
    platform = _dummy_object("li01_platform", archetype="wplatform")
    depot = _dummy_object("li01_depot", archetype="depot")
    tradelane = _dummy_object("li01_ring", archetype="trade_lane_ring")

    view.set_data([jumpgate, buoy, platform, depot, tradelane], [], 0.01)

    assert len(view._obj_component_refs[jumpgate]) > 20
    assert len(view._obj_component_refs[buoy]) > 10
    assert len(view._obj_component_refs[platform]) > 20
    assert len(view._obj_component_refs[depot]) > 15
    assert len(view._obj_component_refs[tradelane]) > 20


def test_system3dview_placeholder_size_factor_is_capped_conservatively(qapp):
    view = System3DView()
    obj = _dummy_object("li01_station", archetype="station")
    obj._model_world_radius = 100.0

    factor = view._placeholder_size_factor(obj, default_radius=2.6)

    assert factor == pytest.approx(1.45)


def test_system3dview_fallback_placeholder_radii_are_reduced(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    surprise = _dummy_object("li01_surprise", archetype="surprise_object")
    station = _dummy_object("li01_station", archetype="station")
    generic = _dummy_object("li01_generic", archetype="thing")
    view.set_data([surprise, station, generic], [], 0.01)

    assert surprise.radius == pytest.approx(1.2)
    assert station.radius == pytest.approx(1.55)
    assert generic.radius == pytest.approx(1.85)


def test_system3dview_selection_change_clears_native_detail_and_restores_marker(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj_a = _dummy_object("li01_station_a")
    obj_b = _dummy_object("li01_station_b", pos="100,0,0")
    view.set_data([obj_a, obj_b], [], 0.01)
    view.set_selected(obj_a)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )
    view.set_selected_native_scene_data(obj_a, scene_data)

    assert view.get_selected_native_detail_debug_state()["has_detail_entity"] is True
    assert view._obj_sphere_ent[obj_a].isEnabled() is False

    view.set_selected(obj_b)

    state = view.get_selected_native_detail_debug_state()
    assert state["selected_object_nickname"] == "li01_station_b"
    assert state["detail_object_nickname"] is None
    assert state["has_scene_data"] is False
    assert state["has_detail_entity"] is False
    assert view._obj_sphere_ent[obj_a].isEnabled() is True


def test_system3dview_planet_atmosphere_helpers_follow_freelancer_values(qapp):
    view = System3DView()

    obj = _dummy_object(
        "li02_01",
        archetype="planet_watgrncld_3000",
        atmosphere_range="3200",
        burn_color="255, 222, 160",
    )

    ratio = view._planet_atmosphere_radius_ratio(obj, 3000.0)
    color = view._planet_burn_color(obj, QColor(10, 20, 30))

    assert ratio > 1.05
    assert round(ratio, 3) == 1.067
    assert color.getRgb()[:3] == (255, 222, 160)


def test_system3dview_planet_cloud_layer_helper_respects_archetype(qapp):
    view = System3DView()

    cloud_planet = _dummy_object("li02_01", archetype="planet_watgrncld_3000")
    rock_planet = _dummy_object("li02_mojave", archetype="planet_desorgrck_2000")

    assert view._planet_has_cloud_layer(cloud_planet) is True
    assert view._planet_has_cloud_layer(rock_planet) is False


def test_system3dview_refresh_native_scene_previews_builds_incrementally(qapp, tmp_path):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj_a = _dummy_object("li01_station_a")
    obj_b = _dummy_object("li01_station_b", pos="100,0,0")
    view.set_data([obj_a, obj_b], [], 0.01)
    preview_a = tmp_path / "a.obj"
    preview_b = tmp_path / "b.obj"
    preview_a.write_text("a", encoding="utf-8")
    preview_b.write_text("b", encoding="utf-8")
    builds: list[str] = []
    progress: list[dict[str, object]] = []

    view.set_native_scene_resolver(lambda _obj: None)
    view.set_preview_mesh_resolver(lambda obj: preview_a if obj is obj_a else preview_b)
    view.set_native_preview_progress_callback(lambda payload: progress.append(dict(payload)))

    def _fake_build_native_preview_entity(*, parent_ent, preview_data, cache_key, transform_state):
        builds.append(Path(preview_data).name)
        return object(), [preview_data]

    view._build_native_preview_entity = _fake_build_native_preview_entity
    if view._native_preview_batch_timer is not None:
        view._native_preview_batch_timer.stop()

    view.refresh_native_scene_previews()

    assert len(view._native_preview_pending_builds) == 2
    assert builds == []

    view._process_native_preview_build_batch()
    assert len(builds) == 1
    assert len(view._native_preview_pending_builds) == 1

    view._process_native_preview_build_batch()
    assert len(builds) == 2
    assert len(view._native_preview_pending_builds) == 0
    assert progress[0]["active"] is True
    assert progress[-1]["active"] is False


def test_system3dview_native_preview_uses_colored_materials_without_textures(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path="C:\\fake\\texture.dds",
        geometry_texture_paths=("C:\\fake\\texture.dds",),
    )

    detail_root, refs = view._build_native_preview_entity(
        parent_ent=view._root,
        preview_data=scene_data,
        cache_key=("native", 1),
        transform_state={},
    )

    assert detail_root is not None
    assert any(isinstance(ref, QPhongMaterial3D) for ref in refs)
    assert not any(QTextureMaterial3D is not None and isinstance(ref, QTextureMaterial3D) for ref in refs)


def test_system3dview_native_wireframe_toggle_updates_preview_entities(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station")
    view.set_data([obj], [], 0.01)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    view.set_native_scene_resolver(lambda current_obj: scene_data if current_obj is obj else None)
    view.refresh_native_scene_previews()

    refs = view._native_preview_refs_by_obj[obj]
    wireframes = [
        ref for ref in refs
        if callable(getattr(ref, "objectName", None)) and str(ref.objectName()) == "flatlas_native_wireframe"
    ]
    assert wireframes
    assert all(not entity.isEnabled() for entity in wireframes)

    view.set_native_wireframe_visible(True)
    assert all(entity.isEnabled() for entity in wireframes)

    view.set_native_wireframe_visible(False)
    assert all(not entity.isEnabled() for entity in wireframes)


def test_system3dview_schedule_refresh_defers_while_batch_is_running(qapp, tmp_path):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj_a = _dummy_object("li01_station_a")
    obj_b = _dummy_object("li01_station_b", pos="100,0,0")
    view.set_data([obj_a, obj_b], [], 0.01)
    preview_a = tmp_path / "a.obj"
    preview_b = tmp_path / "b.obj"
    preview_a.write_text("a", encoding="utf-8")
    preview_b.write_text("b", encoding="utf-8")

    view.set_native_scene_resolver(lambda _obj: None)
    view.set_preview_mesh_resolver(lambda obj: preview_a if obj is obj_a else preview_b)
    view._build_native_preview_entity = lambda **kwargs: (object(), [kwargs.get("preview_data")])
    if view._native_preview_batch_timer is not None:
        view._native_preview_batch_timer.stop()

    view.refresh_native_scene_previews()
    assert len(view._native_preview_pending_builds) == 2

    view._schedule_native_scene_preview_refresh(30)

    assert len(view._native_preview_pending_builds) == 2
    assert view._native_preview_refresh_after_batch is True


def test_system3dview_builds_large_native_scene_preview_across_multiple_ticks(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    class _SceneData:
        def __init__(self):
            self.geometries = tuple(range(12))

    obj = _dummy_object("li03_large_station")
    view.set_data([obj], [], 0.01)
    view.set_native_scene_resolver(lambda _obj: _SceneData())
    view._native_preview_batch_size = 1

    chunk_calls: list[int] = []
    finalized: list[tuple[object, object]] = []

    def _fake_create_native_preview_root(*, parent_ent, transform_state):
        return object(), []

    def _fake_build_native_preview_geometry_chunk(payload):
        chunk_calls.append(int(payload.get("geometry_index", 0) or 0))
        next_index = int(payload.get("geometry_index", 0) or 0) + 6
        payload["geometry_index"] = next_index
        return next_index >= 12

    def _fake_finalize_native_preview_build(*, obj, cache_key, detail_root, refs):
        finalized.append((obj, detail_root))
        view._native_preview_entity_by_obj[obj] = detail_root
        view._native_preview_refs_by_obj[obj] = refs
        view._native_preview_cache_key_by_obj[obj] = cache_key

    view._create_native_preview_root = _fake_create_native_preview_root
    view._build_native_preview_geometry_chunk = _fake_build_native_preview_geometry_chunk
    view._finalize_native_preview_build = _fake_finalize_native_preview_build
    if view._native_preview_batch_timer is not None:
        view._native_preview_batch_timer.stop()

    view.refresh_native_scene_previews()

    assert len(view._native_preview_pending_builds) == 1
    assert chunk_calls == []

    view._process_native_preview_build_batch()

    assert chunk_calls == [0]
    assert len(view._native_preview_pending_builds) == 1
    assert view._native_preview_progress_done == 0
    assert finalized == []

    view._process_native_preview_build_batch()

    assert chunk_calls == [0, 6]
    assert len(view._native_preview_pending_builds) == 0
    assert view._native_preview_progress_done == 1
    assert len(finalized) == 1


def test_system3dview_limits_native_preview_finalizations_per_tick(qapp, tmp_path):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj_a = _dummy_object("li01_station_a")
    obj_b = _dummy_object("li01_station_b", pos="100,0,0")
    view.set_data([obj_a, obj_b], [], 0.01)
    preview_a = tmp_path / "a.obj"
    preview_b = tmp_path / "b.obj"
    preview_a.write_text("a", encoding="utf-8")
    preview_b.write_text("b", encoding="utf-8")

    view._native_preview_batch_size = 2
    view._native_preview_finalize_budget_per_tick = 1
    view.set_native_scene_resolver(lambda _obj: None)
    view.set_preview_mesh_resolver(lambda obj: preview_a if obj is obj_a else preview_b)
    view._build_native_preview_entity = lambda **kwargs: (object(), [kwargs.get("preview_data")])
    if view._native_preview_batch_timer is not None:
        view._native_preview_batch_timer.stop()

    view.refresh_native_scene_previews()
    view._process_native_preview_build_batch()

    assert len(view._native_preview_entity_by_obj) == 1
    assert len(view._native_preview_pending_builds) == 1

    view._process_native_preview_build_batch()

    assert len(view._native_preview_entity_by_obj) == 2
    assert len(view._native_preview_pending_builds) == 0


def test_system3dview_limits_native_preview_batch_work_by_time_budget(qapp, tmp_path, monkeypatch):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj_a = _dummy_object("li01_station_a")
    obj_b = _dummy_object("li01_station_b", pos="100,0,0")
    obj_c = _dummy_object("li01_station_c", pos="200,0,0")
    view.set_data([obj_a, obj_b, obj_c], [], 0.01)
    preview_a = tmp_path / "a.obj"
    preview_b = tmp_path / "b.obj"
    preview_c = tmp_path / "c.obj"
    preview_a.write_text("a", encoding="utf-8")
    preview_b.write_text("b", encoding="utf-8")
    preview_c.write_text("c", encoding="utf-8")

    view._native_preview_batch_size = 3
    view._native_preview_finalize_budget_per_tick = 3
    view._native_preview_batch_time_budget_ms = 5
    view.set_native_scene_resolver(lambda _obj: None)
    view.set_preview_mesh_resolver(
        lambda obj: preview_a if obj is obj_a else preview_b if obj is obj_b else preview_c
    )
    view._build_native_preview_entity = lambda **kwargs: (object(), [kwargs.get("preview_data")])
    if view._native_preview_batch_timer is not None:
        view._native_preview_batch_timer.stop()

    perf_values = iter([0.0, 0.01, 0.01, 0.01, 0.01])
    monkeypatch.setattr("fl_editor.view_3d.time.perf_counter", lambda: next(perf_values))

    view.refresh_native_scene_previews()
    view._process_native_preview_build_batch()

    assert len(view._native_preview_entity_by_obj) == 1
    assert len(view._native_preview_pending_builds) == 2


def test_system3dview_discard_pending_builds_advances_generation(qapp):
    view = System3DView()

    before = int(getattr(view, "_native_preview_build_generation", 0))

    view._discard_native_preview_pending_builds()

    assert int(getattr(view, "_native_preview_build_generation", 0)) == before + 1


def test_system3dview_skips_stale_generation_payloads(qapp, tmp_path):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station_a")
    view.set_data([obj], [], 0.01)
    preview_a = tmp_path / "a.obj"
    preview_a.write_text("a", encoding="utf-8")
    view._native_preview_pending_builds = [
        {
            "obj": obj,
            "scene_data": preview_a,
            "obj_ent": view._obj_map[obj][0],
            "cache_key": ("preview", "a"),
            "transform_state": {"scale": 1.0, "rotate_euler_deg": (0.0, 0.0, 0.0)},
            "generation": 1,
        }
    ]
    view._native_preview_build_generation = 2
    view._build_native_preview_entity = lambda **kwargs: (object(), [kwargs.get("preview_data")])
    if view._native_preview_batch_timer is not None:
        view._native_preview_batch_timer.stop()

    view._process_native_preview_build_batch()

    assert obj not in view._native_preview_entity_by_obj
    assert view._native_preview_pending_builds == []


def test_system3dview_zone_entities_disable_depth_writes_for_transparent_overlap(qapp, monkeypatch):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    zone = _dummy_zone("zone_overlap_a")
    sentinel = object()
    calls: list[object] = []

    def _fake_material_no_depth_write_refs(material, render_ns):
        calls.append(material)
        return [sentinel]

    monkeypatch.setattr("fl_editor.view_3d.material_no_depth_write_refs", _fake_material_no_depth_write_refs)

    _ent, _tr, refs = view._create_zone_entity(zone, 0.01)

    assert len(calls) == 1
    assert sentinel in refs


def test_system3dview_zone_entities_disable_culling_for_transparent_overlap(qapp, monkeypatch):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    zone = _dummy_zone("zone_overlap_b")
    sentinel = object()
    calls: list[object] = []

    def _fake_material_no_cull_refs(material, render_ns):
        calls.append(material)
        return [sentinel]

    monkeypatch.setattr("fl_editor.view_3d.material_no_cull_refs", _fake_material_no_cull_refs)

    _ent, _tr, refs = view._create_zone_entity(zone, 0.01)

    assert len(calls) == 1
    assert sentinel in refs


def test_system3dview_free_camera_moves_and_stops_immediately(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    view.set_free_camera_active(True)
    start_pos = QVector3D(view._free_camera_pos)
    view._free_camera_keys_down.add(int(Qt.Key_W))

    view._on_free_camera_tick()
    moved_pos = QVector3D(view._free_camera_pos)

    view._free_camera_keys_down.clear()
    view._on_free_camera_tick()
    stopped_pos = QVector3D(view._free_camera_pos)

    assert moved_pos != start_pos
    assert stopped_pos == moved_pos


def test_system3dview_native_detail_debug_state_tracks_multiple_geometries(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station_multi")
    view.set_data([obj], [], 0.01)
    view.set_selected(obj)

    geometry_a = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_A",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="structured-family-split",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    geometry_b = _FakeNativeGeometry(
        model_name="meshB_lod0.3db",
        level_name="Level1",
        part_name="Part_B",
        group_start=1,
        group_count=2,
        positions=((0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="structured-single-block",
        bounds=FreelancerBounds(min_xyz=(-1.0, -1.0, 0.0), max_xyz=(0.0, 0.0, 0.0), radius=1.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry_a, geometry_b),
        primary_geometry=geometry_a,
        bounds=FreelancerBounds(min_xyz=(-1.0, -1.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.5),
        part_names=("Part_A", "Part_B"),
        texture_path=None,
        geometry_texture_paths=(None, None),
        cmp_orientation_debug_rows=(
            ("best_part_name", "Part_A"),
            ("axis_map", "X=+X Y=-Y Z=+Z"),
            ("suggested_up_correction_euler_deg", "0.0, 0.0, 180.0"),
        ),
    )

    view.set_selected_native_scene_data(obj, scene_data)

    state = view.get_selected_native_detail_debug_state()
    assert state["has_scene_data"] is True
    assert state["has_detail_entity"] is True
    assert state["geometry_count"] == 2
    assert state["geometry_confidences"] == ("structured-family-split", "structured-single-block")
    assert state["cmp_orientation_debug_rows"] == (
        ("best_part_name", "Part_A"),
        ("axis_map", "X=+X Y=-Y Z=+Z"),
        ("suggested_up_correction_euler_deg", "0.0, 0.0, 180.0"),
    )


def test_system3dview_missing_native_scene_data_falls_back_to_marker(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station")
    view.set_data([obj], [], 0.01)
    view.set_selected(obj)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )
    view.set_selected_native_scene_data(obj, scene_data)
    assert view._obj_sphere_ent[obj].isEnabled() is False

    view.set_selected_native_scene_data(obj, None)

    state = view.get_selected_native_detail_debug_state()
    assert state["selected_object_nickname"] == "li01_station"
    assert state["detail_object_nickname"] is None
    assert state["has_scene_data"] is False
    assert state["has_detail_entity"] is False
    assert view._obj_sphere_ent[obj].isEnabled() is True


def test_system3dview_refresh_native_scene_previews_renders_nearby_budgeted_models(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    selected = _dummy_object("li01_station_selected")
    nearby = _dummy_object("li01_station_nearby", pos="100,0,0")
    far = _dummy_object("li01_station_far", pos="50000,0,0")
    view.set_data([selected, nearby, far], [], 0.01)
    view.set_selected(selected)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(10.0, 10.0, 0.0), radius=10.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    def _resolver(obj):
        if obj is nearby or obj is far:
            return scene_data
        return None

    view.set_native_scene_resolver(_resolver)
    view.refresh_native_scene_previews()

    assert nearby in view._native_preview_entity_by_obj
    assert selected not in view._native_preview_entity_by_obj
    assert far not in view._native_preview_entity_by_obj


def test_system3dview_prioritizes_smaller_prepared_payloads_for_pending_builds(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj_a = _dummy_object("li01_station_large", pos="100,0,0")
    obj_b = _dummy_object("li01_station_small", pos="200,0,0")
    view.set_data([obj_a, obj_b], [], 0.01)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(10.0, 10.0, 0.0), radius=10.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    class _PreparedPayload:
        def __init__(self, scene_data, geometry_count):
            self.scene_data = scene_data
            self.geometry_count = geometry_count

    view.set_native_scene_resolver(lambda _obj: None)
    view.set_native_scene_prepared_payload_resolver(
        lambda obj: _PreparedPayload(scene_data, 24) if obj is obj_a else _PreparedPayload(scene_data, 4)
    )
    if view._native_preview_batch_timer is not None:
        view._native_preview_batch_timer.stop()

    view.refresh_native_scene_previews()

    assert [payload["obj"] for payload in view._native_preview_pending_builds] == [obj_b, obj_a]


def test_system3dview_staggers_duplicate_cache_keys_across_refresh_cycles(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    selected = _dummy_object("li01_station_selected")
    obj_a = _dummy_object("li01_trade_lane_ring_a", pos="100,0,0", archetype="trade_lane_ring")
    obj_b = _dummy_object("li01_trade_lane_ring_b", pos="200,0,0", archetype="trade_lane_ring")
    view.set_data([selected, obj_a, obj_b], [], 0.01)
    view.set_selected(selected)
    view.set_native_preview_max_distance_fl(-1.0)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(10.0, 10.0, 0.0), radius=10.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    view.set_native_scene_resolver(lambda obj: scene_data if obj in {obj_a, obj_b} else None)
    if view._native_preview_batch_timer is not None:
        view._native_preview_batch_timer.stop()

    view.refresh_native_scene_previews()

    assert [payload["obj"] for payload in view._native_preview_pending_builds] == [obj_a]
    assert view._native_preview_refresh_after_batch is True


def test_system3dview_prioritizes_cached_entity_reattach_over_new_build(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj_cached = _dummy_object("li01_station_cached", pos="100,0,0")
    obj_new = _dummy_object("li01_station_new", pos="200,0,0")
    view.set_data([obj_cached, obj_new], [], 0.01)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(10.0, 10.0, 0.0), radius=10.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    view.set_native_scene_resolver(lambda _obj: scene_data)
    if view._native_preview_batch_timer is not None:
        view._native_preview_batch_timer.stop()
    transform_key = native_detail_transform_cache_key(scale=1.0, rotate_euler_deg=(0.0, 0.0, 0.0))
    cached_key = (scene_data, transform_key)
    view._native_preview_entity_cache[cached_key] = (object(), [])

    view.refresh_native_scene_previews()

    assert [payload["obj"] for payload in view._native_preview_pending_builds] == [obj_cached, obj_new]
    assert view._native_preview_pending_builds[0]["cached_entity_available"] is True
    assert view._native_preview_pending_builds[1]["cached_entity_available"] is False


def test_system3dview_refresh_native_scene_previews_keeps_large_planet_visible(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    selected = _dummy_object("li01_station_selected")
    planet = _dummy_object("li01_planet_far", pos="18000,0,0", archetype="planet_earthgrncld_4000")
    view.set_data([selected, planet], [], 0.01)
    view.set_selected(selected)

    geometry = _FakeNativeGeometry(
        model_name="planet_lod0.3db",
        level_name="Level0",
        part_name="Part_Planet",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(4000.0, 4000.0, 4000.0), radius=2000.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Planet",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    view.set_native_scene_resolver(lambda obj: scene_data if obj is planet else None)
    view.refresh_native_scene_previews()

    assert planet in view._native_preview_entity_by_obj
    assert view._obj_sphere_ent[planet].isEnabled() is False


def test_system3dview_sparsifies_distant_tradelane_native_preview_candidates(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    selected = _dummy_object("li01_station_selected")
    tradelanes = [
        _dummy_object(
            f"li01_trade_lane_ring_{index}",
            pos=f"{(index + 1) * 1000},0,0",
            archetype="trade_lane_ring",
        )
        for index in range(18)
    ]
    view.set_data([selected, *tradelanes], [], 0.01)
    view.set_selected(selected)
    view.set_native_preview_max_distance_fl(-1.0)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level2",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(10.0, 10.0, 0.0), radius=10.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )
    view.set_native_scene_resolver(lambda obj: scene_data if obj in tradelanes else None)

    candidates = view._native_preview_candidate_objects()

    assert len(candidates) < len(tradelanes)
    assert tradelanes[0] in candidates
    assert tradelanes[1] in candidates
    assert tradelanes[2] in candidates


def test_system3dview_native_preview_distance_limit_controls_real_models(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    selected = _dummy_object("li01_station_selected")
    near_obj = _dummy_object("li01_station_near", pos="1000,0,0")
    far_obj = _dummy_object("li01_station_far", pos="3000,0,0")
    view.set_data([selected, near_obj, far_obj], [], 0.01)
    view.set_selected(selected)
    view.set_native_preview_max_distance_fl(1500.0)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(10.0, 10.0, 0.0), radius=10.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    view.set_native_scene_resolver(lambda obj: scene_data if obj in {near_obj, far_obj} else None)
    view.refresh_native_scene_previews()

    assert near_obj in view._native_preview_entity_by_obj
    assert far_obj not in view._native_preview_entity_by_obj


def test_system3dview_native_preview_distance_uses_camera_position(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    selected = _dummy_object("li01_station_selected")
    near_camera = _dummy_object("li01_station_cam_near", pos="3000,0,0")
    near_target = _dummy_object("li01_station_target_near", pos="200,0,0")
    view.set_data([selected, near_camera, near_target], [], 0.01)
    view.set_selected(selected)
    view.set_native_preview_max_distance_fl(500.0)
    view._cam_target = QVector3D(0.0, 0.0, 0.0)
    try:
        view._camera.setPosition(QVector3D(30.0, 0.0, 0.0))
    except Exception:
        pass

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(10.0, 10.0, 0.0), radius=10.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    view.set_native_scene_resolver(lambda obj: scene_data if obj in {near_camera, near_target} else None)
    view.refresh_native_scene_previews()

    assert near_camera in view._native_preview_entity_by_obj
    assert near_target not in view._native_preview_entity_by_obj


def test_system3dview_native_preview_candidates_only_include_objects_in_view(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    front_obj = _dummy_object("li01_station_front", pos="0,0,3000")
    back_obj = _dummy_object("li01_station_back", pos="0,0,-3000")
    side_obj = _dummy_object("li01_station_side", pos="3000,0,0")
    view.set_data([front_obj, back_obj, side_obj], [], 0.01)
    view.set_native_preview_max_distance_fl(-1.0)
    try:
        view._camera.setPosition(QVector3D(0.0, 0.0, 0.0))
        view._camera.setViewCenter(QVector3D(0.0, 0.0, 100.0))
    except Exception:
        pass

    candidates = view._native_preview_candidate_objects()

    assert front_obj in candidates
    assert back_obj not in candidates
    assert side_obj not in candidates


def test_system3dview_native_preview_keeps_active_object_within_wider_view_hysteresis(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station_edge", pos="3000,0,1200")
    view.set_data([obj], [], 0.01)
    try:
        view._camera.setPosition(QVector3D(0.0, 0.0, 0.0))
        view._camera.setViewCenter(QVector3D(0.0, 0.0, 100.0))
    except Exception:
        pass

    assert view._is_object_within_native_preview_view(obj, active=False) is False
    assert view._is_object_within_native_preview_view(obj, active=True) is True


def test_system3dview_camera_motion_uses_idle_refresh_delay(qapp, monkeypatch):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    delays: list[int] = []

    def _fake_schedule(delay_ms=90):
        delays.append(int(delay_ms))

    monkeypatch.setattr(view, "_schedule_native_scene_preview_refresh", _fake_schedule)
    view._free_camera_active = False

    view._update_camera()

    assert delays
    assert delays[-1] == int(view._native_preview_camera_idle_delay_ms)


def test_system3dview_free_camera_motion_uses_longer_idle_refresh_delay(qapp, monkeypatch):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    delays: list[int] = []

    def _fake_schedule(delay_ms=90):
        delays.append(int(delay_ms))

    monkeypatch.setattr(view, "_schedule_native_scene_preview_refresh", _fake_schedule)

    view._schedule_native_scene_preview_refresh_for_camera_motion(free_camera=True)

    assert delays == [int(view._native_preview_free_camera_idle_delay_ms)]


def test_system3dview_refresh_native_scene_previews_waits_until_camera_is_idle(qapp, monkeypatch):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    starts: list[int] = []

    class _FakeTimer:
        def start(self, delay_ms):
            starts.append(int(delay_ms))

    monkeypatch.setattr("fl_editor.view_3d.time.monotonic", lambda: 100.0)
    view._native_preview_motion_deadline_monotonic = 100.18
    view._native_preview_refresh_timer = _FakeTimer()

    view.refresh_native_scene_previews()

    assert starts
    assert starts[-1] >= 170


def test_system3dview_native_preview_candidates_wait_for_visibility_stability(qapp, monkeypatch):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station_front", pos="1000,0,0")
    view.set_data([obj], [], 0.01)
    view._native_preview_visibility_stable_ms = 260
    monkeypatch.setattr("fl_editor.view_3d.time.monotonic", lambda: 10.0)

    first = view._native_preview_candidate_objects()

    monkeypatch.setattr("fl_editor.view_3d.time.monotonic", lambda: 10.4)

    second = view._native_preview_candidate_objects()

    assert first == ()
    assert second == (obj,)


def test_system3dview_scene_data_for_preview_lod_uses_coarsest_level_in_system_view(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station_near", pos="1000,0,0")
    view.set_data([obj], [], 0.01)
    try:
        view._camera.setPosition(QVector3D(0.0, 0.0, 0.0))
    except Exception:
        pass

    fine = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0),),
        indices=(0,),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    coarse = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level2",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0),),
        indices=(0,),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(fine,),
        primary_geometry=fine,
        bounds=fine.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
        all_geometries=(fine, coarse),
        all_geometry_texture_paths=(None, None),
    )

    reduced = view._scene_data_for_preview_lod(scene_data, obj)

    assert reduced.geometries[0].level_name == "Level2"


def test_system3dview_scene_data_for_preview_lod_keeps_best_quality_within_hq_radius(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station_near", pos="1000,0,0")
    view.set_data([obj], [], 0.01)
    view.set_native_preview_high_quality_distance_fl(20000.0)
    try:
        view._camera.setPosition(QVector3D(0.0, 0.0, 0.0))
        view._camera.setViewCenter(QVector3D(0.0, 0.0, 100.0))
    except Exception:
        pass

    fine = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0),),
        indices=(0,),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    coarse = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level2",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0),),
        indices=(0,),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(fine,),
        primary_geometry=fine,
        bounds=fine.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
        all_geometries=(fine, coarse),
        all_geometry_texture_paths=(None, None),
    )

    reduced = view._scene_data_for_preview_lod(scene_data, obj)

    assert reduced is scene_data


def test_system3dview_render_tier_uses_hq_radius_and_geometry_budget(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    near_obj = _dummy_object("li01_station_near", pos="1000,0,0")
    far_obj = _dummy_object("li01_station_far", pos="40000,0,0")
    view.set_data([near_obj, far_obj], [], 0.01)
    view.set_native_preview_high_quality_distance_fl(20000.0)

    assert view._native_preview_render_tier(near_obj, prepared_geometry_count=50) == 2
    assert view._native_preview_render_tier(far_obj, prepared_geometry_count=4) == 1
    assert view._native_preview_render_tier(far_obj, prepared_geometry_count=40) == 0


def test_system3dview_refresh_native_scene_previews_caps_native_slots_and_skips_heavy_far_models(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj_a = _dummy_object("li01_station_heavy", pos="25000,0,0")
    obj_b = _dummy_object("li01_station_light_a", pos="26000,0,0")
    obj_c = _dummy_object("li01_station_light_b", pos="27000,0,0")
    view.set_data([obj_a, obj_b, obj_c], [], 0.01)
    view._native_preview_max_active_count = 1
    view.set_native_preview_high_quality_distance_fl(5000.0)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(10.0, 10.0, 0.0), radius=10.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    class _PreparedPayload:
        def __init__(self, scene_data, geometry_count):
            self.scene_data = scene_data
            self.geometry_count = geometry_count

    view.set_native_scene_resolver(lambda _obj: None)
    view.set_native_scene_prepared_payload_resolver(
        lambda obj: (
            _PreparedPayload(scene_data, 40) if obj is obj_a else
            _PreparedPayload(scene_data, 4)
        )
    )
    if view._native_preview_batch_timer is not None:
        view._native_preview_batch_timer.stop()

    view.refresh_native_scene_previews()

    assert [payload["obj"] for payload in view._native_preview_pending_builds] == [obj_b]


def test_system3dview_lod_mode_uses_builtin_thresholds(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    view._native_preview_force_coarsest_lod = False

    assert view._lod_mode_for_distance_fl(7999.0) == 0
    assert view._lod_mode_for_distance_fl(8000.0) == 1
    assert view._lod_mode_for_distance_fl(19999.0) == 1
    assert view._lod_mode_for_distance_fl(20000.0) == 2


def test_system3dview_large_jump_clears_active_native_previews_before_rebuild(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    selected = _dummy_object("li01_station_selected", pos="0,0,0")
    far_obj = _dummy_object("li01_station_far", pos="500000,0,0")
    view.set_data([selected, far_obj], [], 0.01)
    view.set_selected(selected)
    view.set_native_preview_max_distance_fl(-1.0)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(10.0, 10.0, 0.0), radius=10.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    view.set_native_scene_resolver(lambda obj: scene_data if obj is far_obj else None)
    view.refresh_native_scene_previews()
    assert far_obj in view._native_preview_entity_by_obj

    view.jump_to_item_preserving_view(far_obj)

    assert far_obj not in view._native_preview_entity_by_obj
    assert view._obj_sphere_ent[far_obj].isEnabled() is True


def test_system3dview_native_preview_distance_all_mode_renders_far_models(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    selected = _dummy_object("li01_station_selected")
    near_obj = _dummy_object("li01_station_near", pos="1000,0,0")
    far_obj = _dummy_object("li01_station_far", pos="5000000,0,0")
    view.set_data([selected, near_obj, far_obj], [], 0.01)
    view.set_selected(selected)
    view.set_native_preview_max_distance_fl(-1.0)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(10.0, 10.0, 0.0), radius=10.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    view.set_native_scene_resolver(lambda obj: scene_data if obj in {near_obj, far_obj} else None)
    view.refresh_native_scene_previews()

    assert near_obj in view._native_preview_entity_by_obj
    assert far_obj in view._native_preview_entity_by_obj


def test_system3dview_refresh_native_scene_previews_supports_direct_preview_meshes(qapp, tmp_path):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    selected = _dummy_object("li01_station_selected")
    direct_obj = _dummy_object("li01_station_direct", pos="1500,0,0")
    view.set_data([selected, direct_obj], [], 0.01)
    view.set_selected(selected)
    view.set_native_preview_max_distance_fl(-1.0)

    mesh_path = tmp_path / "preview.obj"
    mesh_path.write_text("o test\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n", encoding="utf-8")

    view.set_native_scene_resolver(lambda _obj: None)
    view.set_preview_mesh_resolver(lambda obj: mesh_path if obj is direct_obj else None)
    view.refresh_native_scene_previews()

    assert direct_obj in view._native_preview_entity_by_obj
    assert view._obj_sphere_ent[direct_obj].isEnabled() is False


def test_system3dview_selected_object_keeps_existing_preview_until_detail_is_ready(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station_preview", pos="1000,0,0")
    other = _dummy_object("li01_station_other")
    view.set_data([other, obj], [], 0.01)
    view.set_selected(other)
    view.set_native_preview_max_distance_fl(5000.0)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(10.0, 10.0, 0.0), radius=10.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    view.set_native_scene_resolver(lambda current_obj: scene_data if current_obj is obj else None)
    view.refresh_native_scene_previews()
    assert obj in view._native_preview_entity_by_obj

    view.set_selected(obj)
    view.set_native_scene_resolver(lambda _current_obj: None)
    view.refresh_native_scene_previews()

    assert obj in view._native_preview_entity_by_obj
    assert view._obj_sphere_ent[obj].isEnabled() is False


def test_system3dview_refresh_native_scene_previews_keeps_existing_preview_when_resolver_temporarily_misses(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station_preview", pos="1000,0,0")
    other = _dummy_object("li01_station_other")
    view.set_data([other, obj], [], 0.01)
    view.set_selected(other)
    view.set_native_preview_max_distance_fl(5000.0)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )

    view.set_native_scene_resolver(lambda current_obj: scene_data if current_obj is obj else None)
    view.refresh_native_scene_previews()
    assert obj in view._native_preview_entity_by_obj
    assert view._obj_sphere_ent[obj].isEnabled() is False

    view.set_native_scene_resolver(lambda _current_obj: None)
    view.refresh_native_scene_previews()

    assert obj in view._native_preview_entity_by_obj
    assert view._obj_sphere_ent[obj].isEnabled() is False


def test_system3dview_native_detail_follows_object_position_updates(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station", pos="0,0,0")
    view.set_data([obj], [], 0.01)
    view.set_selected(obj)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )
    view.set_selected_native_scene_data(obj, scene_data)

    obj.data["pos"] = "100,200,300"
    view.update_object_position(obj, 0.01)
    view.center_on_item(obj)

    state = view.get_selected_native_detail_debug_state()
    assert state["detail_object_nickname"] == "li01_station"
    assert state["has_detail_entity"] is True
    assert state["selected_detail_marker_visible"] is False
    assert (view._cam_target.x(), view._cam_target.y(), view._cam_target.z()) == (1.5, 2.5, 3.0)


def test_system3dview_native_detail_survives_object_rotation_updates(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station", rotate="0,0,0")
    view.set_data([obj], [], 0.01)
    view.set_selected(obj)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )
    view.set_selected_native_scene_data(obj, scene_data)
    cached_entity = view._selected_native_detail_entity

    obj.data["rotate"] = "0,90,0"
    view.update_object_rotation(obj)

    state = view.get_selected_native_detail_debug_state()
    assert state["detail_object_nickname"] == "li01_station"
    assert state["has_detail_entity"] is True
    assert state["selected_detail_marker_visible"] is False
    assert view._selected_native_detail_entity is cached_entity


def test_system3dview_clear_scene_resets_native_detail_state(qapp):
    view = System3DView()

    if not QT3D_AVAILABLE:
        assert view.layout() is not None
        return

    obj = _dummy_object("li01_station")
    view.set_data([obj], [], 0.01)
    view.set_selected(obj)

    geometry = _FakeNativeGeometry(
        model_name="meshA_lod0.3db",
        level_name="Level0",
        part_name="Part_Test",
        group_start=0,
        group_count=1,
        positions=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        indices=(0, 1, 2),
        vertex_stride=12,
        index_size=2,
        confidence="exact",
        bounds=FreelancerBounds(min_xyz=(0.0, 0.0, 0.0), max_xyz=(1.0, 1.0, 0.0), radius=1.0),
    )
    scene_data = NativePreviewSceneData(
        geometries=(geometry,),
        primary_geometry=geometry,
        bounds=geometry.bounds,
        part_names=("Part_Test",),
        texture_path=None,
        geometry_texture_paths=(None,),
    )
    view.set_selected_native_scene_data(obj, scene_data)
    assert view.get_selected_native_detail_debug_state()["has_detail_entity"] is True

    view.clear_scene()

    state = view.get_selected_native_detail_debug_state()
    assert state["selected_object_nickname"] is None
    assert state["detail_object_nickname"] is None
    assert state["has_scene_data"] is False
    assert state["has_detail_entity"] is False
    assert state["detail_cache_size"] == 0
