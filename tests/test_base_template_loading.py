from __future__ import annotations

from pathlib import Path

from fl_editor.base_template_loading import (
    load_base_room_template_details,
    load_base_template_virtual_room_targets,
    load_template_rooms,
)


def test_load_template_rooms_reads_room_files(tmp_path: Path):
    base_ini = tmp_path / "base.ini"
    room_ini = tmp_path / "room.ini"
    base_ini.write_text("[Room]\nnickname = Bar\nfile = room.ini\n", encoding="utf-8")
    room_ini.write_text("[Room_Info]\nscene = all, ambient, scene.thn\n", encoding="utf-8")

    universe_sections = [("Base", [("nickname", "li01_01_base"), ("file", "base.ini")])]

    result = load_template_rooms(
        universe_sections=universe_sections,
        template_base_nick="li01_01_base",
        game_path=str(tmp_path),
        resolve_game_path_case_insensitive=lambda _game_path, rel: tmp_path / rel,
        parse_sections=lambda path: [("Room", [("nickname", "Bar"), ("file", "room.ini")])] if path.endswith("base.ini") else [],
        read_text_best_effort=lambda path: path.read_text(encoding="utf-8"),
    )

    assert result == {"bar": "[Room_Info]\nscene = all, ambient, scene.thn\n"}


def test_load_base_room_template_details_reads_scene_and_sorts(tmp_path: Path):
    base_ini = tmp_path / "base.ini"
    room_bar = tmp_path / "bar.ini"
    room_deck = tmp_path / "deck.ini"
    base_ini.write_text("", encoding="utf-8")
    room_bar.write_text("[Room_Info]\nscene = all, ambient, bar.thn\n", encoding="utf-8")
    room_deck.write_text("[Room_Info]\nscene = all, ambient, deck.thn\n", encoding="utf-8")

    universe_sections = [("Base", [("nickname", "li01_01_base"), ("file", "base.ini")])]

    def parse_sections(path: str):
        if path.endswith("base.ini"):
            return [
                ("Room", [("nickname", "Bar"), ("file", "bar.ini")]),
                ("Room", [("nickname", "Deck"), ("file", "deck.ini")]),
            ]
        return []

    rows = load_base_room_template_details(
        universe_sections=universe_sections,
        template_base_nick="li01_01_base",
        game_path=str(tmp_path),
        resolve_game_path_case_insensitive=lambda _game_path, rel: tmp_path / rel,
        parse_sections=parse_sections,
        read_text_best_effort=lambda path: path.read_text(encoding="utf-8"),
        extract_room_scene_path=lambda text: text.split("scene = ", 1)[1].strip(),
    )

    assert rows == [
        {"room": "Deck", "file": "deck.ini", "scene": "all, ambient, deck.thn"},
        {"room": "Bar", "file": "bar.ini", "scene": "all, ambient, bar.thn"},
    ]


def test_load_base_template_virtual_room_targets_orders_targets():
    targets = load_base_template_virtual_room_targets(
        template_rooms={"bar": "x", "deck": "y"},
        extract_virtual_room_targets=lambda content: ["cityscape", "bar"] if content == "x" else ["deck"],
    )

    assert targets == ["deck", "bar", "cityscape"]
