"""Check real PyInstaller archive inspection using a tiny embedded test archive."""
import hashlib
import importlib.util
from pathlib import Path
import struct

import pytest
from PyInstaller.archive.writers import CArchiveWriter, ZlibArchiveWriter

spec = importlib.util.spec_from_file_location('verify_onefile', Path(__file__).parents[1]/'scripts/verify_onefile.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def executable(tmp_path, missing_resource=None, missing_module=None, machine=0x8664):
    resources = [
        'python312.dll', 'PySide6/plugins/platforms/qwindows.dll',
        'graphmath/resources/icon.ico', 'graphmath/resources/qtbase_uk.qm',
        'graphmath/resources/licenses/Inter-OFL.txt', 'licenses/inventory.json',
        'LICENSE', 'THIRD_PARTY_NOTICES.md',
        'graphmath/resources/fonts/Inter-Regular.ttf',
        'graphmath/resources/fonts/Inter-Medium.ttf',
        'graphmath/resources/fonts/Inter-SemiBold.ttf',
        'matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf',
        'matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf',
        'matplotlib/mpl-data/fonts/ttf/DejaVuSans-Oblique.ttf',
        'matplotlib/mpl-data/fonts/ttf/DejaVuSans-BoldOblique.ttf',
    ]
    source = tmp_path/'component'; source.write_bytes(b'test component')
    modules = ['graphmath.app.main', 'numpy', 'sympy', 'pyqtgraph', 'PySide6', 'matplotlib']
    modules = [name for name in modules if name != missing_module]
    pyz = tmp_path/'PYZ.pyz'
    ZlibArchiveWriter(str(pyz), [(name, str(source), 'PYMODULE') for name in modules],
                      {name: compile('pass', '<test module>', 'exec') for name in modules})
    pkg = tmp_path/'archive.pkg'
    CArchiveWriter(str(pkg), [(name, str(source), True, 'b' if name.endswith('.dll') else 'x')
                             for name in resources if name != missing_resource]+[('PYZ.pyz', str(pyz), False, 'z')],
                   'python312.dll')
    header = bytearray(256); header[:2] = b'MZ'
    struct.pack_into('<I', header, 0x3c, 128)
    header[128:132] = b'PE\0\0'; struct.pack_into('<H', header, 132, machine)
    path = tmp_path/'MathLab.exe'; path.write_bytes(header+pkg.read_bytes())
    checksum = tmp_path/'SHA256SUMS.txt'
    checksum.write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'  MathLab.exe\n', encoding='ascii')
    return path, checksum


def test_embedded_windows_resources_and_imports_are_verified(tmp_path):
    result = module.verify(*executable(tmp_path))
    assert result['status'] == 'passed' and result['windows_amd64']
    assert 'sympy' in result['required_modules']
    assert 'graphmath/resources/licenses/Inter-OFL.txt' in result['required_resources']


@pytest.mark.parametrize('name', ['python312.dll', 'graphmath/resources/fonts/Inter-Regular.ttf',
                                 'graphmath/resources/licenses/Inter-OFL.txt'])
def test_onefile_missing_runtime_font_or_license_fails(tmp_path, name):
    with pytest.raises(ValueError, match='Missing embedded resource'):
        module.verify(*executable(tmp_path, missing_resource=name))


def test_onefile_missing_mathematics_module_fails(tmp_path):
    with pytest.raises(ValueError, match='sympy'):
        module.verify(*executable(tmp_path, missing_module='sympy'))


def test_onefile_wrong_architecture_fails(tmp_path):
    with pytest.raises(ValueError, match='AMD64'):
        module.verify(*executable(tmp_path, machine=0x14c))


def test_onefile_mismatched_public_checksum_fails(tmp_path):
    path, checksum = executable(tmp_path)
    checksum.write_text('0'*64+'  MathLab.exe\n', encoding='ascii')
    with pytest.raises(ValueError, match='SHA256'):
        module.verify(path, checksum)
