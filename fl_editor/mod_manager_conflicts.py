"""Conflict and overlap helpers for Mod Manager profiles."""

from __future__ import annotations

from pathlib import Path
from typing import Callable


def mod_manager_is_flmm_repo_profile(
    profile: dict | None,
    flmm_install_path: str,
    normalized_path_key: Callable[[Path | str | None], str],
) -> bool:
    if not isinstance(profile, dict):
        return False
    if str(profile.get("mode", "") or "").strip().lower() != "repo":
        return False
    flmm_install = str(flmm_install_path or "").strip()
    if not flmm_install:
        return False
    flmm_mods_key = normalized_path_key(Path(flmm_install) / "mods")
    if not flmm_mods_key:
        return False
    repo_root_txt = str(profile.get("repo_root", "") or "").strip()
    if not repo_root_txt:
        return False
    return normalized_path_key(repo_root_txt) == flmm_mods_key


def mod_manager_profile_target_relpaths(
    profile: dict | None,
    source: Path | None,
    is_flmm_profile: bool,
    collect_source_files: Callable[[Path], list[Path]],
    flmm_collect_script_spec: Callable[[Path], tuple[bool, dict, str]],
) -> set[str]:
    if not isinstance(profile, dict):
        return set()
    if source is None or not source.exists() or not source.is_dir():
        return set()
    if is_flmm_profile:
        ok, spec, _err = flmm_collect_script_spec(source)
        if not ok:
            return set()
        rels: set[str] = set()
        for op in spec.get("operations", []):
            rel = str(op.get("file", "") or "").replace("\\", "/").strip("/")
            if rel:
                rels.add(rel.lower())
            if str(op.get("method", "") or "").strip().lower() == "renamefile":
                new_rel = str(op.get("newfilename", "") or "").replace("\\", "/").strip("/")
                if new_rel:
                    rels.add(new_rel.lower())
        return rels
    out: set[str] = set()
    for src in collect_source_files(source):
        try:
            out.add(src.relative_to(source).as_posix().lower())
        except Exception:
            continue
    return out


def mod_manager_profile_touch_signature(
    profile: dict | None,
    files: set[str],
    is_flmm_profile: bool,
    source: Path | None,
    flmm_collect_script_spec: Callable[[Path], tuple[bool, dict, str]],
    flmm_split_source_sections: Callable[[str], list[str]],
    flmm_parse_section_identity: Callable[[str], str],
    flmm_source_key_names: Callable[[str], set[str]],
) -> dict[str, set[str]]:
    hard: set[str] = set()
    soft: set[str] = set()
    if not isinstance(profile, dict):
        return {"files": files, "hard": hard, "soft": soft}
    if not is_flmm_profile:
        hard = {f"file:{rel}" for rel in files}
        return {"files": files, "hard": hard, "soft": soft}
    if source is None or not source.exists() or not source.is_dir():
        return {"files": files, "hard": hard, "soft": soft}
    ok, spec, _err = flmm_collect_script_spec(source)
    if not ok:
        hard = {f"file:{rel}" for rel in files}
        return {"files": files, "hard": hard, "soft": soft}
    for op in spec.get("operations", []):
        method = str(op.get("method", "") or "").strip().lower()
        rel = str(op.get("file", "") or "").replace("\\", "/").strip("/").lower()
        if not rel:
            continue
        if method in {"filereplace", "renamefile"}:
            hard.add(f"file:{rel}")
            continue
        if method == "append":
            appended_blocks = flmm_split_source_sections(str((op.get("sources", []) or [""])[0] or ""))
            if appended_blocks:
                for block in appended_blocks:
                    ident = flmm_parse_section_identity(block)
                    if ident:
                        soft.add(f"section:{rel}:{ident}")
                    else:
                        soft.add(f"file:{rel}")
            else:
                hard.add(f"file:{rel}")
            continue
        section_idents = [
            ident
            for ident in (flmm_parse_section_identity(sec) for sec in op.get("sections", []) or [])
            if ident
        ]
        if method == "sectionappend":
            source_keys = flmm_source_key_names(str((op.get("sources", []) or [""])[0] or ""))
            if section_idents and source_keys:
                for ident in section_idents:
                    for key in source_keys:
                        soft.add(f"key:{rel}:{ident}:{key}")
            elif section_idents:
                for ident in section_idents:
                    soft.add(f"section:{rel}:{ident}")
            else:
                hard.add(f"file:{rel}")
            continue
        if method == "sectionreplace":
            dest_keys: set[str] = set()
            for dest in op.get("dests", []) or []:
                dest_keys |= flmm_source_key_names(str(dest or ""))
            if section_idents and dest_keys:
                for ident in section_idents:
                    for key in dest_keys:
                        hard.add(f"key:{rel}:{ident}:{key}")
            elif section_idents:
                for ident in section_idents:
                    hard.add(f"section:{rel}:{ident}")
            else:
                hard.add(f"file:{rel}")
            continue
        hard.add(f"file:{rel}")
    return {"files": files, "hard": hard, "soft": soft}


def mod_manager_conflicting_active_ids(
    hard_ids: set[str],
) -> set[str]:
    return set(hard_ids)


def mod_manager_conflict_details(
    hard_details: dict[str, set[str]],
) -> dict[str, set[str]]:
    return {key: set(values) for key, values in hard_details.items()}


def mod_manager_partial_conflict_details(
    partial_details: dict[str, set[str]],
) -> dict[str, set[str]]:
    return {key: set(values) for key, values in partial_details.items()}


def mod_manager_conflict_analysis(
    profile: dict | None,
    active_entries: list[object],
    profile_by_id: Callable[[str], dict | None],
    profile_touch_signature: Callable[[dict | None], dict[str, set[str]]],
    is_flmm_profile: Callable[[dict | None], bool],
) -> tuple[set[str], dict[str, set[str]], dict[str, set[str]]]:
    if not isinstance(profile, dict):
        return set(), {}, {}
    pid = str(profile.get("id", "") or "").strip()
    mode = str(profile.get("mode", "") or "").strip().lower()
    if mode == "direct":
        return set(), {}, {}

    sig = profile_touch_signature(profile)
    rels = set(sig.get("files", set()) or set())
    hard = set(sig.get("hard", set()) or set())
    soft = set(sig.get("soft", set()) or set())
    if not rels:
        return set(), {}, {}

    hard_ids: set[str] = set()
    hard_details: dict[str, set[str]] = {}
    partial_details: dict[str, set[str]] = {}
    profile_is_flmm = is_flmm_profile(profile)

    for entry in active_entries:
        if not isinstance(entry, dict):
            continue
        other_id = str(entry.get("mod_id", "") or "").strip()
        if not other_id or other_id == pid:
            continue
        other_profile = profile_by_id(other_id)
        other_sig = profile_touch_signature(other_profile)
        other_rels = set(other_sig.get("files", set()) or set())
        other_hard = set(other_sig.get("hard", set()) or set())
        other_soft = set(other_sig.get("soft", set()) or set())
        overlap = rels & other_rels
        if not overlap:
            continue
        is_hard = (hard & other_hard) or (hard & other_soft) or (soft & other_hard)
        if is_hard:
            hard_ids.add(other_id)
            hard_details[other_id] = set(sorted(overlap))
            continue
        is_soft = (soft & other_soft) or (profile_is_flmm and is_flmm_profile(other_profile))
        if is_soft:
            partial_details[other_id] = set(sorted(overlap))
    return hard_ids, hard_details, partial_details
