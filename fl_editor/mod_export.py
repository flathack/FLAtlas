"""Changed-file export helpers for distributable Freelancer mods."""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable


IGNORED_DIR_NAMES = {
    ".git",
    ".flatlas",
    ".flatlaslauncher",
    "__pycache__",
    ".pytest_cache",
}
IGNORED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".sem",
}
IGNORED_FILE_NAMES = {
    "flatlas-change.log",
    "reshade.log",
}
ProgressCallback = Callable[[str, int, int, str], bool | None]


@dataclass(frozen=True)
class ModExportFile:
    source_path: Path
    relative_path: str
    status: str
    size: int
    sha256: str
    reference_sha256: str = ""


@dataclass(frozen=True)
class ModExportPlan:
    mod_root: Path
    reference_root: Path
    files: tuple[ModExportFile, ...]
    unchanged_count: int = 0
    errors: tuple[str, ...] = ()

    @property
    def export_files(self) -> tuple[ModExportFile, ...]:
        return tuple(item for item in self.files if item.status in {"new", "modified"})

    @property
    def new_count(self) -> int:
        return sum(1 for item in self.files if item.status == "new")

    @property
    def modified_count(self) -> int:
        return sum(1 for item in self.files if item.status == "modified")


def normalize_archive_path(path: str | Path) -> str:
    parts = [part for part in str(path).replace("\\", "/").split("/") if part and part != "."]
    return "/".join(parts)


def default_exclusion_labels() -> tuple[str, ...]:
    dirs = tuple(sorted(IGNORED_DIR_NAMES))
    files = tuple(sorted(IGNORED_FILE_NAMES))
    suffixes = tuple(sorted(f"*{suffix}" for suffix in IGNORED_SUFFIXES))
    return dirs + files + suffixes


def filter_export_plan(plan: ModExportPlan, excluded_relative_paths: set[str] | list[str] | tuple[str, ...]) -> ModExportPlan:
    excluded = {
        normalize_archive_path(item).lower()
        for item in excluded_relative_paths
        if str(item or "").strip()
    }
    if not excluded:
        return plan
    return ModExportPlan(
        mod_root=plan.mod_root,
        reference_root=plan.reference_root,
        files=tuple(item for item in plan.files if item.relative_path.lower() not in excluded),
        unchanged_count=plan.unchanged_count,
        errors=plan.errors,
    )


def hash_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _should_ignore(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except Exception:
        rel_parts = path.parts
    lowered_parts = {str(part).lower() for part in rel_parts}
    if lowered_parts & IGNORED_DIR_NAMES:
        return True
    if str(path.name or "").lower() in IGNORED_FILE_NAMES:
        return True
    return str(path.suffix or "").lower() in IGNORED_SUFFIXES


def _iter_files(root: Path) -> list[Path]:
    if not root.exists() or not root.is_dir():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if _should_ignore(path, root):
            continue
        files.append(path)
    return sorted(files, key=lambda item: normalize_archive_path(item.relative_to(root)).lower())


def _reference_map(
    reference_root: Path,
    *,
    progress: ProgressCallback | None = None,
    start_index: int = 0,
    total: int = 0,
) -> dict[str, Path]:
    out: dict[str, Path] = {}
    files = _iter_files(reference_root)
    total_steps = int(total or len(files))
    for idx, path in enumerate(files, start=start_index + 1):
        if progress is not None and progress("reference", idx, total_steps, str(path)) is False:
            break
        try:
            rel = normalize_archive_path(path.relative_to(reference_root)).lower()
        except Exception:
            continue
        if rel and rel not in out:
            out[rel] = path
    return out


def collect_changed_files(
    mod_root: str | Path,
    reference_root: str | Path,
    *,
    progress: ProgressCallback | None = None,
) -> ModExportPlan:
    mod = Path(mod_root)
    reference = Path(reference_root)
    reference_files = _iter_files(reference)
    mod_files = _iter_files(mod)
    total_steps = max(1, len(reference_files) + len(mod_files))
    ref_files: dict[str, Path] = {}
    cancelled = False
    for idx, path in enumerate(reference_files, start=1):
        if progress is not None and progress("reference", idx, total_steps, str(path)) is False:
            cancelled = True
            break
        try:
            rel = normalize_archive_path(path.relative_to(reference)).lower()
        except Exception:
            continue
        if rel and rel not in ref_files:
            ref_files[rel] = path
    changed: list[ModExportFile] = []
    unchanged = 0
    errors: list[str] = []
    if cancelled:
        errors.append("Scan cancelled")
    for offset, source_path in enumerate(mod_files, start=len(reference_files) + 1):
        if cancelled:
            break
        if progress is not None and progress("mod", offset, total_steps, str(source_path)) is False:
            errors.append("Scan cancelled")
            break
        try:
            rel = normalize_archive_path(source_path.relative_to(mod))
            source_hash = hash_file(source_path)
            ref_path = ref_files.get(rel.lower())
            if ref_path is None:
                status = "new"
                ref_hash = ""
            else:
                ref_hash = hash_file(ref_path)
                if source_hash == ref_hash:
                    unchanged += 1
                    continue
                status = "modified"
            changed.append(
                ModExportFile(
                    source_path=source_path,
                    relative_path=rel,
                    status=status,
                    size=int(source_path.stat().st_size),
                    sha256=source_hash,
                    reference_sha256=ref_hash,
                )
            )
        except Exception as exc:
            errors.append(f"{source_path}: {exc}")
    return ModExportPlan(
        mod_root=mod,
        reference_root=reference,
        files=tuple(changed),
        unchanged_count=unchanged,
        errors=tuple(errors),
    )


def default_script_xml(
    *,
    name: str,
    author: str = "",
    description: str = "",
    savesafe: bool = True,
) -> str:
    safe = "true" if savesafe else "false"
    name = _xml_text(name or "FLAtlas Export")
    author = _xml_text(author)
    description = _xml_text(description)
    return (
        "<script>\n"
        f'<header name="{name}" savesafe="{safe}">\n'
        "<scriptversion>\n"
        "2\n"
        "</scriptversion>\n"
        "<author>\n"
        f"{author}\n"
        "</author>\n"
        "<description>\n"
        f"{description}\n"
        "</description>\n"
        "\n"
        "</header>\n"
        "\n"
        "</script>\n"
    )


def _xml_text(value: str) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def export_manifest(plan: ModExportPlan, *, package_format: str) -> dict:
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "format": str(package_format or "").strip().lower(),
        "mod_root": str(plan.mod_root),
        "reference_root": str(plan.reference_root),
        "new_count": plan.new_count,
        "modified_count": plan.modified_count,
        "unchanged_count": plan.unchanged_count,
        "files": [
            {
                "path": item.relative_path,
                "status": item.status,
                "size": item.size,
                "sha256": item.sha256,
                "reference_sha256": item.reference_sha256,
            }
            for item in plan.export_files
        ],
    }


def write_changed_files_zip(
    plan: ModExportPlan,
    target_path: str | Path,
    *,
    include_manifest: bool = True,
    progress: ProgressCallback | None = None,
) -> int:
    return _write_archive(
        plan,
        target_path,
        script_xml=None,
        include_manifest=include_manifest,
        package_format="zip",
        progress=progress,
    )


def write_flmod_package(
    plan: ModExportPlan,
    target_path: str | Path,
    *,
    script_xml: str,
    progress: ProgressCallback | None = None,
) -> int:
    return _write_archive(
        plan,
        target_path,
        script_xml=str(script_xml or ""),
        include_manifest=False,
        package_format="flmod",
        progress=progress,
    )


def _write_archive(
    plan: ModExportPlan,
    target_path: str | Path,
    *,
    script_xml: str | None,
    include_manifest: bool,
    package_format: str,
    progress: ProgressCallback | None,
) -> int:
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    export_files = tuple(plan.export_files)
    total = max(1, len(export_files) + (1 if script_xml is not None else 0) + (1 if include_manifest else 0))
    step = 0
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if script_xml is not None:
            step += 1
            if progress is not None and progress("script", step, total, "script.xml") is False:
                return count
            zf.writestr("script.xml", script_xml)
        for item in export_files:
            arcname = normalize_archive_path(item.relative_path)
            if not arcname:
                continue
            if script_xml is not None and arcname.lower() == "script.xml":
                continue
            step += 1
            if progress is not None and progress("file", step, total, arcname) is False:
                return count
            zf.write(item.source_path, arcname)
            count += 1
        if include_manifest:
            step += 1
            if progress is not None and progress("manifest", step, total, "FLAtlas-export-manifest.json") is False:
                return count
            zf.writestr(
                "FLAtlas-export-manifest.json",
                json.dumps(export_manifest(plan, package_format=package_format), indent=2, ensure_ascii=False),
            )
    return count
