from __future__ import annotations
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal, QTimer, Qt
from PySide6.QtGui import QFont
from graphmath.core.expressions import evaluate
from graphmath.plotting.sampling import sample
from graphmath.ui.theme import PALETTES

pg.setConfigOptions(antialias=True, useOpenGL=False)


class Canvas(pg.PlotWidget):
    selected = Signal(str)
    cursor = Signal(float, float)
    view_changed = Signal(list)

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(280)
        self.plotItem.setMenuEnabled(False)
        self.plotItem.hideButtons()
        self.plotItem.setLabel("bottom", "x")
        self.plotItem.setLabel("left", "y")
        self.plotItem.setDownsampling(auto=True, mode="peak")
        self.plotItem.setClipToView(True)
        self.viewbox = self.plotItem.getViewBox()
        self.viewbox.setMouseMode(pg.ViewBox.PanMode)
        self.viewbox.setLimits(minXRange=1e-6, minYRange=1e-6, maxXRange=2e8, maxYRange=2e8)
        self.functions = []
        self.curves = {}
        self.annotations = []
        self.selected_id = None
        self.cross_x = pg.InfiniteLine(angle=90, movable=False)
        self.cross_y = pg.InfiniteLine(angle=0, movable=False)
        self.cross_x.setZValue(-1)
        self.cross_y.setZValue(-1)
        self.addItem(self.cross_x, ignoreBounds=True)
        self.addItem(self.cross_y, ignoreBounds=True)
        self.hover_dot = pg.ScatterPlotItem(size=8, pen=pg.mkPen("#FFFFFF", width=1.5))
        self.addItem(self.hover_dot)
        self.resample_timer = QTimer(self)
        self.resample_timer.setSingleShot(True)
        self.resample_timer.setInterval(45)
        self.resample_timer.timeout.connect(self.refresh)
        self.viewbox.sigRangeChanged.connect(self.range_changed)
        self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=40, slot=self.mouse_move)
        self.set_theme("light")

    def range_changed(self, *_):
        self.resample_timer.start()
        self.view_changed.emit(self.current_view())

    def current_view(self):
        xr, yr = self.viewbox.viewRange()
        return [*xr, *yr]

    def set_view(self, view):
        self.viewbox.setRange(xRange=view[:2], yRange=view[2:], padding=0)

    def set_theme(self, name):
        self.theme = name
        c = PALETTES[name]
        self.setBackground(c["canvas"])
        for axis in ["left", "bottom"]:
            item = self.getAxis(axis)
            item.setPen(pg.mkPen(c["muted"]))
            item.setTextPen(pg.mkPen(c["muted"]))
            item.setTickFont(QFont("Segoe UI", 10))
        for line in [self.cross_x, self.cross_y]:
            line.setPen(pg.mkPen(c["muted"], width=1, style=Qt.DotLine))
        self.axes_lines = getattr(self, "axes_lines", [])
        for line in self.axes_lines:
            self.removeItem(line)
        self.axes_lines = [pg.InfiniteLine(pos=0, angle=0), pg.InfiniteLine(pos=0, angle=90)]
        for line in self.axes_lines:
            line.setPen(pg.mkPen(c["muted"], width=1))
            line.setZValue(-2)
            self.addItem(line)

    def set_grid_axes(self, grid, axes):
        self.showGrid(x=grid, y=grid, alpha=0.13)
        for line in self.axes_lines:
            line.setVisible(axes)
        self.plotItem.showAxis("left", axes)
        self.plotItem.showAxis("bottom", axes)

    def update_functions(self, functions, selected):
        self.functions = functions
        self.selected_id = selected
        ids = {f.id for f in functions}
        for identifier in list(self.curves):
            if identifier not in ids:
                self.removeItem(self.curves.pop(identifier))
        for f in functions:
            if f.id not in self.curves:
                curve = pg.PlotDataItem(connect="finite")
                curve.setCurveClickable(True, width=10)
                curve.sigClicked.connect(lambda *_, identifier=f.id: self.selected.emit(identifier))
                self.curves[f.id] = curve
                self.addItem(curve)
            self.curves[f.id].setPen(pg.mkPen(self.display_color(f.color), width=2.6 if f.id == selected else 1.9))
            self.curves[f.id].setVisible(f.visible)
        self.refresh()

    def display_color(self, color):
        if self.theme == "dark":
            from PySide6.QtGui import QColor
            return QColor(color).lighter(145)
        return color

    def refresh(self, only=None):
        xmin, xmax, ymin, ymax = self.current_view()
        for f in self.functions:
            if not f.visible or (only is not None and f.id != only):
                continue
            try:
                xx, yy = sample(f.expression, xmin, xmax, {n: p.value for n, p in f.parameters.items()}, pixels=self.width(), yrange=(ymin, ymax))
                self.curves[f.id].setData(xx, yy, connect="finite")
            except Exception:
                self.curves[f.id].setData([], [])

    def mouse_move(self, event):
        position = event[0]
        if not self.sceneBoundingRect().contains(position):
            return
        point = self.viewbox.mapSceneToView(position)
        x, y = point.x(), point.y()
        self.cross_x.setPos(x)
        self.cross_y.setPos(y)
        self.cursor.emit(x, y)
        function = next((f for f in self.functions if f.id == self.selected_id and f.visible), None)
        if function:
            try:
                value = float(evaluate(function.expression, np.array(x), {n: p.value for n, p in function.parameters.items()}))
                if np.isfinite(value):
                    self.hover_dot.setData([x], [value], brush=self.display_color(function.color))
                    self.setToolTip(f"x = {x:.5g}\nf(x) = {value:.5g}")
                    return
            except Exception:
                pass
        self.hover_dot.setData([], [])

    def fit_selected(self):
        function = next((f for f in self.functions if f.id == self.selected_id), None)
        if not function:
            return
        xmin, xmax = self.current_view()[:2]
        try:
            y = evaluate(function.expression, np.linspace(xmin, xmax, 2000), {n: p.value for n, p in function.parameters.items()})
            y = y[np.isfinite(y)]
            if y.size:
                low, high = np.quantile(y, [0.02, 0.98])
                padding = max((high - low) * 0.12, 1)
                self.set_view([xmin, xmax, low - padding, high + padding])
        except Exception:
            pass

    def clear_annotations(self):
        for item in self.annotations:
            self.removeItem(item)
        self.annotations.clear()

    def mark_points(self, points, color):
        if not points:
            return
        dots = pg.ScatterPlotItem([p["x"] for p in points], [p["y"] for p in points], size=9,
                                 brush=color, pen=pg.mkPen(PALETTES[self.theme]["canvas"], width=1.5))
        self.addItem(dots)
        self.annotations.append(dots)
        for point in points[:12]:
            text = pg.TextItem(point["exact"], anchor=(0, 1), color=PALETTES[self.theme]["text"])
            text.setPos(point["x"], point["y"])
            self.addItem(text)
            self.annotations.append(text)

    def mark_line(self, value, vertical, color):
        line = pg.InfiniteLine(pos=value, angle=90 if vertical else 0,
                               pen=pg.mkPen(color, width=1, style=Qt.DashLine),
                               label=("x" if vertical else "y") + f" = {value:.5g}",
                               labelOpts={"color": PALETTES[self.theme]["text"], "position": 0.85})
        self.addItem(line)
        self.annotations.append(line)

    def tangent(self, source, params, point):
        # Local numerical derivative is explicitly identified as approximate in UI.
        h = 1e-5 * max(1, abs(point))
        vals = evaluate(source, np.array([point - h, point, point + h]), params)
        if not np.isfinite(vals).all():
            return None
        slope = (vals[2] - vals[0]) / (2 * h)
        # A cusp has incompatible one-sided slopes.
        if abs((vals[1] - vals[0]) / h - (vals[2] - vals[1]) / h) > 1e-3 * max(1, abs(slope)):
            return None
        x = np.array(self.current_view()[:2])
        line = pg.PlotDataItem(x, vals[1] + slope * (x - point), pen=pg.mkPen("#BF871C", width=1.5, style=Qt.DashLine))
        self.addItem(line)
        self.annotations.append(line)
        self.mark_points([{"x": point, "y": float(vals[1]), "exact": f"≈ ({point:.4g}, {vals[1]:.4g})"}], "#BF871C")
        return slope
