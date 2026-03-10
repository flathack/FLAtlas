from __future__ import annotations

from pathlib import Path

from fl_editor.base_scaffolding import build_base_ini_text, write_base_ini, write_room_ini


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
