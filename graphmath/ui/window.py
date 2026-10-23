from __future__ import annotations
import copy
import json
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt, QSettings, QSize, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QDockWidget, QScrollArea, QPushButton, QLabel, QToolBar, QToolButton, QFileDialog,
    QMessageBox, QLineEdit, QAbstractSpinBox, QMenu, QDialog)
from graphmath.core.expressions import parse, ExpressionError
from graphmath.persistence.projects import Project, Function, Parameter, COLORS, from_dict, save, load
from graphmath.plotting.export import export_graph
from graphmath.ui.canvas import Canvas
from graphmath.ui.editor import FunctionRow, ParameterControl
from graphmath.ui.inspector import Inspector
from graphmath.ui.dialogs import SettingsDialog, ExportDialog
from graphmath.ui.theme import apply_theme, PALETTES
from graphmath.ui.icons import icon, PATHS


class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings("GraphMath", "GraphMath")
        defaults = {"theme": "light", "precision": 5, "scale": "100%", "colors": COLORS,
                    "default_view": [-8, 8, -5, 7], "grid": True, "axes": True}
        try:
            self.preferences = {**defaults, **json.loads(self.settings.value("preferences", "{}"))}
            if self.preferences["theme"] not in PALETTES:
                self.preferences["theme"] = "light"
        except (ValueError, TypeError):
            self.preferences = defaults
        self.project = Project()
        self.project.view = list(self.preferences["default_view"])
        self.project.grid = self.preferences["grid"]
        self.project.axes = self.preferences["axes"]
        self.project.selected = self.project.functions[0].id
        self.path = None
        self.saved_state = self.serialized()
        self.history = [self.serialized()]
        self.history_index = 0
        self.loading = False
        self.rows = {}
        self.actions = {}
        self.setWindowTitle("GraphMath 1.0")
        self.resize(1400, 850)
        self.setMinimumSize(780, 540)
        self.canvas = Canvas()
        self.setCentralWidget(self.canvas)
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
        self.resizeDocks([self.editor_dock], [290], Qt.Horizontal)
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
        self.editor_dock.setWidget(container)
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
            ("reset", "Скинути вигляд", "Ctrl+0", lambda: self.canvas.set_view(self.preferences["default_view"])),
            ("fit", "Вмістити вибрану функцію", "", self.canvas.fit_selected),
            ("export", "Експорт графіка…", "Ctrl+E", self.export),
            ("theme", "Змінити тему", "", self.toggle_theme),
            ("settings", "Налаштування…", "", self.show_settings),
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
        help_menu.addAction("Про GraphMath", lambda: QMessageBox.about(self, "GraphMath 1.0", "GraphMath 1.0.0\nМатематичний простір для досліджень.\nПрацює офлайн · ліцензія MIT\n\nQt / PySide6 (LGPLv3), PyQtGraph (MIT), SymPy (BSD),\nNumPy (BSD), Matplotlib (PSF-compatible).\nПовні ліцензії постачаються з програмою."))

    def create_toolbar(self):
        toolbar = QToolBar("Інструменти", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)
        brand = QLabel("  GraphMath  ")
        brand.setStyleSheet("font-size: 15px; font-weight: 600;")
        toolbar.addWidget(brand)
        toolbar.addSeparator()
        for key in ["new", "open", "save", "|", "undo", "redo", "|", "zoom_in", "zoom_out", "reset", "fit", "|", "export", "panel", "analysis"]:
            if key == "|":
                toolbar.addSeparator()
            else:
                toolbar.addAction(self.actions[key])
        spacer = QWidget()
        from PySide6.QtWidgets import QSizePolicy
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
        toolbar.addAction(self.actions["theme"])
        toolbar.addAction(self.actions["settings"])

    def current_function(self):
        return next((f for f in self.project.functions if f.id == self.project.selected), None)

    def flush_inputs(self):
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
        self.invalidate_analysis()
        self.refresh_canvas()

    def refresh_canvas(self):
        self.canvas.update_functions(self.project.functions, self.project.selected)
        self.canvas.set_grid_axes(self.project.grid, self.project.axes)
        self.grid_action.setChecked(self.project.grid)
        self.axes_action.setChecked(self.project.axes)
        function = self.current_function()
        self.active_label.setText(f"  f(x) = {function.expression[:45]}  " if function else "")

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
            self.record()
            self.invalidate_analysis()
            self.canvas.refresh(only=function.id)

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
        self.invalidate_analysis()

    def recolor(self, identifier, color):
        next(f for f in self.project.functions if f.id == identifier).color = color
        self.after_structure_change()

    def after_structure_change(self):
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
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_history()

    def restore_history(self):
        self.project = from_dict(json.loads(self.history[self.history_index]))
        self.loading = True
        self.rebuild_editor()
        self.canvas.set_view(self.project.view)
        self.loading = False
        self.invalidate_analysis()
        self.refresh_canvas()
        self.update_title()

    def update_title(self):
        dirty = self.serialized() != self.saved_state
        filename = Path(self.path).name if self.path else "Без назви"
        self.setWindowTitle(f"{'● ' if dirty else ''}{filename} — GraphMath 1.0")
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
        self.project = Project(functions=[], view=list(self.preferences["default_view"]),
                               grid=self.preferences["grid"], axes=self.preferences["axes"])
        self.path = None
        self.reset_document()

    def reset_document(self):
        self.loading = True
        self.rebuild_editor()
        self.canvas.set_view(self.project.view)
        self.loading = False
        self.saved_state = self.serialized()
        self.history = [self.saved_state]
        self.history_index = 0
        self.invalidate_analysis()
        self.refresh_canvas()
        self.update_title()

    def open_project(self, path=None):
        if not self.confirm_discard():
            return False
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Відкрити проєкт", "", "GraphMath (*.graphmath)")
        if not path:
            return False
        try:
            project = load(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Не вдалося відкрити проєкт", str(exc))
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
            path, _ = QFileDialog.getSaveFileName(self, "Зберегти проєкт", path or "Дослідження.graphmath", "GraphMath (*.graphmath)")
            if not path:
                return False
            if not path.endswith(".graphmath"):
                path += ".graphmath"
        try:
            save(self.project, path)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Не вдалося зберегти проєкт", str(exc))
            return False
        self.path = path
        self.saved_state = self.serialized()
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
        path, _ = QFileDialog.getSaveFileName(self, "Експорт графіка", f"Графік.{ext}", f"{ext.upper()} (*.{ext})")
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
        except Exception as exc:
            QMessageBox.warning(self, "Помилка експорту", str(exc))
        finally:
            self.canvas.cross_x.show()
            self.canvas.cross_y.show()
            self.canvas.hover_dot.show()

    def set_theme(self, name):
        self.preferences["theme"] = name
        apply_theme(QApplication.instance(), name)
        scale = int(self.preferences["scale"].rstrip("%")) / 100
        if scale != 1:
            stylesheet = QApplication.instance().styleSheet().replace("font-size: 12px", f"font-size: {round(12 * scale)}px")
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
        self.canvas.update_functions(self.project.functions, self.project.selected)
        self.draw_annotations()

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
            self.canvas.set_view(self.preferences["default_view"])
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
        if not self.loading:
            self.project.view = view
            self.update_title()
        if self.inspector.toggles["tangent"].isChecked():
            self.draw_annotations()

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
        QMessageBox.information(self, "Синтаксис і керування", "Введення: x^2, 2^x, sqrt(x), root(x,3), log(x,2), ln(x),\nsin(x), cos(x), tan(x), abs(x), exp(x), pi, e.\nМноження: 2*x (не 2x). Тригонометрія у радіанах.\nПараметри: a*x^2+b*x+c; для кожної функції окремо.\n\nКолесо миші — масштаб; перетягування — панорама.\nКлацніть криву або рядок, щоб вибрати функцію.\nCtrl+B — панель функцій, Ctrl+I — дослідження.\n\nСимвольний аналіз має обмеження 8 секунд.\nНевизначені результати позначаються явно.\nСкінченна вибірка може пропустити надто вузькі особливості;\nзбільшіть потрібну область для перевірки.")

    def closeEvent(self, event):
        if self.confirm_discard():
            self.inspector.cancel()
            self.save_preferences()
            event.accept()
        else:
            event.ignore()
