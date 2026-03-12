from __future__ import annotations

from fl_editor.system_dialog_logic import (
    build_system_creation_payload,
    build_system_settings_result,
)


def test_build_system_creation_payload_normalizes_text_values():
    payload = build_system_creation_payload(
        name=" Taharka ",
        prefix=" te ",
        size=250000,
        space_color="1, 2, 3",
        music_space=" music_space ",
        music_danger=" music_danger ",
        music_battle=" music_battle ",
        ambient_color="4, 5, 6",
        bg_basic=" basic_a ",
        bg_complex=" complex_a ",
        bg_nebulae=" nebula_a ",
        light_color="7, 8, 9",
        local_faction=" li_n_grp ",
    )

    assert payload == {
        "name": "Taharka",
        "prefix": "TE",
        "size": 250000,
        "space_color": "1, 2, 3",
        "music_space": "music_space",
        "music_danger": "music_danger",
        "music_battle": "music_battle",
        "ambient_color": "4, 5, 6",
        "bg_basic": "basic_a",
        "bg_complex": "complex_a",
        "bg_nebulae": "nebula_a",
        "light_color": "7, 8, 9",
        "local_faction": "li_n_grp",
    }


def test_build_system_settings_result_normalizes_text_values():
    result = build_system_settings_result(
        music_space=" music_space ",
        music_danger=" music_danger ",
        music_battle=" music_battle ",
        space_color="1, 2, 3",
        local_faction=" li_n_grp ",
        ambient_color="4, 5, 6",
        dust=" dust_heavy ",
        bg_basic=" basic_a ",
        bg_complex=" complex_a ",
        bg_nebulae=" nebula_a ",
    )

    assert result == {
        "music_space": "music_space",
        "music_danger": "music_danger",
        "music_battle": "music_battle",
        "space_color": "1, 2, 3",
        "local_faction": "li_n_grp",
        "ambient_color": "4, 5, 6",
        "dust": "dust_heavy",
        "bg_basic": "basic_a",
        "bg_complex": "complex_a",
        "bg_nebulae": "nebula_a",
    }
