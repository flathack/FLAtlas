from __future__ import annotations

from fl_editor.base_room_templates import (
    adapt_template_room,
    extract_room_scene_path,
    extract_virtual_room_targets,
    override_room_scene,
)


def test_extract_virtual_room_targets_reads_virtual_and_behavior_links():
    content = """
[Hotspot]
behavior = VirtualRoom
room_switch = Bar

[Hotspot]
set_virtual_room = Trader
"""

    assert extract_virtual_room_targets(content) == ["bar", "trader"]


def test_extract_room_scene_path_reads_last_scene_component():
    content = """
[Room_Info]
scene = all, ambient, universe\\rooms\\bar.thn
"""

    assert extract_room_scene_path(content) == "universe\\rooms\\bar.thn"


def test_override_room_scene_replaces_or_appends_room_info_scene():
    content = """
[Room_Info]
scene = all, ambient, old.thn
"""

    updated = override_room_scene(content, "new.thn")
    assert "scene = all, ambient, new.thn" in updated

    created = override_room_scene("", "created.thn")
    assert "[Room_Info]" in created
    assert "scene = all, ambient, created.thn" in created


def test_override_room_scene_collapses_duplicate_room_info_scene_lines():
    content = """
[Room_Info]
set_script = scripts\\bases\\li_09_Bar_hardpoint_R6.thn
scene = all, ambient, old_a.thn
scene = all, ambient, old_b.thn
scene = all, ambient, old_c.thn
"""

    updated = override_room_scene(content, "scripts\\bases\\li_09_bar_ambi_Li03_03.thn")

    assert updated.count("scene = all, ambient, scripts\\bases\\li_09_bar_ambi_Li03_03.thn") == 1


def test_adapt_template_room_drops_invalid_room_switch_but_keeps_virtual_targets():
    content = """
[Hotspot]
behavior = Room
room_switch = invalid_room

[Hotspot]
behavior = VirtualRoom
room_switch = virtual_target

[Hotspot]
set_virtual_room = cityscape
"""

    adapted = adapt_template_room(content, ["deck", "bar"])

    assert "invalid_room" not in adapted
    assert "virtual_target" in adapted
    assert "cityscape" in adapted
