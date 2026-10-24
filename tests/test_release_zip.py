import hashlib
import importlib.util
from pathlib import Path
import struct
import zipfile
import pytest

spec=importlib.util.spec_from_file_location('verify_release_zip',Path(__file__).parents[1]/'scripts/verify_release_zip.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def archive(tmp_path,machine=0x8664,missing=None):
    exe=bytearray(256);exe[:2]=b'MZ';struct.pack_into('<I',exe,0x3c,128)
    exe[128:132]=b'PE\0\0';struct.pack_into('<H',exe,132,machine)
    members={'MathLab/MathLab.exe':exe,'MathLab/LICENSE':b'license',
             'MathLab/THIRD_PARTY_NOTICES.md':b'notices','MathLab/ПОСІБНИК.md':b'guide',
             'MathLab/_internal/licenses/inventory.json':b'{}',
             'MathLab/_internal/PySide6/plugins/platforms/qwindows.dll':b'plugin',
             'MathLab/_internal/python312.dll':b'runtime'}
    if missing:del members[missing]
    path=tmp_path/'MathLab-v1.1.0-Windows-x64.zip'
    with zipfile.ZipFile(path,'w') as z:
        for name,data in members.items():z.writestr(name,data)
    sums=tmp_path/'SHA256SUMS.txt';sums.write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n')
    return path,sums


def test_valid_release_structure(tmp_path):
    result=module.verify(*archive(tmp_path))
    assert result['windows_amd64'] and result['members']==7


def test_wrong_architecture_fails(tmp_path):
    with pytest.raises(ValueError,match='AMD64'):module.verify(*archive(tmp_path,machine=0x14c))


def test_missing_runtime_fails(tmp_path):
    with pytest.raises(ValueError,match='runtime'):module.verify(*archive(tmp_path,missing='MathLab/_internal/python312.dll'))


def test_tampered_archive_fails(tmp_path):
    path,sums=archive(tmp_path)
    with zipfile.ZipFile(path,'a') as z:z.writestr('MathLab/extra',b'tampered')
    with pytest.raises(ValueError,match='SHA256'):module.verify(path,sums)
