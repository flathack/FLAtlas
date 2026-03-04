"""DLL resource helpers for Freelancer IDS lookup and future write support."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .path_utils import ci_find, ci_resolve

try:
    import pefile  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pefile = None


@dataclass
class PendingStringEntry:
    slot: int
    local_id: int
    text: str


class DllStringResolver:
    """Resolves Freelancer IDS values to texts via string table resources."""

    def __init__(self):
        self._slot_to_dll: dict[int, str] = {}
        self._slot_to_path: dict[int, Path] = {}
        self._slot_to_strings: dict[int, dict[int, str]] = {}
        self._pending: dict[tuple[int, int], PendingStringEntry] = {}

    @property
    def available(self) -> bool:
        return pefile is not None

    @property
    def slot_to_dll(self) -> dict[int, str]:
        return dict(self._slot_to_dll)

    def clear(self):
        self._slot_to_dll.clear()
        self._slot_to_path.clear()
        self._slot_to_strings.clear()
        self._pending.clear()

    def load_from_resources(self, freelancer_ini: Path, dll_entries: list[str]):
        self.clear()
        if not freelancer_ini.exists():
            return
        for slot, dll_name in enumerate(dll_entries, start=1):
            self._slot_to_dll[slot] = dll_name
            dll_path = self._resolve_dll_path(freelancer_ini, dll_name)
            if dll_path is None:
                continue
            self._slot_to_path[slot] = dll_path
            self._slot_to_strings[slot] = self._load_string_table(dll_path)

    def load_from_resource_pairs(self, pairs: list[tuple[Path, str]]):
        """Load DLL resources from explicit (freelancer.ini, dll entry) pairs."""
        self.clear()
        for slot, pair in enumerate(pairs, start=1):
            ini_path, dll_name = pair
            self._slot_to_dll[slot] = str(dll_name)
            dll_path = self._resolve_dll_path(Path(ini_path), str(dll_name))
            if dll_path is None:
                continue
            self._slot_to_path[slot] = dll_path
            self._slot_to_strings[slot] = self._load_string_table(dll_path)

    def resolve_name(self, ids_value: str | int | None) -> str:
        val = self._parse_int(ids_value)
        if val <= 0:
            return ""
        slot, local_id = self._split_global_id(val)
        # Vanilla/legacy IDs can be plain local IDs (< 65536) without
        # an encoded resource slot. In that case, probe all loaded slots
        # in order and return the first match.
        if slot <= 0:
            legacy_local = val & 0xFFFF
            if legacy_local <= 0:
                return ""
            for s in sorted(self._slot_to_strings.keys()):
                txt = self._slot_to_strings.get(s, {}).get(legacy_local, "")
                if txt:
                    return txt
            return ""
        if local_id <= 0:
            return ""
        pend = self._pending.get((slot, local_id))
        if pend is not None:
            return pend.text
        return self._slot_to_strings.get(slot, {}).get(local_id, "")

    def allocate_local_id(self, slot: int, min_local_id: int = 1) -> int:
        used = set(self._slot_to_strings.get(slot, {}).keys())
        used.update(local for s, local in self._pending.keys() if s == slot)
        cand = max(1, int(min_local_id))
        while cand in used:
            cand += 1
        return cand

    def queue_string_entry(self, slot: int, text: str, min_local_id: int = 1) -> int:
        local_id = self.allocate_local_id(slot, min_local_id=min_local_id)
        self._pending[(slot, local_id)] = PendingStringEntry(slot=slot, local_id=local_id, text=text)
        return local_id

    def queue_string_entry_with_local_id(self, slot: int, local_id: int, text: str):
        self._pending[(slot, int(local_id))] = PendingStringEntry(slot=slot, local_id=int(local_id), text=text)

    def pending_entries(self) -> list[PendingStringEntry]:
        return list(self._pending.values())

    def slot_strings(self, slot: int) -> dict[int, str]:
        """Returns a copy of all loaded local string IDs for one resource slot."""
        return dict(self._slot_to_strings.get(int(slot), {}))

    @staticmethod
    def make_global_id(slot: int, local_id: int) -> int:
        return ((int(slot) & 0xFFFF) << 16) | (int(local_id) & 0xFFFF)

    @staticmethod
    def _split_global_id(global_id: int) -> tuple[int, int]:
        return ((int(global_id) >> 16) & 0xFFFF, int(global_id) & 0xFFFF)

    @staticmethod
    def _parse_int(value: str | int | None) -> int:
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        txt = str(value).strip()
        if not txt:
            return 0
        try:
            return int(txt)
        except Exception:
            return 0

    def _resolve_dll_path(self, freelancer_ini: Path, dll_name: str) -> Path | None:
        dll_name = str(dll_name or "").strip().strip("\"'")
        if not dll_name:
            return None
        rel = dll_name.replace("\\", "/")
        ini_dir = freelancer_ini.parent
        base_roots = [ini_dir, ini_dir.parent, ini_dir.parent.parent]
        for base in base_roots:
            if not base or not base.exists():
                continue
            p = self._ci_resolve_rel_with_dotdot(base, rel)
            if p and p.is_file():
                return p
            p2 = ci_resolve(base, rel)
            if p2 and p2.is_file():
                return p2
        p = Path(rel)
        if p.is_file():
            return p
        return None

    @staticmethod
    def _ci_resolve_rel_with_dotdot(base: Path, rel: str) -> Path | None:
        """Resolve like ci_resolve, but supports '.' and '..' path segments."""
        try:
            current = base
            for part in str(rel or "").split("/"):
                seg = part.strip()
                if not seg or seg == ".":
                    continue
                if seg == "..":
                    parent = current.parent
                    if parent == current:
                        return None
                    current = parent
                    continue
                hit = ci_find(current, seg)
                if hit is None:
                    return None
                current = hit
            return current if current.is_file() else None
        except Exception:
            return None

    def _load_string_table(self, dll_path: Path) -> dict[int, str]:
        if pefile is None:
            return {}
        pe = None
        try:
            pe = pefile.PE(str(dll_path), fast_load=True)
            pe.parse_data_directories(
                directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]]
            )
        except Exception:
            return {}

        out: dict[int, str] = {}
        try:
            root = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
            if root is None:
                return out

            for type_entry in getattr(root, "entries", []):
                if getattr(type_entry, "id", None) != 6:  # RT_STRING
                    continue
                for name_entry in getattr(type_entry.directory, "entries", []):
                    block_id = getattr(name_entry, "id", None)
                    if not isinstance(block_id, int):
                        continue
                    for lang_entry in getattr(name_entry.directory, "entries", []):
                        data_entry = getattr(lang_entry, "data", None)
                        if data_entry is None:
                            continue
                        rva = int(data_entry.struct.OffsetToData)
                        size = int(data_entry.struct.Size)
                        blob = pe.get_data(rva, size)
                        self._decode_string_block(blob, block_id, out)
        finally:
            try:
                if pe is not None:
                    pe.close()
            except Exception:
                pass
        return out

    @staticmethod
    def _decode_string_block(blob: bytes, block_id: int, out: dict[int, str]):
        off = 0
        base_id = (int(block_id) - 1) * 16
        for i in range(16):
            if off + 2 > len(blob):
                break
            slen = int.from_bytes(blob[off:off + 2], "little")
            off += 2
            byte_len = slen * 2
            if off + byte_len > len(blob):
                break
            raw = blob[off:off + byte_len]
            off += byte_len
            if slen <= 0:
                continue
            try:
                txt = raw.decode("utf-16le", errors="ignore").strip()
            except Exception:
                txt = ""
            if txt:
                # Win32 StringTable: resource IDs are zero-based within the first block.
                # ID = (block_id - 1) * 16 + index
                out[base_id + i] = txt
