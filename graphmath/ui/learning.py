from __future__ import annotations
from html import escape
import re
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QSlider,QDoubleSpinBox,
    QAbstractSpinBox,QPushButton,QCheckBox,QGridLayout,QMessageBox,QSizePolicy,QLayout)
from graphmath.core.laboratories import LABS, Control, explanation, details, number, formula_latex
from graphmath.ui.formula import FormulaLabel
from graphmath.ui.theme import PALETTES


class CoefficientControl(QWidget):
    changed=Signal(str,float)
    finished=Signal()

    def __init__(self, control: Control, value: float):
        super().__init__()
        self.control=control
        self.ticks=control.values()
        layout=QVBoxLayout(self);layout.setContentsMargins(0,8,0,10);layout.setSpacing(9)
        row=QHBoxLayout();row.setSpacing(12)
        self.label=QLabel(control.label);self.label.setWordWrap(True)
        self.label.setMinimumWidth(0)
        # Keep QLabel's height-for-width flag when relaxing its width hint;
        # replacing the policy discards that flag and can compress long labels.
        policy=self.label.sizePolicy();policy.setHorizontalPolicy(QSizePolicy.Ignored)
        self.label.setSizePolicy(policy)
        row.addWidget(self.label,1)
        self.value=QDoubleSpinBox()
        self.value.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.value.setDecimals(1);self.value.setRange(control.minimum,control.maximum)
        self.value.setSingleStep(control.step);self.value.setValue(value)
        self.value.setMinimumWidth(60);self.value.setMaximumWidth(90);self.value.setKeyboardTracking(False)
        self.value.setAccessibleName(f'Змінити коефіцієнт {control.name}')
        row.addWidget(self.value);layout.addLayout(row)
        self.slider=QSlider(Qt.Horizontal)
        self.slider.setMinimumHeight(22)
        self.slider.setRange(0,len(self.ticks)-1)
        self.slider.setValue(min(range(len(self.ticks)),key=lambda i:abs(self.ticks[i]-value)))
        self.slider.setAccessibleName(f'Повзунок коефіцієнта {control.name}')
        layout.addWidget(self.slider)
        self.slider.valueChanged.connect(lambda tick:self.value.setValue(self.ticks[tick]))
        self.value.valueChanged.connect(self.spin)
        self.value.editingFinished.connect(self.finished)
        self.slider.sliderReleased.connect(self.finished)
        self.value.setToolTip('Додатна основа, відмінна від 1. Значення 1 автоматично замінюється на 1,1.' if control.base else 'Горизонтальний масштаб не може дорівнювати нулю; 0 замінюється на 0,1.' if control.nonzero else f'Від {number(control.minimum)} до {number(control.maximum)}; крок {number(control.step)}')

    def spin(self,value):
        safe=self.control.clamp(value)
        self.value.blockSignals(True);self.value.setValue(safe);self.value.blockSignals(False)
        self.slider.blockSignals(True);self.slider.setValue(self.ticks.index(safe));self.slider.blockSignals(False)
        self.changed.emit(self.control.name,safe)

    def set_value(self,value):
        self.value.blockSignals(True);self.value.setValue(value);self.value.blockSignals(False)
        self.slider.blockSignals(True)
        self.slider.setValue(min(range(len(self.ticks)),key=lambda i:abs(self.ticks[i]-value)))
        self.slider.blockSignals(False)


class LearningPanel(QWidget):
    coefficient_changed=Signal(str,float)
    finished=Signal()
    reset_requested=Signal()
    markers_changed=Signal()
    visibility_requested=Signal()

    def __init__(self):
        super().__init__()
        self.key=None;self.controls={};self.values={};self.color=PALETTES['light']['text']
        layout=QVBoxLayout(self);layout.setContentsMargins(16,6,16,10);layout.setSpacing(8)
        layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.formula=FormulaLabel();self.formula.setMinimumHeight(52)
        layout.addWidget(self.formula)
        self.numeric=FormulaLabel()
        self.numeric.setToolTip('Формула з поточними коефіцієнтами')
        layout.addWidget(self.numeric)
        self.show_graph=QPushButton('Показати прихований графік')
        self.show_graph.clicked.connect(self.visibility_requested)
        self.show_graph.hide()
        layout.addWidget(self.show_graph)
        self.controls_layout=QVBoxLayout();self.controls_layout.setSpacing(4)
        layout.addLayout(self.controls_layout)
        self.explanation=QLabel();self.explanation.setWordWrap(True)
        self.explanation.setTextFormat(Qt.RichText)
        self.explanation.setAlignment(Qt.AlignLeft|Qt.AlignTop)
        self.explanation.setContentsMargins(0,10,0,4)
        layout.addWidget(self.explanation)
        more=QPushButton('Докладніше');more.clicked.connect(self.show_details)
        more.setStyleSheet('text-align: left; padding-left: 0;')
        layout.addWidget(more)
        self.marker_button=QPushButton('Орієнтири на графіку ▾');self.marker_button.setCheckable(True)
        self.marker_button.toggled.connect(lambda show:self.marker_panel.setVisible(show))
        layout.addWidget(self.marker_button)
        self.marker_panel=QWidget();grid=QGridLayout(self.marker_panel);grid.setContentsMargins(0,0,0,0)
        self.toggles={}
        for i,(key,title) in enumerate([('vertex','Вершина'),('symmetry','Вісь симетрії'),('zeros','Нулі функції'),('intercept','Перетин із віссю y')]):
            check=QCheckBox(title);check.toggled.connect(self.markers_changed)
            self.toggles[key]=check;grid.addWidget(check,i//2,i%2)
        self.marker_panel.hide();layout.addWidget(self.marker_panel)
        reset=QPushButton('↺  Скинути коефіцієнти')
        reset.setToolTip('Відновити коефіцієнти цієї функції; масштаб графіка зберігається')
        reset.clicked.connect(self.reset_requested);layout.addWidget(reset)
        layout.addStretch()
        self.preview_timer=QTimer(self);self.preview_timer.setSingleShot(True);self.preview_timer.setInterval(150)
        self.preview_timer.timeout.connect(self.render_formula)

    def set_function(self,key,values,color,precision=5,visible=True):
        self.show_graph.setVisible(not visible)
        self.precision=precision
        changed=key!=self.key
        self.key,self.values,self.color=key,dict(values),color
        if changed:
            while self.controls_layout.count():
                item=self.controls_layout.takeAt(0)
                if item.widget():item.widget().deleteLater()
            self.controls={}
            for c in LABS[key].controls:
                control=CoefficientControl(c,values[c.name]);self.controls[c.name]=control
                control.changed.connect(self.coefficient_changed)
                control.finished.connect(self.finished)
                self.controls_layout.addWidget(control)
        else:
            for name,control in self.controls.items():control.set_value(values[name])
        self.marker_button.setVisible(key=='quadratic')
        self.marker_panel.setVisible(key=='quadratic' and self.marker_button.isChecked())
        self.update_text()
        self.render_formula()

    def update_values(self,values):
        self.values=dict(values)
        self.update_text()
        self.preview_timer.start()

    def update_text(self):
        text=explanation(self.key,self.values,self.precision)
        # Qt stylesheets do not implement label line-height. Rich-text block
        # formatting supplies real leading and paragraph spacing without changing
        # the independently verified mathematical sentences.
        paragraphs=re.split(r'(?<=\.)\s+(?=[А-ЯІЇЄҐA-Za-z])',text)
        self.explanation.setText(''.join(
            '<p style="margin-top:0; margin-bottom:8px; line-height:125%;">'+escape(part)+'</p>'
            for part in paragraphs))
        self.explanation.setAccessibleDescription(text)


    def render_formula(self):
        if self.key:
            generic_key=(self.key,self.color)
            if getattr(self,'generic_key',None)!=generic_key:
                self.formula.update_latex(LABS[self.key].latex,self.color,size=17)
                self.generic_key=generic_key
            self.numeric.update_latex(formula_latex(self.key,self.values,self.precision),self.color,size=13)

    def show_details(self):
        QMessageBox.information(self,LABS[self.key].title,details(self.key,self.values))
