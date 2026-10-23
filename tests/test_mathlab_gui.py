from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
from PySide6.QtCore import QSettings,QPointF,Qt
from PySide6.QtWidgets import QMessageBox,QApplication
from graphmath.ui.window import MainWindow
from graphmath.ui.dialogs import SettingsDialog,ExportDialog
from graphmath.app.localization import install_ukrainian
from graphmath.core.laboratories import LABS,identify
from graphmath.core.expressions import evaluate
from graphmath.persistence.projects import load


@pytest.fixture
def lab(qtbot,tmp_path):
    w=MainWindow(QSettings(str(tmp_path/'mathlab.ini'),QSettings.IniFormat))
    qtbot.addWidget(w,before_close_func=lambda w:setattr(w,'confirm_discard',lambda:True))
    w.show();qtbot.wait(220)
    return w


def choose(w,key):w.mode_selector.setCurrentIndex(w.mode_selector.findData(key))


def test_initial_learning_screen(lab):
    assert lab.mode=='quadratic' and lab.pages.currentIndex()==0
    assert len(lab.learning.controls)==3
    assert 'MathLab' in lab.windowTitle()
    assert len([a for a in lab.main_toolbar.actions() if a.text()])==5
    assert not lab.canvas.coordinates_enabled
    assert not lab.canvas.cross_x.isVisible()
    assert lab.current_function().parameters['a'].value==1
    assert not lab.learning.formula.pixmap().isNull()
    assert lab.canvas.width()>lab.editor_dock.width()


@pytest.mark.parametrize('key',['quadratic','exponential','logarithmic'])
def test_modes_controls_and_history(lab,qtbot,key):
    choose(lab,key)
    assert identify(lab.current_function())==key
    before={k:id(v) for k,v in lab.learning.controls.items()}
    control=lab.learning.controls['a']
    control.slider.setValue(control.slider.maximum())
    qtbot.wait(220)
    assert lab.current_function().parameters['a'].value==5
    assert before=={k:id(v) for k,v in lab.learning.controls.items()}
    assert not lab.learning.numeric.pixmap().isNull()
    assert lab.learning.controls['a'].value.value()==5
    lab.canvas.setFocus();lab.undo()
    assert lab.current_function().parameters['a'].value==1
    lab.redo();assert lab.current_function().parameters['a'].value==5
    lab.reset_coefficients();assert lab.current_function().parameters['a'].value==1


@pytest.mark.parametrize('key',['exponential','logarithmic'])
def test_base_spin_and_slider_constraints(lab,qtbot,key):
    choose(lab,key)
    control=lab.learning.controls['b']
    control.value.setValue(1)
    assert lab.current_function().parameters['b'].value==1.1
    for tick in range(control.slider.maximum()+1):
        control.slider.setValue(tick)
        b=lab.current_function().parameters['b'].value
        assert b>0 and b!=1
    qtbot.wait(220)


def test_coefficients_keep_view_and_other_functions(lab,qtbot):
    original=lab.current_function()
    choose(lab,'exponential')
    view=lab.canvas.current_view()
    lab.learning.controls['b'].value.setValue(.5)
    qtbot.wait(220)
    np.testing.assert_allclose(lab.canvas.current_view(),view)
    assert original.parameters['a'].value==1 and original.parameters['b'].value==0
    choose(lab,'custom')
    assert lab.pages.currentIndex()==1 and len(lab.project.functions)==2
    assert len(lab.canvas.curves)==2


@pytest.mark.parametrize('source,points',[('x^2',[(0,0),(1,1),(2,4),(-2,4)]),('2x+1',[(0,1),(1,3),(2,5)]),('x',[(0,0),(1,1),(-1,-1)])])
def test_axes_and_known_coordinate_mapping(lab,source,points):
    vb=lab.canvas.viewbox
    np.testing.assert_allclose(evaluate(source,[x for x,y in points]),[y for x,y in points])
    zero=vb.mapViewToScene(QPointF(0,0))
    right=vb.mapViewToScene(QPointF(1,0))
    up=vb.mapViewToScene(QPointF(0,1))
    assert right.x()>zero.x() and up.y()<zero.y()
    for x,y in points:
        mapped=vb.mapSceneToView(vb.mapViewToScene(QPointF(x,y)))
        assert mapped.x()==pytest.approx(x) and mapped.y()==pytest.approx(y)


def test_cached_pan_does_not_resample_or_serialize(lab,qtbot):
    lab.canvas.refine_timer.stop();lab.canvas.resample_timer.stop()
    before=lab.canvas.sample_count
    with patch.object(lab,'serialized',side_effect=AssertionError('Serialization in viewport path')):
        for _ in range(20):
            lab.canvas.viewbox.translateBy(x=.01)
            lab.canvas.flush_refresh()
        qtbot.wait(90)
    assert lab.canvas.sample_count==before
    qtbot.wait(180)
    assert lab.canvas.sample_count<=before+2


def test_markers_domain_and_custom_retained(lab,qtbot):
    lab.learning.toggles['vertex'].setChecked(True)
    lab.learning.toggles['symmetry'].setChecked(True)
    assert lab.lab_axis.isVisible() and lab.lab_dots.isVisible()
    choose(lab,'logarithmic')
    lab.learning.controls['h'].value.setValue(2)
    qtbot.wait(220)
    assert lab.lab_boundary.value()==2 and lab.lab_domain.isVisible()
    assert 'x > 2' in lab.graph_hint.text()
    choose(lab,'custom');assert not lab.lab_domain.isVisible()
    lab.add_function();lab.edit_function(lab.project.selected,'1/x')
    assert len(lab.project.functions)==3
    assert not lab.inspector_dock.isVisible()
    lab.toggle_inspector();assert lab.inspector_dock.isVisible()


def test_legacy_fixture_roundtrip(lab,tmp_path):
    fixture=Path(__file__).parent/'fixtures'/'graphmath-v1.graphmath'
    original=load(fixture)
    lab.confirm_discard=lambda:True
    assert lab.open_project(str(fixture))
    assert lab.mode=='custom'
    assert lab.project.to_dict()==original.to_dict()
    lab.path=str(tmp_path/'resaved.graphmath');assert lab.save_project()
    assert load(lab.path).to_dict()==original.to_dict()


def test_minimal_settings_reset_and_ukrainian(qtbot,lab):
    assert install_ukrainian(QApplication.instance())
    dialog=SettingsDialog(lab,{**lab.preferences,'grid':True,'axes':True})
    qtbot.addWidget(dialog);dialog.show()
    dialog.theme.setCurrentIndex(1);dialog.coordinates.setChecked(True)
    dialog.reset_defaults();dialog.validate()
    assert dialog.values['theme']=='light' and not dialog.values['coordinates']
    export=ExportDialog(lab);qtbot.addWidget(export)
    buttons=export.findChild(__import__('PySide6.QtWidgets',fromlist=['QDialogButtonBox']).QDialogButtonBox)
    assert any('Зберегти' in button.text() for button in buttons.buttons())


def test_close_cancel_and_save_prompt(lab):
    lab.lab_coefficient_changed('a',2)
    with patch.object(QMessageBox,'question',return_value=QMessageBox.Cancel):
        assert not lab.close()
    assert lab.isVisible()
    with patch.object(QMessageBox,'question',return_value=QMessageBox.Discard):
        assert lab.close()


def test_smooth_idle_fast_interaction_and_grid_independence(lab,qtbot):
    choose(lab,'logarithmic');qtbot.wait(250)
    curve=lab.canvas.curves[lab.project.selected]
    assert curve.opts['antialias']
    lab.canvas.viewbox.translateBy(x=.01)
    assert not curve.curve.opts['antialias']
    qtbot.wait(250)
    assert curve.curve.opts['antialias']
    lab.set_axes(False)
    assert lab.canvas.grid_item.isVisible()


def test_custom_mode_with_lab_functions_persists(lab,tmp_path):
    choose(lab,'exponential');choose(lab,'custom')
    lab.path=str(tmp_path/'custom-labs.graphmath')
    assert lab.save_project()
    lab.confirm_discard=lambda:True
    assert lab.open_project(lab.path)
    assert lab.mode=='custom' and len(lab.canvas.curves)==2


def test_old_project_payload_is_preserved(lab):
    import json
    path=Path(__file__).parent/'fixtures'/'graphmath-v1.graphmath'
    original=json.loads(path.read_text())
    loaded=load(path).to_dict()
    assert {key:loaded[key] for key in original}==original
    assert loaded['mode']=='custom'


def test_hidden_lab_is_preserved_and_can_be_shown(lab,qtbot):
    function=lab.current_function()
    choose(lab,'custom');lab.visibility(function.id,False)
    choose(lab,'quadratic')
    assert not function.visible and lab.learning.show_graph.isVisible()
    qtbot.mouseClick(lab.learning.show_graph,Qt.LeftButton)
    assert function.visible and not lab.learning.show_graph.isVisible()


def test_entering_lab_preserves_custom_parameter_limits(lab,tmp_path):
    from graphmath.persistence.projects import Project,Function,Parameter
    custom=Function('a*x^2+b*x+c',parameters={n:Parameter() for n in ['a','b','c']})
    lab.project=Project(functions=[custom],selected=custom.id)
    lab.reset_document()
    assert lab.mode=='custom'
    choose(lab,'quadratic')
    assert lab.current_function().id!=custom.id
    lab.learning.controls['b'].value.setValue(8)
    lab.path=str(tmp_path/'separate-parameters.graphmath')
    assert lab.save_project()
    assert custom.parameters['b'].maximum==5 and custom.parameters['b'].value==1
