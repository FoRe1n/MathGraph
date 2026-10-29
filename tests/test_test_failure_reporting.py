"""Make native CI failures inspectable even when anonymous raw logs are unavailable."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('report_test_failures',
                                            Path(__file__).parents[1]/'scripts/report_test_failures.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_junit_failure_annotations_keep_names_counts_and_failure_status(tmp_path, capsys, monkeypatch):
    xml = tmp_path/'tests.xml'
    xml.write_bytes(b'''<testsuites><testsuite tests="4" failures="1" errors="1" skipped="1">
<testcase classname="tests.gui" name="passed"/>
<testcase classname="tests.gui" name="failed"><failure message="50% mismatch">first\r\nsecond</failure></testcase>
<testcase classname="tests.gui" name="broken"><error message="Qt failed">plugin missing</error></testcase>
<testcase classname="tests.gui" name="skipped"><skipped/></testcase>
</testsuite></testsuites>''')
    summary = tmp_path/'summary.md'; monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(summary))
    assert module.report(xml) == 1
    printed = capsys.readouterr().out
    assert 'tests.gui.failed: 50%25 mismatch%0Afirst%0Asecond' in printed
    assert 'tests.gui.broken: Qt failed' in printed
    assert 'tests=4, failures=1, errors=1, skipped=1' in printed
    assert 'tests.gui.failed' in summary.read_text()


def test_successful_junit_report_returns_success(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv('GITHUB_STEP_SUMMARY', raising=False)
    xml = tmp_path/'tests.xml'
    xml.write_text('<testsuites><testsuite tests="1"><testcase name="passed"/></testsuite></testsuites>')
    assert module.report(xml) == 0
    printed = capsys.readouterr().out
    assert 'tests=1, failures=0, errors=0, skipped=0' in printed
    assert '::error' not in printed
