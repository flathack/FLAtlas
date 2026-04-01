"""Persistente Konfiguration mit Legacy-Fallbacks."""

import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "fl_editor" / "config.json"


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
        primary = _load_json_object(CONFIG_PATH)
        merged = dict(primary)
        loaded_from_legacy = False
        for legacy_path in _legacy_config_candidates():
            if legacy_path == CONFIG_PATH:
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

    def save(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(self._d, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def to_dict(self) -> dict:
        return dict(self._d)

    def replace_all(self, data: dict):
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
