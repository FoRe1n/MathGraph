# Build on the target OS: PyInstaller cannot cross-compile Linux -> Windows.
from pathlib import Path
import os
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH)
product = os.environ.get('GRAPHMATH_PRODUCT', 'MathLab')
assert product in ('MathLab','GraphMath')
onefile = os.environ.get('GRAPHMATH_ONEFILE', '0') == '1'
datas = collect_data_files('matplotlib') + collect_data_files('graphmath')
datas += [(str(root / 'LICENSE'), '.'), (str(root / 'THIRD_PARTY_NOTICES.md'), '.'),
          (str(root / 'docs'), 'docs'), (str(root / 'build' / 'licenses'), 'licenses')]
a = Analysis(
    [str(root / 'scripts' / 'launch.py')], pathex=[str(root)],
    binaries=[], datas=datas, hiddenimports=['pyqtgraph.exporters', 'matplotlib.backends.backend_agg'],
    hookspath=[], hooksconfig={'matplotlib': {'backends': ['Agg']}},
    excludes=['tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'IPython', 'notebook', 'scipy', 'pandas'],
    noarchive=False,
)
pyz = PYZ(a.pure)
options = dict(name=product, debug=False, bootloader_ignore_signals=False,
               strip=False, upx=False, console=False,
               disable_windowed_traceback=False,
               icon=str(root / 'graphmath' / 'resources' / 'icon.ico'))
if onefile:
    # PyInstaller owns the temporary extraction directory. Persistent settings
    # continue to use QSettings and projects use the user's chosen paths.
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **options)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **options)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=product)
