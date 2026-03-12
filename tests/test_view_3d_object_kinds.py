from __future__ import annotations

from fl_editor.view_3d_object_kinds import classify_object_kind


def test_classify_object_kind_for_trade_lane_and_buoy():
    state = classify_object_kind(nickname="li01_trade_lane_ring_01", archetype="nav_buoy")

    assert state["is_trade_lane"] is True
    assert state["is_buoy_like"] is True
    assert state["is_planet"] is False


def test_classify_object_kind_for_station_like_and_transport():
    state = classify_object_kind(nickname="li01_station", archetype="space_factory01")
    transport = classify_object_kind(nickname="convoy", archetype="large_transport")

    assert state["is_station_like"] is True
    assert transport["is_transport"] is True
    assert transport["is_capship"] is False


def test_classify_object_kind_for_nomad_and_hazard():
    nomad = classify_object_kind(nickname="dyson_01", archetype="dyson_city")
    hazard = classify_object_kind(nickname="zone", archetype="neutron_star")

    assert nomad["is_nomad_structure"] is True
    assert hazard["is_hazard"] is True
