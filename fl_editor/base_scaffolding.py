from __future__ import annotations

from pathlib import Path

from .text_write_utils import write_text_atomic


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


def write_base_ini(
    path: str | Path,
    *,
    base_nick: str,
    system_nick: str,
    start_room: str,
    price_variance: float,
    rooms: list[str],
) -> Path:
    target = Path(path)
    write_text_atomic(
        target,
        build_base_ini_text(
            base_nick=base_nick,
            system_nick=system_nick,
            start_room=start_room,
            price_variance=price_variance,
            rooms=rooms,
        ),
    )
    return target
