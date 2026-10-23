"""A bounded, directly painted grid; avoids full-plane AxisItem QPicture replay."""
from __future__ import annotations
import math
from PySide6.QtCore import QRectF, QLineF
from PySide6.QtGui import QColor, QPainter, QPen
import pyqtgraph as pg


class CoordinateGrid(pg.GraphicsObject):
    def __init__(self):
        super().__init__()
        self.rectangle = QRectF(-8, -5, 16, 12)
        self.color = QColor('#707781')
        self.setZValue(-20)

    def boundingRect(self):
        return self.rectangle

    def set_view(self, view):
        rect = QRectF(view[0], view[2], view[1]-view[0], view[3]-view[2])
        if rect != self.rectangle:
            self.prepareGeometryChange()
            self.rectangle = rect
            self.update()

    def paint(self, painter, option, widget=None):
        rect = self.rectangle
        painter.setRenderHint(QPainter.Antialiasing, False)
        for major in [False, True]:
            color = QColor(self.color)
            color.setAlpha(42 if major else 16)
            pen = QPen(color, 1)
            pen.setCosmetic(True)
            painter.setPen(pen)
            lines = []
            for vertical, low, high in [(True, rect.left(), rect.right()), (False, rect.top(), rect.bottom())]:
                raw = (high-low) / 8
                magnitude = 10**math.floor(math.log10(max(raw, 1e-12)))
                step = next((v*magnitude for v in [1, 2, 5, 10] if v*magnitude >= raw), 10*magnitude)
                if not major:
                    step /= 5
                start = math.ceil(low/step)
                end = min(math.floor(high/step), start+100)
                for tick in range(start, end+1):
                    value = tick*step
                    lines.append(QLineF(value,rect.top(),value,rect.bottom()) if vertical else QLineF(rect.left(),value,rect.right(),value))
            painter.drawLines(lines)
