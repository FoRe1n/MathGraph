"""Inspect the single-file Windows EXE without executing untrusted archive code.

This verifies its embedded archive and dependencies; native execution is a
separate, required CI step in verify_frozen_app.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct


def verify(path: Path, checksum_path: Path | None = None) -> dict:
    from PyInstaller.archive.readers import CArchiveReader

    with path.open('rb') as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b'MZ':
            raise ValueError('Not a Windows executable')
        offset = struct.unpack_from('<I', header, 0x3c)[0]
        stream.seek(offset)
        pe = stream.read(6)
        if len(pe) != 6 or pe[:4] != b'PE\0\0':
            raise ValueError('Missing PE header')
        if struct.unpack_from('<H', pe, 4)[0] != 0x8664:
            raise ValueError('Executable is not Windows AMD64')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if checksum_path is not None:
        matches = [line.split()[0].lower() for line in checksum_path.read_text(encoding='ascii').splitlines()
                   if len(line.split()) == 2 and line.split()[1] == path.name]
        if matches != [digest]:
            raise ValueError('EXE SHA256 does not match the checksum file')
    archive = CArchiveReader(str(path))
    normalized = {name.replace('\\', '/'): name for name in archive.toc}
    if len(normalized) != len(archive.toc):
        raise ValueError('Duplicate normalized archive paths')
    for name in normalized:
        member = PurePosixPath(name)
        if member.is_absolute() or '..' in member.parts or ':' in name:
            raise ValueError('Unsafe archive path')
    resources = [
        'python312.dll', 'PySide6/plugins/platforms/qwindows.dll',
        'graphmath/resources/icon.ico', 'graphmath/resources/qtbase_uk.qm',
        'graphmath/resources/licenses/Inter-OFL.txt', 'licenses/inventory.json',
        'LICENSE', 'THIRD_PARTY_NOTICES.md',
        *('graphmath/resources/fonts/Inter-'+face+'.ttf' for face in ('Regular','Medium','SemiBold')),
        *('matplotlib/mpl-data/fonts/ttf/'+face+'.ttf' for face in (
            'DejaVuSans','DejaVuSans-Bold','DejaVuSans-Oblique','DejaVuSans-BoldOblique')),
    ]
    for name in resources:
        if name not in normalized or not archive.extract(normalized[name]):
            raise ValueError('Missing embedded resource: '+name)
    # Reading all entries also catches truncated/invalid compressed members.
    for name, entry in archive.toc.items():
        if entry[-1] in ('b', 'x', 's', 'm', 'M', 'z'):
            data = archive.extract(name)
            if len(data) != entry[2]:
                raise ValueError('Embedded member size mismatch: '+name)
    pyz_names = [name for name, entry in archive.toc.items() if entry[-1] == 'z']
    if len(pyz_names) != 1:
        raise ValueError('Expected one embedded Python module archive')
    pyz = archive.open_embedded_archive(pyz_names[0])
    modules = ['graphmath.app.main', 'numpy', 'sympy', 'pyqtgraph', 'PySide6', 'matplotlib']
    for name in modules:
        if name not in pyz.toc:
            raise ValueError('Missing bundled Python module: '+name)
    return {'status': 'passed', 'sha256': digest, 'bytes': path.stat().st_size,
            'windows_amd64': True, 'embedded_members': len(archive.toc),
            'required_resources': resources, 'required_modules': modules}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--checksums', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify(args.executable, args.checksums)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
