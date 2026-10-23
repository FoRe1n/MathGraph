import json
from pathlib import Path
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QLineEdit
import pytest
from graphmath.ui.window import MainWindow
from graphmath.ui.dialogs import ExportDialog, SettingsDialog
from graphmath.ui.formula import formula_png
from graphmath.plotting.export import export_graph
from graphmath.persistence.projects import Parameter, save


@pytest.fixture
def window(qtbot,tmp_path):
    w=MainWindow(QSettings(str(tmp_path/'settings.ini'),QSettings.IniFormat))
    qtbot.addWidget(w, before_close_func=lambda widget: setattr(widget, "confirm_discard", lambda: True))
    w.show()
    qtbot.wait(80)
    yield w
    w.inspector.cancel()
    w.confirm_discard=lambda: True
    w.saved_state=w.serialized()


def test_startup_and_ten_functions(window,qtbot):
    assert window.canvas.width() > window.editor_dock.width()
    for _ in range(8):
        window.add_function()
    assert len(window.project.functions)==10
    assert len(window.canvas.curves)==10
    window.visibility(window.project.selected,False)
    assert not window.canvas.curves[window.project.selected].isVisible()
    window.canvas.setFocus()
    window.delete_selected()
    assert len(window.project.functions)==9
    window.undo()
    assert len(window.project.functions)==10
    window.redo()
    assert len(window.project.functions)==9


def test_expression_edit_template_and_error(window,qtbot):
    row=window.rows[window.project.selected]
    row.input.selectAll()
    qtbot.keyClicks(row.input,'sqrt(x)')
    qtbot.wait(350)
    assert window.current_function().expression=='sqrt(x)'
    assert not row.preview.pixmap().isNull()
    row.input.selectAll()
    qtbot.keyClicks(row.input,'x.__class__')
    qtbot.wait(350)
    assert row.error.isVisible()
    row.input.selectAll()
    window.insert_math('sin(x)',4,1)
    window.flush_inputs()
    assert window.current_function().expression=='sin(x)'


def test_parameters_and_independence(window,qtbot):
    f=window.current_function()
    window.edit_function(f.id,'a*x^2+b')
    other=window.project.functions[1].expression
    window.parameter_changed('a',Parameter(value=3))
    assert f.parameters['a'].value==3
    assert window.project.functions[1].expression==other
    window.canvas.setFocus()
    window.undo()
    assert window.current_function().parameters['a'].value==1


@pytest.mark.parametrize('suffix',['png','svg','pdf'])
def test_live_exports(window,tmp_path,suffix,qtbot):
    qtbot.wait(80)
    path=tmp_path/f'graph.{suffix}'
    export_graph(window.canvas,str(path),transparent=suffix=='png',width=1200)
    data=path.read_bytes()
    assert len(data)>500
    if suffix=='png':
        from PySide6.QtGui import QImage
        image=QImage(str(path))
        assert image.width()==1200
    elif suffix=='svg':
        assert b'<svg' in data and b'path' in data
    else:
        assert data.startswith(b'%PDF')


def test_formula_rendering_and_themes(window):
    for latex in [r'\sqrt{x}',r'\frac{1}{x}',r'x^{2}',r'\log_{2}{x}']:
        assert formula_png(latex).startswith(b'\x89PNG')
    window.toggle_theme()
    assert window.preferences['theme']=='dark'
    assert window.canvas.backgroundBrush().color().name()=='#171b24'
    window.toggle_theme()
    assert window.preferences['theme']=='light'


def test_project_open_save_without_dialogs(window,tmp_path):
    window.path=str(tmp_path/'test.graphmath')
    assert window.save_project()
    window.current_function().expression='x+9'
    window.saved_state=window.serialized()
    assert window.open_project(window.path)
    assert window.current_function().expression=='x^2 - 4'
    assert window.recent_paths()[0]==window.path


def test_inspector_process_and_annotations(window,qtbot):
    window.toggle_inspector()
    window.investigate()
    qtbot.waitUntil(lambda: window.inspector.result is not None,timeout=15000)
    assert len(window.inspector.result['zeros'])==2
    window.inspector.toggles['zeros'].setChecked(True)
    assert len(window.canvas.annotations)>0
    window.inspector.toggles['tangent'].setChecked(True)
    assert window.canvas.tangent('abs(x)',{},0) is None


def test_dialogs_and_narrow_layout(window,qtbot,tmp_path):
    e=ExportDialog(window)
    qtbot.addWidget(e)
    e.show()
    e.format.setCurrentText('SVG')
    assert not e.transparent.isEnabled()
    e.grab().save(str(tmp_path/'export-dialog.png'))
    e.close()
    d=SettingsDialog(window,{**window.preferences,'grid':True,'axes':True})
    qtbot.addWidget(d)
    d.show()
    d.grab().save(str(tmp_path/'settings-dialog.png'))
    d.validate()
    assert d.values['theme']=='light'
    window.resize(800,580)
    qtbot.wait(80)
    assert window.canvas.width()>=280


def test_keyboard_delete_does_not_remove_function(window,qtbot):
    row=window.rows[window.project.selected]
    row.input.setFocus()
    row.input.setCursorPosition(0)
    qtbot.keyClick(row.input,Qt.Key_Delete)
    assert len(window.project.functions)==2
    assert row.input.text()=="^2 - 4"
