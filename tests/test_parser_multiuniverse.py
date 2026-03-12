from __future__ import annotations

from fl_editor.parser import FLParser, find_all_systems


def _write(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_find_all_systems_reads_multiuniverse_positions(tmp_path):
    game = tmp_path / "game"
    uni_ini = game / "DATA" / "UNIVERSE" / "universe.ini"
    _write(
        uni_ini,
        "\n".join(
            [
                "[system]",
                "nickname = Li01",
                "file = systems\\Li01\\Li01.ini",
                "pos = 7, 8",
                "",
                "[system]",
                "nickname = CF80",
                "file = systems\\CF80\\CF80.ini",
                "pos = 5, 12",
                "",
            ]
        ),
    )
    _write(game / "DATA" / "UNIVERSE" / "SYSTEMS" / "Li01" / "Li01.ini", "[System]\n")
    _write(game / "DATA" / "UNIVERSE" / "SYSTEMS" / "CF80" / "CF80.ini", "[System]\n")
    _write(
        game / "DATA" / "UNIVERSE" / "multiuniverse.ini",
        "\n".join(
            [
                "[sector]",
                "mapping = sector01",
                "system = Li01, 7, 8",
                "",
                "[sector]",
                "mapping = sector02",
                "system = CF80, 13, 2",
                "",
            ]
        ),
    )

    systems = find_all_systems(str(game), FLParser())
    by_nick = {str(row.get("nickname", "")).upper(): row for row in systems}

    assert "LI01" in by_nick
    assert "CF80" in by_nick
    assert by_nick["LI01"]["pos_source_map"] == "universe"
    assert by_nick["LI01"]["pos"] == (7.0, 8.0)
    assert by_nick["LI01"]["map_positions"] == [{"map": "sector01", "pos": (7.0, 8.0), "label_ids": []}]
    assert by_nick["CF80"]["map_positions"] == [{"map": "sector02", "pos": (13.0, 2.0), "label_ids": []}]


def test_find_all_systems_uses_multiuniverse_for_stacked_positions(tmp_path):
    game = tmp_path / "game"
    uni_ini = game / "DATA" / "UNIVERSE" / "universe.ini"
    lines = []
    for idx in range(1, 10):
        lines.extend(
            [
                "[system]",
                f"nickname = CF{idx:02d}",
                f"file = systems\\CF{idx:02d}\\CF{idx:02d}.ini",
                "pos = 0, 14",
                "",
            ]
        )
        _write(game / "DATA" / "UNIVERSE" / "SYSTEMS" / f"CF{idx:02d}" / f"CF{idx:02d}.ini", "[System]\n")
    _write(uni_ini, "\n".join(lines))
    _write(
        game / "DATA" / "UNIVERSE" / "multiuniverse.ini",
        "\n".join(
            [
                "[sector]",
                "mapping = sector03",
                "system = CF01, 9, 3",
                "",
            ]
        ),
    )

    systems = find_all_systems(str(game), FLParser())
    cf01 = next(row for row in systems if str(row.get("nickname", "")).upper() == "CF01")
    cf02 = next(row for row in systems if str(row.get("nickname", "")).upper() == "CF02")

    assert cf01["universe_pos"] == (0.0, 14.0)
    assert cf01["pos"] == (9.0, 3.0)
    assert cf01["pos_source_map"] == "sector03"
    assert cf02["pos"] == (0.0, 14.0)
    assert cf02["pos_source_map"] == "universe"
