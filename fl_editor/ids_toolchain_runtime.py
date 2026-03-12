"""Helpers for IDS toolchain detection and command resolution."""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path, PurePosixPath
from typing import Callable


def ids_toolchain_install_supported_platform(platform: str | None = None) -> bool:
    platform_name = str(platform or sys.platform)
    return platform_name.startswith("win") or platform_name.startswith("linux")


def linux_ids_toolchain_install_command(which: Callable[[str], str | None] | None = None) -> str | None:
    which_func = which or shutil.which
    if which_func("apt-get"):
        return "sudo apt-get update && sudo apt-get install -y llvm lld mingw-w64 binutils-mingw-w64"
    if which_func("dnf"):
        return "sudo dnf install -y llvm lld mingw64-binutils mingw32-binutils"
    if which_func("pacman"):
        return "sudo pacman -Sy --noconfirm llvm lld mingw-w64-binutils"
    if which_func("zypper"):
        return "sudo zypper --non-interactive install llvm lld mingw64-cross-binutils"
    return None


def linux_ids_toolchain_manual_text(command: str | None) -> str:
    lines = [
        "FLAtlas IDS Toolchain Installer (Linux)",
        "=======================================",
    ]
    if command:
        lines.extend(
            [
                "Run this command manually:",
                f"  {command}",
                "",
                "Required tools:",
                "  - lld-link (or ld.lld)",
                "  - llvm-windres (or x86_64-w64-mingw32-windres / i686-w64-mingw32-windres / windres / llvm-rc)",
            ]
        )
        return "\n".join(lines)
    lines.extend(
        [
            "ERROR: Unsupported distribution. Install required tools manually:",
            "  - lld-link (or ld.lld)",
            "  - llvm-windres (or x86_64-w64-mingw32-windres / i686-w64-mingw32-windres / windres / llvm-rc)",
        ]
    )
    return "\n".join(lines)


def candidate_tool_dirs(
    *,
    env: dict[str, str] | None = None,
    platform: str | None = None,
    project_root: Path | None = None,
    frozen: bool | None = None,
    executable: str | None = None,
) -> list[Path]:
    env_map = env if env is not None else os.environ
    platform_name = str(platform or sys.platform)
    is_frozen = bool(getattr(sys, "frozen", False) if frozen is None else frozen)
    exe_path = str(getattr(sys, "executable", "") if executable is None else executable)
    root = project_root or (Path(__file__).resolve().parent.parent)

    dirs: list[Path] = []
    env_dir = str(env_map.get("FLATLAS_TOOLCHAIN_DIR", "") or "").strip()
    if env_dir:
        env_parts = [env_dir]
        if ";" in env_dir:
            env_parts = [part for chunk in env_parts for part in chunk.split(";")]
        if ":" in env_dir and not re.match(r"^[A-Za-z]:[\\/]", env_dir):
            env_parts = [part for chunk in env_parts for part in chunk.split(":")]
        for part in env_parts:
            item = str(part or "").strip()
            if item:
                dirs.append(Path(item))

    dirs.extend([root / "tools", root / "tools" / "bin", root / "tools" / "llvm" / "bin"])
    if platform_name.startswith("win"):
        pf = str(env_map.get("ProgramFiles", "") or "").strip()
        pf86 = str(env_map.get("ProgramFiles(x86)", "") or "").strip()
        pfw6432 = str(env_map.get("ProgramW6432", "") or "").strip()
        if pf:
            dirs.append(Path(pf) / "LLVM" / "bin")
        if pf86:
            dirs.append(Path(pf86) / "LLVM" / "bin")
        if pfw6432:
            dirs.append(Path(pfw6432) / "LLVM" / "bin")
        # Some Windows Python/app environments do not expose ProgramFiles
        # reliably. Probe the canonical install locations directly as fallback.
        dirs.extend(
            [
                Path("C:/Program Files/LLVM/bin"),
                Path("C:/Program Files (x86)/LLVM/bin"),
            ]
        )
    elif platform_name.startswith("linux"):
        dirs.extend([Path("/usr/bin"), Path("/usr/local/bin"), Path("/var/run/host/usr/bin"), Path("/run/host/usr/bin")])
        llvm_home = str(env_map.get("LLVM_HOME", "") or "").strip()
        if llvm_home:
            dirs.extend([Path(llvm_home), Path(llvm_home) / "bin"])
        for root_dir in (Path("/usr/lib"), Path("/usr/lib64")):
            if root_dir.exists():
                dirs.extend(sorted(root_dir.glob("llvm*/bin")))

    if is_frozen and exe_path:
        exe_dir = Path(exe_path).resolve().parent
        dirs.extend(
            [
                exe_dir / "tools",
                exe_dir / "tools" / "bin",
                exe_dir / "tools" / "llvm" / "bin",
                exe_dir / "_internal" / "tools",
                exe_dir / "_internal" / "tools" / "bin",
                exe_dir / "_internal" / "tools" / "llvm" / "bin",
            ]
        )

    out: list[Path] = []
    seen: set[str] = set()
    for directory in dirs:
        key = str(directory.resolve()) if directory.exists() else str(directory)
        if key in seen:
            continue
        seen.add(key)
        out.append(directory)
    return out


def resolve_tool_exe(
    exe_name: str,
    *,
    which: Callable[[str], str | None] | None = None,
    dirs: list[Path] | None = None,
) -> str | None:
    which_func = which or shutil.which
    hit = which_func(exe_name)
    if hit:
        return hit
    for directory in dirs if dirs is not None else candidate_tool_dirs():
        candidates = [exe_name]
        if not exe_name.lower().endswith(".exe"):
            candidates.append(f"{exe_name}.exe")
        for name in candidates:
            path = directory / name
            if path.is_file():
                return str(path)
    return None


def resource_toolchain_commands(
    *,
    resolve_exe: Callable[[str], str | None] | None = None,
    platform: str | None = None,
):
    platform_name = str(platform or sys.platform)
    resolver = resolve_exe or (lambda exe: resolve_tool_exe(exe))

    windres = (
        resolver("llvm-windres")
        or resolver("x86_64-w64-mingw32-windres")
        or resolver("i686-w64-mingw32-windres")
        or resolver("windres")
    )
    lld_link = resolver("lld-link")
    ld_lld = resolver("ld.lld")
    llvm_rc = resolver("llvm-rc")
    rc_exe = resolver("rc.exe") or (resolver("rc") if platform_name.startswith("win") else None)
    link_exe = resolver("link.exe") or (resolver("link") if platform_name.startswith("win") else None)

    def _link_cmd(res_path: str, tmp_dll: str) -> list[str]:
        if lld_link:
            return [lld_link, "/NOENTRY", "/DLL", "/MACHINE:X86", f"/OUT:{tmp_dll}", res_path]
        if ld_lld:
            return [ld_lld, "-flavor", "link", "/NOENTRY", "/DLL", "/MACHINE:X86", f"/OUT:{tmp_dll}", res_path]
        return []

    if windres and (lld_link or ld_lld):
        def _llvm_windres(rc_path: str, res_path: str, tmp_dll: str):
            return ([windres, "--target=pe-i386", rc_path, res_path], _link_cmd(res_path, tmp_dll))
        return _llvm_windres

    if llvm_rc and (lld_link or ld_lld):
        def _llvm_rc(rc_path: str, res_path: str, tmp_dll: str):
            return ([llvm_rc, f"/fo{res_path}", rc_path], _link_cmd(res_path, tmp_dll))
        return _llvm_rc

    if platform_name.startswith("win") and rc_exe and link_exe:
        def _msvc(rc_path: str, res_path: str, tmp_dll: str):
            return (
                [rc_exe, "/nologo", f"/fo{res_path}", rc_path],
                [link_exe, "/NOLOGO", "/NOENTRY", "/DLL", "/MACHINE:X86", f"/OUT:{tmp_dll}", res_path],
            )
        return _msvc

    return None


def has_ids_resource_toolchain(**kwargs) -> bool:
    return resource_toolchain_commands(**kwargs) is not None


def apply_ids_toolchain_env_override(path_text: str, env: dict[str, str] | None = None) -> None:
    env_map = env if env is not None else os.environ
    value = str(path_text or "").strip()
    if value:
        env_map["FLATLAS_TOOLCHAIN_DIR"] = value
    else:
        env_map.pop("FLATLAS_TOOLCHAIN_DIR", None)


def auto_detect_ids_toolchain_dir(
    *,
    platform: str | None = None,
    resolve_exe: Callable[[str], str | None] | None = None,
) -> str:
    platform_name = str(platform or sys.platform)
    if not platform_name.startswith("linux"):
        return ""
    resolver = resolve_exe or (lambda exe: resolve_tool_exe(exe))
    found_dirs: list[str] = []
    preferred_dirs = ["/usr/bin", "/usr/local/bin", "/var/run/host/usr/bin", "/run/host/usr/bin"]

    def _add(path_text: str) -> None:
        text = str(path_text or "").strip()
        if text and text not in found_dirs:
            found_dirs.append(text)

    for path_text in preferred_dirs:
        if Path(path_text).is_dir():
            _add(path_text)

    for tool in (
        "lld-link",
        "ld.lld",
        "llvm-windres",
        "x86_64-w64-mingw32-windres",
        "i686-w64-mingw32-windres",
        "windres",
        "llvm-rc",
    ):
        hit = resolver(tool)
        if hit:
            hit_text = str(hit or "").strip()
            if hit_text.startswith("/") and not hit_text.startswith("//"):
                _add(str(PurePosixPath(hit_text).parent))
            else:
                _add(str(Path(hit_text).resolve().parent))
    return ":".join(found_dirs)
