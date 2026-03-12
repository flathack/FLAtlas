from __future__ import annotations

from pathlib import Path

from fl_editor import ids_toolchain_runtime as runtime


def test_ids_toolchain_install_supported_platform_handles_known_platforms():
    assert runtime.ids_toolchain_install_supported_platform("win32") is True
    assert runtime.ids_toolchain_install_supported_platform("linux") is True
    assert runtime.ids_toolchain_install_supported_platform("darwin") is False


def test_linux_ids_toolchain_install_command_picks_first_supported_manager():
    which = lambda name: "/usr/bin/apt-get" if name == "apt-get" else None

    assert runtime.linux_ids_toolchain_install_command(which) == (
        "sudo apt-get update && sudo apt-get install -y llvm lld mingw-w64 binutils-mingw-w64"
    )


def test_linux_ids_toolchain_manual_text_includes_command_or_error():
    assert "sudo apt-get" in runtime.linux_ids_toolchain_manual_text("sudo apt-get install -y llvm")
    assert "ERROR: Unsupported distribution" in runtime.linux_ids_toolchain_manual_text(None)


def test_candidate_tool_dirs_splits_env_and_deduplicates(tmp_path: Path):
    project_root = tmp_path / "repo"
    env = {"FLATLAS_TOOLCHAIN_DIR": f"{tmp_path / 'a'};{tmp_path / 'b'};{tmp_path / 'a'}"}

    dirs = runtime.candidate_tool_dirs(
        env=env,
        platform="win32",
        project_root=project_root,
        frozen=False,
        executable="",
    )

    assert dirs[0] == tmp_path / "a"
    assert dirs[1] == tmp_path / "b"
    assert project_root / "tools" in dirs
    assert dirs.count(tmp_path / "a") == 1


def test_resource_toolchain_commands_prefers_windres_and_lld():
    mapping = {
        "llvm-windres": "/tools/llvm-windres",
        "lld-link": "/tools/lld-link",
    }
    toolchain = runtime.resource_toolchain_commands(resolve_exe=lambda name: mapping.get(name), platform="linux")

    compile_cmd, link_cmd = toolchain("a.rc", "a.res", "a.dll")

    assert compile_cmd == ["/tools/llvm-windres", "--target=pe-i386", "a.rc", "a.res"]
    assert link_cmd == ["/tools/lld-link", "/NOENTRY", "/DLL", "/MACHINE:X86", "/OUT:a.dll", "a.res"]


def test_apply_ids_toolchain_env_override_sets_and_clears_env():
    env = {}

    runtime.apply_ids_toolchain_env_override("/opt/llvm/bin", env=env)
    assert env["FLATLAS_TOOLCHAIN_DIR"] == "/opt/llvm/bin"

    runtime.apply_ids_toolchain_env_override("", env=env)
    assert "FLATLAS_TOOLCHAIN_DIR" not in env


def test_auto_detect_ids_toolchain_dir_collects_linux_dirs(monkeypatch):
    monkeypatch.setattr(runtime, "resolve_tool_exe", lambda exe_name, **kwargs: None)
    monkeypatch.setattr(Path, "is_dir", lambda self: str(self) in {"/usr/bin", "/run/host/usr/bin"})

    mapping = {
        "lld-link": "/usr/bin/lld-link",
        "llvm-windres": "/custom/llvm-windres",
    }
    detected = runtime.auto_detect_ids_toolchain_dir(
        platform="linux",
        resolve_exe=lambda exe_name: mapping.get(exe_name),
    )

    assert detected == "/usr/bin:/custom"
