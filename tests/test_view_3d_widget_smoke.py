from __future__ import annotations

from fl_editor.native_preview_scene_data import NativePreviewSceneData
from fl_editor.qt3d_compat import QT3D_AVAILABLE
from fl_editor.view_3d import System3DView


class _DummySceneItem:
    def __init__(self, nickname: str, data: dict[str, str]):
        self.nickname = nickname
        self.data = data


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

    scene_data = NativePreviewSceneData(
        geometries=(object(),),
        primary_geometry=object(),
        bounds=None,
        part_names=("Part_Test",),
        texture_path=None,
    )
    view.set_selected_native_scene_data(obj, scene_data)
    assert view.get_selected_native_scene_data() is scene_data

    other = _dummy_object("li01_station_other")
    view.set_selected_native_scene_data(other, scene_data)
    assert view.get_selected_native_scene_data() is None

    view.clear_scene()
    assert view._obj_map == {}
    assert view._zone_map == {}
