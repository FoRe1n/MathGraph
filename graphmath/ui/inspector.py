from __future__ import annotations
import multiprocessing as mp
import time
import logging
from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea,
                               QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout)
from graphmath.analysis.symbolic import worker

logger = logging.getLogger(__name__)


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
        if not self.cancel():
            self.status.setText("Не вдалося зупинити попереднє дослідження. Спробуйте ще раз.")
            return
        self.result = None
        self.clear_properties()
        self.status.setText("Обчислення… (до 8 секунд)")
        self.run.setEnabled(False)
        send = None
        try:
            context = mp.get_context("spawn")
            self.connection, send = context.Pipe(duplex=False)
            self.process = context.Process(target=worker, args=(send, source, parameters, other, other_parameters), daemon=True)
            self.process.start()
        except (OSError, RuntimeError, ValueError):
            logger.exception("Failed to start the symbolic analysis process")
            self.cancel()
            self.status.setText("Не вдалося запустити дослідження. Спробуйте ще раз.")
            return
        finally:
            if send is not None:
                send.close()
        self.started = time.monotonic()
        self.timer.start()

    def poll(self):
        try:
            available = self.connection is not None and self.connection.poll()
        except (EOFError, OSError):
            logger.exception("Analysis pipe closed before a result was available")
            self.cancel()
            self.status.setText("Не вдалося завершити дослідження. Спробуйте ще раз.")
            return
        if available:
            try:
                message = self.connection.recv()
            except (EOFError, OSError):
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
        """Stop and reap the worker, including partially started processes."""
        self.timer.stop()
        stopped = True
        if self.process is not None:
            process = self.process
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=0.2)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=0.2)
                stopped = not process.is_alive()
            if stopped:
                process.close()
                self.process = None
            else:
                # Keep the handle so a later cancel can reap it; closing a live
                # multiprocessing.Process raises and loses its cleanup path.
                logger.error("Analysis worker did not exit after termination")
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self.run.setEnabled(True)
        return stopped
