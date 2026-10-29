"""Readability changes preserve existing math text, controls and navigation."""
import re

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QLabel

from graphmath.core.laboratories import GROUPS, LABS, explanation
from graphmath.ui.learning import LearningPanel
from graphmath.ui.window import MainWindow


@pytest.fixture
def window(qtbot,tmp_path):
    widget=MainWindow(QSettings(str(tmp_path/'polish.ini'),QSettings.IniFormat))
    qtbot.addWidget(widget,before_close_func=lambda w:setattr(w,'confirm_discard',lambda:True))
    widget.show()
    qtbot.wait(50)
    return widget


def controls_fit(panel):
    """Wait for queued Qt font/layout work, then assert the actual geometry."""
    previous=None
    for control in panel.controls.values():
        label,value,slider=control.label,control.value,control.slider
        if not label.sizePolicy().hasHeightForWidth() or not control.layout().hasHeightForWidth():return False
        if label.geometry().right()>=value.geometry().left():return False
        if label.height()<label.heightForWidth(label.width()):return False
        if value.height()<value.minimumSizeHint().height():return False
        if slider.geometry().top()<=max(label.geometry().bottom(),value.geometry().bottom()):return False
        if previous is not None and control.y()<=previous.geometry().bottom():return False
        previous=control
    return True


def test_selector_keyboard_skips_nonselectable_headers(window,qtbot):
    selector=window.mode_selector
    expected=[key for _,keys in GROUPS for key in keys]+['custom']
    headings=[selector.model().index(i,0) for i in range(selector.count()) if selector.itemData(i) is None]
    assert [index.data() for index in headings]==[title for title,_ in GROUPS]
    assert all(not index.flags() & (Qt.ItemIsSelectable|Qt.ItemIsEnabled) for index in headings)
    selector.setCurrentIndex(selector.findData(expected[0]))
    selector.setFocus()
    visited=[selector.currentData()]
    for _ in expected[1:]:
        qtbot.keyClick(selector,Qt.Key_Down)
        visited.append(selector.currentData())
    assert visited==expected
    for key in reversed(expected[:-1]):
        qtbot.keyClick(selector,Qt.Key_Up)
        assert selector.currentData()==key
    assert 'Змінюйте коефіцієнти. Спостерігайте за графіком.' not in [label.text() for label in window.findChildren(QLabel)]


@pytest.mark.parametrize('scale',['100%','125%','150%'])
@pytest.mark.parametrize('theme',['light','dark'])
def test_long_coefficient_labels_wrap_above_slider_in_narrow_window(window,qtbot,scale,theme):
    window.preferences['scale']=scale
    window.set_theme(theme)
    window.mode_selector.setCurrentIndex(window.mode_selector.findData('logarithmic_scale'))
    window.resize(780,540)
    qtbot.waitUntil(lambda:controls_fit(window.learning),timeout=1000)
    previous=None
    for control in window.learning.controls.values():
        label,value,slider=control.label,control.value,control.slider
        assert label.sizePolicy().hasHeightForWidth() and control.layout().hasHeightForWidth()
        assert label.geometry().right()<value.geometry().left()
        assert slider.geometry().top()>max(label.geometry().bottom(),value.geometry().bottom())
        assert label.height()>=label.heightForWidth(label.width()),(control.control.name,label.geometry())
        assert value.height()>=value.minimumSizeHint().height()
        if previous is not None:assert control.y()>previous.geometry().bottom()
        previous=control
        assert value.decimals()==1
        assert value.minimum()==control.control.minimum and value.maximum()==control.control.maximum
        assert value.singleStep()==control.control.step
        assert slider.maximum()==len(control.control.values())-1


@pytest.mark.parametrize('theme',['light','dark'])
def test_all_scaled_modes_scroll_without_compressing_their_controls(window,qtbot,theme):
    window.resize(780,540)
    window.preferences['scale']='150%'
    window.set_theme(theme)
    for key in LABS:
        window.mode_selector.setCurrentIndex(window.mode_selector.findData(key))
        qtbot.waitUntil(lambda:controls_fit(window.learning),timeout=1000)
        previous=None
        for control in window.learning.controls.values():
            label,value,slider=control.label,control.value,control.slider
            assert label.sizePolicy().hasHeightForWidth() and control.layout().hasHeightForWidth()
            assert label.height()>=label.heightForWidth(label.width()),(theme,key,control.control.name,label.geometry())
            assert value.height()>=value.minimumSizeHint().height(),(theme,key,control.control.name,value.geometry())
            assert slider.geometry().top()>max(label.geometry().bottom(),value.geometry().bottom())
            if previous is not None:assert control.y()>previous.geometry().bottom()
            previous=control


def test_explanation_paragraphs_preserve_every_verified_sentence(qtbot):
    panel=LearningPanel()
    qtbot.addWidget(panel)
    for key,lab in LABS.items():
        values={control.name:control.default for control in lab.controls}
        candidates=[values]
        if 'a' in values:candidates.append({**values,'a':0})
        for candidate in candidates:
            panel.key,panel.values,panel.precision=key,candidate,5
            panel.update_text()
            document=QTextDocument()
            document.setHtml(panel.explanation.text())
            expected=explanation(key,candidate,5)
            assert re.sub(r'\s+',' ',document.toPlainText()).strip()==expected
            assert panel.explanation.accessibleDescription()==expected
            block=document.begin()
            while block.isValid():
                assert block.blockFormat().lineHeight()==125
                block=block.next()
