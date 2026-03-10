from __future__ import annotations


def news_item_to_row(entries: list[tuple[str, str]]) -> dict:
    row = {
        "rank": "",
        "autoselect": False,
        "icon": "",
        "logo": "",
        "category": "0",
        "headline": "0",
        "text": "0",
        "bases": [],
    }
    for key, value in entries:
        normalized_key = str(key).strip().lower()
        normalized_value = str(value).strip()
        if normalized_key == "rank":
            row["rank"] = normalized_value
        elif normalized_key == "autoselect":
            row["autoselect"] = True
        elif normalized_key == "icon":
            row["icon"] = normalized_value
        elif normalized_key == "logo":
            row["logo"] = normalized_value
        elif normalized_key == "category":
            row["category"] = normalized_value or "0"
        elif normalized_key == "headline":
            row["headline"] = normalized_value or "0"
        elif normalized_key == "text":
            row["text"] = normalized_value or "0"
        elif normalized_key == "base" and normalized_value:
            row["bases"].append(normalized_value)
    return row


def news_split_rank(raw: str) -> tuple[str, str]:
    text = str(raw or "").strip()
    if not text:
        return "", ""
    if "," not in text:
        return text, text
    first, second = text.split(",", 1)
    return first.strip(), second.strip()


def news_build_entries(row: dict) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    rank_from = str(row.get("rank_from", "")).strip()
    rank_to = str(row.get("rank_to", "")).strip()
    if rank_from or rank_to:
        if not rank_to:
            rank_to = rank_from
        if not rank_from:
            rank_from = rank_to
        entries.append(("rank", f"{rank_from}, {rank_to}"))
    if bool(row.get("autoselect", False)):
        entries.append(("autoselect", ""))
    entries.append(("icon", str(row.get("icon", "")).strip() or "world"))
    entries.append(("logo", str(row.get("logo", "")).strip()))
    entries.append(("category", str(row.get("category", "0")).strip() or "0"))
    entries.append(("headline", str(row.get("headline", "0")).strip() or "0"))
    entries.append(("text", str(row.get("text", "0")).strip() or "0"))
    for base_value in row.get("bases", []):
        base_nickname = str(base_value).strip()
        if base_nickname:
            entries.append(("base", base_nickname))
    return entries


def build_news_save_row(
    *,
    rank_from: str,
    rank_to: str,
    autoselect: bool,
    icon: str,
    logo: str,
    category_id: str,
    headline_id: str,
    text_id: str,
    bases: list[str],
) -> dict:
    return {
        "rank_from": str(rank_from or "").strip(),
        "rank_to": str(rank_to or "").strip(),
        "autoselect": bool(autoselect),
        "icon": str(icon or "").strip() or "world",
        "logo": str(logo or "").strip(),
        "category": str(category_id or "").strip() or "0",
        "headline": str(headline_id or "").strip() or "0",
        "text": str(text_id or "").strip() or "0",
        "bases": [str(base).strip() for base in bases if str(base).strip()],
    }
