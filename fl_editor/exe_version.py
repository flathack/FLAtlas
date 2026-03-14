"""Read and write VS_VERSIONINFO resources in PE executables.

Used to change the displayed version of *freelancer.exe* (or similar
32-bit EXEs) without altering game code.

* **Reading** uses ``pefile`` and works cross-platform.
* **Writing** uses ``kernel32.UpdateResourceW`` and requires Windows.
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import pefile  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional dependency
    pefile = None

# Windows resource type id for version info
RT_VERSION = 16


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class VersionInfo:
    """Parsed VS_VERSIONINFO data."""

    file_version: tuple[int, int, int, int] = (0, 0, 0, 0)
    product_version: tuple[int, int, int, int] = (0, 0, 0, 0)
    strings: dict[str, str] = field(default_factory=dict)
    lang_id: int = 0x0409      # English (US)
    charset_id: int = 0x04B0   # Unicode


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_version_string(version: str) -> tuple[int, int, int, int]:
    """Parse ``'1.2.3.4'`` or ``'1.2'`` into a 4-part tuple.

    Missing parts default to 0.  Commas or dots are accepted as separators.
    """
    parts = version.replace(",", ".").split(".")
    result = [0, 0, 0, 0]
    for i, p in enumerate(parts[:4]):
        try:
            result[i] = int(p.strip())
        except ValueError:
            pass
    return (result[0], result[1], result[2], result[3])


def format_version_tuple(v: tuple[int, int, int, int]) -> str:
    """Format ``(1, 2, 3, 4)`` as ``'1.2.3.4'``."""
    return ".".join(str(x) for x in v)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def read_version_info(exe_path: Path | str) -> VersionInfo | None:
    """Read VS_VERSIONINFO from a PE file.  Returns *None* on failure."""
    if pefile is None:
        return None

    exe_path = Path(exe_path)
    if not exe_path.is_file():
        return None

    try:
        pe = pefile.PE(str(exe_path), fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]]
        )
    except Exception:
        return None

    if not hasattr(pe, "FileInfo") or not pe.FileInfo:
        pe.close()
        return None

    info = VersionInfo()

    # --- Fixed file info (binary version numbers) ---
    if hasattr(pe, "VS_FIXEDFILEINFO") and pe.VS_FIXEDFILEINFO:
        ffi = pe.VS_FIXEDFILEINFO[0]
        info.file_version = (
            (ffi.FileVersionMS >> 16) & 0xFFFF,
            ffi.FileVersionMS & 0xFFFF,
            (ffi.FileVersionLS >> 16) & 0xFFFF,
            ffi.FileVersionLS & 0xFFFF,
        )
        info.product_version = (
            (ffi.ProductVersionMS >> 16) & 0xFFFF,
            ffi.ProductVersionMS & 0xFFFF,
            (ffi.ProductVersionLS >> 16) & 0xFFFF,
            ffi.ProductVersionLS & 0xFFFF,
        )

    # --- String table entries ---
    for file_info_list in pe.FileInfo:
        for entry in file_info_list:
            if hasattr(entry, "StringTable"):
                for st in entry.StringTable:
                    try:
                        key_str = st.LangID if hasattr(st, "LangID") else ""
                        if isinstance(key_str, bytes):
                            key_str = key_str.decode("ascii", errors="ignore")
                        if len(key_str) == 8:
                            info.lang_id = int(key_str[:4], 16)
                            info.charset_id = int(key_str[4:], 16)
                    except (ValueError, TypeError):
                        pass

                    for k, v in st.entries.items():
                        key = k.decode("utf-8", errors="ignore") if isinstance(k, bytes) else str(k)
                        val = v.decode("utf-8", errors="ignore") if isinstance(v, bytes) else str(v)
                        info.strings[key] = val

            if hasattr(entry, "Var"):
                for var in entry.Var:
                    if hasattr(var, "entry"):
                        for vk, vv in var.entry.items():
                            key = vk.decode("utf-8", errors="ignore") if isinstance(vk, bytes) else str(vk)
                            if key.lower() == "translation":
                                if isinstance(vv, int):
                                    info.lang_id = vv & 0xFFFF
                                    info.charset_id = (vv >> 16) & 0xFFFF

    pe.close()
    return info


# ---------------------------------------------------------------------------
# Binary builders for VS_VERSIONINFO resource blob
# ---------------------------------------------------------------------------

def _pad(data: bytes, alignment: int = 4) -> bytes:
    """Append zero bytes so *len(data)* is a multiple of *alignment*."""
    remainder = len(data) % alignment
    if remainder:
        data += b"\x00" * (alignment - remainder)
    return data


def _align(offset: int, alignment: int = 4) -> int:
    remainder = offset % alignment
    return offset + (alignment - remainder) if remainder else offset


def _build_version_string(key: str, value: str) -> bytes:
    """Build a single *String* child (key/value pair)."""
    key_bytes = (key + "\0").encode("utf-16-le")
    value_bytes = (value + "\0").encode("utf-16-le")
    value_len_chars = len(value) + 1  # including null terminator

    header_size = 6
    padded_before_value = _align(header_size + len(key_bytes))
    total_len = padded_before_value + len(value_bytes)

    result = struct.pack("<HHH", total_len, value_len_chars, 1)  # wType=1 (text)
    result += key_bytes
    result = _pad(result)
    result += value_bytes
    return result


def _build_string_table(lang_charset: str, strings: dict[str, str]) -> bytes:
    """Build a *StringTable* structure."""
    key_bytes = (lang_charset + "\0").encode("utf-16-le")

    children = b""
    for k, v in strings.items():
        children += _pad(_build_version_string(k, v))

    header_size = 6
    content_before_children = _align(header_size + len(key_bytes))
    total_len = content_before_children + len(children)

    result = struct.pack("<HHH", total_len, 0, 1)
    result += key_bytes
    result = _pad(result)
    result += children
    return result


def _build_string_file_info(lang_charset: str, strings: dict[str, str]) -> bytes:
    key_bytes = ("StringFileInfo\0").encode("utf-16-le")
    table = _pad(_build_string_table(lang_charset, strings))

    header_size = 6
    content_before_children = _align(header_size + len(key_bytes))
    total_len = content_before_children + len(table)

    result = struct.pack("<HHH", total_len, 0, 1)
    result += key_bytes
    result = _pad(result)
    result += table
    return result


def _build_var_file_info(lang_id: int, charset_id: int) -> bytes:
    key_bytes = ("VarFileInfo\0").encode("utf-16-le")

    # Var child: Translation
    var_key_bytes = ("Translation\0").encode("utf-16-le")
    var_value = struct.pack("<HH", lang_id, charset_id)

    var_header_size = 6
    var_content_before_value = _align(var_header_size + len(var_key_bytes))
    var_total_len = var_content_before_value + len(var_value)

    var_data = struct.pack("<HHH", var_total_len, len(var_value), 0)  # wType=0 (binary)
    var_data += var_key_bytes
    var_data = _pad(var_data)
    var_data += var_value
    var_data = _pad(var_data)

    header_size = 6
    content_before_children = _align(header_size + len(key_bytes))
    total_len = content_before_children + len(var_data)

    result = struct.pack("<HHH", total_len, 0, 1)
    result += key_bytes
    result = _pad(result)
    result += var_data
    return result


def _build_vs_fixedfileinfo(
    file_version: tuple[int, int, int, int],
    product_version: tuple[int, int, int, int],
) -> bytes:
    """Build VS_FIXEDFILEINFO (52 bytes)."""
    fv_ms = (file_version[0] << 16) | file_version[1]
    fv_ls = (file_version[2] << 16) | file_version[3]
    pv_ms = (product_version[0] << 16) | product_version[1]
    pv_ls = (product_version[2] << 16) | product_version[3]

    return struct.pack(
        "<LLLLLLLLLLLLL",
        0xFEEF04BD,   # dwSignature
        0x00010000,   # dwStrucVersion (1.0)
        fv_ms, fv_ls,
        pv_ms, pv_ls,
        0x0000003F,   # dwFileFlagsMask (VS_FFI_FILEFLAGSMASK)
        0x00000000,   # dwFileFlags
        0x00040004,   # dwFileOS (VOS_NT_WINDOWS32)
        0x00000001,   # dwFileType (VFT_APP)
        0x00000000,   # dwFileSubtype
        0x00000000,   # dwFileDateMS
        0x00000000,   # dwFileDateLS
    )


def build_version_resource(info: VersionInfo) -> bytes:
    """Build the complete VS_VERSIONINFO binary blob from *info*."""
    root_key_bytes = ("VS_VERSION_INFO\0").encode("utf-16-le")
    ffi = _build_vs_fixedfileinfo(info.file_version, info.product_version)

    lang_charset = f"{info.lang_id:04x}{info.charset_id:04x}"

    # Make sure the text version strings are consistent with the fixed info
    strings = dict(info.strings)
    strings["FileVersion"] = format_version_tuple(info.file_version)
    strings["ProductVersion"] = format_version_tuple(info.product_version)

    sfi = _pad(_build_string_file_info(lang_charset, strings))
    vfi = _pad(_build_var_file_info(info.lang_id, info.charset_id))

    header_size = 6
    content_before_ffi = _align(header_size + len(root_key_bytes))
    padded_after_ffi = _align(content_before_ffi + len(ffi))
    total_len = padded_after_ffi + len(sfi) + len(vfi)

    result = struct.pack("<HHH", total_len, len(ffi), 0)  # wType=0 (binary)
    result += root_key_bytes
    result = _pad(result)
    result += ffi
    result = _pad(result)
    result += sfi
    result += vfi
    return result


# ---------------------------------------------------------------------------
# Existing resource enumeration
# ---------------------------------------------------------------------------

def _existing_version_lang_ids(exe_path: Path) -> list[int]:
    """Return language IDs of all existing RT_VERSION resources in *exe_path*."""
    if pefile is None:
        return []
    try:
        pe = pefile.PE(str(exe_path), fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]]
        )
    except Exception:
        return []
    lang_ids: list[int] = []
    if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        pe.close()
        return lang_ids
    for type_entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if type_entry.id != RT_VERSION:
            continue
        for id_entry in type_entry.directory.entries:
            for lang_entry in id_entry.directory.entries:
                lang_ids.append(int(lang_entry.id))
    pe.close()
    return lang_ids


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def write_version_info(exe_path: Path | str, info: VersionInfo) -> tuple[bool, str]:
    """Write *info* as ``RT_VERSION`` resource into an existing PE executable.

    Returns ``(True, "")`` on success, ``(False, error_message)`` on failure.

    .. note:: Windows only – uses ``kernel32.UpdateResourceW``.
    """
    if not sys.platform.startswith("win"):
        return False, "Writing PE resources is only supported on Windows."

    exe_path = Path(exe_path)
    if not exe_path.is_file():
        return False, f"File not found: {exe_path}"

    import ctypes
    from ctypes import wintypes

    blob = build_version_resource(info)

    # Enumerate existing language IDs BEFORE locking the file.
    old_lang_ids = _existing_version_lang_ids(exe_path)

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        begin_update = kernel32.BeginUpdateResourceW
        begin_update.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
        begin_update.restype = wintypes.HANDLE

        update_resource = kernel32.UpdateResourceW
        update_resource.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.WORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        update_resource.restype = wintypes.BOOL

        end_update = kernel32.EndUpdateResourceW
        end_update.argtypes = [wintypes.HANDLE, wintypes.BOOL]
        end_update.restype = wintypes.BOOL

        handle = begin_update(str(exe_path), False)
        if not handle:
            err = ctypes.get_last_error()
            return False, f"BeginUpdateResource failed (error {err})"

        try:
            res_type = ctypes.c_void_p(RT_VERSION)
            res_id = ctypes.c_void_p(1)

            # Remove ALL existing RT_VERSION entries (may have multiple
            # language IDs, e.g. 0x0000 and 0x0409) so the old binary
            # VS_FIXEDFILEINFO doesn't shadow the new one.
            for old_lang in old_lang_ids:
                update_resource(handle, res_type, res_id, old_lang, None, 0)

            data_buf = ctypes.create_string_buffer(blob)

            if not update_resource(
                handle, res_type, res_id, info.lang_id,
                data_buf, len(blob),
            ):
                err = ctypes.get_last_error()
                end_update(handle, True)
                return False, f"UpdateResource failed (error {err})"
        except Exception:
            end_update(handle, True)
            raise

        if not end_update(handle, False):
            err = ctypes.get_last_error()
            return False, f"EndUpdateResource failed (error {err})"

        return True, ""
    except Exception as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# High-level convenience
# ---------------------------------------------------------------------------

def patch_exe_version(
    exe_path: Path | str,
    new_file_version: str | None = None,
    new_product_version: str | None = None,
    extra_strings: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """Read current version info, apply changes and write back.

    *new_file_version* / *new_product_version*: version strings like
    ``"1.1.0.0"`` – only changed when not *None*.

    *extra_strings*: additional string-table entries to set/override
    (e.g. ``{"InternalName": "Freelancer", "CompanyName": "..."}``).

    Returns ``(success, error_message)``.
    """
    info = read_version_info(exe_path)
    if info is None:
        # No existing version info – start from scratch
        info = VersionInfo()

    if new_file_version is not None:
        info.file_version = parse_version_string(new_file_version)
    if new_product_version is not None:
        info.product_version = parse_version_string(new_product_version)
    if extra_strings:
        info.strings.update(extra_strings)

    return write_version_info(exe_path, info)
