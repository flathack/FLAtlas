from __future__ import annotations

from dataclasses import dataclass

from fl_editor.freelancer_mesh_data import FreelancerBounds
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
        bounds=None,
        part_names=("Part_Test",),
        texture_path=None,
    )
    view.set_selected_native_scene_data(obj, scene_data)
    assert view.get_selected_native_scene_data() is scene_data
    assert view._selected_native_detail_entity is not None
    assert view._obj_sphere_ent[obj].isEnabled() is False
    view.center_on_item(obj)
    assert (view._cam_target.x(), view._cam_target.y(), view._cam_target.z()) == (0.5, 0.5, 0.0)
    assert view._cam_distance == 120.0

    other = _dummy_object("li01_station_other")
    view.set_selected_native_scene_data(other, scene_data)
    assert view.get_selected_native_scene_data() is None
    assert view._selected_native_detail_entity is None
    assert view._obj_sphere_ent[obj].isEnabled() is True

    view.clear_scene()
    assert view._obj_map == {}
    assert view._zone_map == {}
