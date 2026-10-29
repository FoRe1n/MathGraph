"""Run both Windows distributions outside the checkout without Python on PATH.

Readiness latency includes executable loading, one-file extraction, imports and
the first prepared window. Each format is launched with both offscreen and real
Windows Qt platform plugins. Compare formats within the same backend; the two
launches are not a controlled cold/warm-cache experiment.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def verify_launch(executable: Path, output: Path, kind: str, version: str, timeout: float, backend: str) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    environment = os.environ.copy()
    system_root = Path(environment['SystemRoot'])
    environment['PATH'] = os.pathsep.join(map(str, (system_root/'System32', system_root)))
    environment.pop('PYTHONPATH', None)
    environment.pop('PYTHONHOME', None)
    environment['QT_QPA_PLATFORM'] = backend
    ready_path = output/'ready.json'
    process = None
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='mathlab-packaged-working-') as working:
        with (output/'stdout.log').open('wb') as stdout, (output/'stderr.log').open('wb') as stderr:
            process = subprocess.Popen([str(executable), '--smoke-test', '--smoke-output', str(output)],
                                       cwd=working, env=environment, stdout=stdout, stderr=stderr)
            try:
                ready = None
                while time.perf_counter()-started < timeout:
                    ready = read_json(ready_path)
                    if ready is not None:
                        break
                    if process.poll() is not None:
                        raise RuntimeError(f'{kind} exited before readiness: {process.returncode}')
                    time.sleep(.025)
                if ready is None:
                    raise RuntimeError(f'{kind} did not reach readiness in {timeout}s')
                ready_ms = round((time.perf_counter()-started)*1000, 3)
                if ready.get('status') != 'ready' or ready.get('version') != version:
                    raise RuntimeError(f'{kind} readiness status/version is invalid')
                if ready.get('qt_backend') != backend:
                    raise RuntimeError(f'{kind} did not initialize the requested Qt platform: {backend}')
                bundle = Path(ready['bundle_root']).resolve()
                if not bundle.is_dir():
                    raise RuntimeError('Frozen bundle root was not present at readiness')
                if output.is_relative_to(bundle):
                    raise RuntimeError('Smoke output is inside the frozen extraction directory')
                smoke_settings = Path(ready['smoke_settings_file']).resolve()
                if smoke_settings.is_relative_to(bundle) or not smoke_settings.is_relative_to(output):
                    raise RuntimeError('Smoke settings are not in the isolated persistent output directory')
                if ready.get('default_settings_format') != 'native':
                    raise RuntimeError('Expected native Windows QSettings storage')
                default_settings = ready.get('default_settings_file', '').casefold()
                if not default_settings or str(bundle).casefold() in default_settings or '_mei' in default_settings:
                    raise RuntimeError('Default settings appear to use a temporary bundle path')
                if not ready.get('resource_checks') or not all(ready['resource_checks'].values()):
                    raise RuntimeError('Readiness resource checks failed')
                remaining = max(.1, timeout-(time.perf_counter()-started))
                code = process.wait(timeout=remaining)
                if code != 0:
                    raise RuntimeError(f'{kind} smoke exit code: {code}')
            finally:
                if process.poll() is None:
                    # PyInstaller one-file uses a parent/child pair; terminate
                    # this launched tree rather than leaving its child running.
                    subprocess.run([str(system_root/'System32'/'taskkill.exe'), '/PID', str(process.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                    process.wait(timeout=10)
    result = read_json(output/'result.json')
    if not result or result.get('status') != 'passed' or result.get('version') != version:
        raise RuntimeError(f'{kind} smoke result is missing or failed')
    if result.get('qt_backend') != backend:
        raise RuntimeError(f'{kind} smoke used an unexpected Qt platform')
    if len(result.get('laboratory_modes', [])) != 20:
        raise RuntimeError('Not all twenty templates were exercised')
    for key in ('ui_glyph_coverage', 'analysis_subprocess', 'project_roundtrip', 'coefficient_controls'):
        if not result.get(key):
            raise RuntimeError('Missing packaged smoke check: '+key)
    if set(result.get('exports', [])) != {'png', 'svg', 'pdf'}:
        raise RuntimeError('Packaged exports were not exercised')
    project_path = Path(result['persistent_project_file']).resolve()
    if not project_path.is_file() or project_path.is_relative_to(bundle) or not project_path.is_relative_to(output):
        raise RuntimeError('Saved project did not survive outside the bundle')
    if not smoke_settings.is_file():
        raise RuntimeError('Isolated settings did not survive application exit')
    if kind == 'onefile':
        if not bundle.name.startswith('_MEI'):
            raise RuntimeError('Single-file launch did not use a temporary extraction directory')
        deadline = time.perf_counter()+5
        while bundle.exists() and time.perf_counter() < deadline:
            time.sleep(.025)
        if bundle.exists():
            raise RuntimeError('Single-file temporary extraction directory was not cleaned up')
    return {'status': 'passed', 'kind': kind, 'version': version,
            'qt_backend': backend,
            'ready_ms': ready_ms, 'total_smoke_ms': round((time.perf_counter()-started)*1000, 3),
            'executable_bytes': executable.stat().st_size, 'outside_checkout': True,
            'python_removed_from_path': True, 'temporary_bundle_cleaned': not bundle.exists() if kind == 'onefile' else None,
            'project_and_settings_survived_outside_bundle': True, 'ready': ready}


def verify(onedir: Path, onefile: Path, output: Path, version: str, timeout: float) -> dict:
    if os.name != 'nt':
        raise RuntimeError('Frozen Windows execution checks require a native Windows runner')
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    launches = []
    for kind, executable in (('onedir', onedir.resolve()), ('onefile', onefile.resolve())):
        if not executable.is_file():
            raise RuntimeError('Missing packaged executable: '+str(executable))
        for index, backend in enumerate(('offscreen', 'windows'), 1):
            result = verify_launch(executable, output/f'{kind}-run-{index}', kind, version, timeout, backend)
            result['launch_number'] = index
            launches.append(result)
    result = {'status': 'passed', 'version': version, 'platform': 'native Windows; offscreen and windows QPA',
              'startup_definition': 'Process launch to first prepared window; includes imports and one-file extraction.',
              'cache_note': 'Launch 1 is offscreen, launch 2 uses the Windows platform plugin. Compare formats within a backend; OS/antivirus cache state is not controlled.',
              'launches': launches}
    (output/'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--onedir', type=Path, required=True)
    parser.add_argument('--onefile', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('artifacts/packaged-validation'))
    parser.add_argument('--version', required=True)
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    print(json.dumps(verify(args.onedir, args.onefile, args.output, args.version, args.timeout), indent=2))
