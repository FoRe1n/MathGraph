"""Capture real MathLab Qt screenshots for the stabilization visual review.

No mockups are generated. Temporary settings avoid changing user preferences.
The manifest records each capture's dimensions and scenario. Use
MATHLAB_BENCH_SOURCE to inspect an archived implementation with the same runner.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('XDG_CACHE_HOME', str(Path(tempfile.gettempdir()) / 'mathlab-audit-cache'))
sys.path.insert(0, os.environ.get('MATHLAB_BENCH_SOURCE', str(Path(__file__).resolve().parents[1])))


def run(output, dpi_only=False):
    from PySide6.QtGui import QRawFont
    from PySide6.QtCore import QSettings
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QPushButton, QLabel, QLineEdit, QAbstractButton, QComboBox, QWidget
    from graphmath.app.localization import install_ukrainian
    from graphmath.core.laboratories import LABS
    from graphmath.persistence.projects import Function, Project
    from graphmath.ui.dialogs import ExportDialog, SettingsDialog
    from graphmath.ui.window import MainWindow
    from graphmath.ui.theme import ui_text_has_glyphs

    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion'); install_ukrainian(app)
    output.mkdir(parents=True, exist_ok=True)
    captures = []
    glyph_coverage = {}
    probe = 'MathLab0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzАБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯабвгґдеєжзиіїйклмнопрстуфхцчшщьюя→↑−'
    callback_errors = []
    previous_hook = sys.excepthook
    def record_callback_error(kind, value, traceback):
        callback_errors.append(f'{kind.__name__}: {value}')
        previous_hook(kind, value, traceback)
    sys.excepthook = record_callback_error
    with tempfile.TemporaryDirectory(prefix='mathlab-visual-audit-') as temp:
        window = MainWindow(QSettings(str(Path(temp) / 'settings.ini'), QSettings.IniFormat))
        window.show(); QTest.qWait(260)
        try:
            def capture(name, target=None, description=''):
                widget = target or window
                app.processEvents(); QTest.qWait(180)
                if callback_errors:
                    raise RuntimeError('Qt callback errors: '+'; '.join(callback_errors))
                fonts = [widget.font()] + [child.font() for child in widget.findChildren(QPushButton) if child.isVisible()]
                for font in fonts:
                    key = font.toString()
                    if key in glyph_coverage:continue
                    raw = QRawFont.fromFont(font)
                    glyphs = raw.glyphIndexesForString(probe) if raw.isValid() else []
                    missing = [character for character, glyph in zip(probe,glyphs) if glyph == 0]
                    if not raw.isValid() or len(glyphs) != len(probe) or missing:
                        raise RuntimeError(f'Qt UI font cannot render Latin/Ukrainian text: {key}; missing {missing!r}')
                    glyph_coverage[key] = {'family':raw.familyName(),'probe_characters':len(probe),'missing_glyphs':0}
                for child in widget.findChildren(QWidget):
                    if not child.isVisible() or not isinstance(child,(QLabel,QLineEdit,QAbstractButton,QComboBox)):continue
                    raw=QRawFont.fromFont(child.font())
                    texts=[child.itemText(i) for i in range(child.count())] if isinstance(child,QComboBox) else [child.text()]
                    for text in texts:
                        if not text:continue
                        if not ui_text_has_glyphs(child.font(),text):
                            raise RuntimeError(f'Missing actual control glyphs in {name}: {text!r}')
                path = output / (name + '.png')
                pixmap = widget.grab()
                if pixmap.isNull() or not pixmap.save(str(path)):
                    raise RuntimeError('Screenshot capture failed: '+name)
                captures.append({'file': path.name, 'width': pixmap.width(), 'height': pixmap.height(),
                                 'device_pixel_ratio': pixmap.devicePixelRatio(),
                                 'theme': window.preferences['theme'], 'scale': window.preferences['scale'],
                                 'mode': window.mode, 'description': description, 'control_text_glyphs_verified':True})

            def selector_captures(prefix):
                window.mode_selector.showPopup()
                view = window.mode_selector.view()
                view.scrollToTop()
                capture(prefix+'-top', target=view.window(), description='Real function popup: first groups, disabled headers.')
                view.scrollToBottom()
                capture(prefix+'-bottom', target=view.window(), description='Real function popup: final groups and custom option.')
                window.mode_selector.hidePopup()

            if dpi_only:
                for theme in ('light', 'dark'):
                    window.set_theme(theme)
                    window.mode_selector.setCurrentIndex(window.mode_selector.findData('quadratic'))
                    capture('coefficients-'+theme, description='Coefficient controls at native Qt display scaling.')
                    selector_captures('dropdown-'+theme)
                    window.mode_selector.setCurrentIndex(window.mode_selector.findData('logarithmic_scale'))
                    app.processEvents()
                    bar = window.pages.widget(0).verticalScrollBar()
                    bar.setValue(bar.maximum())
                    capture('explanation-'+theme, description='Long mathematical explanation at native Qt display scaling.')
                    window.mode_selector.setCurrentIndex(window.mode_selector.findData('custom'))
                    capture('custom-'+theme)
                    values = {**window.preferences, 'grid': window.project.grid, 'axes': window.project.axes}
                    dialog = SettingsDialog(window, values); dialog.show()
                    capture('settings-'+theme, target=dialog)
                    dialog.close(); dialog.deleteLater()
                window.mode_selector.setCurrentIndex(window.mode_selector.findData('vertex'))
                window.resize(780,540)
                capture('narrow-dark', description='Narrow window at native Qt display scaling.')
                (output/'font-coverage.json').write_text(json.dumps(glyph_coverage,ensure_ascii=False,indent=2),encoding='utf-8')
                return captures

            capture('startup', description='Unmodified default startup screen.')
            for theme in ('light', 'dark'):
                window.set_theme(theme)
                for key in LABS:
                    window.mode_selector.setCurrentIndex(window.mode_selector.findData(key))
                    assert window.mode == key
                    capture(f'{key}-{theme}', description=LABS[key].title)
                window.mode_selector.setCurrentIndex(window.mode_selector.findData('logarithmic_scale'))
                app.processEvents()
                bar = window.pages.widget(0).verticalScrollBar()
                bar.setValue(bar.maximum())
                capture('long-explanation-'+theme, description='Long explanation scrolled into view; all mathematical sentences preserved.')
                window.mode_selector.setCurrentIndex(window.mode_selector.findData('custom'))
                function = Function('a*(x-h)^2+k')
                window.project = Project([function], [-6,6,-3,9], selected=function.id, mode='custom')
                window.reset_document()
                capture(f'custom-{theme}', description='Custom editor with automatic a, h, k sliders.')
                row = window.rows[window.project.selected]
                row.input.setText('sqrt('); row.commit()
                capture(f'custom-error-{theme}', description='Incomplete formula and Ukrainian error message.')
                row.input.setText('a*(x-h)^2+k'); row.commit()
                values = {**window.preferences, 'grid': window.project.grid, 'axes': window.project.axes}
                for name, dialog in [('settings', SettingsDialog(window, values)), ('export', ExportDialog(window))]:
                    dialog.show()
                    capture(f'{name}-{theme}', target=dialog, description='Existing '+name+' dialog.')
                    if name == 'settings':
                        advanced = next((button for button in dialog.findChildren(QPushButton)
                                         if button.isCheckable()), None)
                        if advanced:
                            advanced.setChecked(True)
                            capture(f'{name}-advanced-{theme}', target=dialog, description='Expanded existing settings.')
                    dialog.close(); dialog.deleteLater()

            window.set_theme('light')
            window.mode_selector.setCurrentIndex(window.mode_selector.findData('vertex'))
            window.learning.controls['h'].value.setValue(3)
            window.learning.controls['k'].value.setValue(2)
            window.reset_view()
            capture('transformed-vertex', description='a=1, h=3, k=2; vertex at (3,2).')
            window.canvas.viewbox.scaleBy((.25,.25))
            capture('zoomed-in', description='Quarter-size viewport spans after zooming in.')
            window.canvas.viewbox.scaleBy((16,16))
            capture('zoomed-out', description='Four times reset viewport spans after zooming out.')
            if hasattr(window, 'show_ranges'):
                window.show_ranges(True)
                capture('coordinate-ranges', description='Expanded existing manual X/Y controls.')
                window.show_ranges(False)

            for scale in ('100%', '125%', '150%'):
                window.preferences['scale'] = scale
                for theme in ('light', 'dark'):
                    window.set_theme(theme); window.resize(780,540)
                    capture(f'narrow-{scale[:-1]}-{theme}', description='Minimum-size window with text scaling.')
                    selector_captures(f'dropdown-{scale[:-1]}-{theme}')
            (output/'font-coverage.json').write_text(json.dumps(glyph_coverage,ensure_ascii=False,indent=2),encoding='utf-8')
            return captures
        finally:
            window.confirm_discard = lambda: True
            window.close(); app.processEvents()
            sys.excepthook = previous_hook
            if callback_errors:
                raise RuntimeError('Qt callback errors: '+'; '.join(callback_errors))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('artifacts/audit/screenshots'))
    parser.add_argument('--dpi-only', action='store_true', help='Focused screenshots in a fresh process using QT_SCALE_FACTOR.')
    args = parser.parse_args()
    (args.output/'manifest.json').unlink(missing_ok=True)
    captures = run(args.output, args.dpi_only)
    manifest = {'status': 'passed', 'real_qt_captures': len(captures), 'qt_backend': os.environ['QT_QPA_PLATFORM'],
                'qt_scale_factor': os.environ.get('QT_SCALE_FACTOR', '1'),
                'source_root': str(Path(sys.path[0]).resolve()), 'captures': captures}
    (args.output/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': 'passed', 'captures': len(captures), 'output': str(args.output)}))
