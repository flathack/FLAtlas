from __future__ import annotations

import json
import zipfile
from pathlib import Path

from fl_editor.mod_export import (
    collect_changed_files,
    default_script_xml,
    filter_export_plan,
    normalize_archive_path,
    write_changed_files_zip,
    write_flmod_package,
)


def test_collect_changed_files_detects_new_and_modified(tmp_path: Path):
    reference = tmp_path / "clean"
    mod = tmp_path / "mod"
    (reference / "DATA" / "EQUIPMENT").mkdir(parents=True)
    (mod / "DATA" / "EQUIPMENT").mkdir(parents=True)
    (reference / "DATA" / "EQUIPMENT" / "goods.ini").write_text("same\n", encoding="utf-8")
    (mod / "DATA" / "EQUIPMENT" / "goods.ini").write_text("changed\n", encoding="utf-8")
    (reference / "DATA" / "EQUIPMENT" / "market.ini").write_text("same\n", encoding="utf-8")
    (mod / "DATA" / "EQUIPMENT" / "market.ini").write_text("same\n", encoding="utf-8")
    (mod / "DATA" / "UNIVERSE" / "Systems").mkdir(parents=True)
    (mod / "DATA" / "UNIVERSE" / "Systems" / "New.ini").write_text("[System]\n", encoding="utf-8")

    plan = collect_changed_files(mod, reference)

    rows = {(item.relative_path, item.status) for item in plan.export_files}
    assert rows == {
        ("DATA/EQUIPMENT/goods.ini", "modified"),
        ("DATA/UNIVERSE/Systems/New.ini", "new"),
    }
    assert plan.unchanged_count == 1


def test_collect_changed_files_reports_progress(tmp_path: Path):
    reference = tmp_path / "clean"
    mod = tmp_path / "mod"
    (reference / "DATA").mkdir(parents=True)
    (mod / "DATA").mkdir(parents=True)
    (reference / "DATA" / "a.ini").write_text("old\n", encoding="utf-8")
    (mod / "DATA" / "a.ini").write_text("new\n", encoding="utf-8")
    calls: list[tuple[str, int, int, str]] = []

    collect_changed_files(
        mod,
        reference,
        progress=lambda stage, current, total, path: calls.append((stage, current, total, path)) or True,
    )

    assert [call[0] for call in calls] == ["reference", "mod"]
    assert calls[-1][1] == calls[-1][2]


def test_collect_changed_files_ignores_flatlas_history_folder(tmp_path: Path):
    reference = tmp_path / "clean"
    mod = tmp_path / "mod"
    (reference / "DATA").mkdir(parents=True)
    (mod / ".flatlas").mkdir(parents=True)
    (mod / ".flatlas" / "history.json").write_text("{}", encoding="utf-8")

    plan = collect_changed_files(mod, reference)

    assert plan.export_files == ()


def test_collect_changed_files_ignores_flatlas_launcher_folder(tmp_path: Path):
    reference = tmp_path / "clean"
    mod = tmp_path / "mod"
    (reference / "DATA").mkdir(parents=True)
    (mod / ".FLAtlasLauncher").mkdir(parents=True)
    (mod / ".FLAtlasLauncher" / "launcher-state.json").write_text("{}", encoding="utf-8")

    plan = collect_changed_files(mod, reference)

    assert plan.export_files == ()


def test_collect_changed_files_ignores_runtime_log_files(tmp_path: Path):
    reference = tmp_path / "clean"
    mod = tmp_path / "mod"
    reference.mkdir()
    mod.mkdir()
    (mod / "FLAtlas-Change.log").write_text("history\n", encoding="utf-8")
    (mod / "ReShade.log").write_text("runtime\n", encoding="utf-8")

    plan = collect_changed_files(mod, reference)

    assert plan.export_files == ()


def test_write_changed_files_zip_includes_manifest_and_export_files(tmp_path: Path):
    reference = tmp_path / "clean"
    mod = tmp_path / "mod"
    (reference / "DATA").mkdir(parents=True)
    (mod / "DATA").mkdir(parents=True)
    (reference / "DATA" / "a.ini").write_text("old\n", encoding="utf-8")
    (mod / "DATA" / "a.ini").write_text("new\n", encoding="utf-8")
    plan = collect_changed_files(mod, reference)
    target = tmp_path / "out.zip"

    count = write_changed_files_zip(plan, target)

    assert count == 1
    with zipfile.ZipFile(target, "r") as zf:
        assert sorted(zf.namelist()) == ["DATA/a.ini", "FLAtlas-export-manifest.json"]
        manifest = json.loads(zf.read("FLAtlas-export-manifest.json").decode("utf-8"))
    assert manifest["modified_count"] == 1


def test_write_archive_reports_progress(tmp_path: Path):
    reference = tmp_path / "clean"
    mod = tmp_path / "mod"
    (reference / "DATA").mkdir(parents=True)
    (mod / "DATA").mkdir(parents=True)
    (reference / "DATA" / "a.ini").write_text("old\n", encoding="utf-8")
    (mod / "DATA" / "a.ini").write_text("new\n", encoding="utf-8")
    plan = collect_changed_files(mod, reference)
    calls: list[tuple[str, int, int, str]] = []

    write_changed_files_zip(
        plan,
        tmp_path / "out.zip",
        progress=lambda stage, current, total, path: calls.append((stage, current, total, path)) or True,
    )

    assert [call[0] for call in calls] == ["file", "manifest"]
    assert calls[-1][1] == calls[-1][2]


def test_filter_export_plan_removes_manual_exclusions_from_archive(tmp_path: Path):
    reference = tmp_path / "clean"
    mod = tmp_path / "mod"
    (reference / "DATA").mkdir(parents=True)
    (mod / "DATA").mkdir(parents=True)
    (reference / "DATA" / "a.ini").write_text("old\n", encoding="utf-8")
    (reference / "DATA" / "b.ini").write_text("old\n", encoding="utf-8")
    (mod / "DATA" / "a.ini").write_text("new\n", encoding="utf-8")
    (mod / "DATA" / "b.ini").write_text("new\n", encoding="utf-8")
    plan = collect_changed_files(mod, reference)
    filtered = filter_export_plan(plan, {"DATA/a.ini"})
    target = tmp_path / "out.zip"

    count = write_changed_files_zip(filtered, target)

    assert count == 1
    with zipfile.ZipFile(target, "r") as zf:
        assert "DATA/a.ini" not in zf.namelist()
        assert "DATA/b.ini" in zf.namelist()


def test_write_flmod_package_contains_basic_script_and_no_existing_script(tmp_path: Path):
    reference = tmp_path / "clean"
    mod = tmp_path / "mod"
    (reference / "DATA").mkdir(parents=True)
    (mod / "DATA").mkdir(parents=True)
    (reference / "DATA" / "a.ini").write_text("old\n", encoding="utf-8")
    (mod / "DATA" / "a.ini").write_text("new\n", encoding="utf-8")
    (mod / "script.xml").write_text("<script><data method=\"copyfile\"></data></script>\n", encoding="utf-8")
    plan = collect_changed_files(mod, reference)
    target = tmp_path / "out.flmod"
    script = default_script_xml(name="My Mod", author="Me", description="Test", savesafe=True)

    count = write_flmod_package(plan, target, script_xml=script)

    assert count == 1
    with zipfile.ZipFile(target, "r") as zf:
        assert sorted(zf.namelist()) == ["DATA/a.ini", "script.xml"]
        script_text = zf.read("script.xml").decode("utf-8")
    assert '<header name="My Mod" savesafe="true">' in script_text
    assert "<data" not in script_text


def test_normalize_archive_path_uses_forward_slashes():
    assert normalize_archive_path(r"DATA\UNIVERSE\foo.ini") == "DATA/UNIVERSE/foo.ini"
