from __future__ import annotations

from pathlib import Path


def rc_escape(text: str) -> str:
    out: list[str] = []
    last_hex_escape = False
    for ch in str(text or "").replace("\r\n", "\n").replace("\r", "\n"):
        code = ord(ch)
        if ch == '"':
            out.append('""')
            last_hex_escape = False
            continue
        if ch == "\\":
            out.append("\\\\")
            last_hex_escape = False
            continue
        if ch == "\n":
            out.append("\\012")
            last_hex_escape = False
            continue
        if 32 <= code <= 126:
            if last_hex_escape and ch in "0123456789ABCDEFabcdef":
                out.append('""')
            out.append(ch)
            last_hex_escape = False
            continue
        out.append(f"\\x{code:04X}")
        last_hex_escape = True
    return "".join(out)


def write_resource_rc_bundle(
    target_dir: str | Path,
    *,
    strings_by_local_id: dict[int, str],
    infos_by_local_id: dict[int, str],
) -> tuple[Path, Path, Path]:
    tdir = Path(target_dir)
    rc_path = tdir / "resource.rc"
    res_path = tdir / "resource.res"
    tmp_dll = tdir / "resource.dll"
    rc_lines = ["#pragma code_page(65001)", ""]
    if strings_by_local_id:
        rc_lines.extend(["STRINGTABLE", "BEGIN"])
        for lid in sorted(strings_by_local_id.keys()):
            rc_lines.append(f'    {lid} L"{rc_escape(strings_by_local_id[lid])}"')
        rc_lines.extend(["END", ""])
    for lid in sorted(infos_by_local_id.keys()):
        info_file = tdir / f"ids_info_{lid}.xml"
        info_file.write_text(infos_by_local_id[lid], encoding="utf-8")
        rc_lines.append(f'{lid} 23 "{info_file.as_posix()}"')
    rc_lines.append("")
    rc_path.write_text("\n".join(rc_lines), encoding="utf-8-sig")
    return rc_path, res_path, tmp_dll
