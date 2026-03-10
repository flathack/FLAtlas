from __future__ import annotations

from pathlib import Path

from fl_editor.base_scaffolding import (
    build_base_ini_text,
    build_nav_hotspots,
    generate_room_ini_text,
    normalize_room_navigation,
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
