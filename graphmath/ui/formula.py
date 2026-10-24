"""Bounded, cached MathText rendering with packaged DejaVu mathematical fonts."""
from functools import lru_cache
from io import BytesIO
import os
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.environ.get("TEMP", "/tmp"), "graphmath-mpl"))
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy
from PySide6.QtCore import Qt
from graphmath.core.expressions import parse


@lru_cache(maxsize=256)
def formula_png(latex: str, color: str = "#24272D", size: int = 13) -> bytes:
    fig = Figure(figsize=(4, 0.65), dpi=140)
    FigureCanvasAgg(fig)
    fig.patch.set_alpha(0)
    text = fig.text(0, 0.5, f"${latex if latex.startswith('x=') else 'y = '+latex}$", color=color, fontsize=size, va="center", math_fontfamily="dejavusans")
    fig.canvas.draw()
    bounds = text.get_window_extent(fig.canvas.get_renderer()).expanded(1.06, 1.2).transformed(fig.dpi_scale_trans.inverted())
    output = BytesIO()
    fig.savefig(output, format="png", transparent=True, bbox_inches=bounds, pad_inches=0.02)
    return output.getvalue()


class FormulaLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original = None
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setMinimumHeight(36)
        self.setMaximumHeight(66)
        self.setContentsMargins(4, 2, 2, 2)
        self.setToolTip("Математичний вигляд введеного виразу")

    def update_expression(self, source, color):
        try:
            self.update_latex(parse(source).latex, color)
        except Exception:
            self.clear()

    def update_latex(self, latex, color, size=13):
        try:
            image = QPixmap()
            image.loadFromData(formula_png(latex, color, size))
            image.setDevicePixelRatio(1.4)
            self.original = image
            self.fit_preview()
        except Exception:
            self.clear()

    def clear(self):
        self.original = None
        super().clear()

    def fit_preview(self):
        if self.original is not None:
            logical = self.original.deviceIndependentSize()
            if logical.width() > self.width() - 8:
                self.setPixmap(self.original.scaled(int(max(20, self.width() - 8) * 1.4), 86, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.setPixmap(self.original)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_preview()
