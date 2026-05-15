from __future__ import annotations

from fl_editor.faction_data import Faction, FactionRep, FactionWorld


def _world_with_initialworld_order() -> FactionWorld:
    world = FactionWorld()
    for nick in ("li_n_grp", "li_p_grp", "fc_lr_grp"):
        world.factions[nick] = Faction(nickname=nick, in_initialworld=True)
    world._initialworld_faction_order = ["li_n_grp", "li_p_grp", "fc_lr_grp"]
    return world


def test_validate_warns_when_initialworld_rep_entries_are_out_of_group_order():
    world = _world_with_initialworld_order()
    world.factions["li_n_grp"].reputations = [
        FactionRep(target="fc_lr_grp", value=-0.65),
        FactionRep(target="li_p_grp", value=0.91),
    ]
    world.factions["li_p_grp"].reputations = [
        FactionRep(target="li_n_grp", value=0.91),
        FactionRep(target="fc_lr_grp", value=-0.65),
    ]
    world.factions["fc_lr_grp"].reputations = [
        FactionRep(target="li_n_grp", value=-0.65),
        FactionRep(target="li_p_grp", value=-0.65),
    ]

    issues = world.validate()

    assert {
        "severity": "warning",
        "faction": "li_n_grp",
        "message": "Rep entries are not ordered like initialworld.ini groups",
    } in issues


def test_validate_accepts_initialworld_rep_entries_in_group_order():
    world = _world_with_initialworld_order()
    world.factions["li_n_grp"].reputations = [
        FactionRep(target="li_p_grp", value=0.91),
        FactionRep(target="fc_lr_grp", value=-0.65),
    ]

    messages = [issue["message"] for issue in world.validate() if issue["faction"] == "li_n_grp"]

    assert "Rep entries are not ordered like initialworld.ini groups" not in messages


def test_build_initialworld_sections_writes_reps_in_group_order():
    world = _world_with_initialworld_order()
    world.factions["li_n_grp"].reputations = [
        FactionRep(target="fc_lr_grp", value=-0.65),
        FactionRep(target="li_p_grp", value=0.91),
        FactionRep(target="unknown_grp", value=0.0),
    ]

    sections = world.build_initialworld_sections()
    first_group_entries = sections[0][1]

    assert [value for key, value in first_group_entries if key == "rep"] == [
        "0.91, li_p_grp",
        "-0.65, fc_lr_grp",
        "0.0, unknown_grp",
    ]


def test_build_initialworld_sections_preserves_group_order():
    world = _world_with_initialworld_order()

    sections = world.build_initialworld_sections()

    assert [entries[0][1] for name, entries in sections if name == "Group"] == [
        "li_n_grp",
        "li_p_grp",
        "fc_lr_grp",
    ]
