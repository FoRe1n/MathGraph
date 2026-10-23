"""Real Qt screenshots for light/dark, analysis, parameters and narrow layouts."""
from pathlib import Path
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from graphmath.ui.window import MainWindow
from graphmath.ui.dialogs import ExportDialog, SettingsDialog
from graphmath.analysis.symbolic import analyze

out=Path('artifacts/visual-qa')
out.mkdir(parents=True,exist_ok=True)
app=QApplication([])
app.setStyle('Fusion')
settings=QSettings(str(out/'settings.ini'),QSettings.IniFormat)
settings.clear()
w=MainWindow(settings)
w.show()
app.processEvents()
w.canvas.refresh()
w.grab().save(str(out/'light.png'))
w.toggle_inspector()
w.inspector.result=analyze('x^2-4')
for title,value in w.inspector.result['properties'].items():
 from PySide6.QtWidgets import QLabel
 label=QLabel(f'{title}\n{value}')
 label.setWordWrap(True)
 w.inspector.properties.insertWidget(w.inspector.properties.count()-1,label)
w.inspector.toggles['zeros'].setChecked(True)
w.inspector.toggles['extrema'].setChecked(True)
app.processEvents()
w.grab().save(str(out/'analysis.png'))
w.inspector_dock.hide()
w.edit_function(w.project.selected,'a*x^2+b*x+c')
w.rows[w.project.selected].input.setText('a*x^2+b*x+c')
w.rows[w.project.selected].render()
app.processEvents()
w.canvas.refresh()
w.grab().save(str(out/'parameters.png'))
w.toggle_theme()
app.processEvents()
w.grab().save(str(out/'dark.png'))
w.resize(800,580)
app.processEvents()
w.grab().save(str(out/'narrow.png'))
e=ExportDialog(w)
e.show()
app.processEvents()
e.grab().save(str(out/'export-dialog.png'))
e.close()
d=SettingsDialog(w,{**w.preferences,'grid':w.project.grid,'axes':w.project.axes})
d.show()
app.processEvents()
d.grab().save(str(out/'settings-dialog.png'))
d.close()
w.confirm_discard=lambda: True
w.close()
print('Captured seven actual Qt screenshots in',out)
