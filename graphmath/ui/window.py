from __future__ import annotations
import copy
import json
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QDockWidget, QScrollArea, QPushButton, QLabel, QToolBar, QToolButton, QFileDialog,
    QMessageBox, QLineEdit, QAbstractSpinBox, QMenu, QDialog, QStackedWidget, QComboBox)
from graphmath.core.expressions import parse, ExpressionError
from graphmath.persistence.projects import Project, Function, Parameter, COLORS, from_dict, save, load
from graphmath.plotting.export import export_graph
from graphmath.ui.canvas import Canvas
from graphmath.ui.editor import FunctionRow, ParameterControl
from graphmath.ui.inspector import Inspector
from graphmath.ui.dialogs import SettingsDialog, ExportDialog
from graphmath.ui.theme import apply_theme, PALETTES
from graphmath.ui.icons import icon, PATHS
from graphmath.core.laboratories import LABS, default_project, identify, markers, number, suggested_view
from graphmath.ui.learning import LearningPanel


class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings("GraphMath", "GraphMath")
        defaults = {"theme": "light", "precision": 5, "scale": "100%", "colors": COLORS,
                    "default_view": [-6, 6, -3, 9], "grid": True, "axes": True, "coordinates": False}
        try:
            self.preferences = {**defaults, **json.loads(self.settings.value("preferences", "{}"))}
            if self.preferences["theme"] not in PALETTES:
                self.preferences["theme"] = "light"
        except (ValueError, TypeError):
            self.preferences = defaults
        self.project = default_project()
        self.mode = "quadratic"
        self.project.view = list(self.preferences["default_view"])
        self.project.grid = self.preferences["grid"]
        self.project.axes = self.preferences["axes"]
        self.project.selected = self.project.functions[0].id
        self.path = None
        self.saved_state = self.serialized()
        self.history = [self.serialized()]
        self.history_index = 0
        self.loading = False
        self.dirty = False
        self.rows = {}
        self.actions = {}
        self.setWindowTitle("MathLab 1.0")
        self.resize(1400, 850)
        self.setMinimumSize(780, 540)
        self.canvas = Canvas()
        graph_area = QWidget()
        graph_layout = QVBoxLayout(graph_area)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_header = QHBoxLayout()
        self.graph_hint = QLabel('  x → праворуч    ·    y ↑ вгору')
        self.graph_hint.setObjectName('muted')
        graph_header.addWidget(self.graph_hint)
        graph_header.addStretch()
        for label, tooltip, callback in [('+', 'Збільшити', lambda:self.canvas.viewbox.scaleBy((.8,.8))),
                                          ('−', 'Зменшити', lambda:self.canvas.viewbox.scaleBy((1.25,1.25))),
                                          ('Початковий вигляд', 'Повернути зручний масштаб для цієї функції', self.reset_view)]:
            button=QPushButton(label);button.setToolTip(tooltip);button.clicked.connect(callback)
            graph_header.addWidget(button)
        graph_layout.addLayout(graph_header)
        graph_layout.addWidget(self.canvas, 1)
        self.setCentralWidget(graph_area)
        self.create_editor()
        self.inspector = Inspector()
        self.inspector_dock = QDockWidget("Дослідження функції", self)
        self.inspector_dock.setObjectName("analysisDock")
        self.inspector_dock.setWidget(self.inspector)
        self.inspector_dock.setMinimumWidth(290)
        self.addDockWidget(Qt.RightDockWidgetArea, self.inspector_dock)
        self.inspector_dock.hide()
        self.inspector.investigate.connect(self.investigate)
        self.inspector.annotations_changed.connect(self.draw_annotations)
        self.inspector.other.currentIndexChanged.connect(self.invalidate_analysis)
        self.create_actions()
        self.create_menus()
        self.create_toolbar()
        self.cursor_label = QLabel("x  0     y  0")
        self.scale_label = QLabel()
        self.active_label = QLabel()
        self.statusBar().addWidget(self.cursor_label, 1)
        self.statusBar().addPermanentWidget(self.active_label)
        self.statusBar().addPermanentWidget(self.scale_label)
        self.canvas.cursor.connect(self.cursor_moved)
        self.canvas.selected.connect(self.select)
        self.canvas.view_changed.connect(self.view_changed)
        self.set_theme(self.preferences["theme"])
        self.rebuild_editor()
        self.canvas.set_view(self.project.view)
        self.refresh_canvas()
        self.resizeDocks([self.editor_dock], [310], Qt.Horizontal)
        self.canvas.set_coordinates(self.preferences['coordinates'])
        self.cursor_label.setVisible(self.preferences['coordinates'])
        self.canvas.curves_updated.connect(self.draw_lab_markers)
        self.history_timer = QTimer(self)
        self.history_timer.setSingleShot(True)
        self.history_timer.setInterval(180)
        self.history_timer.timeout.connect(self.record)
        self.sync_learning()
        self.dirty = False
        self.saved_state = self.serialized()
        self.history = [self.saved_state]
        self.update_title()

    def serialized(self):
        return json.dumps(self.project.to_dict(), sort_keys=True, ensure_ascii=False)

    def create_editor(self):
        self.editor_dock = QDockWidget("ФУНКЦІЇ", self)
        self.editor_dock.setObjectName("functionsDock")
        self.editor_dock.setMinimumWidth(255)
        self.editor_dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(0)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_widget)
        layout.addWidget(self.scroll, 1)
        add = QPushButton("＋  Додати функцію")
        add.setToolTip("Додати незалежну функцію (до 100)")
        add.clicked.connect(self.add_function)
        layout.addWidget(add)
        self.math_toolbar = QToolBar()
        self.math_toolbar.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.math_toolbar.setStyleSheet("QToolButton { padding: 4px; min-width: 22px; }")
        # Templates select their placeholder so users can immediately type over it.
        templates = [("x²", "x^2", 0, 1), ("xⁿ", "x^(2)", 3, 1), ("√", "sqrt(x)", 5, 1),
                     ("ⁿ√", "root(x,3)", 5, 1), ("a/b", "(x)/(2)", 1, 1),
                     ("log", "log(x,2)", 4, 1)]
        for title, text, start, length in templates:
            action = self.math_toolbar.addAction(title)
            action.setToolTip(text)
            action.triggered.connect(lambda checked=False, t=text, s=start, n=length: self.insert_math(t, s, n))
        layout.addWidget(self.math_toolbar)
        second = QToolBar()
        second.setStyleSheet("QToolButton { padding: 4px; min-width: 22px; }")
        for title, text, start, length in [("ln", "ln(x)", 3, 1), ("sin", "sin(x)", 4, 1), ("cos", "cos(x)", 4, 1),
                                           ("tan", "tan(x)", 4, 1), ("π", "pi", 2, 0), ("( )", "(x)", 1, 1)]:
            action = second.addAction(title)
            action.setToolTip(text)
            action.triggered.connect(lambda checked=False, t=text, s=start, n=length: self.insert_math(t, s, n))
        layout.addWidget(second)
        self.parameter_container = QWidget()
        self.parameter_layout = QVBoxLayout(self.parameter_container)
        self.parameter_layout.setContentsMargins(12, 6, 12, 6)
        self.parameter_scroll = QScrollArea()
        self.parameter_scroll.setWidgetResizable(True)
        self.parameter_scroll.setMaximumHeight(250)
        self.parameter_scroll.setWidget(self.parameter_container)
        self.parameter_scroll.hide()
        layout.addWidget(self.parameter_scroll)
        self.custom_page = container
        sidebar = QWidget()
        outer = QVBoxLayout(sidebar)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(5)
        brand = QLabel('MathLab')
        brand.setStyleSheet('font-size: 23px; font-weight: 600; padding: 15px 16px 0 16px;')
        outer.addWidget(brand)
        hint=QLabel('Змінюйте коефіцієнти. Спостерігайте за графіком.')
        hint.setObjectName('muted');hint.setWordWrap(True);hint.setContentsMargins(16,0,16,5)
        outer.addWidget(hint)
        self.mode_selector=QComboBox()
        self.mode_selector.setAccessibleName('Тип функції')
        for key,lab in LABS.items():self.mode_selector.addItem(lab.title,key)
        self.mode_selector.addItem('Власна функція','custom')
        selector_layout=QHBoxLayout();selector_layout.setContentsMargins(16,0,16,0)
        selector_layout.addWidget(self.mode_selector);outer.addLayout(selector_layout)
        self.learning=LearningPanel()
        self.learning.coefficient_changed.connect(self.lab_coefficient_changed)
        self.learning.finished.connect(self.flush_history)
        self.learning.reset_requested.connect(self.reset_coefficients)
        self.learning.markers_changed.connect(self.draw_lab_markers)
        self.learning.visibility_requested.connect(lambda:self.visibility(self.project.selected,True))
        learning_scroll=QScrollArea();learning_scroll.setWidgetResizable(True)
        learning_scroll.setWidget(self.learning)
        self.pages=QStackedWidget();self.pages.addWidget(learning_scroll);self.pages.addWidget(container)
        outer.addWidget(self.pages,1)
        self.editor_dock.setWidget(sidebar)
        self.editor_dock.setTitleBarWidget(QWidget())
        self.mode_selector.currentIndexChanged.connect(self.mode_changed)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.editor_dock)

    def create_actions(self):
        definitions = [
            ("new", "Новий проєкт", "Ctrl+N", self.new_project),
            ("open", "Відкрити…", "Ctrl+O", self.open_project),
            ("save", "Зберегти", "Ctrl+S", self.save_project),
            ("save_as", "Зберегти як…", "Ctrl+Shift+S", lambda: self.save_project(True)),
            ("undo", "Скасувати", "Ctrl+Z", self.undo), ("redo", "Повторити", "Ctrl+Y", self.redo),
            ("zoom_in", "Збільшити", "", lambda: self.canvas.viewbox.scaleBy((0.8, 0.8))),
            ("zoom_out", "Зменшити", "", lambda: self.canvas.viewbox.scaleBy((1.25, 1.25))),
            ("reset", "Скинути вигляд", "Ctrl+0", self.reset_view),
            ("fit", "Вмістити вибрану функцію", "", self.canvas.fit_selected),
            ("export", "Експорт графіка…", "Ctrl+E", self.export),
            ("theme", "Змінити тему", "", self.toggle_theme),
            ("settings", "Налаштування", "", self.show_settings),
            ("analysis", "Дослідження функції", "Ctrl+I", self.toggle_inspector),
            ("panel", "Показати / приховати функції", "Ctrl+B", lambda: self.editor_dock.setVisible(not self.editor_dock.isVisible())),
            ("delete", "Видалити функцію", "Delete", self.delete_selected),
            ("escape", "Закрити дослідження", "Escape", self.inspector_dock.hide),
        ]
        for key, title, shortcut, callback in definitions:
            action = QAction(title, self)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(lambda checked=False, fn=callback: fn())
            self.addAction(action)
            self.actions[key] = action
        self.grid_action = QAction("Сітка", self, checkable=True)
        self.grid_action.triggered.connect(self.set_grid)
        self.axes_action = QAction("Осі координат", self, checkable=True)
        self.axes_action.triggered.connect(self.set_axes)

    def create_menus(self):
        file_menu = self.menuBar().addMenu("Файл")
        for key in ["new", "open", "save", "save_as", "export"]:
            file_menu.addAction(self.actions[key])
        self.recent_menu = file_menu.addMenu("Нещодавні проєкти")
        self.update_recents()
        file_menu.addSeparator()
        file_menu.addAction("Вийти", self.close)
        edit = self.menuBar().addMenu("Редагування")
        for key in ["undo", "redo", "delete"]:
            edit.addAction(self.actions[key])
        view = self.menuBar().addMenu("Вигляд")
        for key in ["panel", "analysis", "reset", "fit"]:
            view.addAction(self.actions[key])
        view.addAction(self.grid_action)
        view.addAction(self.axes_action)
        view.addSeparator()
        view.addAction(self.actions["theme"])
        view.addAction(self.actions["settings"])
        help_menu = self.menuBar().addMenu("Довідка")
        help_menu.addAction("Синтаксис і керування", self.help)
        help_menu.addAction("Про MathLab", lambda: QMessageBox.about(self, "MathLab 1.0", "MathLab 1.0.0\nМатематичний простір для досліджень.\nПрацює офлайн · ліцензія MIT\n\nQt / PySide6 (LGPLv3), PyQtGraph (MIT), SymPy (BSD),\nNumPy (BSD), Matplotlib (PSF-compatible).\nПовні ліцензії постачаються з програмою."))

    def create_toolbar(self):
        toolbar=QToolBar('Основні дії',self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(19,19))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)
        for key in ['new','open','save','export']:
            toolbar.addAction(self.actions[key])
        spacer=QWidget()
        from PySide6.QtWidgets import QSizePolicy
        spacer.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
        toolbar.addAction(self.actions['settings'])
        self.main_toolbar=toolbar

    def reset_view(self):
        function=self.current_function()
        view=suggested_view(self.mode,{n:p.value for n,p in function.parameters.items()}) if self.mode in LABS and function else self.preferences['default_view']
        self.canvas.set_view(view)

    def mode_changed(self, *_):
        key=self.mode_selector.currentData()
        self.flush_inputs()
        self.flush_history()
        if key in LABS:
            function=next((f for f in self.project.functions if identify(f)==key),None)
            if function is None:
                if len(self.project.functions)>=100:
                    self.statusBar().showMessage('Проєкт уже містить 100 функцій. Видаліть зайву у власному режимі.',5000)
                    self.sync_learning();return
                function=LABS[key].make_function()
                function.color=self.preferences['colors'][list(LABS).index(key)%len(self.preferences['colors'])]
                self.project.functions.append(function)
            self.project.selected=function.id
            self.mode=key
            self.project.mode=key
            self.rebuild_editor()
            self.reset_view()
        else:
            self.mode='custom'
            self.project.mode='custom'
        self.sync_learning(preserve_custom=True)
        self.invalidate_analysis()
        self.refresh_canvas()
        self.record()

    def sync_learning(self, preserve_custom=False):
        if not preserve_custom or self.mode!='custom':
            self.mode=self.project.mode if self.project.mode==identify(self.current_function()) else 'custom'
        self.mode_selector.blockSignals(True)
        self.mode_selector.setCurrentIndex(self.mode_selector.findData(self.mode))
        self.mode_selector.blockSignals(False)
        self.project.mode=self.mode
        self.pages.setCurrentIndex(0 if self.mode in LABS else 1)
        if self.mode in LABS:
            function=self.current_function()
            values={c.name:function.parameters[c.name].value for c in LABS[self.mode].controls}
            self.learning.set_function(self.mode,values,PALETTES[self.preferences['theme']]['text'],self.preferences['precision'],function.visible)
        self.draw_lab_markers()

    def lab_coefficient_changed(self,name,value):
        function=self.current_function()
        if self.mode not in LABS or function is None:return
        control=next(c for c in LABS[self.mode].controls if c.name==name)
        value=control.clamp(value)
        function.parameters[name].value=value
        self.learning.update_values({c.name:function.parameters[c.name].value for c in LABS[self.mode].controls})
        self.dirty=True
        self.update_title()
        self.history_timer.start()
        self.invalidate_analysis()
        self.canvas.begin_interaction(only=function.id)
        self.canvas.schedule_refresh(only=function.id)

    def flush_history(self):
        if hasattr(self,'history_timer') and self.history_timer.isActive():
            self.history_timer.stop()
            self.record()

    def reset_coefficients(self):
        if self.mode in LABS:
            for c in LABS[self.mode].controls:self.lab_coefficient_changed(c.name,c.default)
            self.sync_learning()
            self.flush_history()

    def draw_lab_markers(self):
        if not hasattr(self,'learning'):return
        from PySide6.QtGui import QColor
        import pyqtgraph as pg
        if not hasattr(self,'lab_dots'):
            self.lab_dots=pg.ScatterPlotItem(size=8,pen=pg.mkPen('#FFFFFF',width=1))
            self.lab_axis=pg.InfiniteLine(angle=90,pen=pg.mkPen('#A87C42',width=1,style=Qt.DashLine))
            self.lab_domain=pg.LinearRegionItem(orientation='vertical',movable=False,brush=QColor(112,119,129,25),pen=pg.mkPen(None))
            self.lab_boundary=pg.InfiniteLine(angle=90,pen=pg.mkPen('#A87C42',width=1,style=Qt.DashLine))
            for item in [self.lab_dots,self.lab_axis,self.lab_domain,self.lab_boundary]:self.canvas.addItem(item,ignoreBounds=True)
            self.lab_domain.setZValue(-15)
            self.lab_labels=[pg.TextItem(anchor=(0,1)) for _ in range(4)]
            for label in self.lab_labels:self.canvas.addItem(label,ignoreBounds=True)
        for item in [self.lab_dots,self.lab_axis,self.lab_domain,self.lab_boundary,*self.lab_labels]:item.hide()
        function=self.current_function()
        if self.mode not in LABS or not function or not function.visible:
            self.graph_hint.setText('  x → праворуч    ·    y ↑ вгору')
            return
        values={n:p.value for n,p in function.parameters.items()}
        if self.mode=='logarithmic':
            h=values['h'];xmin,xmax=self.canvas.current_view()[:2]
            self.lab_domain.setRegion((xmin,max(xmin,min(h,xmax))))
            self.lab_domain.setVisible(h>xmin)
            self.lab_boundary.setPos(h);self.lab_boundary.show()
            self.graph_hint.setText(f"  Область визначення: x > {number(values['h'],self.preferences['precision'])} · сіра область не належить графіку")
        else:self.graph_hint.setText('  x → праворуч    ·    y ↑ вгору')
        if self.mode=='quadratic':
            data=markers(values,self.preferences['precision']);points=[]
            for key in ['vertex','zeros','intercept']:
                if self.learning.toggles[key].isChecked():points.extend(data[key])
            if self.learning.toggles['symmetry'].isChecked() and data['symmetry'] is not None:
                self.lab_axis.setPos(data['symmetry']);self.lab_axis.show()
            unique=[];seen=set()
            for point in points:
                coordinate=(point['x'],point['y'])
                if coordinate not in seen:
                    seen.add(coordinate);unique.append(point)
            points=unique
            self.lab_dots.setData([p['x'] for p in points],[p['y'] for p in points],brush=self.canvas.display_color(function.color))
            self.lab_dots.show()
            for label,point in zip(self.lab_labels,points):
                label.setText(point['exact'],color=PALETTES[self.preferences['theme']]['text'])
                label.setPos(point['x'],point['y']);label.show()
        if self.mode=='custom':self.graph_hint.setText('  x → праворуч    ·    y ↑ вгору')

    def current_function(self):
        return next((f for f in self.project.functions if f.id == self.project.selected), None)

    def flush_inputs(self):
        self.project.view = self.canvas.current_view()
        self.flush_history()
        for row in list(self.rows.values()):
            row.flush()

    def rebuild_editor(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.rows = {}
        for index, function in enumerate(self.project.functions):
            row = FunctionRow(function, index, PALETTES[self.preferences["theme"]]["text"])
            row.changed.connect(self.edit_function)
            row.selected.connect(self.select)
            row.visibility.connect(self.visibility)
            row.removed.connect(self.remove_function)
            row.duplicated.connect(self.duplicate)
            row.recolored.connect(self.recolor)
            row.set_selected(function.id == self.project.selected)
            self.rows[function.id] = row
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)
        self.rebuild_parameters()
        self.update_other_functions()
        self.sync_learning(preserve_custom=True)

    def rebuild_parameters(self):
        while self.parameter_layout.count():
            item = self.parameter_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        function = self.current_function()
        if not function:
            self.parameter_scroll.hide()
            return
        try:
            names = parse(function.expression).parameters
        except ExpressionError:
            names = ()
        for name in names:
            function.parameters.setdefault(name, Parameter())
        if not names:
            self.parameter_scroll.hide()
            return
        self.parameter_scroll.show()
        title = QLabel("ПАРАМЕТРИ ВИБРАНОЇ ФУНКЦІЇ")
        title.setObjectName("muted")
        self.parameter_layout.addWidget(title)
        for name in names:
            # Edit a copy so history snapshots retain the previous parameter value.
            control = ParameterControl(name, copy.deepcopy(function.parameters[name]))
            control.changed.connect(self.parameter_changed)
            control.slider.sliderReleased.connect(self.flush_history)
            control.value.editingFinished.connect(self.flush_history)
            self.parameter_layout.addWidget(control)

    def update_other_functions(self):
        previous = self.inspector.other.currentData()
        self.inspector.other.blockSignals(True)
        self.inspector.other.clear()
        self.inspector.other.addItem("Без другої функції", None)
        for i, f in enumerate(self.project.functions):
            if f.id != self.project.selected and f.visible:
                self.inspector.other.addItem(f"f{i + 1}(x) = {f.expression}", f.id)
        ix = self.inspector.other.findData(previous)
        self.inspector.other.setCurrentIndex(max(0, ix))
        self.inspector.other.blockSignals(False)

    def select(self, identifier):
        if identifier == self.project.selected:
            return
        self.project.selected = identifier
        for key, row in self.rows.items():
            row.set_selected(key == identifier)
        self.rebuild_parameters()
        self.update_other_functions()
        self.sync_learning(preserve_custom=True)
        self.invalidate_analysis()
        self.refresh_canvas()

    def refresh_canvas(self):
        displayed=self.project.functions if self.mode=='custom' else [self.current_function()] if self.current_function() else []
        self.canvas.update_functions(displayed, self.project.selected)
        self.canvas.set_grid_axes(self.project.grid, self.project.axes)
        self.grid_action.setChecked(self.project.grid)
        self.axes_action.setChecked(self.project.axes)
        function = self.current_function()
        self.active_label.setText('  Власна функція  ' if self.mode=='custom' else '  '+LABS[self.mode].title+'  ')
        self.draw_lab_markers()

    def edit_function(self, identifier, source):
        function = next(f for f in self.project.functions if f.id == identifier)
        function.expression = source
        self.rebuild_parameters()
        self.record()
        self.update_other_functions()
        self.invalidate_analysis()
        self.canvas.refresh(only=identifier)
        if identifier == self.project.selected:
            self.active_label.setText(f"  f(x) = {source[:45]}  ")

    def parameter_changed(self, name, parameter):
        function = self.current_function()
        if function:
            function.parameters[name] = copy.deepcopy(parameter)
            self.dirty=True
            self.update_title()
            self.history_timer.start()
            self.invalidate_analysis()
            self.canvas.begin_interaction(only=function.id)
            self.canvas.schedule_refresh(only=function.id)

    def add_function(self):
        self.flush_inputs()
        if len(self.project.functions) >= 100:
            QMessageBox.information(self, "Функції", "Досягнуто межу 100 функцій.")
            return
        colors = self.preferences["colors"]
        function = Function("x", colors[len(self.project.functions) % len(colors)])
        self.project.functions.append(function)
        self.project.selected = function.id
        self.after_structure_change()
        self.rows[function.id].input.setFocus()
        self.rows[function.id].input.selectAll()
        self.scroll.ensureWidgetVisible(self.rows[function.id])

    def duplicate(self, identifier):
        if len(self.project.functions) >= 100:
            return
        self.flush_inputs()
        function = copy.deepcopy(next(f for f in self.project.functions if f.id == identifier))
        import uuid
        function.id = uuid.uuid4().hex
        function.color = self.preferences["colors"][len(self.project.functions) % len(self.preferences["colors"])]
        self.project.functions.append(function)
        self.project.selected = function.id
        self.after_structure_change()

    def remove_function(self, identifier):
        self.flush_inputs()
        self.project.functions = [f for f in self.project.functions if f.id != identifier]
        if self.project.selected == identifier:
            self.project.selected = self.project.functions[-1].id if self.project.functions else None
        self.after_structure_change()

    def delete_selected(self):
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit):
            focus.del_()
            return
        if isinstance(focus, QAbstractSpinBox):
            focus.lineEdit().del_()
            return
        if self.project.selected:
            self.remove_function(self.project.selected)

    def visibility(self, identifier, state):
        next(f for f in self.project.functions if f.id == identifier).visible = state
        self.record()
        self.refresh_canvas()
        self.update_other_functions()
        self.sync_learning(preserve_custom=True)
        self.invalidate_analysis()

    def recolor(self, identifier, color):
        next(f for f in self.project.functions if f.id == identifier).color = color
        self.after_structure_change()

    def after_structure_change(self):
        self.mode='custom'
        self.rebuild_editor()
        self.record()
        self.invalidate_analysis()
        self.refresh_canvas()

    def insert_math(self, text, start, length):
        function = self.current_function()
        if not function:
            self.add_function()
            function = self.current_function()
        editor = self.rows[function.id].input
        position = editor.selectionStart() if editor.hasSelectedText() else editor.cursorPosition()
        editor.insert(text)
        editor.setFocus()
        editor.setSelection(position + start, length)
        self.rows[function.id].timer.start()

    def record(self):
        state = self.serialized()
        if state != self.history[self.history_index]:
            self.history = self.history[:self.history_index + 1]
            self.history.append(state)
            self.history = self.history[-100:]
            self.history_index = len(self.history) - 1
        self.dirty = state != self.saved_state
        self.update_title()

    def undo(self):
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit) and focus.isUndoAvailable():
            focus.undo()
            if self.project.selected in self.rows:
                self.rows[self.project.selected].timer.start()
            return
        self.flush_inputs()
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_history()

    def redo(self):
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit) and focus.isRedoAvailable():
            focus.redo()
            if self.project.selected in self.rows:
                self.rows[self.project.selected].timer.start()
            return
        self.flush_inputs()
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_history()

    def restore_history(self):
        self.project = from_dict(json.loads(self.history[self.history_index]))
        self.mode=self.project.mode if self.project.mode==identify(self.current_function()) else 'custom'
        self.loading = True
        self.rebuild_editor()
        self.canvas.set_view(self.project.view)
        self.loading = False
        self.invalidate_analysis()
        self.refresh_canvas()
        self.dirty = self.serialized() != self.saved_state
        self.update_title()

    def update_title(self):
        dirty = self.dirty
        filename = Path(self.path).name if self.path else "Без назви"
        title=f"{'● ' if dirty else ''}{filename} — MathLab 1.0"
        if title!=self.windowTitle():self.setWindowTitle(title)
        self.actions["undo"].setEnabled(True)
        self.actions["redo"].setEnabled(True)

    def confirm_discard(self):
        self.flush_inputs()
        if self.serialized() == self.saved_state:
            return True
        answer = QMessageBox.question(self, "Незбережені зміни", "Зберегти зміни у проєкті?",
                                       QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self.save_project()
        return answer == QMessageBox.Discard

    def new_project(self):
        if not self.confirm_discard():
            return
        self.project = default_project()
        self.project.grid,self.project.axes=self.preferences['grid'],self.preferences['axes']
        self.mode='quadratic'
        self.path = None
        self.reset_document()

    def reset_document(self):
        self.mode=self.project.mode if self.project.mode==identify(self.current_function()) else 'custom'
        self.loading = True
        self.rebuild_editor()
        self.canvas.set_view(self.project.view)
        self.loading = False
        self.saved_state = self.serialized()
        self.dirty = False
        self.history = [self.saved_state]
        self.history_index = 0
        self.invalidate_analysis()
        self.refresh_canvas()
        self.update_title()

    def open_project(self, path=None):
        if not self.confirm_discard():
            return False
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Відкрити проєкт", "", "Математичні проєкти (*.graphmath)", options=QFileDialog.DontUseNativeDialog)
        if not path:
            return False
        try:
            project = load(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Не вдалося відкрити проєкт", str(exc) if isinstance(exc,ValueError) else 'Не вдалося прочитати файл. Перевірте шлях і доступ до папки.')
            return False
        self.project, self.path = project, str(path)
        if not self.project.selected and self.project.functions:
            self.project.selected = self.project.functions[0].id
        self.reset_document()
        self.remember(path)
        return True

    def save_project(self, save_as=False):
        self.flush_inputs()
        path = self.path
        if save_as or not path:
            path, _ = QFileDialog.getSaveFileName(self, "Зберегти проєкт", path or "Дослідження.graphmath", "Математичні проєкти (*.graphmath)", options=QFileDialog.DontUseNativeDialog)
            if not path:
                return False
            if not path.endswith(".graphmath"):
                path += ".graphmath"
        try:
            save(self.project, path)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Не вдалося зберегти проєкт", str(exc) if isinstance(exc,ValueError) else 'Не вдалося записати файл. Перевірте доступ до папки та вільне місце.')
            return False
        self.path = path
        self.saved_state = self.serialized()
        self.dirty = False
        self.update_title()
        self.remember(path)
        self.statusBar().showMessage("Проєкт збережено", 2500)
        return True

    def remember(self, path):
        paths = self.recent_paths()
        paths = [str(path)] + [p for p in paths if p != str(path)]
        self.settings.setValue("recent", json.dumps(paths[:8], ensure_ascii=False))
        self.update_recents()

    def recent_paths(self):
        try:
            return json.loads(self.settings.value("recent", "[]"))
        except (ValueError, TypeError):
            return []

    def update_recents(self):
        self.recent_menu.clear()
        for path in self.recent_paths():
            self.recent_menu.addAction(path, lambda checked=False, p=path: self.open_project(p))
        self.recent_menu.setEnabled(bool(self.recent_paths()))

    def export(self):
        self.flush_inputs()
        dialog = ExportDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        ext = dialog.format.currentText().lower()
        path, _ = QFileDialog.getSaveFileName(self, "Експорт графіка", f"Графік.{ext}", f"{ext.upper()} (*.{ext})", options=QFileDialog.DontUseNativeDialog)
        if not path:
            return
        if not path.lower().endswith(f".{ext}"):
            path += f".{ext}"
        try:
            self.canvas.refresh()
            self.canvas.cross_x.hide()
            self.canvas.cross_y.hide()
            self.canvas.hover_dot.hide()
            export_graph(self.canvas, path, transparent=dialog.transparent.isChecked(), width=dialog.width.value())
            self.statusBar().showMessage(f"Графік експортовано: {Path(path).name}", 5000)
        except Exception:
            QMessageBox.warning(self, "Помилка експорту", 'Не вдалося експортувати графік. Спробуйте іншу папку або формат.')
        finally:
            self.canvas.set_coordinates(self.preferences['coordinates'])

    def set_theme(self, name):
        self.preferences["theme"] = name
        apply_theme(QApplication.instance(), name)
        scale = int(self.preferences["scale"].rstrip("%")) / 100
        if scale != 1:
            stylesheet = QApplication.instance().styleSheet().replace("font-size: 13px", f"font-size: {round(13 * scale)}px")
            QApplication.instance().setStyleSheet(stylesheet)
        self.canvas.set_theme(name)
        c = PALETTES[name]
        for key in self.actions:
            if key in PATHS:
                self.actions[key].setIcon(icon(key, c["text"]))
        if self.rows:
            for row in self.rows.values():
                row.text_color = c["text"]
                row.render()
        self.canvas.set_grid_axes(self.project.grid, self.project.axes)
        displayed=self.project.functions if self.mode=='custom' else [self.current_function()] if self.current_function() else []
        self.canvas.update_functions(displayed, self.project.selected)
        self.draw_annotations()
        self.sync_learning(preserve_custom=True)

    def toggle_theme(self):
        self.set_theme("dark" if self.preferences["theme"] == "light" else "light")
        self.save_preferences()

    def save_preferences(self):
        self.settings.setValue("preferences", json.dumps(self.preferences))

    def show_settings(self):
        values = {**self.preferences, "grid": self.project.grid, "axes": self.project.axes}
        dialog = SettingsDialog(self, values)
        if dialog.exec() == QDialog.Accepted:
            self.preferences = dialog.values
            self.project.grid, self.project.axes = self.preferences["grid"], self.preferences["axes"]
            self.canvas.set_coordinates(self.preferences['coordinates'])
            self.cursor_label.setVisible(self.preferences['coordinates'])
            self.set_theme(self.preferences["theme"])
            self.record()
            self.save_preferences()

    def set_grid(self, state):
        self.project.grid = state
        self.canvas.set_grid_axes(state, self.project.axes)
        self.record()

    def set_axes(self, state):
        self.project.axes = state
        self.canvas.set_grid_axes(self.project.grid, state)
        self.record()

    def view_changed(self, view):
        self.scale_label.setText(f"  x: {view[0]:.3g} … {view[1]:.3g}  ")
        if not self.loading and not np.allclose(self.project.view, view, rtol=1e-10, atol=1e-10):
            self.project.view = view
            self.dirty = True
            self.update_title()
        if self.inspector.toggles["tangent"].isChecked():
            self.draw_annotations()
        self.draw_lab_markers()

    def cursor_moved(self, x, y):
        precision = self.preferences["precision"]
        self.cursor_label.setText(f"  x  {x:.{precision}g}     y  {y:.{precision}g}")

    def toggle_inspector(self):
        self.inspector_dock.setVisible(not self.inspector_dock.isVisible())
        if self.inspector_dock.isVisible():
            self.resizeDocks([self.inspector_dock], [300], Qt.Horizontal)

    def invalidate_analysis(self, *_):
        self.inspector.invalidate()
        self.canvas.clear_annotations()
        self.draw_annotations()

    def investigate(self):
        self.flush_inputs()
        function = self.current_function()
        if not function:
            return
        try:
            parse(function.expression)
        except ExpressionError as exc:
            self.inspector.status.setText(str(exc))
            return
        other = next((f for f in self.project.functions if f.id == self.inspector.other.currentData()), None)
        self.inspector.start(function.expression, {k: p.value for k, p in function.parameters.items()},
                             other.expression if other else None, {k: p.value for k, p in other.parameters.items()} if other else None)

    def draw_annotations(self):
        if not hasattr(self, "inspector"):
            return
        self.canvas.clear_annotations()
        result = self.inspector.result
        if result:
            for key, color in [("zeros", "#248568"), ("extrema", "#A65AB5"), ("intersections", "#D15C46")]:
                if self.inspector.toggles[key].isChecked():
                    self.canvas.mark_points(result[key], color)
            if self.inspector.toggles["asymptotes"].isChecked():
                for key, vertical in [("vertical", True), ("horizontal", False)]:
                    for item in result[key]:
                        self.canvas.mark_line(item["value"], vertical, "#8B8392")
        if self.inspector.toggles["tangent"].isChecked():
            function = self.current_function()
            if function:
                try:
                    slope = self.canvas.tangent(function.expression, {n: p.value for n, p in function.parameters.items()}, self.inspector.point.value())
                    if slope is None:
                        self.statusBar().showMessage("У цій точці дотична не визначена або не підтверджена.", 2500)
                except Exception:
                    pass

    def help(self):
        QMessageBox.information(self, "Синтаксис і керування", "Введення: x^2, 2^x, sqrt(x), root(x,3), log(x,2), ln(x),\nsin(x), cos(x), tan(x), abs(x), exp(x), pi, e.\nМноження: 2x або 2*x; також підтримано x². Тригонометрія у радіанах.\nПараметри: a*x^2+b*x+c; для кожної функції окремо.\n\nКолесо миші — масштаб; перетягування — панорама.\nКлацніть криву або рядок, щоб вибрати функцію.\nCtrl+B — панель функцій, Ctrl+I — дослідження.\n\nСимвольний аналіз має обмеження 8 секунд.\nНевизначені результати позначаються явно.\nСкінченна вибірка може пропустити надто вузькі особливості;\nзбільшіть потрібну область для перевірки.")

    def closeEvent(self, event):
        if self.confirm_discard():
            self.inspector.cancel()
            self.save_preferences()
            event.accept()
        else:
            event.ignore()
