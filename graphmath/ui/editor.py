from __future__ import annotations
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLineEdit, QToolButton,
                               QLabel, QMenu, QColorDialog, QWidget, QSlider, QDoubleSpinBox,
                               QPushButton, QDialog, QFormLayout, QDialogButtonBox, QAbstractSpinBox)
from graphmath.core.expressions import parse, ExpressionError
from graphmath.persistence.projects import Function, Parameter
from graphmath.ui.formula import FormulaLabel


class FunctionRow(QFrame):
    changed = Signal(str, str)
    selected = Signal(str)
    visibility = Signal(str, bool)
    removed = Signal(str)
    duplicated = Signal(str)
    recolored = Signal(str, str)

    def __init__(self, function: Function, index: int, text_color: str):
        super().__init__()
        self.function = function
        self.text_color = text_color
        self.setObjectName("functionRow")
        self.setProperty("selected", False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 8, 6)
        layout.setSpacing(3)
        top = QHBoxLayout()
        self.color = QToolButton()
        self.color.setText("●")
        self.color.setStyleSheet(f"color: {function.color}; font-size: 19px;")
        self.color.setToolTip("Колір функції")
        self.color.clicked.connect(self.choose_color)
        self.eye = QToolButton()
        self.eye.setText("✓")
        self.eye.setCheckable(True)
        self.eye.setChecked(function.visible)
        self.eye.setToolTip("Показати / приховати функцію")
        self.eye.toggled.connect(lambda state: self.visibility.emit(function.id, state))
        label = QLabel(f"f{index + 1}(x)")
        label.setObjectName("muted")
        more = QToolButton()
        more.setText("⋯")
        more.setToolTip("Дії з функцією")
        menu = QMenu(more)
        menu.addAction("Дублювати", lambda: self.duplicated.emit(function.id))
        menu.addAction("Видалити", lambda: self.removed.emit(function.id))
        more.setMenu(menu)
        more.setPopupMode(QToolButton.InstantPopup)
        top.addWidget(self.color)
        top.addWidget(label)
        top.addStretch()
        top.addWidget(self.eye)
        top.addWidget(more)
        layout.addLayout(top)
        self.input = QLineEdit(function.expression)
        self.input.setMaxLength(600)
        self.input.setPlaceholderText("y = x^2 − 4")
        self.input.setAccessibleName(f"Вираз функції {index + 1}")
        self.input.installEventFilter(self)
        layout.addWidget(self.input)
        self.preview = FormulaLabel()
        layout.addWidget(self.preview)
        self.error = QLabel()
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.commit)
        self.input.textEdited.connect(lambda: self.timer.start())
        self.input.editingFinished.connect(self.flush)
        self.render()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self.input and event.type() == QEvent.FocusIn:
            self.selected.emit(self.function.id)
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        self.selected.emit(self.function.id)
        super().mousePressEvent(event)

    def set_selected(self, selected):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def choose_color(self):
        color = QColorDialog.getColor(self.function.color, self, "Колір функції", options=QColorDialog.DontUseNativeDialog)
        if color.isValid():
            self.recolored.emit(self.function.id, color.name())

    def render(self):
        try:
            parse(self.input.text())
            self.error.hide()
            self.preview.update_expression(self.input.text(), self.text_color)
        except ExpressionError as exc:
            self.error.setText(str(exc))
            self.error.show()
            self.preview.clear()

    def flush(self):
        if self.timer.isActive():
            self.timer.stop()
            self.commit()

    def commit(self):
        self.render()
        if self.input.text() != self.function.expression:
            self.changed.emit(self.function.id, self.input.text())


class ParameterControl(QWidget):
    changed = Signal(str, object)

    def __init__(self, name: str, parameter: Parameter):
        super().__init__()
        self.name, self.parameter = name, parameter
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 8)
        top = QHBoxLayout()
        top.addWidget(QLabel(name))
        self.value = QDoubleSpinBox()
        self.value.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.value.setDecimals(5)
        self.value.setRange(parameter.minimum, parameter.maximum)
        self.value.setSingleStep(parameter.step)
        self.value.setValue(parameter.value)
        self.value.setKeyboardTracking(False)
        self.value.setMaximumWidth(110)
        top.addWidget(self.value)
        top.addStretch()
        reset = QToolButton()
        reset.setText("↺")
        reset.setToolTip("Початкове значення")
        reset.clicked.connect(lambda: self.value.setValue(parameter.initial))
        settings = QToolButton()
        settings.setText("⋯")
        settings.setToolTip("Межі та крок параметра")
        settings.clicked.connect(self.configure)
        top.addWidget(reset)
        top.addWidget(settings)
        outer.addLayout(top)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, round((parameter.maximum - parameter.minimum) / parameter.step))
        self.slider.setValue(round((parameter.value - parameter.minimum) / parameter.step))
        self.slider.setToolTip(f"{parameter.minimum:g} … {parameter.maximum:g}; крок {parameter.step:g}")
        outer.addWidget(self.slider)
        self.slider.valueChanged.connect(self.slide)
        self.value.valueChanged.connect(self.spin)

    def slide(self, tick):
        self.value.setValue(min(self.parameter.maximum, self.parameter.minimum + tick * self.parameter.step))

    def spin(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(round((value - self.parameter.minimum) / self.parameter.step))
        self.slider.blockSignals(False)
        self.parameter.value = value
        self.changed.emit(self.name, self.parameter)

    def configure(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Параметр {self.name}")
        layout = QFormLayout(dialog)
        fields = {}
        for key, label in [("minimum", "Мінімум"), ("maximum", "Максимум"), ("step", "Крок")]:
            box = QDoubleSpinBox()
            box.setDecimals(5)
            box.setRange(0.00001 if key == "step" else -1e6, 1e6)
            box.setValue(getattr(self.parameter, key))
            fields[key] = box
            layout.addRow(label, box)
        error = QLabel()
        error.setObjectName("error")
        layout.addRow(error)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addRow(buttons)
        buttons.rejected.connect(dialog.reject)
        def accept():
            lo, hi, step = (fields[k].value() for k in ["minimum", "maximum", "step"])
            if hi <= lo or step > hi - lo or (hi - lo) / step > 100000:
                error.setText("Перевірте межі та крок (до 100 000 кроків).")
                return
            self.parameter.minimum, self.parameter.maximum, self.parameter.step = lo, hi, step
            self.parameter.value = max(lo, min(hi, self.parameter.value))
            self.parameter.initial = max(lo, min(hi, self.parameter.initial))
            dialog.accept()
        buttons.accepted.connect(accept)
        if dialog.exec():
            self.changed.emit(self.name, self.parameter)
            self.slider.setRange(0, round((self.parameter.maximum - self.parameter.minimum) / self.parameter.step))
            self.value.setRange(self.parameter.minimum, self.parameter.maximum)
            self.value.setSingleStep(self.parameter.step)
            self.value.setValue(self.parameter.value)
