from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fl_editor.dll_resources import DllStringResolver, pefile
from fl_editor.infocard_utils import normalize_infocard_xml
from fl_editor.ids_toolchain_runtime import resource_toolchain_commands
from fl_editor.path_utils import ci_find
from fl_editor.resource_rc_bundle import write_resource_rc_bundle
from fl_editor.text_write_utils import write_text_with_fallback


STRING_MACRO_RE = re.compile(
    r"(?i)^(?P<indent>\s*)(?P<key>[A-Za-z0-9_]+)(?P<sep>\s*=\s*)0\s*;\s*GENERATESTRRES\((?P<arg>.*)\)\s*$"
)
XML_MACRO_RE = re.compile(
    r"(?i)^(?P<indent>\s*)(?P<key>[A-Za-z0-9_]+)(?P<sep>\s*=\s*)0\s*;\s*GENERATEXMLRES\((?P<arg>.*)\)\s*$"
)
INTEGER_ASSIGNMENT_RE = re.compile(r"^\s*[A-Za-z0-9_]+\s*=\s*(\d+)\s*$")
FLMM_BLOCK_RE_TEMPLATE = r"(?is)<{tag}\b(?P<attrs>[^>]*)>(?P<body>.*?)</{tag}>"
FLMM_ATTR_RE = re.compile(r"([A-Za-z0-9_:-]+)\s*=\s*\"([^\"]*)\"")


def detect_encoding(data: bytes) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return "utf-16"
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            data.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"


def read_text_preserve(path: Path) -> tuple[str, str, str]:
    raw = path.read_bytes()
    encoding = detect_encoding(raw)
    text = raw.decode(encoding)
    if "\r\n" in text:
        newline = "\r\n"
    elif "\n" in text:
        newline = "\n"
    elif "\r" in text:
        newline = "\r"
    else:
        newline = "\r\n"
    return text, encoding, newline


def normalize_dll_name(dll_name: str) -> str:
    return str(dll_name or "").strip().strip("\"'").replace("\\", "/").lower()


def resource_dlls_from_freelancer_ini(freelancer_ini: Path) -> list[str]:
    if not freelancer_ini.exists():
        return []
    text, _encoding, _newline = read_text_preserve(freelancer_ini)
    lines = text.splitlines()
    in_resources = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        lowered = stripped.lower()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_resources = lowered == "[resources]"
            continue
        if not in_resources or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip().lower() != "dll":
            continue
        dll_name = value.split(",", 1)[0].strip()
        if dll_name:
            out.append(dll_name)
    return out


def insert_resource_dll_line(raw_text: str, dll_name: str) -> tuple[str, bool]:
    current = {normalize_dll_name(item) for item in resource_dlls_from_freelancer_ini_text(raw_text)}
    if normalize_dll_name(dll_name) in current:
        return raw_text if raw_text.endswith("\n") else raw_text + ("\n" if raw_text else ""), False
    lines = raw_text.splitlines()
    sec_start = -1
    sec_end = len(lines)
    for index, line in enumerate(lines):
        stripped = line.strip().lower()
        if stripped == "[resources]":
            sec_start = index
            for inner in range(index + 1, len(lines)):
                candidate = lines[inner].strip()
                if candidate.startswith("[") and candidate.endswith("]"):
                    sec_end = inner
                    break
            break
    if sec_start < 0:
        out = list(lines)
        if out and out[-1].strip():
            out.append("")
        out.append("[Resources]")
        out.append(f"DLL = {dll_name}")
        return "\n".join(out) + "\n", True
    insert_at = sec_start + 1
    for index in range(sec_start + 1, sec_end):
        if lines[index].strip().lower().startswith("dll"):
            insert_at = index + 1
    out = lines[:insert_at] + [f"DLL = {dll_name}"] + lines[insert_at:]
    return "\n".join(out) + "\n", True


def resource_dlls_from_freelancer_ini_text(raw_text: str) -> list[str]:
    lines = raw_text.splitlines()
    in_resources = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        lowered = stripped.lower()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_resources = lowered == "[resources]"
            continue
        if not in_resources or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip().lower() != "dll":
            continue
        dll_name = value.split(",", 1)[0].strip()
        if dll_name:
            out.append(dll_name)
    return out


def ensure_resource_dll_registered(freelancer_ini: Path, dll_name: str, dry_run: bool) -> bool:
    text, encoding, _newline = read_text_preserve(freelancer_ini)
    updated_text, changed = insert_resource_dll_line(text, dll_name)
    if changed and not dry_run:
        write_text_with_fallback(
            freelancer_ini,
            updated_text,
            ensure_parent=True,
            primary_encoding=encoding,
            fallback_encoding="utf-8",
        )
    return changed


def resolve_dll_path(freelancer_ini: Path, dll_name: str) -> Path:
    resolver = DllStringResolver()
    resolved = resolver._resolve_dll_path(freelancer_ini, dll_name)  # noqa: SLF001
    if resolved is not None:
        return resolved
    relative = str(dll_name or "").strip().strip("\"'").replace("\\", "/")
    return freelancer_ini.parent / relative


def decode_resource_text_blob(blob: bytes) -> str:
    if not blob:
        return ""
    if len(blob) >= 2 and blob[:2] in {b"\xff\xfe", b"\xfe\xff"}:
        try:
            return blob.decode("utf-16", errors="ignore").replace("\x00", "").strip()
        except Exception:
            pass
    if b"\x00" in blob:
        try:
            return blob.decode("utf-16le", errors="ignore").replace("\x00", "").strip()
        except Exception:
            pass
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return blob.decode(encoding, errors="ignore").strip()
        except Exception:
            continue
    return ""


def load_html_resources(dll_path: Path) -> dict[int, str]:
    out: dict[int, str] = {}
    if pefile is None or not dll_path.is_file():
        return out
    pe = None
    try:
        pe = pefile.PE(str(dll_path), fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]]
        )
    except Exception:
        return out
    try:
        root = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
        if root is None:
            return out
        for type_entry in getattr(root, "entries", []):
            if getattr(type_entry, "id", None) != 23:
                continue
            for name_entry in getattr(type_entry.directory, "entries", []):
                local_id = getattr(name_entry, "id", None)
                if not isinstance(local_id, int) or local_id <= 0:
                    continue
                for lang_entry in getattr(name_entry.directory, "entries", []):
                    data_entry = getattr(lang_entry, "data", None)
                    if data_entry is None:
                        continue
                    rva = int(data_entry.struct.OffsetToData)
                    size = int(data_entry.struct.Size)
                    blob = pe.get_data(rva, size)
                    text = decode_resource_text_blob(blob)
                    if text:
                        out[int(local_id)] = text
                    break
    finally:
        try:
            if pe is not None:
                pe.close()
        except Exception:
            pass
    return out


def write_resource_dll_entries(dll_path: Path, strings_by_local_id: dict[int, str], infos_by_local_id: dict[int, str]) -> None:
    toolchain = resource_toolchain_commands()
    if toolchain is None:
        raise RuntimeError(
            "No supported resource toolchain found (need llvm-windres+lld-link, llvm-rc+lld-link, or rc.exe+link.exe)"
        )
    with tempfile.TemporaryDirectory(prefix="flatlas_ids_repair_") as temp_dir:
        rc_path, res_path, tmp_dll = write_resource_rc_bundle(
            temp_dir,
            strings_by_local_id=strings_by_local_id,
            infos_by_local_id=infos_by_local_id,
        )
        compile_cmd, link_cmd = toolchain(str(rc_path), str(res_path), str(tmp_dll))
        subprocess.run(compile_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run(link_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dll_path.parent.mkdir(parents=True, exist_ok=True)
        last_err = None
        for _attempt in range(8):
            try:
                shutil.copy2(tmp_dll, dll_path)
                last_err = None
                break
            except PermissionError as exc:
                last_err = exc
                time.sleep(0.15)
            except OSError as exc:
                last_err = exc
                if getattr(exc, "winerror", None) in (5, 32, 33, 1224):
                    time.sleep(0.15)
                    continue
                break
        if last_err is not None:
            staged_path = dll_path.with_name(f"{dll_path.name}.new")
            backup_path = dll_path.with_name(f"{dll_path.name}.bak")
            try:
                if staged_path.exists():
                    staged_path.unlink()
                shutil.copy2(tmp_dll, staged_path)
                if backup_path.exists():
                    backup_path.unlink()
                if dll_path.exists():
                    dll_path.replace(backup_path)
                staged_path.replace(dll_path)
                last_err = None
                try:
                    if backup_path.exists():
                        backup_path.unlink()
                except Exception:
                    pass
            except Exception:
                try:
                    if staged_path.exists():
                        staged_path.unlink()
                except Exception:
                    pass
        if last_err is not None:
            raise last_err


def find_freelancer_ini(game_root: Path) -> Path:
    exe_dir = ci_find(game_root, "EXE")
    if exe_dir is None:
        raise FileNotFoundError(f"EXE folder not found below {game_root}")
    freelancer_ini = ci_find(exe_dir, "freelancer.ini")
    if freelancer_ini is None or not freelancer_ini.is_file():
        raise FileNotFoundError(f"freelancer.ini not found below {exe_dir}")
    return freelancer_ini


def scan_used_ids(data_root: Path) -> set[int]:
    used: set[int] = set()
    for ini_path in sorted(path for path in data_root.rglob("*.ini") if path.is_file()):
        try:
            text, _encoding, _newline = read_text_preserve(ini_path)
        except Exception:
            continue
        for raw_line in text.splitlines():
            value_part = raw_line.split(";", 1)[0].strip()
            match = INTEGER_ASSIGNMENT_RE.match(value_part)
            if match is None:
                continue
            try:
                value = int(match.group(1))
            except Exception:
                continue
            if value > 0:
                used.add(value)
    return used


def unquote_argument(arg: str) -> str:
    text = str(arg or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    return text


def extract_flmm_blocks(text: str, tag: str) -> list[tuple[dict[str, str], str]]:
    pattern = re.compile(FLMM_BLOCK_RE_TEMPLATE.format(tag=re.escape(tag)), re.IGNORECASE | re.DOTALL)
    out: list[tuple[dict[str, str], str]] = []
    for match in pattern.finditer(str(text or "")):
        attrs_text = str(match.group("attrs") or "")
        attrs: dict[str, str] = {}
        for attr_match in FLMM_ATTR_RE.finditer(attrs_text):
            attrs[str(attr_match.group(1) or "").strip().lower()] = str(attr_match.group(2) or "")
        out.append((attrs, str(match.group("body") or "")))
    return out


def collect_flmm_xml_map(source_root: Path) -> dict[str, str]:
    xml_files = sorted(
        [path for path in source_root.iterdir() if path.is_file() and path.suffix.lower() == ".xml"],
        key=lambda path: (path.name.lower() != "script.xml", path.name.lower()),
    )
    xml_map: dict[str, str] = {}
    for xml_path in xml_files:
        text, _encoding, _newline = read_text_preserve(xml_path)
        for attrs, body in extract_flmm_blocks(text, "xmldata"):
            name = str(attrs.get("name", "") or "").strip()
            if not name:
                continue
            normalized = normalize_infocard_xml(str(body).strip())
            xml_map[name] = normalized or str(body).strip()
    return xml_map


def process_game_install(
    game_root: Path,
    dll_name: str,
    dry_run: bool,
    mod_source: Path | None = None,
) -> tuple[int, int, int, int, list[str]]:
    freelancer_ini = find_freelancer_ini(game_root)
    data_root = ci_find(game_root, "DATA")
    if data_root is None:
        raise FileNotFoundError(f"DATA folder not found below {game_root}")

    xml_map = collect_flmm_xml_map(mod_source) if mod_source is not None else {}
    xml_map_ci = {key.lower(): value for key, value in xml_map.items()}

    ensure_resource_dll_registered(freelancer_ini, dll_name, dry_run=dry_run)
    dll_entries = resource_dlls_from_freelancer_ini(freelancer_ini)
    slot = 0
    for index, entry in enumerate(dll_entries, start=1):
        if normalize_dll_name(entry) == normalize_dll_name(dll_name):
            slot = index
            break
    if slot <= 0:
        dll_entries.append(dll_name)
        slot = len(dll_entries)

    dll_path = resolve_dll_path(freelancer_ini, dll_name)
    resolver = DllStringResolver()
    resolver.load_from_resources(freelancer_ini, dll_entries)
    local_strings = resolver.slot_strings(slot)
    local_infos = load_html_resources(dll_path)
    used_global_ids = scan_used_ids(data_root)

    existing_global_by_text: dict[str, int] = {}
    for local_id, text in local_strings.items():
        existing_global_by_text[text] = DllStringResolver.make_global_id(slot, int(local_id))

    next_local_id = max(set(local_strings.keys()) | set(local_infos.keys()) | {0}) + 1
    queued_strings = dict(local_strings)
    queued_text_to_gid = dict(existing_global_by_text)
    queued_infos = dict(local_infos)
    queued_xml_to_gid: dict[str, int] = {}
    for local_id, xml_text in local_infos.items():
        normalized = normalize_infocard_xml(xml_text)
        if not normalized:
            continue
        queued_xml_to_gid[normalized] = DllStringResolver.make_global_id(slot, int(local_id))

    changed_files = 0
    replaced_lines = 0
    written_strings = 0
    written_infos = 0
    unresolved_xml_names: set[str] = set()

    ini_paths = sorted(path for path in data_root.rglob("*.ini") if path.is_file())
    for ini_path in ini_paths:
        text, encoding, newline = read_text_preserve(ini_path)
        lines = text.splitlines()
        file_changed = False
        for index, raw_line in enumerate(lines):
            match = STRING_MACRO_RE.match(raw_line)
            if match is not None:
                value = unquote_argument(match.group("arg"))
                if not value:
                    continue
                gid = queued_text_to_gid.get(value)
                if gid is None:
                    local_id = next_local_id
                    gid = DllStringResolver.make_global_id(slot, local_id)
                    while gid in used_global_ids:
                        local_id += 1
                        gid = DllStringResolver.make_global_id(slot, local_id)
                    next_local_id = local_id + 1
                    queued_strings[local_id] = value
                    queued_text_to_gid[value] = gid
                    used_global_ids.add(gid)
                    written_strings += 1
                replacement = f"{match.group('indent')}{match.group('key')}{match.group('sep')}{gid}"
                if lines[index] != replacement:
                    lines[index] = replacement
                    file_changed = True
                    replaced_lines += 1
                continue
            
            xml_match = XML_MACRO_RE.match(raw_line)
            if xml_match is None:
                continue
            xml_name = unquote_argument(xml_match.group("arg"))
            xml_text = xml_map.get(xml_name)
            if xml_text is None:
                xml_text = xml_map_ci.get(xml_name.lower())
            if xml_text is None:
                unresolved_xml_names.add(xml_name)
                continue
            normalized_xml = normalize_infocard_xml(xml_text)
            if not normalized_xml:
                unresolved_xml_names.add(xml_name)
                continue
            gid = queued_xml_to_gid.get(normalized_xml)
            if gid is None:
                local_id = next_local_id
                gid = DllStringResolver.make_global_id(slot, local_id)
                while gid in used_global_ids:
                    local_id += 1
                    gid = DllStringResolver.make_global_id(slot, local_id)
                next_local_id = local_id + 1
                queued_infos[local_id] = normalized_xml
                queued_xml_to_gid[normalized_xml] = gid
                used_global_ids.add(gid)
                written_infos += 1
            replacement = f"{xml_match.group('indent')}{xml_match.group('key')}{xml_match.group('sep')}{gid}"
            if lines[index] != replacement:
                lines[index] = replacement
                file_changed = True
                replaced_lines += 1
        if file_changed:
            changed_files += 1
            if not dry_run:
                output = newline.join(lines)
                if text.endswith(("\r\n", "\n", "\r")):
                    output += newline
                write_text_with_fallback(
                    ini_path,
                    output,
                    ensure_parent=True,
                    primary_encoding=encoding,
                    fallback_encoding="utf-8",
                )

    if not dry_run and (queued_strings != local_strings or queued_infos != local_infos):
        write_resource_dll_entries(dll_path, queued_strings, queued_infos)

    return changed_files, replaced_lines, written_strings, written_infos, sorted(unresolved_xml_names)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repair installed GENERATESTRRES and GENERATEXMLRES leftovers by writing real IDS values into INI files and a resource DLL."
    )
    parser.add_argument("game_root", help="Freelancer installation root or mod install root")
    parser.add_argument("--dll-name", default="FLAtlas_resources.dll", help="Resource DLL to write generated strings to")
    parser.add_argument("--mod-source", help="Optional FLMM mod source folder used to resolve GENERATEXMLRES xmldata names")
    parser.add_argument("--dry-run", action="store_true", help="Only report what would change")
    args = parser.parse_args()

    game_root = Path(args.game_root).resolve()
    if not game_root.exists() or not game_root.is_dir():
        parser.error(f"Folder not found: {game_root}")

    mod_source: Path | None = None
    if args.mod_source:
        mod_source = Path(args.mod_source).resolve()
        if not mod_source.exists() or not mod_source.is_dir():
            parser.error(f"Mod source folder not found: {mod_source}")

    changed_files, replaced_lines, written_strings, written_infos, unresolved_xml_names = process_game_install(
        game_root,
        dll_name=str(args.dll_name),
        dry_run=bool(args.dry_run),
        mod_source=mod_source,
    )
    mode = "Would change" if args.dry_run else "Changed"
    print(f"{mode} files: {changed_files}")
    print(f"Replaced macro lines: {replaced_lines}")
    print(f"String IDs allocated: {written_strings}")
    print(f"Infocard IDs allocated: {written_infos}")
    if unresolved_xml_names:
        print(f"Unresolved GENERATEXMLRES names: {len(unresolved_xml_names)}")
        for name in unresolved_xml_names:
            print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())