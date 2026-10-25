from __future__ import annotations
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal, QTimer, Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QApplication
from graphmath.core.expressions import evaluate, parse, relation_x
from graphmath.plotting.sampling import sample
from graphmath.ui.theme import PALETTES, ensure_ui_font
from graphmath.ui.grid import CoordinateGrid

pg.setConfigOptions(antialias=False, useOpenGL=False)


class Canvas(pg.PlotWidget):
    selected = Signal(str)
    cursor = Signal(float, float)
    view_changed = Signal(list)
    curves_updated = Signal()

    def __init__(self):
        ensure_ui_font(QApplication.instance())
        super().__init__()
        self.setMinimumWidth(280)
        self.plotItem.setMenuEnabled(False)
        self.plotItem.hideButtons()
        self.plotItem.setLabel("bottom", "x — горизонтальна вісь")
        self.plotItem.setLabel("left", "y — вертикальна вісь")
        self.plotItem.setDownsampling(auto=True, mode="peak")
        self.plotItem.setClipToView(True)
        self.viewbox = self.plotItem.getViewBox()
        self.viewbox.setMouseMode(pg.ViewBox.PanMode)
        self.viewbox.setLimits(minXRange=1e-6, minYRange=1e-6, maxXRange=2e8, maxYRange=2e8)
        self.grid_item = CoordinateGrid()
        self.addItem(self.grid_item, ignoreBounds=True)
        self.sample_cache = {}
        self.sample_count = 0
        self.pending_functions = set()
        self.coordinates_enabled = False
        self.interacting = False
        self.refine_ids = set()
        self.functions = []
        self.curves = {}
        self.annotations = []
        self.selected_id = None
        self.cross_x = pg.InfiniteLine(angle=90, movable=False)
        self.cross_y = pg.InfiniteLine(angle=0, movable=False)
        self.cross_x.hide()
        self.cross_x.setZValue(-1)
        self.cross_y.hide()
        self.cross_y.setZValue(-1)
        self.addItem(self.cross_x, ignoreBounds=True)
        self.addItem(self.cross_y, ignoreBounds=True)
        self.hover_dot = pg.ScatterPlotItem(size=8, pen=pg.mkPen("#FFFFFF", width=1.5))
        self.addItem(self.hover_dot)
        self.resample_timer = QTimer(self)
        self.resample_timer.setSingleShot(True)
        self.resample_timer.setInterval(16)
        self.resample_timer.timeout.connect(self.flush_refresh)
        self.refine_timer = QTimer(self)
        self.refine_timer.setSingleShot(True)
        self.refine_timer.setInterval(140)
        self.refine_timer.timeout.connect(self.finish_interaction)
        self.notify_timer = QTimer(self)
        self.notify_timer.setSingleShot(True)
        self.notify_timer.setInterval(80)
        self.notify_timer.timeout.connect(lambda: self.view_changed.emit(self.current_view()))
        self.viewbox.sigRangeChanged.connect(self.range_changed)
        self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=20, slot=self.mouse_move)
        self.set_theme("light")

    def range_changed(self, *_):
        view = self.current_view()
        self.grid_item.set_view(view)
        self.begin_interaction()
        self.schedule_refresh()
        if not self.notify_timer.isActive():
            self.notify_timer.start()

    def current_view(self):
        xr, yr = self.viewbox.viewRange()
        return [*xr, *yr]

    def set_view(self, view):
        self.viewbox.setRange(xRange=view[:2], yRange=view[2:], padding=0)

    def set_theme(self, name):
        self.theme = name
        c = PALETTES[name]
        self.grid_item.color = QColor(c["muted"])
        self.grid_item.update()
        self.setBackground(c["canvas"])
        for axis in ["left", "bottom"]:
            item = self.getAxis(axis)
            item.setPen(pg.mkPen(c["muted"]))
            item.setTextPen(pg.mkPen(c["muted"]))
            font=QFont(QApplication.font());font.setPointSize(10)
            item.setTickFont(font)
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
        self.showGrid(x=False, y=False)
        self.grid_item.setVisible(grid)
        for line in self.axes_lines:
            line.setVisible(axes)
        self.plotItem.showAxis("left", axes)
        self.plotItem.showAxis("bottom", axes)

    def update_functions(self, functions, selected):
        if selected != self.selected_id or self.coordinates_enabled:
            self.hover_dot.setData([], [])
        self.functions = functions
        self.selected_id = selected
        ids = {f.id for f in functions}
        for identifier in list(self.curves):
            if identifier not in ids:
                self.removeItem(self.curves.pop(identifier))
                self.sample_cache.pop(identifier, None)
        for f in functions:
            if f.id not in self.curves:
                curve = pg.PlotDataItem(connect="finite", antialias=False)
                curve.setCurveClickable(True, width=10)
                curve.sigClicked.connect(lambda *_, identifier=f.id: self.selected.emit(identifier))
                self.curves[f.id] = curve
                self.addItem(curve)
            self.curves[f.id].setPen(pg.mkPen(self.display_color(f.color), width=2 if f.id == selected else 1.5))
            self.curves[f.id].setVisible(f.visible)
            if self.interacting:self.refine_ids.add(f.id)
        self.refresh()

    def display_color(self, color):
        if self.theme == "dark":
            from PySide6.QtGui import QColor
            return QColor(color).lighter(145)
        return color

    def begin_interaction(self, only=None):
        if self.coordinates_enabled and len(self.hover_dot.data):
            self.hover_dot.setData([], [])
        if not self.interacting:
            self.interacting=True
            for curve in self.curves.values():
                curve.opts['antialias']=False
                curve.curve.opts['antialias']=False
                curve.curve.update()
        self.refine_ids.update([only] if only else [f.id for f in self.functions])
        self.refine_timer.start()

    def finish_interaction(self):
        self.interacting=False
        for curve in self.curves.values():
            curve.opts['antialias']=True
            curve.curve.opts['antialias']=True
            curve.curve.update()
        identifiers=self.refine_ids.copy()
        self.refine_ids.clear()
        self.refresh(force=True,identifiers=identifiers)

    def schedule_refresh(self, only=None):
        if only:
            self.pending_functions.add(only)
        else:
            self.pending_functions.update(f.id for f in self.functions)
        if not self.resample_timer.isActive():
            self.resample_timer.start()

    def flush_refresh(self):
        pending = self.pending_functions.copy()
        self.pending_functions.clear()
        self.refresh(identifiers=pending)

    def refresh(self, only=None, *, force=False, identifiers=None):
        xmin, xmax, ymin, ymax = self.current_view()
        width, height = xmax-xmin, ymax-ymin
        for f in self.functions:
            if not f.visible or (only is not None and f.id != only) or (identifiers is not None and f.id not in identifiers):
                continue
            parameters = {n: p.value for n, p in f.parameters.items()}
            try:
                if parse(f.expression).relation:
                    x=relation_x(f.expression,parameters)
                    self.curves[f.id].setData([x,x] if x is not None else [], [ymin,ymax] if x is not None else [])
                    self.sample_cache.pop(f.id,None)
                    continue
            except Exception:
                self.curves[f.id].setData([],[])
                self.sample_cache.pop(f.id, None)
                continue
            key = (f.expression, tuple(sorted(parameters.items())), self.width())
            cached = self.sample_cache.get(f.id)
            if not force and cached and cached['key'] == key:
                if (cached['left'] <= xmin and cached['right'] >= xmax
                    and .65 <= width/cached['width'] <= 1.5
                    and .65 <= height/cached['height'] <= 1.5
                    and ymin >= cached['ymin']-cached['height']*2
                    and ymax <= cached['ymax']+cached['height']*2):
                    continue  # Qt transforms existing data; do not reupload identical paths.
            try:
                left, right = xmin-width*.6, xmax+width*.6
                xx, yy = sample(f.expression, left, right, parameters,
                                pixels=int(self.width()*1.1), yrange=(ymin, ymax))
                self.sample_count += 1
                self.curves[f.id].setData(xx, yy, connect="finite", antialias=not self.interacting)
                self.sample_cache[f.id] = dict(key=key, left=left, right=right, width=width,
                                               height=height, ymin=ymin, ymax=ymax)
            except Exception:
                self.curves[f.id].setData([], [])
                self.sample_cache.pop(f.id, None)
        self.curves_updated.emit()

    def prepare_export(self):
        """Synchronize queued edits and restore final-quality paths for a snapshot."""
        self.resample_timer.stop()
        self.refine_timer.stop()
        self.pending_functions.clear()
        self.refine_ids.clear()
        self.interacting=False
        for curve in self.curves.values():
            curve.opts['antialias']=True
            curve.curve.opts['antialias']=True
        self.refresh(force=True)

    def set_coordinates(self, enabled):
        self.coordinates_enabled = enabled
        self.hover_dot.setVisible(enabled)
        self.cross_x.hide()
        self.cross_y.hide()
        self.setToolTip('')

    def mouse_move(self, event):
        if not self.coordinates_enabled:
            return
        position = event[0]
        if not self.viewbox.sceneBoundingRect().contains(position):
            self.hover_dot.setData([], [])
            return
        point = self.viewbox.mapSceneToView(position)
        x, y = point.x(), point.y()
        self.cursor.emit(x, y)
        function = next((f for f in self.functions if f.id == self.selected_id and f.visible), None)
        if function:
            try:
                value = float(evaluate(function.expression, np.array(x), {n: p.value for n, p in function.parameters.items()}))
                if np.isfinite(value):
                    self.hover_dot.setData([x], [value], brush=self.display_color(function.color))

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
            if parse(function.expression).relation:
                x=relation_x(function.expression,{n:p.value for n,p in function.parameters.items()})
                if x is not None:
                    ymin,ymax=self.current_view()[2:]
                    self.set_view([x-5,x+5,ymin,ymax])
                return
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
