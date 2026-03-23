"""Workflow helpers for Mod Manager activation, deactivation and edit context."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QMessageBox

from .i18n import tr
from .parser import find_universe_ini


def mod_manager_apply_edit_context_from_state(window: Any) -> None:
    pid = str(window._mm_editing_mod_id or "").strip()
    if not pid:
        return
    profile = None
    for candidate in window._mm_profiles:
        if str(candidate.get("id", "")).strip() == pid:
            profile = candidate
            break
    if profile is None:
        window._mm_editing_mod_id = ""
        window._mod_manager_save_state()
        window._update_active_mod_indicator()
        return
    source = window._mod_manager_profile_source(profile)
    if source is None or not source.exists() or not source.is_dir():
        window._mm_editing_mod_id = ""
        window._mod_manager_save_state()
        window._update_active_mod_indicator()
        return
    mode = str(profile.get("mode", "") or "").strip().lower()
    if mode == "direct":
        window._storage_mode = "single"
        window._single_game_path = str(source)
        return
    clean_target = window._mod_manager_clean_root_path()
    ref_root = str(clean_target or window._vanilla_game_path or "").strip()
    if not ref_root or not find_universe_ini(ref_root):
        window._mm_editing_mod_id = ""
        window._mod_manager_save_state()
        window._update_active_mod_indicator()
        return
    window._storage_mode = "overlay"
    window._vanilla_game_path = ref_root
    window._mod_game_path = str(source)


def mod_manager_deactivate_active(window: Any, mod_id: str | None = None, *, show_dialog: bool = True) -> tuple[bool, str]:
    active = window._mod_manager_active_entry_by_id(mod_id) if mod_id else window._mod_manager_last_active_entry()
    if not isinstance(active, dict):
        message = tr("mod_manager.err.not_active")
        if show_dialog:
            QMessageBox.warning(window, tr("mod_manager.title"), message)
        return False, message
    active = dict(active)
    active_pid = str(active.get("mod_id", "") or "").strip()
    target_root = Path(str(active.get("target_root", "") or "").strip())
    backup_dir = Path(str(active.get("backup_dir", "") or "").strip())
    created_rel = [str(x) for x in active.get("created_rel", []) if str(x).strip()]
    overwritten_rel = [str(x) for x in active.get("overwritten_rel", []) if str(x).strip()]
    opensp_overwritten_rel = [str(x) for x in active.get("opensp_overwritten_rel", []) if str(x).strip()]
    temp_resource_dll_name = str(active.get("temp_resource_dll_name", "") or "").strip()
    if not target_root or not target_root.exists():
        window._mm_active = [
            entry for entry in window._mm_active
            if not (isinstance(entry, dict) and str(entry.get("mod_id", "") or "").strip() == active_pid)
        ]
        window._mod_manager_save_state()
        window._mod_manager_append_active_log(active, tr("mod_manager.log.deactivate_target_missing"), category="ERROR")
        return False, tr("mod_manager.err.target_missing")
    if not window._close_system_tabs_under_root(target_root):
        return False, tr("mod_manager.msg.deactivate_cancelled_tabs")

    created_rel, overwritten_rel = window._mod_manager_reconcile_active_relpaths(
        active,
        target_root,
        backup_dir,
        created_rel,
        overwritten_rel,
        opensp_overwritten_rel,
    )

    errors: list[str] = []
    restored = 0
    removed = 0
    restore_rel = []
    seen_rel: set[str] = set()
    for rel in overwritten_rel + opensp_overwritten_rel:
        key = str(rel).replace("\\", "/").lower()
        if key in seen_rel:
            continue
        seen_rel.add(key)
        restore_rel.append(rel)
    progress = window._make_mod_manager_progress(tr("mod_manager.progress.deactivating"), len(created_rel) + len(restore_rel))
    step = 0
    window._mod_manager_append_active_log(
        active,
        tr("mod_manager.log.deactivate_started").format(target=str(target_root)),
        category="DEACTIVATE",
    )
    try:
        for rel in created_rel:
            target = target_root / rel
            step += 1
            window._update_mod_manager_progress(progress, step, template=tr("mod_manager.progress.removing"), path=rel)
            try:
                if target.is_file():
                    target.unlink()
                    removed += 1
                    window._mod_manager_remove_empty_parents(target, target_root)
                window._append_mod_manager_progress_action(progress, tr("mod_manager.progress.removing_action").format(path=rel), ok=True)
            except Exception as exc:
                errors.append(f"remove {rel}: {exc}")
                window._append_mod_manager_progress_action(progress, tr("mod_manager.progress.removing_action").format(path=rel), ok=False)
        for rel in restore_rel:
            source = backup_dir / rel
            target = target_root / rel
            step += 1
            window._update_mod_manager_progress(progress, step, template=tr("mod_manager.progress.restoring"), path=rel)
            try:
                if not source.is_file():
                    window._append_mod_manager_progress_action(progress, tr("mod_manager.progress.restoring_action").format(path=rel), ok=False)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                restored += 1
                window._append_mod_manager_progress_action(progress, tr("mod_manager.progress.restoring_action").format(path=rel), ok=True)
            except Exception as exc:
                errors.append(f"restore {rel}: {exc}")
                window._append_mod_manager_progress_action(progress, tr("mod_manager.progress.restoring_action").format(path=rel), ok=False)
        try:
            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)
        except Exception:
            pass
        if temp_resource_dll_name:
            try:
                window._cleanup_temporary_flmm_resource_dll(target_root, temp_resource_dll_name)
            except Exception as exc:
                errors.append(f"temp dll cleanup {temp_resource_dll_name}: {exc}")
        remaining_after = [
            entry for entry in window._mm_active
            if not (isinstance(entry, dict) and str(entry.get("mod_id", "") or "").strip() == active_pid)
        ]
        ok_saves, saves_msg = True, ""
        if not remaining_after:
            ok_saves, saves_msg = window._mod_manager_store_savegames_for_deactivation(active)
            if not ok_saves:
                errors.append(f"savegames: {saves_msg}")
        window._mm_active = remaining_after
        window._mod_manager_save_state()
        message = tr("mod_manager.msg.deactivate_result").format(removed=removed, restored=restored)
        if saves_msg:
            message += "\n" + saves_msg
        if errors:
            message += "\n\n" + tr("mod_manager.errors") + ":\n" + "\n".join(errors[:25])
            window._mod_manager_append_active_log(active, message, category="ERROR")
        else:
            window._mod_manager_append_active_log(active, message, category="DEACTIVATE")
        if show_dialog:
            QMessageBox.information(window, tr("mod_manager.title"), message)
        return len(errors) == 0, message
    finally:
        progress.setValue(progress.maximum())
        progress.close()


def mod_manager_activate_profile(window: Any, profile: dict, *, show_dialog: bool = True) -> tuple[bool, str]:
    source = window._mod_manager_profile_source(profile)
    clean_root = window._mod_manager_clean_root_path()
    if source is None or not source.exists() or not source.is_dir():
        window._mod_manager_append_profile_log(profile, tr("mod_manager.err.source_not_found"), category="ERROR")
        return False, tr("mod_manager.err.source_not_found")
    if clean_root is None or not clean_root.exists() or not clean_root.is_dir():
        window._mod_manager_append_profile_log(profile, tr("mod_manager.err.clean_invalid"), category="ERROR")
        return False, tr("mod_manager.err.clean_invalid")

    is_flmm_profile = window._mod_manager_is_flmm_profile(profile)
    files = window._mod_manager_collect_flmm_activation_files(source) if is_flmm_profile else window._mod_manager_collect_source_files(source)
    if not files and not is_flmm_profile:
        window._mod_manager_append_profile_log(profile, tr("mod_manager.err.no_files"), category="ERROR")
        return False, tr("mod_manager.err.no_files")
    pid = str(profile.get("id", "") or "").strip()
    if pid and window._mod_manager_active_entry_by_id(pid) is not None:
        window._mod_manager_append_profile_log(profile, tr("mod_manager.err.already_active"), category="ERROR")
        return False, tr("mod_manager.err.already_active")
    conflicting_ids = window._mod_manager_conflicting_active_ids(profile)
    if conflicting_ids:
        conflict_names = [window._mod_manager_profile_name_by_id(item) or item for item in sorted(conflicting_ids)]
        window._mod_manager_append_profile_log(
            profile,
            tr("mod_manager.err.conflict_active").format(mods=", ".join(conflict_names)),
            category="ERROR",
        )
        return False, tr("mod_manager.err.conflict_active").format(mods=", ".join(conflict_names))
    had_active_before = window._mod_manager_has_active_entries()

    backup_base = window._mod_manager_backup_base_dir()
    backup_id = window._mod_manager_make_id(str(profile.get("id", "")))
    backup_dir = backup_base / backup_id
    backup_dir.mkdir(parents=True, exist_ok=True)

    overwritten_rel: list[str] = []
    created_rel: list[str] = []
    temp_resource_dll_name = window._temporary_flmm_resource_dll_name(profile) if is_flmm_profile else ""
    copied = 0
    errors: list[str] = []
    rollback_errors: list[str] = []
    flmm_ops_total = len(window._flmm_collect_script_spec(source)[1].get("operations", [])) if is_flmm_profile else 0
    progress_total = max(1, len(files) + flmm_ops_total)
    progress = window._make_mod_manager_progress(tr("mod_manager.progress.activating"), progress_total)
    progress_step = 0
    window._mod_manager_append_profile_log(
        profile,
        tr("mod_manager.log.activate_started").format(source=str(source), target=str(clean_root)),
        category="ACTIVATE",
    )

    def _rollback_activation_changes() -> None:
        for rel in dict.fromkeys(created_rel):
            target = clean_root / rel
            try:
                if target.is_file():
                    target.unlink()
                    window._mod_manager_remove_empty_parents(target, clean_root)
            except Exception as exc:
                rollback_errors.append(f"rollback remove {rel}: {exc}")
        for rel in dict.fromkeys(overwritten_rel):
            source_backup = backup_dir / rel
            target = clean_root / rel
            try:
                if source_backup.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_backup, target)
            except Exception as exc:
                rollback_errors.append(f"rollback restore {rel}: {exc}")
        try:
            shutil.rmtree(backup_dir, ignore_errors=True)
        except Exception:
            pass
        if temp_resource_dll_name:
            try:
                window._cleanup_temporary_flmm_resource_dll(clean_root, temp_resource_dll_name)
            except Exception as exc:
                rollback_errors.append(f"rollback temp dll {temp_resource_dll_name}: {exc}")

    try:
        for src in files:
            if (copied % 25) == 0:
                window._pump_ui(tr("status.loading"))
            try:
                rel = src.relative_to(source).as_posix()
            except Exception:
                continue
            progress_step += 1
            window._update_mod_manager_progress(progress, progress_step, template=tr("mod_manager.progress.copying"), path=rel)
            target = clean_root / rel
            try:
                if target.exists() and target.is_file():
                    backup = backup_dir / rel
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, backup)
                    overwritten_rel.append(rel)
                elif not target.exists():
                    created_rel.append(rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
                copied += 1
                window._append_mod_manager_progress_action(progress, tr("mod_manager.progress.copying_action").format(path=rel), ok=True)
            except Exception as exc:
                errors.append(f"copy {rel}: {exc}")
                window._append_mod_manager_progress_action(progress, tr("mod_manager.progress.copying_action").format(path=rel), ok=False)

        if is_flmm_profile and not errors:
            old_override = str(getattr(window, "_ids_resource_dll_override", "") or "").strip()
            old_ids_scan_cache = getattr(window, "_ids_scan_cache", None)
            window._ids_resource_dll_override = temp_resource_dll_name
            window._ids_scan_cache = {}
            try:
                ok_flmm, flmm_ops_done, flmm_overwritten_rel, flmm_created_rel, flmm_err = window._flmm_apply_script_to_target(
                    profile,
                    source,
                    clean_root,
                    backup_dir,
                    progress_cb=lambda idx, total, rel: (
                        progress.setMaximum(max(1, len(files) + int(total))),
                        window._update_mod_manager_progress(
                            progress,
                            len(files) + int(idx),
                            template=tr("mod_manager.progress.applying"),
                            path=rel or "...",
                        ),
                    ),
                    action_result_cb=lambda action, ok: window._append_mod_manager_progress_action(progress, action, ok=ok),
                )
                for rel in flmm_overwritten_rel:
                    if rel not in overwritten_rel:
                        overwritten_rel.append(rel)
                for rel in flmm_created_rel:
                    if rel not in created_rel:
                        created_rel.append(rel)
                copied += int(flmm_ops_done)
            finally:
                window._ids_resource_dll_override = old_override
                window._ids_scan_cache = old_ids_scan_cache
            if not ok_flmm:
                _rollback_activation_changes()
                message = tr("mod_manager.err.activate_failed") + ":\n" + flmm_err
                if rollback_errors:
                    message += "\n\nRollback errors:\n" + "\n".join(rollback_errors[:10])
                window._mod_manager_append_profile_log(profile, message, category="ERROR")
                return False, message

        if errors:
            _rollback_activation_changes()
            message = tr("mod_manager.err.activate_failed") + ":\n" + "\n".join(errors[:25])
            if rollback_errors:
                message += "\n\nRollback errors:\n" + "\n".join(rollback_errors[:10])
            window._mod_manager_append_profile_log(profile, message, category="ERROR")
            return False, message

        opensp_enabled = bool(profile.get("opensp_enabled", False)) if str(profile.get("mode", "") or "").strip().lower() == "direct" else False
        opensp_msg = ""
        opensp_overwritten_rel: list[str] = []
        if opensp_enabled:
            window._update_mod_manager_progress(progress, progress.maximum(), template=tr("mod_manager.progress.opensp"))
            ok_opensp, opensp_msg, opensp_overwritten_rel = window._mod_manager_apply_opensp_patch(
                clean_root,
                backup_dir=backup_dir,
                existing_created_rel=created_rel,
                existing_overwritten_rel=overwritten_rel,
            )
            window._append_mod_manager_progress_action(progress, tr("mod_manager.progress.opensp_action"), ok=ok_opensp)
            if not ok_opensp:
                _rollback_activation_changes()
                message = tr("mod_manager.err.activate_failed") + ":\n" + opensp_msg
                if rollback_errors:
                    message += "\n\nRollback errors:\n" + "\n".join(rollback_errors[:10])
                window._mod_manager_append_profile_log(profile, message, category="ERROR")
                return False, message

        window._update_mod_manager_progress(progress, progress.maximum(), template=tr("mod_manager.progress.bini"))
        include_rel_for_bini = {str(item).replace("\\", "/") for item in (created_rel + overwritten_rel) if str(item).strip()}
        ok_bini, bini_scanned, bini_converted, bini_err = window._convert_bini_in_folder_in_place(
            str(clean_root),
            include_rel_paths=include_rel_for_bini,
        )
        window._append_mod_manager_progress_action(progress, tr("mod_manager.progress.bini_action"), ok=ok_bini)
        if not ok_bini:
            _rollback_activation_changes()
            message = tr("mod_manager.err.activate_failed") + f":\nBINI conversion failed: {bini_err}"
            if rollback_errors:
                message += "\n\nRollback errors:\n" + "\n".join(rollback_errors[:10])
            window._mod_manager_append_profile_log(profile, message, category="ERROR")
            return False, message

        savegame_risk = window._mod_manager_profile_savegame_risk(profile)
        window._mm_active.append({
            "mod_id": str(profile.get("id", "") or "").strip(),
            "mod_name": str(profile.get("name", "") or "").strip(),
            "mode": str(profile.get("mode", "") or "").strip().lower(),
            "target_root": str(clean_root),
            "backup_dir": str(backup_dir),
            "created_rel": created_rel,
            "overwritten_rel": overwritten_rel,
            "temp_resource_dll_name": temp_resource_dll_name,
            "opensp_enabled": opensp_enabled,
            "opensp_overwritten_rel": opensp_overwritten_rel,
            "log_path": str(window._mod_manager_profile_log_path(profile) or ""),
            "savegame_risk_level": str(savegame_risk.get("level", "safe") or "safe"),
            "savegame_risk_reasons": [str(item) for item in savegame_risk.get("reasons", []) if str(item).strip()],
            "activated_at": datetime.now().isoformat(timespec="seconds"),
        })
        window._mm_editing_mod_id = ""
        window._mod_manager_save_state()
        message = tr("mod_manager.msg.activate_result").format(
            name=str(profile.get("name", "")).strip(),
            copied=copied,
            overwritten=len(overwritten_rel),
            created=len(created_rel),
        )
        message += f"\nBINI scan: {bini_scanned}, converted: {bini_converted}"
        if bini_err:
            message += f"\nBINI warnings: {bini_err}"
        if opensp_enabled:
            message += "\n" + tr("mod_manager.msg.opensp_enabled")
            if opensp_msg:
                message += "\n" + opensp_msg
        ok_saves, saves_msg = (True, "")
        if not had_active_before:
            ok_saves, saves_msg = window._mod_manager_prepare_savegames_for_profile(profile)
        if not ok_saves:
            message += "\n" + tr("mod_manager.saves.error").format(error=saves_msg)
        elif saves_msg:
            message += "\n" + saves_msg
        window._mod_manager_append_profile_log(profile, message, category="ACTIVATE")
        if show_dialog:
            QMessageBox.information(window, tr("mod_manager.title"), message)
        return True, message
    finally:
        progress.setValue(progress.maximum())
        progress.close()


def mod_manager_switch_edit_context(window: Any, profile: dict) -> tuple[bool, str]:
    source = window._mod_manager_profile_source(profile)
    if source is None or not source.exists() or not source.is_dir():
        return False, tr("mod_manager.err.source_not_found")

    mode = str(profile.get("mode", "") or "").strip().lower()
    if mode == "direct":
        window._storage_mode = "single"
        window._single_game_path = str(source)
    else:
        vanilla = str(window._vanilla_game_path or window._mod_manager_clean_root_path() or "").strip()
        if not vanilla or not find_universe_ini(vanilla):
            return False, tr("mod_manager.err.repo_needs_clean")
        window._storage_mode = "overlay"
        window._vanilla_game_path = vanilla
        window._mod_game_path = str(source)
        window._seed_mod_universe_if_missing()

    window._mm_editing_mod_id = str(profile.get("id", "") or "").strip()
    window._mod_manager_save_state()
    window._update_active_mod_indicator()
    window._refresh_ids_toolchain_header_notice()
    window._persist_storage()
    primary = window._primary_game_path()
    window.browser.set_game_path(primary, scan=True)
    window._refresh_game_path_actions(primary)
    window._load_universe(primary)
    return True, tr("mod_manager.msg.edit_context_set")


def mod_manager_clear_edit_context(window: Any) -> tuple[bool, str]:
    if not str(window._mm_editing_mod_id or "").strip():
        return True, ""
    window._mm_editing_mod_id = ""
    window._mod_manager_save_state()
    window._update_active_mod_indicator()
    window._refresh_game_path_actions("")
    window.statusBar().showMessage(tr("mod_manager.msg.edit_context_cleared"))
    return True, tr("mod_manager.msg.edit_context_cleared")
