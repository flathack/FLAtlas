from __future__ import annotations

from pathlib import Path


def build_base_ini_text(
    *,
    base_nick: str,
    system_nick: str,
    start_room: str,
    price_variance: float,
    rooms: list[str],
) -> str:
    lines = [
        "[BaseInfo]",
        f"nickname = {base_nick}",
        f"start_room = {start_room}",
        f"price_variance = {float(price_variance):.2f}",
        "",
    ]
    for room_name in rooms:
        room_lower = str(room_name or "").strip().lower()
        rel = f"Universe\\Systems\\{system_nick}\\Bases\\Rooms\\{base_nick}_{room_lower}.ini"
        lines.extend(
            [
                "[Room]",
                f"nickname = {room_name}",
                f"file = {rel}",
                "",
            ]
        )
    return "\n".join(lines)


def write_room_ini(path: str | Path, content: str) -> Path:
    target = Path(path)
    target.write_text(content, encoding="utf-8")
    return target
