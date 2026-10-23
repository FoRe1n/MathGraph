from __future__ import annotations
from PySide6.QtWidgets import (QDialog, QFormLayout, QComboBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QLineEdit, QDialogButtonBox, QLabel, QVBoxLayout, QFileDialog, QWidget, QPushButton)
import re


class SettingsDialog(QDialog):
    def __init__(self, parent, values):
        super().__init__(parent)
        self.setWindowTitle("Налаштування MathLab")
        self.setMinimumWidth(380)
        layout = QFormLayout(self)
        self.theme = QComboBox()
        self.theme.addItems(["Світла", "Темна"])
        self.theme.setCurrentIndex(values["theme"] == "dark")
        layout.addRow("Тема", self.theme)
        self.grid = QCheckBox("Показувати сітку")
        self.grid.setChecked(values["grid"])
        layout.addRow(self.grid)
        self.coordinates=QCheckBox('Показувати координати курсора')
        self.coordinates.setChecked(values.get('coordinates',False))
        layout.addRow(self.coordinates)
        advanced_button=QPushButton('Додаткові налаштування ▾')
        advanced_button.setCheckable(True)
        layout.addRow(advanced_button)
        advanced=QWidget()
        advanced_layout=QFormLayout(advanced)
        layout.addRow(advanced)
        advanced.hide()
        advanced_button.toggled.connect(advanced.setVisible)
        self.axes = QCheckBox("Показувати осі")
        self.axes.setChecked(values["axes"])
        advanced_layout.addRow(self.axes)
        self.precision = QSpinBox()
        self.precision.setRange(2, 10)
        self.precision.setValue(values["precision"])
        layout.addRow("Значущі цифри", self.precision)
        self.scale = QComboBox()
        self.scale.addItems(["100%", "115%", "130%", "150%"])
        self.scale.setCurrentText(values["scale"])
        advanced_layout.addRow("Масштаб тексту", self.scale)
        self.colors = QLineEdit(", ".join(values["colors"]))
        self.colors.setToolTip("Кольори нових функцій у форматі #RRGGBB, через кому")
        advanced_layout.addRow("Палітра функцій", self.colors)
        self.ranges = []
        for label, value in zip(["x мін.", "x макс.", "y мін.", "y макс."], values["default_view"]):
            spin = QDoubleSpinBox()
            spin.setRange(-1e6, 1e6)
            spin.setDecimals(3)
            spin.setValue(value)
            self.ranges.append(spin)
            advanced_layout.addRow(label, spin)
        hint = QLabel("Діапазон застосовується до поточного графіка та скидання виду.")
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        advanced_layout.addRow(hint)
        reset=QPushButton('Повернути типові налаштування')
        reset.clicked.connect(self.reset_defaults)
        layout.addRow(reset)
        self.error = QLabel()
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        layout.addRow(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def reset_defaults(self):
        from graphmath.persistence.projects import COLORS
        self.theme.setCurrentIndex(0)
        self.grid.setChecked(True);self.axes.setChecked(True);self.coordinates.setChecked(False)
        self.precision.setValue(5);self.scale.setCurrentText('100%')
        self.colors.setText(', '.join(COLORS))
        for spin,value in zip(self.ranges,[-6,6,-3,9]):spin.setValue(value)

    def validate(self):
        view = [s.value() for s in self.ranges]
        colors = [c.strip() for c in self.colors.text().split(",")]
        if view[0] >= view[1] or view[2] >= view[3] or not 1 <= len(colors) <= 20 or any(not re.fullmatch("#[0-9a-fA-F]{6}", c) for c in colors):
            self.error.setText("Перевірте діапазони та кольори (#RRGGBB).")
            return
        self.values = {"theme": "dark" if self.theme.currentIndex() else "light", "grid": self.grid.isChecked(),
                       "axes": self.axes.isChecked(), "precision": self.precision.value(),
                       "scale": self.scale.currentText(), "colors": colors, "default_view": view,
                       "coordinates":self.coordinates.isChecked()}
        self.accept()


class ExportDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Експорт графіка")
        layout = QFormLayout(self)
        self.format = QComboBox()
        self.format.addItems(["PNG", "SVG", "PDF"])
        layout.addRow("Формат", self.format)
        self.width = QSpinBox()
        self.width.setRange(800, 8000)
        self.width.setValue(2400)
        self.width.setSingleStep(400)
        layout.addRow("Ширина (px, PNG / SVG)", self.width)
        self.transparent = QCheckBox("Прозоре тло (PNG)")
        layout.addRow(self.transparent)
        self.format.currentTextChanged.connect(lambda value: self.transparent.setEnabled(value == "PNG"))
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
