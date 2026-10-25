"""Failures must preserve saved work and leave the analysis UI usable."""
import json
import multiprocessing as mp
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from graphmath.persistence import projects
from graphmath.persistence.projects import Project, from_dict, load, save
from graphmath.ui.inspector import Inspector


@pytest.mark.parametrize('field', ['view', 'parameter'])
def test_project_oversized_integer_is_a_readable_validation_error(field):
    data = Project().to_dict()
    if field == 'view':
        data['view'][0] = -(10**1000)
    else:
        data['functions'][0]['parameters'] = {
            'a': {'value': 10**1000, 'minimum': -5, 'maximum': 5, 'step': .1, 'initial': 1}}
    with pytest.raises(ValueError, match='числове значення'):
        from_dict(data)


def test_json_integer_decoder_limit_has_a_ukrainian_error(tmp_path):
    path = tmp_path / 'damaged.graphmath'
    path.write_text('{"integer":' + '9' * 10000 + '}', encoding='utf-8')
    with pytest.raises(ValueError, match='Не вдалося прочитати JSON проєкту'):
        load(path)


def test_project_validation_keeps_specific_error_messages(tmp_path):
    path = tmp_path / 'version.graphmath'
    path.write_text('{"format":"GraphMath","version":9}', encoding='utf-8')
    with pytest.raises(ValueError, match='Непідтримуваний формат'):
        load(path)


def test_invalid_unicode_formula_is_rejected_before_gui_or_save(tmp_path):
    data = Project().to_dict()
    data['functions'][0]['expression'] = '\ud800'
    path = tmp_path / 'unicode.graphmath'
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='текст формули'):
        load(path)


def test_failed_atomic_replace_preserves_old_file_and_cleans_temporary(tmp_path, monkeypatch):
    path = tmp_path / 'work.graphmath'
    project = Project()
    save(project, path)
    original = path.read_bytes()
    project.functions[0].expression = 'x+99'
    def denied(*_):
        raise PermissionError('read-only destination')
    monkeypatch.setattr(projects.os, 'replace', denied)
    with pytest.raises(PermissionError):
        save(project, path)
    assert path.read_bytes() == original
    assert load(path).functions[0].expression == 'x^2 - 4'
    assert list(tmp_path.glob('*.tmp')) == []


@pytest.fixture
def inspector(qtbot):
    widget = Inspector()
    qtbot.addWidget(widget)
    yield widget
    widget.cancel()


def test_worker_spawn_failure_closes_both_pipe_ends_and_restores_ui(inspector, monkeypatch):
    context = mp.get_context('spawn')
    receive, send = context.Pipe(duplex=False)
    process = Mock(pid=None)
    process.start.side_effect = OSError('process resource limit')
    process.is_alive.side_effect = AssertionError('An unstarted worker must not be queried')
    monkeypatch.setattr('graphmath.ui.inspector.mp.get_context', lambda *_: SimpleNamespace(
        Pipe=lambda **_: (receive, send), Process=lambda **_: process))
    inspector.start('x^2', {}, None, None)
    assert receive.closed and send.closed
    assert inspector.process is None and inspector.connection is None
    assert inspector.run.isEnabled() and not inspector.timer.isActive()
    assert 'Не вдалося запустити' in inspector.status.text()
    process.close.assert_called_once()
    process.join.assert_not_called()


def test_worker_pipe_failure_does_not_escape_the_qt_timer(inspector):
    connection = Mock()
    connection.poll.side_effect = OSError('broken pipe')
    inspector.connection = connection
    inspector.poll()
    assert inspector.connection is None and inspector.run.isEnabled()
    assert 'Не вдалося завершити' in inspector.status.text()
    connection.close.assert_called_once()


def test_slow_termination_escalates_to_kill_before_process_close(inspector):
    alive = {'value': True}
    process = Mock(pid=123)
    process.is_alive.side_effect = lambda: alive['value']
    process.kill.side_effect = lambda: alive.update(value=False)
    inspector.process = process
    assert inspector.cancel()
    process.terminate.assert_called_once()
    process.kill.assert_called_once()
    process.close.assert_called_once()
    assert inspector.process is None


def test_cancel_reaps_a_real_spawned_worker(inspector):
    process = mp.get_context('spawn').Process(target=time.sleep, args=(30,), daemon=True)
    process.start()
    worker_pid = process.pid
    inspector.process = process
    inspector.started = time.monotonic()
    inspector.timer.start()
    assert inspector.cancel()
    assert inspector.process is None and not inspector.timer.isActive()
    assert worker_pid not in {child.pid for child in mp.active_children()}


def test_cancel_before_any_worker_is_safe_and_repeatable(inspector):
    assert inspector.cancel()
    assert inspector.cancel()
    assert inspector.run.isEnabled()



def test_export_dialog_only_enables_relevant_controls(qtbot):
    from graphmath.ui.dialogs import ExportDialog
    dialog = ExportDialog(None)
    qtbot.addWidget(dialog)
    dialog.format.setCurrentText('PDF')
    assert not dialog.width.isEnabled() and not dialog.transparent.isEnabled()
    dialog.format.setCurrentText('SVG')
    assert dialog.width.isEnabled() and not dialog.transparent.isEnabled()
    dialog.format.setCurrentText('PNG')
    assert dialog.width.isEnabled() and dialog.transparent.isEnabled()


def test_window_close_cancels_and_reaps_its_analysis_worker(qtbot, tmp_path):
    from PySide6.QtCore import QSettings
    from graphmath.ui.window import MainWindow
    window = MainWindow(QSettings(str(tmp_path / 'shutdown.ini'), QSettings.IniFormat))
    qtbot.addWidget(window)
    window.confirm_discard = lambda: True
    window.inspector.start('x^2', {}, None, None)
    worker_pid = window.inspector.process.pid
    assert window.close()
    assert window.inspector.process is None and window.inspector.connection is None
    assert not window.inspector.timer.isActive()
    assert worker_pid not in {child.pid for child in mp.active_children()}



def test_worker_receive_failure_is_reported_without_traceback(inspector):
    connection = Mock()
    connection.poll.return_value = True
    connection.recv.side_effect = ConnectionResetError('worker exited while sending')
    inspector.connection = connection
    inspector.poll()
    assert inspector.connection is None and inspector.run.isEnabled()
    assert inspector.status.text() == 'Не вдалося завершити дослідження.'
