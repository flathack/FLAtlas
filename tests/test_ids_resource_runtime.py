from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fl_editor.dll_resources import DllStringResolver
from fl_editor import ids_resource_runtime as runtime


class _Cfg:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value


class _Parser:
    def __init__(self, parsed=None):
        self.parsed = dict(parsed or {})

    def parse(self, path):
        return self.parsed[str(path)]


def _build_window(tmp_path: Path):
    window = SimpleNamespace()
    window._ids_resource_dll_override = ""
    window._cfg = _Cfg()
    window._dll_resolver = DllStringResolver()
    window._ids_display_cache = {"old": "value"}
    window._parser = _Parser()
    window.logged = []
    window.reload_calls = 0
    window.write_calls = []
    window._find_freelancer_ini_write = lambda: tmp_path / "EXE" / "freelancer.ini"
    window._find_freelancer_ini_read = lambda: tmp_path / "EXE" / "freelancer.ini"
    window._read_text_best_effort = lambda path: "[Resources]\nDLL = other.dll\n"
    window._resource_dlls_from_freelancer_ini = lambda path: ["other.dll"]
    window._normalize_dll_name = lambda name: str(name).strip().lower()
    window._insert_resource_dll_line = lambda text, dll_name: (text + f'DLL = {dll_name}\n', True)
    window._remove_resource_dll_line = lambda text, dll_name: (text.replace(f"DLL = {dll_name}\n", ""), True)
    window._append_dll_change_log = lambda msg: window.logged.append(msg)
    window._reload_dll_name_cache = lambda: setattr(window, "reload_calls", window.reload_calls + 1)
    window._resource_slot_for_dll_name = lambda name: runtime.resource_slot_for_dll_name(window, name)
    window._resolve_preferred_resource_dll_path = lambda name: tmp_path / "EXE" / name
    window._load_dll_html_resources = lambda path: {5: "<RDL/>"}
    window._write_resource_dll_entries = lambda path, strings, infos=None: (
        window.write_calls.append((path, dict(strings), dict(infos or {}))) or (True, "")
    )
    window._scan_used_ids_name_values = lambda game_path=None: {DllStringResolver.make_global_id(1, 5)}
    window._scan_used_ids_info_values = lambda game_path=None: {DllStringResolver.make_global_id(1, 6)}
    window._primary_game_path = lambda: str(tmp_path)
    window._find_all_systems = lambda gp: []
    window._iter_equipment_ini_paths_for_usage = lambda gp: []
    window._iter_missions_ini_paths_for_ids_scan = lambda gp: []
    window._entry_get_value = lambda entries, key: next((v for k, v in entries if k.lower() == key.lower()), "")
    window._ensure_writable_path = lambda path: path
    window._write_sections_to_file = lambda path, sections: window.write_calls.append((path, sections))
    window._active_resource_dll_name = lambda: runtime.active_resource_dll_name(window)
    window._ensure_preferred_resource_dll_registered = lambda name: True
    return window


def test_ensure_preferred_resource_dll_registered_appends_entry(monkeypatch, tmp_path: Path):
    target = tmp_path / "EXE" / "freelancer.ini"
    target.parent.mkdir(parents=True)
    target.write_text("[Resources]\n", encoding="utf-8")
    writes = []

    monkeypatch.setattr(
        runtime,
        "write_text_with_fallback",
        lambda path, text, ensure_parent=False: writes.append((path, text, ensure_parent)),
    )

    window = _build_window(tmp_path)

    ok = runtime.ensure_preferred_resource_dll_registered(window, "FLAtlas_resources.dll")

    assert ok is True
    assert writes[0][0] == target
    assert "FLAtlas_resources.dll" in writes[0][1]
    assert window.logged[-1].endswith("FLAtlas_resources.dll")


def test_resource_slot_for_dll_name_uses_resolver_before_ini_list(tmp_path: Path):
    ini_path = tmp_path / "EXE" / "freelancer.ini"
    ini_path.parent.mkdir(parents=True)
    ini_path.write_text("", encoding="utf-8")
    window = _build_window(tmp_path)
    window._dll_resolver.load_from_resource_pairs([(ini_path, "first.dll"), (ini_path, "second.dll")])
    window._resource_dlls_from_freelancer_ini = lambda path: ["third.dll"]

    assert runtime.resource_slot_for_dll_name(window, "second.dll") == 2
    assert runtime.resource_slot_for_dll_name(window, "third.dll") == 1


def test_ensure_ids_name_in_user_dll_reuses_existing_local_id(tmp_path: Path):
    ini_path = tmp_path / "EXE" / "freelancer.ini"
    ini_path.parent.mkdir(parents=True)
    ini_path.write_text("", encoding="utf-8")
    window = _build_window(tmp_path)
    window._dll_resolver.load_from_resource_pairs([(ini_path, "FLAtlas_resources.dll")])
    window._dll_resolver.queue_string_entry_with_local_id(1, 7, "old")

    gid = DllStringResolver.make_global_id(1, 7)
    result = runtime.ensure_ids_name_in_user_dll(window, str(gid), "New Name")

    assert result == str(gid)
    path, strings, infos = window.write_calls[-1]
    assert path == tmp_path / "EXE" / "FLAtlas_resources.dll"
    assert strings[7] == "New Name"
    assert infos[5] == "<RDL/>"
    assert window._cfg.values["ids.resource_dll_name"] == "FLAtlas_resources.dll"
    assert window.reload_calls == 2
    assert window._ids_display_cache == {}


def test_ensure_ids_info_in_user_dll_allocates_new_local_id(tmp_path: Path):
    ini_path = tmp_path / "EXE" / "freelancer.ini"
    ini_path.parent.mkdir(parents=True)
    ini_path.write_text("", encoding="utf-8")
    window = _build_window(tmp_path)
    window._dll_resolver.load_from_resource_pairs([(ini_path, "FLAtlas_resources.dll")])
    window._dll_resolver.slot_strings = lambda slot: {1: "Name"}
    window._load_dll_html_resources = lambda path: {2: "<old/>"}

    result = runtime.ensure_ids_info_in_user_dll(window, "0", "<RDL><TEXT/></RDL>")

    assert result == str(DllStringResolver.make_global_id(1, 3))
    path, strings, infos = window.write_calls[-1]
    assert strings[1] == "Name"
    assert infos[3] == "<RDL><TEXT/></RDL>"


def test_ensure_ids_info_in_user_dll_normalizes_plain_text_to_rdl(tmp_path: Path):
    ini_path = tmp_path / "EXE" / "freelancer.ini"
    ini_path.parent.mkdir(parents=True)
    ini_path.write_text("", encoding="utf-8")
    window = _build_window(tmp_path)
    window._dll_resolver.load_from_resource_pairs([(ini_path, "FLAtlas_resources.dll")])
    window._dll_resolver.slot_strings = lambda slot: {1: "Name"}
    window._load_dll_html_resources = lambda path: {2: "<old/>"}

    result = runtime.ensure_ids_info_in_user_dll(window, "0", "#Headline\\nBody line")

    assert result == str(DllStringResolver.make_global_id(1, 3))
    _path, _strings, infos = window.write_calls[-1]
    assert infos[3].startswith("<RDL>")
    assert "<TEXT>Headline</TEXT>" in infos[3]
    assert "<TEXT>Body line</TEXT>" in infos[3]


def test_ensure_ids_info_in_user_dll_strips_xml_declaration(tmp_path: Path):
    ini_path = tmp_path / "EXE" / "freelancer.ini"
    ini_path.parent.mkdir(parents=True)
    ini_path.write_text("", encoding="utf-8")
    window = _build_window(tmp_path)
    window._dll_resolver.load_from_resource_pairs([(ini_path, "FLAtlas_resources.dll")])
    window._dll_resolver.slot_strings = lambda slot: {1: "Name"}
    window._load_dll_html_resources = lambda path: {2: "<old/>"}

    result = runtime.ensure_ids_info_in_user_dll(window, "0", '<?xml version="1.0" encoding="UTF-16"?><RDL><TEXT>Ok</TEXT></RDL>')

    assert result == str(DllStringResolver.make_global_id(1, 3))
    _path, _strings, infos = window.write_calls[-1]
    assert infos[3] == "<RDL><TEXT>Ok</TEXT></RDL>"


def test_ensure_ids_name_in_user_dll_reuses_cached_scan_results(tmp_path: Path):
    ini_path = tmp_path / "EXE" / "freelancer.ini"
    ini_path.parent.mkdir(parents=True)
    ini_path.write_text("", encoding="utf-8")
    window = _build_window(tmp_path)
    window._dll_resolver.load_from_resource_pairs([(ini_path, "FLAtlas_resources.dll")])
    window._ids_scan_cache = {}
    calls = {"name": 0, "info": 0}

    def _scan_name(game_path=None):
        calls["name"] += 1
        return runtime.scan_used_ids_name_values(window, game_path)

    def _scan_info(game_path=None):
        calls["info"] += 1
        return runtime.scan_used_ids_info_values(window, game_path)

    window._scan_used_ids_name_values = _scan_name
    window._scan_used_ids_info_values = _scan_info

    first = runtime.ensure_ids_name_in_user_dll(window, "0", "Name A")
    second = runtime.ensure_ids_name_in_user_dll(window, "0", "Name B")

    assert first == str(DllStringResolver.make_global_id(1, 6))
    assert second == str(DllStringResolver.make_global_id(1, 7))
    assert calls == {"name": 1, "info": 1}


def test_relink_ids_info_references_updates_unique_files_only(tmp_path: Path):
    a = tmp_path / "a.ini"
    b = tmp_path / "b.ini"
    window = _build_window(tmp_path)
    old_id = 100
    new_id = 200
    window._find_all_systems = lambda gp: [{"path": str(a)}, {"path": str(a)}]
    window._iter_equipment_ini_paths_for_usage = lambda gp: [b]
    window._iter_missions_ini_paths_for_ids_scan = lambda gp: [b]
    window._parser = _Parser(
        {
            str(a): [("Object", [("ids_info", "100"), ("other", "x")])],
            str(b): [("Object", [("ids_info", "100"), ("ids_info", "300")])],
        }
    )

    files, refs = runtime.relink_ids_info_references(window, old_id, new_id, str(tmp_path))

    assert (files, refs) == (2, 2)
    assert window.write_calls == [
        (str(a), [("Object", [("ids_info", "200"), ("other", "x")])]),
        (str(b), [("Object", [("ids_info", "200"), ("ids_info", "300")])]),
    ]
