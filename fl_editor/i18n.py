"""Internationalisation helper for FL Atlas.

Translations live in a JSON file with top-level keys ``"de"`` and ``"en"``
(or any other language codes).  The *bundled* default file is shipped next to
this module (``translations.json``).  A user-level override is loaded from
``~/.config/fl_editor/translations.json`` when present – this is the file
that users are expected to edit.

Usage::

    from fl_editor.i18n import tr, set_language, get_language

    label.setText(tr("btn.save"))
    status.showMessage(tr("status.universe_loaded").format(count=42))
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Dict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BUNDLED_FILE = Path(__file__).with_name("translations.json")
_USER_DIR = Path.home() / ".config" / "fl_editor"
_USER_FILE = _USER_DIR / "translations.json"

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------
_translations: Dict[str, Dict[str, str]] = {}
_current_lang: str = "de"


def _load_translations() -> None:
    """(Re)load translations from disk.

    The user file takes priority.  If it doesn't exist yet the bundled copy
    is placed there so users can customise it.
    """
    global _translations

    # Ensure user file exists
    if not _USER_FILE.exists():
        _USER_DIR.mkdir(parents=True, exist_ok=True)
        if _BUNDLED_FILE.exists():
            shutil.copy2(_BUNDLED_FILE, _USER_FILE)

    # Load from user file first, fall back to bundled
    src = _USER_FILE if _USER_FILE.exists() else _BUNDLED_FILE
    try:
        with open(src, "r", encoding="utf-8") as fh:
            _translations = json.load(fh)
    except Exception:
        _translations = {}


# Load on import
_load_translations()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tr(key: str) -> str:
    """Return the translated string for *key* in the current language.

    Falls back to German (``"de"``), then to the raw key itself so that
    missing translations are immediately visible during development.
    """
    lang_dict = _translations.get(_current_lang)
    if lang_dict and key in lang_dict:
        return lang_dict[key]
    # Fallback: German
    de_dict = _translations.get("de")
    if de_dict and key in de_dict:
        return de_dict[key]
    return key  # last resort


def set_language(lang: str) -> None:
    """Switch the active language (e.g. ``"de"`` or ``"en"``)."""
    global _current_lang
    _current_lang = lang


def get_language() -> str:
    """Return the active language code."""
    return _current_lang


def available_languages() -> list[str]:
    """Return sorted list of language codes present in the translation file."""
    return sorted(_translations.keys())


def reload_translations() -> None:
    """Force-reload translations from disk (e.g. after external edits)."""
    _load_translations()
