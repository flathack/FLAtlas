"""Persistente Konfiguration (~/.config/fl_editor/config.json)."""

import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "fl_editor" / "config.json"


class Config:
    """Einfaches JSON-basiertes Key-Value-Konfigurationsobjekt."""

    def __init__(self):
        self._d: dict = {}
        if CONFIG_PATH.exists():
            try:
                self._d = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass

    def get(self, key: str, default=None):
        return self._d.get(key, default)

    def set(self, key: str, value):
        self._d[key] = value
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(self._d, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
