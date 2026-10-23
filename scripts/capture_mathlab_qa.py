"""Capture the actual application, including every learning mode and dialogs."""
import os,sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('XDG_CACHE_HOME',str(Path(os.environ.get('TEMP','/tmp'))/'mathlab-cache'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from graphmath.ui.window import MainWindow
from graphmath.ui.dialogs import SettingsDialog,ExportDialog
from graphmath.app.localization import install_ukrainian

out=Path('artifacts/mathlab/visual-qa');out.mkdir(parents=True,exist_ok=True)
app=QApplication([]);app.setStyle('Fusion');install_ukrainian(app)
settings=QSettings(str(out/'settings.ini'),QSettings.IniFormat);settings.clear()
w=MainWindow(settings);w.show();QTest.qWait(260)
w.grab().save(str(out/'quadratic-light.png'))
w.learning.marker_button.setChecked(True)
w.learning.toggles['vertex'].setChecked(True);w.learning.toggles['zeros'].setChecked(True)
w.learning.controls['b'].value.setValue(-2)
w.learning.controls['c'].value.setValue(-3)
w.reset_view()
QTest.qWait(260);w.grab().save(str(out/'quadratic-markers.png'))
for key in ['exponential','logarithmic']:
    w.mode_selector.setCurrentIndex(w.mode_selector.findData(key));QTest.qWait(260)
    w.grab().save(str(out/f'{key}-light.png'))
w.toggle_theme();QTest.qWait(200);w.grab().save(str(out/'logarithmic-dark.png'))
w.mode_selector.setCurrentIndex(w.mode_selector.findData('custom'));w.add_function()
row=w.rows[w.project.selected];row.input.setText('x² − 4');row.commit();QTest.qWait(260)
w.grab().save(str(out/'custom-dark.png'))
w.toggle_theme();w.mode_selector.setCurrentIndex(w.mode_selector.findData('quadratic'))
w.resize(820,620);QTest.qWait(260);w.grab().save(str(out/'narrow.png'))
for name,dialog in [('settings',SettingsDialog(w,{**w.preferences,'grid':True,'axes':True})),('export',ExportDialog(w))]:
    dialog.show();QTest.qWait(100);dialog.grab().save(str(out/f'{name}.png'));dialog.close()
w.confirm_discard=lambda:True;w.close()
print('Captured nine real MathLab Qt screenshots in',out)
