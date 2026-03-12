from __future__ import annotations

from pathlib import Path

from fl_editor.base_scaffolding import (
    build_base_ini_text,
    build_nav_hotspots,
    create_base_room_files,
    generate_room_ini_text,
    normalize_room_navigation,
    sync_base_room_files,
    write_base_ini,
    write_room_ini,
)


def test_build_base_ini_text_renders_rooms_and_price_variance():
    text = build_base_ini_text(
        base_nick="li01_01_base",
        system_nick="li01",
        start_room="Deck",
        price_variance=0.15,
        rooms=["Deck", "Bar"],
    )

    assert text == (
        "[BaseInfo]\n"
        "nickname = li01_01_base\n"
        "start_room = Deck\n"
        "price_variance = 0.15\n"
        "\n"
        "[Room]\n"
        "nickname = Deck\n"
        "file = Universe\\Systems\\li01\\Bases\\Rooms\\li01_01_base_deck.ini\n"
        "\n"
        "[Room]\n"
        "nickname = Bar\n"
        "file = Universe\\Systems\\li01\\Bases\\Rooms\\li01_01_base_bar.ini\n"
    )


def test_write_room_ini_writes_utf8_content(tmp_path: Path):
    target = tmp_path / "room.ini"

    written = write_room_ini(target, "[Room]\nnickname = Deck\n")

    assert written == target
    assert target.read_text(encoding="utf-8") == "[Room]\nnickname = Deck\n"


def test_write_base_ini_writes_generated_content(tmp_path: Path):
    target = tmp_path / "li01_01_base.ini"

    written = write_base_ini(
        target,
        base_nick="li01_01_base",
        system_nick="li01",
        start_room="Deck",
        price_variance=0.15,
        rooms=["Deck", "Bar"],
    )

    text = target.read_text(encoding="utf-8")
    assert written == target
    assert "nickname = li01_01_base" in text
    assert "start_room = Deck" in text
    assert "file = Universe\\Systems\\li01\\Bases\\Rooms\\li01_01_base_bar.ini" in text


def test_build_nav_hotspots_uses_exit_and_named_targets():
    hotspots = build_nav_hotspots(["Deck", "Bar", "Trader"], "Deck")

    assert hotspots == [
        ("IDS_HOTSPOT_EXIT", "Deck"),
        ("IDS_HOTSPOT_BAR", "Bar"),
        ("IDS_HOTSPOT_COMMODITYTRADER_ROOM", "Trader"),
    ]


def test_generate_room_ini_text_includes_navigation_and_role_specific_hotspots():
    text = generate_room_ini_text("Bar", ["Deck", "Bar"], "Deck")

    assert "name = IDS_HOTSPOT_EXIT" in text
    assert "room_switch = Deck" in text
    assert "name = IDS_HOTSPOT_NEWSVENDOR" in text
    assert "behavior = MissionVendor" in text


def test_normalize_room_navigation_replaces_non_virtual_exit_doors_only():
    content = (
        "[Room_Info]\n"
        "set_script = test\n"
        "\n"
        "[Hotspot]\n"
        "name = IDS_HOTSPOT_EXIT\n"
        "behavior = ExitDoor\n"
        "room_switch = OldRoom\n"
        "\n"
        "[Hotspot]\n"
        "name = IDS_SPECIAL_VIRTUAL\n"
        "behavior = ExitDoor\n"
        "set_virtual_room = virtual_bar\n"
        "\n"
    )

    normalized = normalize_room_navigation(content, "Bar", ["Deck", "Bar"], "Deck")

    assert "room_switch = OldRoom" not in normalized
    assert "name = IDS_HOTSPOT_EXIT" in normalized
    assert "room_switch = Deck" in normalized
    assert "name = IDS_HOTSPOT_BAR" in normalized
    assert "name = IDS_SPECIAL_VIRTUAL" in normalized


def test_create_base_room_files_creates_and_reports_new_rooms(tmp_path: Path):
    results = create_base_room_files(
        rooms_dir=tmp_path,
        base_nick="li01_01_base",
        rooms=["Deck", "Bar"],
        start_room="Deck",
        template_rooms={"bar": "[Room_Info]\nscene = template\n"},
        room_customizations={"bar": {"scene": "override_scene"}},
        adapt_template_room=lambda content, _base, _rooms: content + "adapted\n",
        generate_room_ini=lambda room, _rooms, _start: f"[Room_Info]\nroom = {room}\n",
        override_room_scene=lambda content, scene: content + f"scene = {scene}\n",
        normalize_room_navigation_callback=lambda content, room, _rooms, _start: content + f"normalized = {room}\n",
        room_exists_message=lambda file: f"exists:{file}",
        room_created_message=lambda file: f"created:{file}",
    )

    assert results == [
        "created:li01_01_base_deck.ini",
        "created:li01_01_base_bar.ini",
    ]
    assert (tmp_path / "li01_01_base_deck.ini").read_text(encoding="utf-8").endswith("normalized = Deck\n")
    bar_text = (tmp_path / "li01_01_base_bar.ini").read_text(encoding="utf-8")
    assert "adapted" in bar_text
    assert "scene = override_scene" in bar_text
    assert "normalized = Bar" in bar_text


def test_create_base_room_files_reports_existing_room_without_overwriting(tmp_path: Path):
    existing = tmp_path / "li01_01_base_deck.ini"
    existing.write_text("keep", encoding="utf-8")

    results = create_base_room_files(
        rooms_dir=tmp_path,
        base_nick="li01_01_base",
        rooms=["Deck"],
        start_room="Deck",
        template_rooms={},
        room_customizations={},
        adapt_template_room=lambda content, _base, _rooms: content,
        generate_room_ini=lambda room, _rooms, _start: f"generated:{room}",
        override_room_scene=lambda content, _scene: content,
        normalize_room_navigation_callback=lambda content, _room, _rooms, _start: content,
        room_exists_message=lambda file: f"exists:{file}",
        room_created_message=lambda file: f"created:{file}",
    )

    assert results == ["exists:li01_01_base_deck.ini"]
    assert existing.read_text(encoding="utf-8") == "keep"


def test_sync_base_room_files_updates_existing_and_new_rooms_and_removes_old_ones(tmp_path: Path):
    existing = tmp_path / "li01_01_base_deck.ini"
    removed = tmp_path / "li01_01_base_bar.ini"
    existing.write_text("existing deck\n", encoding="utf-8")
    removed.write_text("old bar\n", encoding="utf-8")

    sync_base_room_files(
        rooms_dir=tmp_path,
        base_nick="li01_01_base",
        selected_rooms=["Deck", "Trader"],
        existing_rooms=["Deck", "Bar"],
        start_room="Deck",
        template_rooms={"trader": "template trader\n"},
        room_customizations={"deck": {"scene": "same_scene"}, "trader": {"scene": "new_scene"}},
        room_scene_by_name={"deck": "same_scene"},
        adapt_template_room=lambda content, _base, _rooms: content + "adapted\n",
        read_room_text=lambda path: path.read_text(encoding="utf-8"),
        generate_room_ini=lambda room, _rooms, _start: f"generated:{room}\n",
        override_room_scene=lambda content, scene: content + f"scene:{scene}\n",
        normalize_room_navigation_callback=lambda content, room, _rooms, _start: content + f"normalized:{room}\n",
        remove_room_file=lambda path: path.unlink(),
    )

    assert existing.read_text(encoding="utf-8") == "existing deck\n"
    trader_text = (tmp_path / "li01_01_base_trader.ini").read_text(encoding="utf-8")
    assert "template trader" in trader_text
    assert "adapted" in trader_text
    assert "scene:new_scene" in trader_text
    assert "normalized:Trader" in trader_text
    assert not removed.exists()
