from __future__ import annotations

from PySide6.QtGui import QColor

from .view_3d_object_logic import is_trade_lane_object


def object_color(*, nickname: str, archetype: str) -> QColor:
    arch = str(archetype or "").lower()
    name = str(nickname or "").lower()
    if is_trade_lane_object(nickname=name, archetype=arch):
        return QColor(70, 140, 255)
    if arch == "nav_buoy":
        return QColor(255, 230, 80)
    if "surprise" in name:
        return QColor(230, 60, 60)
    if any(x in arch for x in ("sun", "star")):
        return QColor(255, 215, 40)
    if "planet" in arch:
        return QColor(60, 130, 220)
    if any(x in arch for x in ("base", "station")):
        return QColor(80, 210, 100)
    if any(x in arch for x in ("jump", "gate")):
        return QColor(210, 90, 210)
    return QColor(190, 190, 190)


def sun_palette(arch: str, name: str) -> tuple[QColor, QColor, QColor]:
    value = f"{arch} {name}".lower()
    if any(k in value for k in ("blue", "blu", "aqua")):
        return QColor(168, 214, 255), QColor(130, 190, 255, 170), QColor(86, 150, 255, 120)
    if any(k in value for k in ("red", "rdd", "orange")):
        return QColor(255, 168, 96), QColor(255, 140, 82, 170), QColor(255, 108, 58, 120)
    if any(k in value for k in ("white", "wht")):
        return QColor(255, 244, 214), QColor(255, 220, 170, 170), QColor(255, 188, 126, 120)
    return QColor(255, 202, 102), QColor(255, 178, 82, 170), QColor(255, 148, 56, 120)


def planet_palette(arch: str, name: str) -> tuple[QColor, QColor]:
    value = f"{arch} {name}".lower()
    if "earthgrncld" in value or "earth" in value:
        return QColor(76, 146, 118), QColor(228, 238, 246, 100)
    if any(k in value for k in ("desored", "desert", "rock", "lava")):
        return QColor(176, 108, 74), QColor(220, 176, 142, 72)
    if any(k in value for k in ("icemoon", "ice", "frozen")):
        return QColor(164, 194, 226), QColor(230, 240, 252, 88)
    if any(k in value for k in ("gas", "jupiter", "storm")):
        return QColor(196, 154, 118), QColor(226, 208, 180, 70)
    if any(k in value for k in ("volcan", "molten")):
        return QColor(178, 90, 70), QColor(232, 150, 110, 64)
    return QColor(92, 138, 212), QColor(220, 232, 252, 86)


def zone_color(*, nickname: str, data: dict[str, str]) -> QColor:
    name = str(nickname or "").lower()
    damage = 0.0
    try:
        damage = float(str((data or {}).get("damage", "")).strip() or "0")
    except Exception:
        damage = 0.0
    if "death" in name or damage > 0.0:
        return QColor(220, 50, 50, 50)
    if "nebula" in name or "badlands" in name:
        return QColor(150, 80, 220, 50)
    if "debris" in name or "asteroid" in name:
        return QColor(180, 130, 60, 50)
    if "tradelane" in name:
        return QColor(70, 140, 255, 180)
    return QColor(80, 160, 200, 50)
