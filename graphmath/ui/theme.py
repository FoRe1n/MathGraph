from __future__ import annotations
from PySide6.QtGui import QColor, QPalette

PALETTES = {
    "light": {"canvas": "#FAFAF8", "panel": "#F3F4F1", "surface": "#FFFFFF", "text": "#24272D", "muted": "#707781", "border": "#DFE3E6", "accent": "#4868D8", "selection": "#E8EDFC"},
    "dark": {"canvas": "#171B24", "panel": "#202632", "surface": "#272E3B", "text": "#E9EDF4", "muted": "#A2ACBC", "border": "#3D4658", "accent": "#92A9FF", "selection": "#333F5E"},
}


def apply_theme(app, name: str):
    c = PALETTES[name]
    p = QPalette()
    for role, key in [(QPalette.Window, "panel"), (QPalette.Base, "surface"), (QPalette.AlternateBase, "panel"),
                      (QPalette.WindowText, "text"), (QPalette.Text, "text"), (QPalette.ButtonText, "text"),
                      (QPalette.Button, "panel"), (QPalette.Highlight, "accent"), (QPalette.ToolTipBase, "surface"),
                      (QPalette.ToolTipText, "text")]:
        p.setColor(role, QColor(c[key]))
    app.setPalette(p)
    app.setStyleSheet(f"""
        QWidget {{ color: {c['text']}; font-family: 'Segoe UI', 'DejaVu Sans', sans-serif; font-size: 12px; }}
        QMainWindow, QDialog {{ background: {c['panel']}; }}
        QToolBar {{ background: {c['surface']}; border: 0; border-bottom: 1px solid {c['border']}; spacing: 3px; padding: 5px; }}
        QToolButton, QPushButton {{ border: 1px solid transparent; background: transparent; padding: 6px 8px; border-radius: 3px; }}
        QToolButton:hover, QPushButton:hover {{ background: {c['selection']}; border-color: {c['border']}; }}
        QToolButton:checked, QPushButton:checked {{ background: {c['selection']}; color: {c['accent']}; }}
        QPushButton:focus, QToolButton:focus, QLineEdit:focus {{ border: 1px solid {c['accent']}; }}
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: {c['surface']}; border: 1px solid {c['border']}; padding: 5px; border-radius: 3px; selection-background-color: {c['accent']}; }}
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
