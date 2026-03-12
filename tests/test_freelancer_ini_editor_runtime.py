from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fl_editor import freelancer_ini_editor_runtime as runtime


class _Cfg:
    def __init__(self):
        self.values = {}

    def get(self, key, default=""):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


def test_resource_dlls_from_text_collects_unique_resource_entries():
    text = """
    [Resources]
    DLL = alpha.dll
    dll = beta.dll, something
    DLL = alpha.dll
    ; DLL = ignored.dll
    [Other]
    DLL = gamma.dll
    """

    assert runtime.resource_dlls_from_text(text) == ["alpha.dll", "beta.dll"]


def test_build_freelancer_ini_editor_meta_prefers_custom_dlls(tmp_path: Path):
    meta = runtime.build_freelancer_ini_editor_meta(
        ini_read=tmp_path / "EXE" / "freelancer.ini",
        ini_write=tmp_path / "overlay" / "EXE" / "freelancer.ini",
        is_overlay_mode=True,
        editor_text="[Resources]\nDLL = custom.dll\n",
        baseline_dlls=["vanilla.dll"],
        current_dlls_from_ini=["custom.dll"],
        preferred_dll="",
        default_dll="FLAtlas_resources.dll",
    )

    assert meta.shown_path.endswith("overlay\\EXE\\freelancer.ini")
    assert "custom.dll" in meta.info_html
    assert meta.choices[0][1] == "custom.dll"
    assert meta.selected_dll == "custom.dll"


def test_normalize_freelancer_ini_text_enforces_lf_and_trailing_newline():
    assert runtime.normalize_freelancer_ini_text("a\r\nb") == "a\nb\n"


def test_apply_selected_resource_dll_inserts_missing_dll_only_once():
    updated, changed = runtime.apply_selected_resource_dll(
        "[Resources]\nDLL = alpha.dll\n",
        "beta.dll",
        lambda text, dll: (text + f"DLL = {dll}\n", True),
    )

    assert changed is True
    assert "beta.dll" in updated

    unchanged, changed_again = runtime.apply_selected_resource_dll(
        updated,
        "beta.dll",
        lambda text, dll: (text + f"DLL = {dll}\n", True),
    )

    assert changed_again is False
    assert unchanged == updated


def test_refresh_after_freelancer_ini_save_updates_name_dependent_ui(tmp_path: Path):
    target = tmp_path / "EXE" / "freelancer.ini"
    window = SimpleNamespace(
        _reload_dll_name_cache=lambda: setattr(window, "reload_called", True),
        _refresh_system_name_cache=lambda gp: setattr(window, "name_cache_path", gp),
        _primary_game_path=lambda: str(tmp_path),
        _apply_system_name_mode_to_ui=lambda: setattr(window, "name_mode_applied", True),
        _rebuild_object_combo=lambda: setattr(window, "combo_rebuilt", True),
        _selected=None,
        _object_display_label=lambda obj: "Selected",
        name_lbl=SimpleNamespace(setText=lambda text: setattr(window, "name_label", text)),
        status=SimpleNamespace(showMessage=lambda text: setattr(window, "status_message", text)),
        statusBar=lambda: window.status,
    )

    runtime.refresh_after_freelancer_ini_save(window, target)

    assert window.reload_called is True
    assert window.name_cache_path == str(tmp_path)
    assert window.name_mode_applied is True
    assert window.combo_rebuilt is True
    assert str(target) in window.status_message
