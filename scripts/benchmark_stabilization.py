"""Additional reproducible desktop workloads for stabilization audits.

Use MATHLAB_BENCH_SOURCE to run the same script against an archived source tree.
Measurements include actual Qt event delivery and forced raster grabs; they are
interaction latencies, not hardware/compositor frame rates. No user preferences
or project files are changed. A failed operation makes this runner exit nonzero.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('XDG_CACHE_HOME', str(Path(tempfile.gettempdir()) / 'mathlab-audit-cache'))
sys.path.insert(0, os.environ.get('MATHLAB_BENCH_SOURCE', str(Path(__file__).resolve().parents[1])))


def rss_bytes():
    if sys.platform == 'linux':
        return int(Path('/proc/self/statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
    if sys.platform == 'win32':
        import ctypes
        class Memory(ctypes.Structure):
            _fields_ = [('cb', ctypes.c_uint32), ('faults', ctypes.c_uint32)] + [
                (name, ctypes.c_size_t) for name in ('peak', 'working', 'qpp', 'qp', 'qnp', 'qn', 'page', 'peakpage')]
        memory = Memory(); memory.cb = ctypes.sizeof(memory)
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
        get_memory.argtypes = [ctypes.c_void_p, ctypes.POINTER(Memory), ctypes.c_uint32]
        return memory.working if get_memory(kernel.GetCurrentProcess(), ctypes.byref(memory), memory.cb) else None
    return None


def statistics_ms(samples):
    ordered = sorted(samples)
    return {'count': len(samples), 'mean_ms': round(statistics.mean(samples), 3),
            'median_ms': round(statistics.median(samples), 3),
            'p95_ms': round(ordered[min(len(ordered)-1, int(.95*len(ordered)))], 3),
            'max_ms': round(max(samples), 3)}


def run(frames):
    from PySide6.QtCore import QCoreApplication, QEvent, QSettings, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QWidget
    from graphmath.core.laboratories import LABS
    from graphmath.persistence.projects import Function, Project
    from graphmath.ui.window import MainWindow

    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    errors = []
    previous_hook = sys.excepthook
    def record_callback_error(kind, value, traceback):
        errors.append(f'{kind.__name__}: {value}')
        previous_hook(kind, value, traceback)
    sys.excepthook = record_callback_error
    temporary = tempfile.TemporaryDirectory(prefix='mathlab-stabilization-benchmark-')
    window = None
    results = {'status': 'running', 'platform': platform.platform(), 'python': platform.python_version(),
               'qt_backend': os.environ['QT_QPA_PLATFORM'], 'source_root': str(Path(sys.path[0]).resolve()),
               'iterations_per_scenario': frames, 'scenarios': {}}
    try:
        window = MainWindow(QSettings(str(Path(temporary.name) / 'settings.ini'), QSettings.IniFormat))
        window.show(); QTest.qWait(220)

        def settle():
            app.processEvents()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            app.processEvents()

        def state():
            settle(); gc.collect()
            return {'rss_bytes': rss_bytes(), 'widget_objects': len(window.findChildren(QWidget)),
                    'scene_items': len(window.canvas.scene().items()), 'curve_objects': len(window.canvas.curves),
                    'sample_cache_entries': len(window.canvas.sample_cache),
                    'project_function_records': len(window.project.functions)}

        def measure(name, callback, operation):
            before = state(); samples = []
            for index in range(frames):
                started = time.perf_counter(); callback(index)
                settle(); window.canvas.viewport().grab()
                samples.append((time.perf_counter()-started)*1000)
            QTest.qWait(220)
            after = state()
            results['scenarios'][name] = {**statistics_ms(samples), 'operation': operation,
                                          'before': before, 'after': after}
            if errors:
                raise RuntimeError('Qt callback errors: ' + '; '.join(errors))

        keys = list(LABS)
        # Prewarm every existing template so record creation is not confused with
        # repeated switching or reported as a leak during the measured workload.
        for key in keys:
            window.mode_selector.setCurrentIndex(window.mode_selector.findData(key)); settle()
            assert window.mode == key
        QTest.qWait(220)

        def switch(index):
            key = keys[index % len(keys)]
            window.mode_selector.setCurrentIndex(window.mode_selector.findData(key))
            assert window.mode == key
        measure('function_category_switch', switch,
                'Select an existing template through the real QComboBox; templates prewarmed once.')

        window.mode_selector.setCurrentIndex(window.mode_selector.findData('custom'))
        # A bounded single-function project isolates editing work from rendering
        # all twenty prewarmed records. These are temporary in-memory records.
        function = Function('x^2')
        window.project = Project([function], [-6,6,-3,9], selected=function.id, mode='custom')
        window.reset_document(); QTest.qWait(220)
        sources = ('x² − 4', '2x + 1', 'sqrt(x)', '1/x', '2^x', 'log(x,2)', 'sin(x)')
        def edit(index):
            source = sources[index % len(sources)]
            row = window.rows[window.project.selected]
            row.input.setText(source); row.commit()
            assert window.current_function().expression == source
        measure('custom_formula_update', edit,
                'Set and commit one of the supported beginner examples in the real function row.')

        def panels(index):
            window.editor_dock.setVisible(index % 2 == 0)
            window.inspector_dock.setVisible(index % 2 != 0)
        measure('editor_and_analysis_panels', panels,
                'Alternate the visibility of the existing editor and analysis docks.')
        window.editor_dock.show(); window.inspector_dock.hide(); settle()

        window.use_example('x^2');settle()
        viewport=window.canvas.viewport()
        def mouse_drag(index):
            before=window.canvas.current_view()
            point=QPointF(viewport.rect().center())
            global_point=QPointF(viewport.mapToGlobal(viewport.rect().center()))
            direction=1 if index%2==0 else -1
            def send(kind,offset,button,buttons):
                delta=QPointF(direction*offset,0)
                event=QMouseEvent(kind,point+delta,global_point+delta,button,buttons,Qt.NoModifier)
                app.sendEvent(viewport,event);app.processEvents()
            send(QEvent.MouseButtonPress,0,Qt.LeftButton,Qt.LeftButton)
            for offset in (5,15,25):send(QEvent.MouseMove,offset,Qt.NoButton,Qt.LeftButton)
            send(QEvent.MouseButtonRelease,25,Qt.LeftButton,Qt.NoButton)
            assert window.canvas.current_view()[0]!=before[0], 'Mouse drag did not move the actual viewport'
        measure('mouse_drag_gesture',mouse_drag,
                'Deliver a real Qt mouse press, three moves and release through the viewport; assert a changed X range.')

        measure('theme_change', lambda index: window.set_theme('dark' if index % 2 == 0 else 'light'),
                'Apply alternating light/dark themes through MainWindow.set_theme.')
        window.set_theme('light'); settle()
        measure('repeated_zoom_in_out', lambda index: window.canvas.viewbox.scaleBy((.8,.8) if index % 2 == 0 else (1.25,1.25)),
                'Alternate reciprocal ViewBox zoom factors without resetting the function.')
        measure('window_resize', lambda index: window.resize(820,620) if index % 2 == 0 else window.resize(1400,850),
                'Alternate narrow and standard window sizes while the graph is visible.')
        results['status'] = 'passed'
        results['callback_errors'] = errors
        results['final_state'] = state()
        return results
    finally:
        if window is not None:
            window.confirm_discard = lambda: True
            window.close(); app.processEvents()
        sys.excepthook = previous_hook
        temporary.cleanup()
        if errors:
            raise RuntimeError('Qt callback errors: '+'; '.join(errors))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=int, default=30)
    parser.add_argument('--output', type=Path, default=Path('artifacts/audit/extended-benchmark.json'))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run(max(10, args.frames))
    except Exception as error:
        args.output.write_text(json.dumps({'status': 'failed', 'error': str(error)}, ensure_ascii=False, indent=2), encoding='utf-8')
        raise
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
