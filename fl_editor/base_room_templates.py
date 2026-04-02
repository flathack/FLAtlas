from __future__ import annotations


def extract_virtual_room_targets(content: str) -> list[str]:
    targets: list[str] = []
    seen: set[str] = set()
    in_hotspot = False
    behavior = ""
    for raw in str(content or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            in_hotspot = line[1:-1].strip().lower() == "hotspot"
            behavior = ""
            continue
        if not in_hotspot or "=" not in line:
            continue
        key, _, value = line.partition("=")
        normalized_key = key.strip().lower()
        normalized_value = value.strip()
        if not normalized_value:
            continue
        if normalized_key == "behavior":
            behavior = normalized_value.lower()
            continue
        candidate = ""
        if normalized_key in {"virtual_room", "set_virtual_room"}:
            candidate = normalized_value
        elif normalized_key == "room_switch" and behavior == "virtualroom":
            candidate = normalized_value
        if candidate:
            room = candidate.split(",")[0].strip().lower()
            if room and room not in seen:
                seen.add(room)
                targets.append(room)
    return targets


def extract_room_scene_path(content: str) -> str:
    in_room_info = False
    for raw in str(content or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            in_room_info = line[1:-1].strip().lower() == "room_info"
            continue
        if not in_room_info or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip().lower() != "scene":
            continue
        normalized_value = value.strip()
        if "," in normalized_value:
            parts = [part.strip() for part in normalized_value.split(",") if part.strip()]
            if parts:
                return parts[-1]
        return normalized_value
    return ""


def override_room_scene(content: str, scene_path: str) -> str:
    target = str(scene_path or "").strip()
    if not target:
        return content
    lines = str(content or "").splitlines()
    output: list[str] = []
    in_room_info = False
    room_info_seen = False
    scene_written = False
    for raw in lines:
        line = str(raw)
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_room_info and room_info_seen and not scene_written:
                output.append(f"scene = all, ambient, {target}")
            in_room_info = stripped[1:-1].strip().lower() == "room_info"
            room_info_seen = room_info_seen or in_room_info
            scene_written = scene_written if not in_room_info else False
            output.append(line)
            continue
        if in_room_info and "=" in stripped:
            key, _, _value = stripped.partition("=")
            if key.strip().lower() == "scene":
                if not scene_written:
                    output.append(f"scene = all, ambient, {target}")
                    scene_written = True
                continue
        output.append(line)
    if in_room_info and room_info_seen and not scene_written:
        output.append(f"scene = all, ambient, {target}")
    if not room_info_seen:
        output.extend(["", "[Room_Info]", f"scene = all, ambient, {target}"])
    return "\n".join(output)


def adapt_template_room(content: str, rooms: list[str]) -> str:
    lines = str(content or "").splitlines()
    rooms_lower = {str(room).strip().lower() for room in rooms if str(room).strip()}
    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip().lower()
        if stripped != "[hotspot]":
            output.append(line)
            index += 1
            continue

        block: list[str] = [line]
        index += 1
        while index < len(lines):
            next_line = lines[index]
            next_stripped = next_line.strip()
            if next_stripped.startswith("[") and next_stripped.endswith("]"):
                break
            block.append(next_line)
            index += 1

        keep = True
        behavior = ""
        has_virtual_target = False
        for block_line in block[1:]:
            stripped_line = block_line.strip()
            if "=" not in stripped_line:
                continue
            key, value = [part.strip() for part in stripped_line.split("=", 1)]
            normalized_key = key.lower()
            normalized_value = value.strip()
            if normalized_key == "behavior":
                behavior = normalized_value.lower()
            elif normalized_key == "room_switch":
                target = normalized_value.lower()
                if target and target not in rooms_lower:
                    keep = False
            elif normalized_key in {"virtual_room", "set_virtual_room"}:
                has_virtual_target = has_virtual_target or bool(normalized_value)

        if not keep and (behavior == "virtualroom" or has_virtual_target):
            keep = True

        if keep:
            output.extend(block)

    return "\n".join(output)
