from __future__ import annotations

from typing import Callable


def rumor_split_csv(raw: str) -> list[str]:
    values = [item.strip() for item in str(raw or "").split(",")]
    if len(values) < 4:
        values.extend([""] * (4 - len(values)))
    return values[:4]


def rumor_row_label(row: dict, resolve_text: Callable[[str], str]) -> str:
    rumor_type = "R2" if str(row.get("kind", "")).strip().lower() == "rumor_type2" else "R1"
    line = str(row.get("line", "")).strip()
    values = rumor_split_csv(line)
    rumor_id = values[3]
    text = resolve_text(rumor_id) if rumor_id else ""
    preview = str(text or "").replace("\n", " ").strip()
    if len(preview) > 80:
        preview = preview[:77] + "..."
    npc_nick = str(row.get("npc", "")).strip()
    if preview:
        return f"[{rumor_type}] {npc_nick}: {line} | {preview}"
    return f"[{rumor_type}] {npc_nick}: {line}"


def collect_rumor_scope_rows(
    sections: list[tuple[str, list[tuple[str, str]]]],
    npc_to_base: dict[str, str],
    base_by_nick: dict[str, dict],
    system_filter: str,
    base_filter: str,
) -> tuple[list[dict], set[str]]:
    normalized_system = str(system_filter or "").strip().upper()
    normalized_base = str(base_filter or "").strip().lower()
    state_values = {"base_0_rank", "mission_end"}
    if not normalized_system:
        return [], state_values

    scope_rows: list[dict] = []
    for sec_idx, (sec_name, entries) in enumerate(sections):
        if str(sec_name).strip().lower() != "gf_npc":
            continue
        npc_nick = ""
        for key, value in entries:
            if str(key).strip().lower() == "nickname":
                npc_nick = str(value).strip()
                break
        if not npc_nick:
            continue
        base_nick = str(npc_to_base.get(npc_nick.lower(), "")).strip()
        if not base_nick:
            continue
        base_meta = base_by_nick.get(base_nick.lower())
        if not base_meta:
            continue
        row_system = str(base_meta.get("system", "")).strip().upper()
        if row_system != normalized_system:
            continue
        if normalized_base and base_nick.lower() != normalized_base:
            continue
        for entry_idx, (key, value) in enumerate(entries):
            kind = str(key).strip().lower()
            if kind not in {"rumor", "rumor_type2"}:
                continue
            line = str(value).strip()
            if not line:
                continue
            values = rumor_split_csv(line)
            if values[0]:
                state_values.add(values[0])
            if values[1]:
                state_values.add(values[1])
            scope_rows.append(
                {
                    "sec_idx": sec_idx,
                    "entry_idx": entry_idx,
                    "kind": kind,
                    "line": line,
                    "npc": npc_nick,
                    "base_nick": base_nick,
                    "base_display": str(base_meta.get("display", base_nick)),
                    "system_nick": row_system,
                    "system_label": str(base_meta.get("system_label", row_system)),
                }
            )

    scope_rows.sort(
        key=lambda row: (
            str(row.get("system_nick", "")).lower(),
            str(row.get("base_display", "")).lower(),
            str(row.get("npc", "")).lower(),
            str(row.get("kind", "")).lower(),
            str(row.get("line", "")).lower(),
        )
    )
    return scope_rows, state_values


def build_rumor_line(*, state_from: str, state_to: str, weight: int, rumor_id: str) -> str:
    return ", ".join(
        [
            str(state_from or "").strip(),
            str(state_to or "").strip(),
            str(weight),
            str(rumor_id or "").strip(),
        ]
    ).strip(", ").strip()


def rumor_form_data(kind: str, line: str) -> dict:
    values = rumor_split_csv(line)
    try:
        weight = int(values[2] or "1")
    except Exception:
        weight = 1
    return {
        "type_index": 1 if str(kind).strip().lower() == "rumor_type2" else 0,
        "state_from": values[0] or "base_0_rank",
        "state_to": values[1] or "mission_end",
        "weight": weight,
        "rumor_id": values[3],
    }
