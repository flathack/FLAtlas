from __future__ import annotations

from fl_editor.news_editor_logic import (
    build_news_save_row,
    news_build_entries,
    news_item_to_row,
    news_split_rank,
)


def test_news_item_to_row_reads_entries_and_defaults():
    row = news_item_to_row(
        [
            ("rank", "base_0_rank, mission_end"),
            ("autoselect", ""),
            ("icon", "world"),
            ("logo", "li"),
            ("category", "111"),
            ("headline", "222"),
            ("text", "333"),
            ("base", "li01_01_base"),
            ("base", "li01_02_base"),
        ]
    )

    assert row == {
        "rank": "base_0_rank, mission_end",
        "autoselect": True,
        "icon": "world",
        "logo": "li",
        "category": "111",
        "headline": "222",
        "text": "333",
        "bases": ["li01_01_base", "li01_02_base"],
    }


def test_news_split_rank_handles_empty_single_and_pair():
    assert news_split_rank("") == ("", "")
    assert news_split_rank("base_0_rank") == ("base_0_rank", "base_0_rank")
    assert news_split_rank("base_0_rank, mission_end") == ("base_0_rank", "mission_end")


def test_news_build_entries_normalizes_values():
    entries = news_build_entries(
        {
            "rank_from": "base_0_rank",
            "rank_to": "",
            "autoselect": True,
            "icon": "",
            "logo": "li",
            "category": "",
            "headline": "222",
            "text": "333",
            "bases": ["li01_01_base", "", "li01_02_base"],
        }
    )

    assert entries == [
        ("rank", "base_0_rank, base_0_rank"),
        ("autoselect", ""),
        ("icon", "world"),
        ("logo", "li"),
        ("category", "0"),
        ("headline", "222"),
        ("text", "333"),
        ("base", "li01_01_base"),
        ("base", "li01_02_base"),
    ]


def test_build_news_save_row_normalizes_editor_values():
    row = build_news_save_row(
        rank_from=" base_0_rank ",
        rank_to=" mission_end ",
        autoselect=True,
        icon="",
        logo=" li ",
        category_id="",
        headline_id="222",
        text_id="333",
        bases=[" li01_01_base ", "", "li01_02_base"],
    )

    assert row == {
        "rank_from": "base_0_rank",
        "rank_to": "mission_end",
        "autoselect": True,
        "icon": "world",
        "logo": "li",
        "category": "0",
        "headline": "222",
        "text": "333",
        "bases": ["li01_01_base", "li01_02_base"],
    }
