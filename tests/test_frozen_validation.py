"""Portable regressions for Windows runner environment and failure reporting."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('verify_frozen_app',
                                            Path(__file__).parents[1]/'scripts/verify_frozen_app.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize('root_key', ['SYSTEMROOT', 'SystemRoot', 'systemroot'])
def test_windows_environment_handles_copied_key_casing(root_key):
    source = {root_key: r'C:\Windows', 'Path': r'C:\Python312;C:\Windows',
              'PythonPath': r'C:\checkout', 'pythonhome': r'C:\Python312',
              'Qt_Qpa_Platform': 'offscreen', 'USERPROFILE': r'C:\Users\runneradmin'}
    original = dict(source)
    environment, root = module.windows_environment(source, 'windows')
    assert str(root) == r'C:\Windows'
    assert environment['PATH'] == r'C:\Windows\System32;C:\Windows'
    assert environment['QT_QPA_PLATFORM'] == 'windows'
    assert environment['USERPROFILE'] == source['USERPROFILE']
    assert not any(key.casefold() in ('pythonpath', 'pythonhome') for key in environment)
    assert [key for key in environment if key.casefold() == 'path'] == ['PATH']
    assert source == original


def test_missing_system_root_has_actionable_error():
    with pytest.raises(RuntimeError, match='SystemRoot environment variable is missing'):
        module.windows_environment({'PATH': 'external-python'}, 'offscreen')


@pytest.mark.parametrize('newline', [b'\n', b'\r\n'], ids=['LF', 'CRLF'])
def test_failed_packaged_check_emits_escaped_annotation_and_diagnostics(tmp_path, capsys, monkeypatch, newline):
    output = tmp_path/'validation'
    run = output/'onedir-run-1'; run.mkdir(parents=True)
    raw_stderr = b'Qt failed: 50%'+newline+b'second line'
    (run/'stderr.log').write_bytes(raw_stderr)
    (run/'error.txt').write_text('Smoke diagnostic', encoding='utf-8')
    summary = tmp_path/'summary.md'
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(summary))
    module.report_failure(output, RuntimeError('did not reach readiness'))
    printed = capsys.readouterr().out
    assert printed.startswith('::error title=Packaged Windows validation failed::RuntimeError:')
    assert '50%25%0Asecond line' in printed
    assert 'Smoke diagnostic' in printed
    assert printed.count('\n') == 1
    assert (run/'stderr.log').read_bytes() == raw_stderr
    failure = json.loads((output/'failure.json').read_text())
    assert failure['status'] == 'failed'
    assert 'did not reach readiness' in failure['diagnostics']
    assert '50%\nsecond line' in summary.read_text()
