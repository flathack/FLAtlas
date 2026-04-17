from __future__ import annotations

import importlib
import json
from pathlib import Path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_i18n_legacy_full_copy_keeps_bundled_tab_names(monkeypatch, tmp_path: Path):
    bundled = tmp_path / "bundled.json"
    user = tmp_path / "user.json"

    bundled_payload = {
        "en": {
            "action.ini_editor": "File Explorer",
            "action.name_editor": "Name & Info Editor",
            **{f"misc.key_{idx}": f"Bundled {idx}" for idx in range(24)},
        }
    }
    user_payload = {
        "en": {
            "action.ini_editor": "INI Editor",
            "action.name_editor": "Name Editor",
            **{f"misc.key_{idx}": f"Old {idx}" for idx in range(24)},
            "misc.key_3": "Custom legacy text",
        }
    }
    _write_json(bundled, bundled_payload)
    _write_json(user, user_payload)

    import fl_editor.i18n as i18n_module

    monkeypatch.setattr(i18n_module, "_BUNDLED_FILE", bundled)
    monkeypatch.setattr(i18n_module, "_USER_FILE", user)
    monkeypatch.setattr(i18n_module, "_USER_DIR", user.parent)

    i18n_module = importlib.reload(i18n_module)
    monkeypatch.setattr(i18n_module, "_BUNDLED_FILE", bundled)
    monkeypatch.setattr(i18n_module, "_USER_FILE", user)
    monkeypatch.setattr(i18n_module, "_USER_DIR", user.parent)
    i18n_module.reload_translations()
    i18n_module.set_language("en")

    assert i18n_module.tr("action.ini_editor") == "File Explorer"
    assert i18n_module.tr("action.name_editor") == "Name & Info Editor"
    assert i18n_module.tr("misc.key_3") == "Custom legacy text"


def test_i18n_sparse_user_override_can_still_override_tab_names(monkeypatch, tmp_path: Path):
    bundled = tmp_path / "bundled.json"
    user = tmp_path / "user.json"

    _write_json(
        bundled,
        {
            "en": {
                "action.ini_editor": "File Explorer",
                **{f"misc.key_{idx}": f"Bundled {idx}" for idx in range(24)},
            }
        },
    )
    _write_json(user, {"en": {"action.ini_editor": "Custom Explorer"}})

    import fl_editor.i18n as i18n_module

    monkeypatch.setattr(i18n_module, "_BUNDLED_FILE", bundled)
    monkeypatch.setattr(i18n_module, "_USER_FILE", user)
    monkeypatch.setattr(i18n_module, "_USER_DIR", user.parent)

    i18n_module = importlib.reload(i18n_module)
    monkeypatch.setattr(i18n_module, "_BUNDLED_FILE", bundled)
    monkeypatch.setattr(i18n_module, "_USER_FILE", user)
    monkeypatch.setattr(i18n_module, "_USER_DIR", user.parent)
    i18n_module.reload_translations()
    i18n_module.set_language("en")

    assert i18n_module.tr("action.ini_editor") == "Custom Explorer"


def test_i18n_large_legacy_partial_copy_still_prefers_bundled_tab_names(monkeypatch, tmp_path: Path):
    bundled = tmp_path / "bundled.json"
    user = tmp_path / "user.json"

    bundled_keys = {
        "action.ini_editor": "File Explorer",
        "action.name_editor": "Name & Info Editor",
        **{f"misc.key_{idx}": f"Bundled {idx}" for idx in range(100)},
    }
    user_keys = {f"misc.key_{idx}": f"Legacy {idx}" for idx in range(74)}
    user_keys["action.ini_editor"] = "INI Editor"

    _write_json(bundled, {"en": bundled_keys})
    _write_json(user, {"en": user_keys})

    import fl_editor.i18n as i18n_module

    monkeypatch.setattr(i18n_module, "_BUNDLED_FILE", bundled)
    monkeypatch.setattr(i18n_module, "_USER_FILE", user)
    monkeypatch.setattr(i18n_module, "_USER_DIR", user.parent)

    i18n_module = importlib.reload(i18n_module)
    monkeypatch.setattr(i18n_module, "_BUNDLED_FILE", bundled)
    monkeypatch.setattr(i18n_module, "_USER_FILE", user)
    monkeypatch.setattr(i18n_module, "_USER_DIR", user.parent)
    i18n_module.reload_translations()
    i18n_module.set_language("en")

    assert i18n_module.tr("action.ini_editor") == "File Explorer"
    assert i18n_module.tr("misc.key_10") == "Legacy 10"
