from __future__ import annotations


def normalize_room_npc_customizations(
    *,
    existing_rooms: list[str],
    selected_rooms: list[str],
    room_customizations: dict,
    room_npcs_existing: dict,
) -> tuple[list[str], dict]:
    npc_rooms = sorted(set(existing_rooms + selected_rooms), key=lambda value: str(value).lower())
    npc_customizations = dict(room_customizations or {})

    def role_key(raw: str) -> str:
        return str(raw or "").strip().lower()

    existing_npc_rows_by_room: dict[str, list[dict]] = {
        str(key or "").strip().lower(): list(value or [])
        for key, value in dict(room_npcs_existing or {}).items()
        if str(key or "").strip()
    }

    for room_name in npc_rooms:
        room_key = str(room_name or "").strip().lower()
        cfg = npc_customizations.get(room_key)
        if not isinstance(cfg, dict):
            cfg = {}
            npc_customizations[room_key] = cfg
        npc_rows = cfg.get("npc_rows")
        if not isinstance(npc_rows, list):
            npc_rows = []
        cfg["npc_rows"] = npc_rows

        if not npc_rows:
            fallback_rows = list(existing_npc_rows_by_room.get(room_key, []))
            if fallback_rows:
                cfg["npc_rows"] = fallback_rows
                cfg["npcs"] = [
                    str(row.get("nickname", "")).strip()
                    for row in fallback_rows
                    if isinstance(row, dict) and str(row.get("nickname", "")).strip()
                ]
            continue

        required_roles: set[str] = set()
        if room_key == "deck":
            required_roles = {"trader", "equipment"}
        elif room_key == "bar":
            required_roles = {"bartender"}
        required_roles |= {
            role_key(row.get("role", "") if isinstance(row, dict) else "")
            for row in existing_npc_rows_by_room.get(room_key, [])
            if role_key(row.get("role", "") if isinstance(row, dict) else "")
        }

        present_roles = {
            role_key(row.get("role", "") if isinstance(row, dict) else "")
            for row in npc_rows
            if isinstance(row, dict)
        }
        missing_roles = {role for role in required_roles if role not in present_roles}
        fallback_rows = list(existing_npc_rows_by_room.get(room_key, []))
        used_nicks = {
            str(row.get("nickname", "")).strip().lower()
            for row in npc_rows
            if isinstance(row, dict) and str(row.get("nickname", "")).strip()
        }
        for missing in sorted(missing_roles):
            candidate = next(
                (
                    row for row in fallback_rows
                    if isinstance(row, dict)
                    and role_key(row.get("role", "")) == missing
                    and str(row.get("nickname", "")).strip().lower() not in used_nicks
                ),
                None,
            )
            if not candidate:
                continue
            npc_rows.append(dict(candidate))
            nickname = str(candidate.get("nickname", "")).strip().lower()
            if nickname:
                used_nicks.add(nickname)

        existing_role_by_nick = {
            str(row.get("nickname", "")).strip().lower(): role_key(row.get("role", ""))
            for row in fallback_rows
            if isinstance(row, dict) and str(row.get("nickname", "")).strip()
        }
        for row in npc_rows:
            if not isinstance(row, dict):
                continue
            nickname = str(row.get("nickname", "")).strip().lower()
            if not nickname:
                continue
            current_role = role_key(row.get("role", ""))
            previous_role = existing_role_by_nick.get(nickname, "")
            if previous_role and current_role != previous_role and room_key == "bar":
                row["role"] = previous_role

        cfg["npc_rows"] = npc_rows
        cfg["npcs"] = [
            str(row.get("nickname", "")).strip()
            for row in npc_rows
            if isinstance(row, dict) and str(row.get("nickname", "")).strip()
        ]

    return npc_rooms, npc_customizations
