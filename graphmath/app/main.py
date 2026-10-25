from __future__ import annotations
import argparse
import json
import multiprocessing
import os
from pathlib import Path
import sys


def main():
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description="MathLab 1.1")
    parser.add_argument("project", nargs="?")
    parser.add_argument("--smoke-test", action="store_true", help="Launch, exercise exports and project I/O, then exit")
    parser.add_argument("--smoke-output", default="artifacts/smoke")
    args = parser.parse_args()
    if args.smoke_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QTimer, QSettings, QEventLoop
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from graphmath.ui.window import MainWindow
    app = QApplication(sys.argv[:1])
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[1] / "resources" / "icon.ico")))
    app.setApplicationName("MathLab")
    from graphmath.app.localization import install_ukrainian
    install_ukrainian(app)
    app.setApplicationVersion("1.1.3")
    app.setOrganizationName("GraphMath")
    app.setStyle("Fusion")
    output = Path(args.smoke_output)
    if args.smoke_test:
        output.mkdir(parents=True, exist_ok=True)
        settings = QSettings(str(output / "smoke-settings.ini"), QSettings.IniFormat)
        settings.clear()
        window = MainWindow(settings)
    else:
        window = MainWindow()
    if args.project:
        window.open_project(args.project)
    window.show()
    if args.smoke_test:
        def smoke():
            from graphmath.persistence.projects import save, load
            from graphmath.plotting.export import export_graph
            from graphmath.core.expressions import evaluate
            import numpy as np
            try:
                from PySide6.QtGui import QRawFont
                from graphmath.ui.theme import UI_REQUIRED_GLYPHS
                assert all(QRawFont.fromFont(window.font()).glyphIndexesForString(UI_REQUIRED_GLYPHS)), "UI glyph coverage failed"
                window.canvas.refresh()
                save(window.project, output / "workspace.graphmath")
                assert load(output / "workspace.graphmath").to_dict() == window.project.to_dict()
                assert np.allclose(evaluate("x^2 - 4", np.array([-2., 0., 2.])), [0, -4, 0])
                from graphmath.core.laboratories import LABS, identify
                for mode in LABS:
                    window.mode_selector.setCurrentIndex(window.mode_selector.findData(mode))
                    window.canvas.flush_refresh()
                    assert identify(window.current_function()) == mode
                    assert window.learning.formula.pixmap() is not None
                    save(window.project, output / (mode+'.graphmath'))
                    assert load(output / (mode+'.graphmath')).mode == mode
                # Exercise the original laboratories, then the preserved custom-analysis path.
                for mode, values in [('quadratic', {'a': 2., 'b': 0., 'c': -4.}),
                                     ('exponential', {'a': 1., 'b': .5, 'c': 0.}),
                                     ('logarithmic', {'a': 1., 'b': 2., 'h': 1., 'k': 0.})]:
                    window.mode_selector.setCurrentIndex(window.mode_selector.findData(mode))
                    for name,value in values.items():window.lab_coefficient_changed(name,value)
                    window.canvas.flush_refresh()
                    assert window.current_function().parameters['b'].value == values['b']
                window.mode_selector.setCurrentIndex(window.mode_selector.findData('custom'))
                window.edit_function(window.project.selected,'x^2 - 4')
                window.canvas.refresh()
                window.investigate()
                loop = QEventLoop()
                check = QTimer()
                check.setInterval(50)
                check.timeout.connect(lambda: loop.quit() if window.inspector.result is not None or window.inspector.process is None else None)
                check.start()
                QTimer.singleShot(11000, loop.quit)
                loop.exec()
                check.stop()
                assert window.inspector.result is not None, window.inspector.status.text()
                assert len(window.inspector.result["zeros"]) == 2
                for suffix in ["png", "svg", "pdf"]:
                    export_graph(window.canvas, str(output / f"graph.{suffix}"))
                window.grab().save(str(output / "workspace-light.png"))
                window.toggle_theme()
                app.processEvents()
                window.grab().save(str(output / "workspace-dark.png"))
                (output / "result.json").write_text(json.dumps({"status": "passed", "version": "1.1.3", "exports": ["png", "svg", "pdf"], "project_roundtrip": True, "analysis_subprocess": True, "laboratory_modes": list(LABS), "application": "MathLab", "ui_font": app.mathlab_ui_font, "ui_glyph_coverage": True}), encoding="utf-8")
                window.flush_inputs()
                window.saved_state = window.serialized()
                window.close()
                app.exit(0)
            except Exception:
                import traceback
                (output / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
                app.exit(1)
        QTimer.singleShot(600, smoke)
    return app.exec()
