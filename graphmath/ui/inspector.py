from __future__ import annotations
import multiprocessing as mp
import time
from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea,
                               QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout)
from graphmath.analysis.symbolic import worker


class Inspector(QWidget):
    annotations_changed = Signal()
    investigate = Signal()

    def __init__(self):
        super().__init__()
        self.result = None
        self.process = None
        self.connection = None
        layout = QVBoxLayout(self)
        title = QLabel("ВЛАСТИВОСТІ ТА ОРІЄНТИРИ")
        title.setObjectName("muted")
        layout.addWidget(title)
        self.other = QComboBox()
        self.other.setToolTip("Друга функція для обчислення перетинів")
        layout.addWidget(self.other)
        self.run = QPushButton("Дослідити функцію")
        self.run.clicked.connect(self.investigate)
        layout.addWidget(self.run)
        self.status = QLabel("Виберіть функцію та запустіть дослідження.")
        self.status.setWordWrap(True)
        self.status.setObjectName("muted")
        layout.addWidget(self.status)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.properties = QVBoxLayout(content)
        self.properties.setContentsMargins(2, 4, 2, 4)
        self.properties.setSpacing(10)
        self.properties.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        self.toggles = {}
        for key, text in [("zeros", "Нулі"), ("extrema", "Екстремуми"), ("intersections", "Перетини функцій"), ("asymptotes", "Асимптоти"), ("tangent", "Дотична (наближено)")]:
            toggle = QCheckBox(text)
            toggle.toggled.connect(self.annotations_changed)
            self.toggles[key] = toggle
            layout.addWidget(toggle)
        tangent_form = QFormLayout()
        self.point = QDoubleSpinBox()
        self.point.setRange(-1e6, 1e6)
        self.point.setDecimals(4)
        self.point.setSingleStep(0.1)
        self.point.valueChanged.connect(self.annotations_changed)
        tangent_form.addRow("Дотична в x =", self.point)
        layout.addLayout(tangent_form)
        self.timer = QTimer(self)
        self.timer.setInterval(70)
        self.timer.timeout.connect(self.poll)

    def invalidate(self):
        self.cancel()
        self.result = None
        self.status.setText("Функція змінилася. Запустіть дослідження знову.")
        self.clear_properties()

    def clear_properties(self):
        while self.properties.count() > 1:
            item = self.properties.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def start(self, source, parameters, other, other_parameters):
        self.cancel()
        self.result = None
        self.clear_properties()
        self.status.setText("Обчислення… (до 8 секунд)")
        self.run.setEnabled(False)
        self.connection, send = mp.get_context("spawn").Pipe(duplex=False)
        self.process = mp.get_context("spawn").Process(target=worker, args=(send, source, parameters, other, other_parameters), daemon=True)
        self.process.start()
        send.close()
        self.started = time.monotonic()
        self.timer.start()

    def poll(self):
        if self.connection and self.connection.poll():
            try:
                message = self.connection.recv()
            except EOFError:
                message = {"error": "Не вдалося завершити дослідження."}
            self.cancel()
            if "result" in message:
                self.result = message["result"]
                self.status.setText("Точні символьні результати · координати маркерів наближені")
                for title, value in self.result.get("display_properties",self.result["properties"]).items():
                    label = QLabel(f"{title}\n{value}")
                    label.setTextFormat(Qt.PlainText)
                    label.setWordWrap(True)
                    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    self.properties.insertWidget(self.properties.count() - 1, label)
                self.annotations_changed.emit()
            else:
                self.status.setText(message["error"])
        elif self.process and (time.monotonic() - self.started > 8 or not self.process.is_alive()):
            self.cancel()
            self.status.setText("Не вдалося визначити автоматично за відведений час. Спростіть вираз.")

    def cancel(self):
        self.timer.stop()
        if self.process:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=0.2)
            self.process.close()
            self.process = None
        if self.connection:
            self.connection.close()
            self.connection = None
        self.run.setEnabled(True)
