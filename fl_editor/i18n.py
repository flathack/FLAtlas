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
_current_lang: str = "en"
_BUNDLED_PRIORITY_KEYS = {
    "mod_manager.title",
    "mod_settings.title",
}
_BUNDLED_PRIORITY_PREFIXES = (
    "action.",
    "app.title",
)


def _is_bundled_priority_key(key: str) -> bool:
    normalized = str(key or "").strip()
    return normalized in _BUNDLED_PRIORITY_KEYS or normalized.startswith(_BUNDLED_PRIORITY_PREFIXES)


def _looks_like_legacy_full_copy(base_lang: Dict[str, str], user_lang: Dict[str, str]) -> bool:
    if not isinstance(base_lang, dict) or not isinstance(user_lang, dict):
        return False
    base_count = len(base_lang)
    user_count = len(user_lang)
    if base_count < 20:
        return False
    return user_count >= max(20, int(base_count * 0.7))


def _load_translations() -> None:
    """(Re)load translations from disk.

    The user file takes priority. Legacy installs may still carry a full copy
    of an old bundled translation file in the user location; for a small set
    of core navigation captions we prefer the bundled values in that case so
    renamed tabs stay in sync after updates.
    """
    global _translations

    if not _USER_FILE.exists():
        _USER_DIR.mkdir(parents=True, exist_ok=True)

    bundled_data: Dict[str, Dict[str, str]] = {}
    user_data: Dict[str, Dict[str, str]] = {}

    if _BUNDLED_FILE.exists():
        try:
            with open(_BUNDLED_FILE, "r", encoding="utf-8") as fh:
                bundled_data = json.load(fh)
        except Exception:
            bundled_data = {}

    if _USER_FILE.exists():
        try:
            with open(_USER_FILE, "r", encoding="utf-8") as fh:
                user_data = json.load(fh)
        except Exception:
            user_data = {}

    merged: Dict[str, Dict[str, str]] = {}
    for lang in set(bundled_data.keys()) | set(user_data.keys()):
        base_lang = bundled_data.get(lang, {})
        user_lang = user_data.get(lang, {})
        merged_lang = dict(base_lang)
        legacy_full_copy = _looks_like_legacy_full_copy(base_lang, user_lang)
        for key, value in user_lang.items():
            if legacy_full_copy and key in base_lang and _is_bundled_priority_key(key):
                continue
            merged_lang[key] = value
        merged[lang] = merged_lang
    _translations = merged


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
