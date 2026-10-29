from __future__ import annotations
from pathlib import Path
from PySide6.QtGui import QColor, QPalette, QFont, QFontDatabase, QRawFont, QTextLayout

PALETTES = {
    "light": {"canvas": "#FAFAF8", "panel": "#F3F4F1", "surface": "#FFFFFF", "text": "#24272D", "muted": "#707781", "border": "#DFE3E6", "accent": "#4868D8", "selection": "#E8EDFC"},
    "dark": {"canvas": "#171B24", "panel": "#202632", "surface": "#272E3B", "text": "#E9EDF4", "muted": "#A2ACBC", "border": "#3D4658", "accent": "#92A9FF", "selection": "#333F5E"},
}


UI_REQUIRED_GLYPHS='MathLab0123456789АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯабвгґдеєжзиіїйклмнопрстуфхцчшщьюя→↑−√²↺'
UI_FONT_DIRECTORY = Path(__file__).resolve().parents[1] / 'resources' / 'fonts'
UI_FONT_FILES = ('Inter-Regular.ttf', 'Inter-Medium.ttf', 'Inter-SemiBold.ttf')


def _register_fonts(paths):
    return tuple(identifier for path in paths
                 if (identifier := QFontDatabase.addApplicationFont(str(path))) >= 0)


def ui_text_has_glyphs(font, text):
    """Check actual Qt text shaping, including the configured symbol fallback.

    QRawFont alone tests only the primary face. Inter intentionally delegates a
    few mathematical symbols to DejaVu; Qt's shaped runs reveal the actual face
    and glyph chosen for each run, so missing-glyph boxes still fail this check.
    """
    text = ''.join(character for character in text if not character.isspace())
    if not text:
        return True
    layout = QTextLayout(text, font)
    layout.beginLayout()
    line = layout.createLine()
    line.setLineWidth(1e9)
    layout.endLayout()
    runs = layout.glyphRuns()
    return bool(runs) and all(run.rawFont().isValid() and all(run.glyphIndexes()) for run in runs)


def ensure_ui_font(app):
    """Use bundled Inter for UI text, with verified Ukrainian-capable fallbacks.

    Static, unmodified OFL-licensed faces provide real regular/medium/semibold
    weights. Matplotlib retains its dedicated mathematical font; its bundled
    DejaVu faces also provide a fallback on fontless Windows installations.
    Qt renders text at native device resolution, including fractional Windows DPI.
    """
    if getattr(app,'mathlab_ui_font',None):return app.mathlab_ui_font
    from matplotlib import get_data_path
    folder=Path(get_data_path())/'fonts'/'ttf'
    app.mathlab_inter_font_ids = _register_fonts(UI_FONT_DIRECTORY / name for name in UI_FONT_FILES)
    fallback_ids = _register_fonts(folder / name for name in
                                  ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf', 'DejaVuSans-Oblique.ttf', 'DejaVuSans-BoldOblique.ttf'))
    app.mathlab_font_ids = app.mathlab_inter_font_ids + fallback_ids
    families=QFontDatabase.families()
    candidates = (['Inter'] if app.mathlab_inter_font_ids else []) + ['Segoe UI', 'DejaVu Sans', app.font().family()]
    for family in candidates:
        if family not in families:continue
        raw=QRawFont.fromFont(QFont(family,10))
        if raw.isValid() and all(raw.glyphIndexesForString(UI_REQUIRED_GLYPHS)):
            app.mathlab_ui_font=family
            font = QFont(family, 10, QFont.Normal)
            font.setFamilies([family, 'DejaVu Sans'])
            app.setFont(font)
            return family
    raise RuntimeError('Не вдалося завантажити шрифт інтерфейсу з українськими літерами.')


def apply_theme(app, name: str):
    family=ensure_ui_font(app)
    c = PALETTES[name]
    selected_text = c['panel'] if name == 'dark' else '#FFFFFF'
    p = QPalette()
    for role, key in [(QPalette.Window, "panel"), (QPalette.Base, "surface"), (QPalette.AlternateBase, "panel"),
                      (QPalette.WindowText, "text"), (QPalette.Text, "text"), (QPalette.ButtonText, "text"),
                      (QPalette.Button, "panel"), (QPalette.Highlight, "accent"), (QPalette.ToolTipBase, "surface"),
                      (QPalette.ToolTipText, "text")]:
        p.setColor(role, QColor(c[key]))
    p.setColor(QPalette.HighlightedText, QColor(selected_text))
    app.setPalette(p)
    app.setStyleSheet(f"""
        QWidget {{ color: {c['text']}; font-family: '{family}', 'DejaVu Sans', sans-serif; font-size: 13px; }}
        QMainWindow, QDialog {{ background: {c['panel']}; }}
        QToolBar {{ background: {c['surface']}; border: 0; border-bottom: 1px solid {c['border']}; spacing: 3px; padding: 5px; }}
        QToolButton, QPushButton {{ border: 1px solid transparent; background: transparent; padding: 6px 8px; border-radius: 3px; }}
        QToolButton:hover, QPushButton:hover {{ background: {c['selection']}; border-color: {c['border']}; }}
        QToolButton:checked, QPushButton:checked {{ background: {c['selection']}; color: {c['accent']}; }}
        QPushButton:focus, QToolButton:focus, QLineEdit:focus {{ border: 1px solid {c['accent']}; }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: {c['surface']}; border: 1px solid {c['border']}; padding: 5px; border-radius: 3px; selection-background-color: {c['accent']}; selection-color: {selected_text}; }}
        QComboBox QAbstractItemView {{ selection-background-color: {c['accent']}; selection-color: {selected_text}; }}
        QFrame#functionRow {{ border: 0; border-bottom: 1px solid {c['border']}; background: {c['panel']}; }}
        QFrame#functionRow[selected="true"] {{ background: {c['selection']}; border-left: 3px solid {c['accent']}; }}
        QLabel#muted {{ color: {c['muted']}; }}
        QLabel#error {{ color: {'#E99989' if name == 'dark' else '#AE352B'}; font-size: 11px; }}
        QScrollArea {{ border: none; background: {c['panel']}; }}
        QDockWidget {{ titlebar-close-icon: none; }}
        QDockWidget::title {{ background: {c['panel']}; border-bottom: 1px solid {c['border']}; padding: 8px; font-weight: 600; }}
        QStatusBar {{ background: {c['surface']}; border-top: 1px solid {c['border']}; }}
        QMenu {{ background: {c['surface']}; border: 1px solid {c['border']}; padding: 4px; }}
        QMenu::item {{ padding: 6px 20px; }} QMenu::item:selected {{ background: {c['selection']}; }}
        QSlider::groove:horizontal {{ height: 3px; background: {c['border']}; }}
        QSlider::handle:horizontal {{ background: {c['accent']}; width: 12px; margin: -5px 0; border-radius: 6px; }}
        QSplitter::handle {{ background: {c['border']}; width: 1px; }}
        QCheckBox {{ spacing: 6px; }}
        QGroupBox {{ border: 1px solid {c['border']}; margin-top: 10px; padding-top: 10px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 8px; }}
    """)
