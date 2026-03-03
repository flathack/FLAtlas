"""Theme engine for FL Atlas.

Provides built-in themes (Founder, Dark, Light, XP, Custom) and generates
the full Qt stylesheet from a small palette dictionary.  The active theme
is persisted via :mod:`fl_editor.config`.

Usage::

    from fl_editor.themes import get_stylesheet, THEME_NAMES, apply_theme

    apply_theme(main_window, "founder")
"""

from __future__ import annotations

from typing import Dict

from fl_editor.config import Config
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

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
        "bg":           "#171a1f",
        "bg_alt":       "#1d2229",
        "bg_input":     "#11151b",
        "bg_list":      "#11151b",
        "bg_toolbar":   "#1b2027",
        "bg_textedit":  "#0f1318",
        "fg":           "#e4e9f0",
        "fg_dim":       "#7e8897",
        "fg_accent":    "#7dc4ff",
        "border":       "#2c333d",
        "border_light": "#3a4451",
        "btn_bg":       "#232a33",
        "btn_hover":    "#2d3743",
        "sel_bg":       "#255d90",
        "list_hover":   "#242b35",
        "splitter":     "#2a313b",
        "cb_checked":   "#4ea3ea",
        "menu_bg":      "#1b2027",
        "scrollbar_bg": "#12161c",
        "scrollbar_fg": "#3a4552",
    },
    "light": {
        "bg":           "#f6f8fb",
        "bg_alt":       "#edf1f6",
        "bg_input":     "#ffffff",
        "bg_list":      "#ffffff",
        "bg_toolbar":   "#e9edf3",
        "bg_textedit":  "#ffffff",
        "fg":           "#1f2937",
        "fg_dim":       "#6b7280",
        "fg_accent":    "#0d4f94",
        "border":       "#cfd7e3",
        "border_light": "#b9c5d6",
        "btn_bg":       "#f3f6fb",
        "btn_hover":    "#e8edf5",
        "sel_bg":       "#2f7dd1",
        "list_hover":   "#eef3fa",
        "splitter":     "#d4dbe6",
        "cb_checked":   "#2f7dd1",
        "menu_bg":      "#f4f7fc",
        "scrollbar_bg": "#edf2f8",
        "scrollbar_fg": "#c4cedd",
    },
    "xp": {
        # Windows XP "Luna" inspired bright-blue theme
        "variant":      "xp",
        "bg":           "#dbeafc",
        "bg_alt":       "#eaf2fd",
        "bg_input":     "#ffffff",
        "bg_list":      "#ffffff",
        "bg_toolbar":   "#c9ddf7",
        "bg_textedit":  "#ffffff",
        "fg":           "#001a52",
        "fg_dim":       "#4b628a",
        "fg_accent":    "#003c9d",
        "border":       "#7f9db9",
        "border_light": "#96b3d5",
        "btn_bg":       "#e7f0fc",
        "btn_hover":    "#d7e9ff",
        "sel_bg":       "#316ac5",
        "list_hover":   "#edf5ff",
        "splitter":     "#9fbbe0",
        "cb_checked":   "#316ac5",
        "menu_bg":      "#f2f7ff",
        "scrollbar_bg": "#d6e6fb",
        "scrollbar_fg": "#9fb7d8",
    },
}


# ── helpers ───────────────────────────────────────────────────────────

def _normalize_hex_rgb(hex_color: str) -> str:
    c = hex_color.lstrip("#")
    if len(c) == 8:
        # Accept #AARRGGBB and ignore alpha for palette generation.
        c = c[2:]
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return "#5060c0"
    return f"#{c.lower()}"


def _hsl_shift(hex_color: str, lightness_delta: int) -> str:
    """Shift lightness of a hex colour by *lightness_delta* (−100…+100)."""
    c = _normalize_hex_rgb(hex_color).lstrip("#")
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
    accent_rgb = _normalize_hex_rgb(accent)
    return {
        "bg":           _hsl_shift(accent_rgb, -80),
        "bg_alt":       _hsl_shift(accent_rgb, -75),
        "bg_input":     _hsl_shift(accent_rgb, -82),
        "bg_list":      _hsl_shift(accent_rgb, -85),
        "bg_toolbar":   _hsl_shift(accent_rgb, -78),
        "bg_textedit":  _hsl_shift(accent_rgb, -90),
        "fg":           "#dde",
        "fg_dim":       "#556",
        "fg_accent":    _hsl_shift(accent_rgb, 30),
        "border":       _hsl_shift(accent_rgb, -50),
        "border_light": _hsl_shift(accent_rgb, -40),
        "btn_bg":       _hsl_shift(accent_rgb, -40),
        "btn_hover":    _hsl_shift(accent_rgb, -20),
        "sel_bg":       _hsl_shift(accent_rgb, -25),
        "list_hover":   _hsl_shift(accent_rgb, -45),
        "splitter":     _hsl_shift(accent_rgb, -55),
        "cb_checked":   accent_rgb,
        "menu_bg":      _hsl_shift(accent_rgb, -70),
        "scrollbar_bg": _hsl_shift(accent_rgb, -85),
        "scrollbar_fg": _hsl_shift(accent_rgb, -50),
    }


def get_stylesheet(palette: Dict[str, str]) -> str:
    """Generate a complete Qt stylesheet from a palette dict."""
    p = palette
    base = f"""
    QWidget {{ color:{p['fg']}; font-family: Tahoma, "MS Sans Serif", "Segoe UI", sans-serif; }}
    QMainWindow, QDialog, QWidget#centralWidget {{ background:{p['bg']}; }}
    QFrame, QStackedWidget, QDockWidget {{ background:{p['bg']}; }}
    QGroupBox {{ border:1px solid {p['border']}; margin-top:10px; padding:5px;
                 border-radius:4px; background:{p['bg_alt']}; }}
    QGroupBox::title {{ color:{p['fg_accent']}; }}
    QPushButton {{ background:{p['btn_bg']}; border:1px solid {p['border_light']};
                  padding:4px 8px; border-radius:3px; color:{p['fg']}; }}
    QPushButton:hover    {{ background:{p['btn_hover']}; }}
    QPushButton:disabled {{ color:{p['fg_dim']}; }}
    QTextEdit, QPlainTextEdit {{ background:{p['bg_textedit']}; color:{p['fg']};
                                border:1px solid {p['border']}; selection-background-color:{p['sel_bg']}; }}
    QLineEdit  {{ background:{p['bg_input']}; border:1px solid {p['border_light']};
                 padding:3px; border-radius:2px; color:{p['fg']}; selection-background-color:{p['sel_bg']}; }}
    QComboBox, QSpinBox, QDoubleSpinBox {{ background:{p['bg_input']}; color:{p['fg']};
                                          border:1px solid {p['border_light']}; padding:3px; border-radius:2px; }}
    QComboBox QAbstractItemView, QMenu, QListView {{
        background:{p['menu_bg']}; color:{p['fg']}; border:1px solid {p['border_light']};
        selection-background-color:{p['sel_bg']};
    }}
    QListWidget, QTreeWidget, QTableWidget {{
        background:{p['bg_list']}; color:{p['fg']}; border:1px solid {p['border']};
        alternate-background-color:{p['bg_alt']}; gridline-color:{p['border']};
        selection-background-color:{p['sel_bg']};
    }}
    QListWidget::item:hover, QTreeWidget::item:hover, QTableWidget::item:hover {{ background:{p['list_hover']}; }}
    QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {{ background:{p['sel_bg']}; color:#ffffff; }}
    QHeaderView::section {{ background:{p['bg_toolbar']}; color:{p['fg']}; border:1px solid {p['border']}; padding:4px; }}
    QTabWidget::pane {{ border:1px solid {p['border']}; background:{p['bg']}; }}
    QTabBar::tab {{ background:{p['btn_bg']}; color:{p['fg']}; border:1px solid {p['border_light']};
                    padding:5px 10px; margin-right:2px; }}
    QTabBar::tab:selected {{ background:{p['bg']}; border-bottom-color:{p['bg']}; }}
    QTabBar::tab:hover {{ background:{p['btn_hover']}; }}
    QToolBar   {{ background:{p['bg_toolbar']}; border-bottom:1px solid {p['border']};
                 spacing:4px; padding:2px; }}
    QStatusBar {{ background:{p['bg_toolbar']}; color:{p['fg_accent']}; }}
    QStatusBar QLabel {{ color:{p['fg']}; }}
    QSplitter::handle {{ background:{p['splitter']}; width:3px; }}
    QCheckBox  {{ color:{p['fg']}; spacing:5px; }}
    QCheckBox::indicator {{ width:14px; height:14px;
                           border:1px solid {p['border_light']}; border-radius:2px;
                           background:{p['btn_bg']}; }}
    QCheckBox::indicator:checked {{ background:{p['cb_checked']}; }}
    QScrollBar:vertical   {{ background:{p['scrollbar_bg']}; width:10px; border:none; }}
    QScrollBar::handle:vertical {{ background:{p['scrollbar_fg']}; border-radius:4px; }}
    QMenu {{ background:{p['menu_bg']}; color:{p['fg']}; border:1px solid {p['border_light']}; }}
    QMenu::item {{ padding:6px 24px; }}
    QMenu::item:selected {{ background:{p['btn_hover']}; }}
    """
    if p.get("variant") == "xp":
        base += f"""
    QMenuBar {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f7fbff, stop:1 #d6e7fb);
        border-bottom: 1px solid #7f9db9;
    }}
    QToolBar {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #edf5ff, stop:1 #c6dbf7);
        border-bottom: 1px solid #7f9db9;
    }}
    QPushButton {{
        border: 1px solid #6f8fb5;
        border-radius: 2px;
        padding: 4px 10px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #d9e9fb);
        color: #001a52;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #cfe3fb);
    }}
    QPushButton:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #c4dbf8, stop:1 #eaf2fd);
    }}
    QTabBar::tab {{
        border: 1px solid #7f9db9;
        border-bottom: none;
        border-top-left-radius: 3px;
        border-top-right-radius: 3px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8fcff, stop:1 #dceafd);
        color: #00225f;
    }}
    QTabBar::tab:selected {{
        background: #ffffff;
        color: #003c9d;
    }}
    QHeaderView::section {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8fcff, stop:1 #d7e8fd);
        color: #002a72;
        border: 1px solid #9ab3d4;
    }}
    """
    return base


# ── theme names (for UI display; order matters) ──────────────────────
THEME_NAMES = ["founder", "dark", "light", "xp", "custom"]


def get_palette(theme_name: str) -> Dict[str, str]:
    """Return the palette for *theme_name*.

    For ``"custom"`` the accent colour is read from the config file.
    Falls back to Founder if unknown.
    """
    if theme_name == "custom":
        accent = Config().get("custom_accent", "#5060c0")
        return palette_from_accent(accent)
    # Backward compatibility for saved "modern" configs.
    if theme_name == "modern":
        theme_name = "xp"
    return PALETTES.get(theme_name, PALETTES["founder"])


def current_theme() -> str:
    """Return the persisted theme name (default ``"dark"``)."""
    t = Config().get("theme", "dark")
    if t == "modern":
        return "xp"
    return t


def set_theme(name: str) -> None:
    """Persist the chosen theme name."""
    cfg = Config()
    cfg.set("theme", name)


def apply_theme(widget, theme_name: str | None = None) -> None:
    """Apply *theme_name* (or the persisted theme) to *widget*."""
    if theme_name is None:
        theme_name = current_theme()
    palette = get_palette(theme_name)
    qt_palette = QPalette()
    qt_palette.setColor(QPalette.Window, QColor(palette["bg"]))
    qt_palette.setColor(QPalette.Base, QColor(palette["bg_input"]))
    qt_palette.setColor(QPalette.AlternateBase, QColor(palette["bg_alt"]))
    qt_palette.setColor(QPalette.ToolTipBase, QColor(palette["menu_bg"]))
    qt_palette.setColor(QPalette.ToolTipText, QColor(palette["fg"]))
    qt_palette.setColor(QPalette.Text, QColor(palette["fg"]))
    qt_palette.setColor(QPalette.WindowText, QColor(palette["fg"]))
    qt_palette.setColor(QPalette.Button, QColor(palette["btn_bg"]))
    qt_palette.setColor(QPalette.ButtonText, QColor(palette["fg"]))
    qt_palette.setColor(QPalette.Highlight, QColor(palette["sel_bg"]))
    qt_palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    qt_palette.setColor(QPalette.PlaceholderText, QColor(palette["fg_dim"]))
    app = QApplication.instance()
    if app is not None:
        app.setPalette(qt_palette)
    widget.setStyleSheet(get_stylesheet(palette))
    set_theme(theme_name)
