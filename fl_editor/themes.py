"""Theme engine for FL Atlas.

Provides four built-in themes (Founder, Dark, Light, Custom) and generates
the full Qt stylesheet from a small palette dictionary.  The active theme
is persisted via :mod:`fl_editor.config`.

Usage::

    from fl_editor.themes import get_stylesheet, THEME_NAMES, apply_theme

    apply_theme(main_window, "founder")
"""

from __future__ import annotations

from typing import Dict

from fl_editor.config import Config

_cfg = Config()

# ── palette keys ──────────────────────────────────────────────────────
#   bg           – main background
#   bg_alt       – alternate row / secondary bg
#   bg_input     – text edit / line edit bg
#   bg_list      – list widget bg
#   bg_toolbar   – toolbar / status bar bg
#   fg           – primary text colour
#   fg_dim       – disabled / secondary text
#   fg_accent    – group-box titles, status-bar text
#   border       – general border
#   border_light – button border, darker border
#   btn_bg       – button background
#   btn_hover    – button hover
#   sel_bg       – list selection / menu highlight
#   splitter     – splitter handle
#   cb_checked   – checkbox checked indicator
#   menu_bg      – context menu bg
#   scrollbar_bg – scrollbar track
#   scrollbar_fg – scrollbar handle

PALETTES: Dict[str, Dict[str, str]] = {
    "founder": {
        "bg":           "#12122a",
        "bg_alt":       "#0d0d25",
        "bg_input":     "#0d0d22",
        "bg_list":      "#0a0a1e",
        "bg_toolbar":   "#0e0e28",
        "bg_textedit":  "#08080f",
        "fg":           "#dde",
        "fg_dim":       "#445",
        "fg_accent":    "#99aaff",
        "border":       "#334",
        "border_light": "#446",
        "btn_bg":       "#1e1e50",
        "btn_hover":    "#2a2a70",
        "sel_bg":       "#2a3070",
        "list_hover":   "#1e2050",
        "splitter":     "#224",
        "cb_checked":   "#5060c0",
        "menu_bg":      "#16163a",
        "scrollbar_bg": "#0a0a1e",
        "scrollbar_fg": "#334",
    },
    "dark": {
        "bg":           "#1e1e1e",
        "bg_alt":       "#252525",
        "bg_input":     "#2a2a2a",
        "bg_list":      "#1a1a1a",
        "bg_toolbar":   "#252525",
        "bg_textedit":  "#1a1a1a",
        "fg":           "#d4d4d4",
        "fg_dim":       "#555",
        "fg_accent":    "#9cdcfe",
        "border":       "#3c3c3c",
        "border_light": "#505050",
        "btn_bg":       "#333",
        "btn_hover":    "#444",
        "sel_bg":       "#264f78",
        "list_hover":   "#2a2d2e",
        "splitter":     "#3c3c3c",
        "cb_checked":   "#569cd6",
        "menu_bg":      "#252526",
        "scrollbar_bg": "#1e1e1e",
        "scrollbar_fg": "#424242",
    },
    "light": {
        "bg":           "#f5f5f5",
        "bg_alt":       "#ebebeb",
        "bg_input":     "#ffffff",
        "bg_list":      "#ffffff",
        "bg_toolbar":   "#e8e8e8",
        "bg_textedit":  "#ffffff",
        "fg":           "#1e1e1e",
        "fg_dim":       "#a0a0a0",
        "fg_accent":    "#0055a4",
        "border":       "#c8c8c8",
        "border_light": "#b0b0b0",
        "btn_bg":       "#e0e0e0",
        "btn_hover":    "#d0d0d0",
        "sel_bg":       "#0078d4",
        "list_hover":   "#e8e8e8",
        "splitter":     "#c8c8c8",
        "cb_checked":   "#0078d4",
        "menu_bg":      "#f0f0f0",
        "scrollbar_bg": "#f5f5f5",
        "scrollbar_fg": "#c0c0c0",
    },
}


# ── helpers ───────────────────────────────────────────────────────────

def _hsl_shift(hex_color: str, lightness_delta: int) -> str:
    """Shift lightness of a hex colour by *lightness_delta* (−100…+100)."""
    c = hex_color.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    # Simple approach: shift each channel towards 0 or 255
    factor = lightness_delta / 100
    if factor > 0:
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
    else:
        r = int(r * (1 + factor))
        g = int(g * (1 + factor))
        b = int(b * (1 + factor))
    r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def palette_from_accent(accent: str) -> Dict[str, str]:
    """Derive a full dark palette from a single accent colour."""
    return {
        "bg":           _hsl_shift(accent, -80),
        "bg_alt":       _hsl_shift(accent, -75),
        "bg_input":     _hsl_shift(accent, -82),
        "bg_list":      _hsl_shift(accent, -85),
        "bg_toolbar":   _hsl_shift(accent, -78),
        "bg_textedit":  _hsl_shift(accent, -90),
        "fg":           "#dde",
        "fg_dim":       "#556",
        "fg_accent":    _hsl_shift(accent, 30),
        "border":       _hsl_shift(accent, -50),
        "border_light": _hsl_shift(accent, -40),
        "btn_bg":       _hsl_shift(accent, -40),
        "btn_hover":    _hsl_shift(accent, -20),
        "sel_bg":       _hsl_shift(accent, -25),
        "list_hover":   _hsl_shift(accent, -45),
        "splitter":     _hsl_shift(accent, -55),
        "cb_checked":   accent,
        "menu_bg":      _hsl_shift(accent, -70),
        "scrollbar_bg": _hsl_shift(accent, -85),
        "scrollbar_fg": _hsl_shift(accent, -50),
    }


def get_stylesheet(palette: Dict[str, str]) -> str:
    """Generate a complete Qt stylesheet from a palette dict."""
    p = palette
    return f"""
    * {{ background:{p['bg']}; color:{p['fg']}; }}
    QGroupBox {{ border:1px solid {p['border']}; margin-top:10px;
                padding:5px; border-radius:4px; }}
    QGroupBox::title {{ color:{p['fg_accent']}; }}
    QPushButton {{ background:{p['btn_bg']}; border:1px solid {p['border_light']};
                  padding:4px 8px; border-radius:3px; }}
    QPushButton:hover    {{ background:{p['btn_hover']}; }}
    QPushButton:disabled {{ color:{p['fg_dim']}; }}
    QTextEdit  {{ background:{p['bg_textedit']}; border:1px solid {p['border']}; }}
    QLineEdit  {{ background:{p['bg_input']}; border:1px solid {p['border_light']};
                 padding:3px; border-radius:2px; }}
    QListWidget {{ background:{p['bg_list']}; border:1px solid {p['border']};
                  alternate-background-color:{p['bg_alt']}; }}
    QListWidget::item:hover    {{ background:{p['list_hover']}; }}
    QListWidget::item:selected {{ background:{p['sel_bg']}; color:#fff; }}
    QToolBar   {{ background:{p['bg_toolbar']}; border-bottom:1px solid {p['border']};
                 spacing:4px; padding:2px; }}
    QStatusBar {{ background:{p['bg_toolbar']}; color:{p['fg_accent']}; }}
    QSplitter::handle {{ background:{p['splitter']}; width:3px; }}
    QCheckBox  {{ color:{p['fg']}; spacing:5px; }}
    QCheckBox::indicator {{ width:14px; height:14px;
                           border:1px solid {p['border_light']}; border-radius:2px;
                           background:{p['btn_bg']}; }}
    QCheckBox::indicator:checked {{ background:{p['cb_checked']}; }}
    QScrollBar:vertical   {{ background:{p['scrollbar_bg']}; width:10px; }}
    QScrollBar::handle:vertical {{ background:{p['scrollbar_fg']}; border-radius:4px; }}
    QMenu {{ background:{p['menu_bg']}; color:{p['fg']}; border:1px solid {p['border_light']}; }}
    QMenu::item {{ padding:6px 24px; }}
    QMenu::item:selected {{ background:{p['btn_hover']}; }}
    """


# ── theme names (for UI display; order matters) ──────────────────────
THEME_NAMES = ["founder", "dark", "light", "custom"]


def get_palette(theme_name: str) -> Dict[str, str]:
    """Return the palette for *theme_name*.

    For ``"custom"`` the accent colour is read from the config file.
    Falls back to Founder if unknown.
    """
    if theme_name == "custom":
        accent = _cfg.get("custom_accent", "#5060c0")
        return palette_from_accent(accent)
    return PALETTES.get(theme_name, PALETTES["founder"])


def current_theme() -> str:
    """Return the persisted theme name (default ``"founder"``)."""
    return _cfg.get("theme", "founder")


def set_theme(name: str) -> None:
    """Persist the chosen theme name."""
    _cfg.set("theme", name)


def apply_theme(widget, theme_name: str | None = None) -> None:
    """Apply *theme_name* (or the persisted theme) to *widget*."""
    if theme_name is None:
        theme_name = current_theme()
    palette = get_palette(theme_name)
    widget.setStyleSheet(get_stylesheet(palette))
    set_theme(theme_name)
