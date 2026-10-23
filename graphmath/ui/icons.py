"""Small original line icons, rendered at device resolution by Qt."""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

PATHS = {
 "new": '<path d="M6 3h8l4 4v14H6z M13 3v5h5 M9 14h6 M12 11v6"/>',
 "open": '<path d="M3 8V5h7l2 3h9l-3 12H3z M3 8h18"/>',
 "save": '<path d="M4 3h14l3 3v15H3V3z M7 3v6h10V3 M7 21v-8h10v8"/>',
 "undo": '<path d="M8 5L3 10l5 5 M3 10h11a6 6 0 0 1 0 12"/>',
 "redo": '<path d="M16 5l5 5-5 5 M21 10h-11a6 6 0 0 0 0 12"/>',
 "zoom_in": '<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6 M7 10h6 M10 7v6"/>',
 "zoom_out": '<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6 M7 10h6"/>',
 "reset": '<path d="M3 10V4m0 6h6 M3 10a9 9 0 1 1 0 5"/>',
 "fit": '<path d="M8 3H3v5 M16 3h5v5 M8 21H3v-5 M16 21h5v-5 M6 16l4-8 4 8 4-8"/>',
 "export": '<path d="M12 16V2 M7 7l5-5 5 5 M4 13v8h16v-8"/>',
 "theme": '<path d="M20 15A9 9 0 0 1 9 3a9 9 0 1 0 11 12z"/>',
 "settings": '<path d="M3 6h18 M3 12h18 M3 18h18"/><circle cx="8" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="10" cy="18" r="2"/>',
 "analysis": '<path d="M3 20V4 M3 20h18 M6 16c3 0 3-10 7-10s3 10 7 5"/>',
 "panel": '<rect x="3" y="3" width="18" height="18" rx="1"/><path d="M9 3v18"/>',
}


def icon(name, color):
    renderer = QSvgRenderer(QByteArray(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</svg>'.encode()))
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)
