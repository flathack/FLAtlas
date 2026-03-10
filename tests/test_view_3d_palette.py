from __future__ import annotations

from fl_editor.view_3d_palette import object_color, planet_palette, sun_palette, zone_color


def test_object_color_uses_expected_categories():
    assert object_color(nickname="li01_trade_lane_ring_01", archetype="foo").getRgb()[:3] == (70, 140, 255)
    assert object_color(nickname="planet_manhattan", archetype="planet_3000").getRgb()[:3] == (60, 130, 220)
    assert object_color(nickname="foo", archetype="space_station").getRgb()[:3] == (80, 210, 100)


def test_sun_palette_matches_blue_variant():
    core, inner, outer = sun_palette("blue_sun", "some_star")
    assert core.getRgb()[:3] == (168, 214, 255)
    assert inner.alpha() == 170
    assert outer.alpha() == 120


def test_planet_palette_matches_earth_variant():
    base, cloud = planet_palette("planet_earthgrncld_3000", "earth")
    assert base.getRgb()[:3] == (76, 146, 118)
    assert cloud.alpha() == 100


def test_zone_color_prefers_damage_and_named_categories():
    assert zone_color(nickname="zone_death", data={}).getRgb() == (220, 50, 50, 50)
    assert zone_color(nickname="li01_badlands", data={}).getRgb() == (150, 80, 220, 50)
    assert zone_color(nickname="asteroid_field", data={}).getRgb() == (180, 130, 60, 50)
    assert zone_color(nickname="tradelane_path", data={}).getRgb() == (70, 140, 255, 180)
