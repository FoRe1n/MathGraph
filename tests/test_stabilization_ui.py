import json
from unittest.mock import patch
import pytest
from PySide6.QtCore import QSettings,QTimer
from PySide6.QtWidgets import QDialog,QDialogButtonBox,QDoubleSpinBox
from graphmath.ui.window import MainWindow
from graphmath.ui.editor import ParameterControl
from graphmath.persistence.projects import Parameter,Function,Project,save,load


@pytest.fixture
def window(qtbot,tmp_path):
    w=MainWindow(QSettings(str(tmp_path/'ui.ini'),QSettings.IniFormat))
    qtbot.addWidget(w,before_close_func=lambda w:setattr(w,'confirm_discard',lambda:True))
    w.show();qtbot.wait(180)
    w.mode_selector.setCurrentIndex(w.mode_selector.findData('custom'))
    return w


@pytest.mark.parametrize('saved',[
    {'theme':[],'precision':False,'scale':'garbage','colors':[],'default_view':[0]},
    {'grid':'yes','axes':1,'coordinates':{},'default_view':[0,0,1,2]},
    {'default_view':[10**1000,2,3,4]},[],None,
])
def test_damaged_preferences_fall_back_safely(qtbot,tmp_path,saved):
    settings=QSettings(str(tmp_path/'broken.ini'),QSettings.IniFormat)
    settings.setValue('preferences',json.dumps(saved));settings.setValue('recent','42')
    w=MainWindow(settings);qtbot.addWidget(w,before_close_func=lambda w:setattr(w,'confirm_discard',lambda:True))
    assert w.preferences['theme']=='light' and w.preferences['colors']
    assert w.recent_paths()==[]


def test_recent_entries_are_validated(window):
    window.settings.setValue('recent',json.dumps([None,{},'one.graphmath',3,'']))
    assert window.recent_paths()==['one.graphmath']
    window.update_recents()


def test_temporary_invalid_formula_retains_parameter_values(window):
    f=window.current_function();window.edit_function(f.id,'a*(x-h)^2+k')
    window.parameter_changed('a',Parameter(value=3))
    window.parameter_changed('h',Parameter(value=2,initial=0))
    window.edit_function(f.id,'a*(x-h)^2+')
    assert f.parameters['a'].value==3 and f.parameters['h'].value==2
    window.edit_function(f.id,'a*(x-h)^2+k')
    assert f.parameters['a'].value==3 and f.parameters['h'].value==2


def test_delayed_unselected_edit_updates_only_its_own_parameters(window):
    first=window.current_function();window.add_function();selected=window.current_function()
    before=dict(selected.parameters)
    window.edit_function(first.id,'a*(x-h)^2+k')
    assert selected.parameters==before
    assert set(first.parameters)=={'a','h','k'}
    assert first.parameters['h'].value==0


def test_unchanged_parameter_controls_are_reused(window):
    f=window.current_function();window.edit_function(f.id,'a*x+h')
    before=[id(window.parameter_layout.itemAt(i).widget()) for i in range(window.parameter_layout.count())]
    window.edit_function(f.id,'a*x^2+h')
    assert before==[id(window.parameter_layout.itemAt(i).widget()) for i in range(window.parameter_layout.count())]


def test_settings_apply_changed_view_but_theme_only_keeps_pan(window):
    values={**window.preferences,'default_view':[-2,4,-3,8]}
    with patch('graphmath.ui.window.SettingsDialog') as dialog:
        dialog.return_value.exec.return_value=QDialog.Accepted;dialog.return_value.values=values
        window.show_settings()
    assert window.canvas.current_view()==pytest.approx([-2,4,-3,8])
    window.canvas.set_view([-4,2,-5,6]);view=window.canvas.current_view()
    with patch('graphmath.ui.window.SettingsDialog') as dialog:
        dialog.return_value.exec.return_value=QDialog.Accepted;dialog.return_value.values={**values,'theme':'dark'}
        window.show_settings()
    assert window.canvas.current_view()==pytest.approx(view)


def test_small_parameter_slider_is_effective_and_serializes(qtbot,tmp_path):
    parameter=Parameter(value=1e-8,minimum=0,maximum=1e-6,step=1e-8,initial=1e-8)
    control=ParameterControl('a',parameter);qtbot.addWidget(control)
    control.slider.setValue(2)
    assert control.value.value()==pytest.approx(2e-8,rel=1e-12,abs=0)
    assert parameter.value==pytest.approx(2e-8,rel=1e-12,abs=0)
    f=Function('a*x',parameters={'a':parameter});p=Project([f],selected=f.id)
    path=tmp_path/'tiny.graphmath';save(p,path)
    assert load(path).functions[0].parameters['a'].value==parameter.value


def test_parameter_configure_keeps_loaded_precision_and_emits_once(qtbot):
    parameter=Parameter(value=2e-8,minimum=0,maximum=1e-6,step=1e-8,initial=1e-8)
    control=ParameterControl('a',parameter);qtbot.addWidget(control);events=[]
    control.changed.connect(lambda *args:events.append(args))
    def accept():
        dialog=control.findChild(QDialog)
        buttons=dialog.findChild(QDialogButtonBox)
        buttons.button(QDialogButtonBox.Ok).click()
    QTimer.singleShot(0,accept);control.configure()
    assert parameter.step==1e-8 and parameter.value==2e-8 and parameter.maximum==1e-6
    assert len(events)==1



def test_formula_native_undo_restores_previous_parameter_values(window,qtbot):
    f=window.current_function();window.edit_function(f.id,'a*x')
    window.parameter_changed('a',Parameter(value=3))
    row=window.rows[f.id];row.input.setText('a*x');row.input.setFocus();row.input.selectAll()
    qtbot.keyClicks(row.input,'b*x');row.flush()
    assert set(f.parameters)=={'b'}
    window.undo();row.flush()
    assert f.expression=='a*x' and f.parameters['a'].value==3


def test_switching_existing_templates_reuses_editor_rows(window):
    window.mode_selector.setCurrentIndex(window.mode_selector.findData('exponential'))
    rows={identifier:id(row) for identifier,row in window.rows.items()}
    for key in ['quadratic','exponential']*5:
        window.mode_selector.setCurrentIndex(window.mode_selector.findData(key))
    assert rows=={identifier:id(row) for identifier,row in window.rows.items()}



def test_hidden_markers_do_no_root_work_during_cached_pan(window):
    window.mode_selector.setCurrentIndex(window.mode_selector.findData('quadratic'))
    with patch('graphmath.ui.window.markers',side_effect=AssertionError('unnecessary roots')):
        for _ in range(10):
            window.canvas.viewbox.translateBy(x=.01);window.canvas.flush_refresh()


def test_visible_markers_reuse_coordinates_during_pan(window):
    window.mode_selector.setCurrentIndex(window.mode_selector.findData('quadratic'))
    window.learning.toggles['vertex'].setChecked(True)
    before=window.lab_dots.data.copy()
    with patch('graphmath.ui.window.markers',side_effect=AssertionError('unnecessary roots')):
        window.canvas.viewbox.translateBy(x=.01);window.canvas.flush_refresh()
    assert (window.lab_dots.data==before).all()



def test_reset_document_clears_native_editor_undo(window,qtbot):
    row=window.rows[window.project.selected];row.input.setFocus();row.input.selectAll()
    qtbot.keyClicks(row.input,'x^3');row.flush()
    assert row.input.isUndoAvailable()
    window.reset_document()
    assert not window.rows[window.project.selected].input.isUndoAvailable()


def test_close_stops_owned_debounce_timers(window):
    window.history_timer.start();window.learning.preview_timer.start()
    window.confirm_discard=lambda:True
    assert window.close()
    assert not any(timer.isActive() for timer in window.findChildren(QTimer))
