"""Persistente Konfiguration mit Legacy-Fallbacks und Backup-Schutz."""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "fl_editor" / "config.json"
CONFIG_LOCATION_FILENAME = "config-location.json"
CONFIG_BACKUP_DIRNAME = "backups"
CONFIG_BACKUP_KEEP = 30


def _location_pointer_path() -> Path:
    return CONFIG_PATH.parent / CONFIG_LOCATION_FILENAME


def _normalize_config_path(path: str | Path) -> Path:
    p = Path(path).expanduser()
    if p.suffix.lower() != ".json":
        p = p / "config.json"
    return p


def _configured_config_path() -> Path:
    pointer = _location_pointer_path()
    if not pointer.exists():
        return CONFIG_PATH
    try:
        data = json.loads(pointer.read_text(encoding="utf-8"))
    except Exception:
        return CONFIG_PATH
    if not isinstance(data, dict):
        return CONFIG_PATH
    configured = str(data.get("config_path", "") or "").strip()
    if not configured:
        return CONFIG_PATH
    return _normalize_config_path(configured)


def _write_location_pointer(path: Path) -> None:
    pointer = _location_pointer_path()
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(
        json.dumps({"config_path": str(path)}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _legacy_config_candidates() -> list[Path]:
    candidates: list[Path] = []
    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        candidates.append(Path(appdata) / "fl_editor" / "config.json")
    candidates.append(Path.home() / "AppData" / "Roaming" / "fl_editor" / "config.json")
    return candidates


def _load_json_object(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


class Config:
    """Einfaches JSON-basiertes Key-Value-Konfigurationsobjekt."""

    def __init__(self):
        self._d: dict = {}
        self.path: Path = _configured_config_path()
        self._auto_backup_done_paths: set[Path] = set()
        primary = _load_json_object(self.path)
        merged = dict(primary)
        loaded_from_legacy = False
        for legacy_path in [CONFIG_PATH, *_legacy_config_candidates()]:
            if legacy_path == CONFIG_PATH:
                if self.path == CONFIG_PATH:
                    continue
            if legacy_path == self.path:
                continue
            legacy = _load_json_object(legacy_path)
            if not legacy:
                continue
            for key, value in legacy.items():
                if key not in merged:
                    merged[key] = value
                    loaded_from_legacy = True
        self._d = merged
        if loaded_from_legacy:
            try:
                self.save()
            except Exception:
                pass

    def get(self, key: str, default=None):
        return self._d.get(key, default)

    def set(self, key: str, value):
        self._d[key] = value
        self.save()

    def backup_dir(self) -> Path:
        return self.path.parent / CONFIG_BACKUP_DIRNAME

    def create_backup(self, reason: str = "manual") -> Path | None:
        if not self.path.exists():
            return None
        backup_dir = self.backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)
        safe_reason = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in str(reason or "manual"))
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = backup_dir / f"config-{stamp}-{safe_reason}.json"
        shutil.copy2(self.path, backup)
        self._prune_backups()
        return backup

    def _prune_backups(self) -> None:
        try:
            backups = sorted(
                self.backup_dir().glob("config-*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except Exception:
            return
        for old in backups[CONFIG_BACKUP_KEEP:]:
            try:
                old.unlink()
            except Exception:
                pass

    def save(self):
        payload = json.dumps(self._d, indent=2, ensure_ascii=False)
        if self.path.exists() and self.path not in self._auto_backup_done_paths:
            try:
                if self.path.read_text(encoding="utf-8") != payload:
                    self.create_backup("save")
                    self._auto_backup_done_paths.add(self.path)
            except Exception:
                self.create_backup("save")
                self._auto_backup_done_paths.add(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            payload,
            encoding="utf-8",
        )

    def to_dict(self) -> dict:
        return dict(self._d)

    def replace_all(self, data: dict):
        self.create_backup("replace")
        self._auto_backup_done_paths.add(self.path)
        self._d = dict(data or {})
        self.save()

    def export_to_file(self, target_path: str | Path):
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self._d, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def import_from_file(self, source_path: str | Path):
        source = Path(source_path)
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Config file must contain a JSON object")
        self.replace_all(data)

    def move_to(self, target_path: str | Path) -> Path:
        target = _normalize_config_path(target_path)
        if target == self.path:
            self.save()
            return self.path
        if target.exists():
            data = json.loads(target.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Target config file must contain a JSON object")
        self.create_backup("move")
        old_path = self.path
        self.path = target
        if self.path.exists():
            self.create_backup("move-target")
        self._auto_backup_done_paths.add(target)
        self.save()
        _write_location_pointer(target)
        if old_path == CONFIG_PATH and old_path.exists() and old_path != target:
            self.export_to_file(old_path)
        return self.path
