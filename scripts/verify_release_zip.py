"""Validate the portable Windows archive before uploading or publishing it."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import struct
import zipfile


def verify(path: Path, checksum_path: Path) -> dict:
    entries=checksum_path.read_text(encoding='ascii').splitlines()
    matches=[line.split()[0] for line in entries if len(line.split())==2 and line.split()[1]==path.name]
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if len(matches)!=1 or matches[0].lower()!=digest:
        raise ValueError('Archive SHA256 does not match the checksum file')
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:raise ValueError('Archive CRC verification failed')
        names=archive.namelist()
        if len(set(names))!=len(names):raise ValueError('Duplicate archive members')
        for name in names:
            member=PurePosixPath(name)
            if member.is_absolute() or '..' in member.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe archive path')
        required=['MathLab/MathLab.exe','MathLab/LICENSE','MathLab/THIRD_PARTY_NOTICES.md',
                  'MathLab/ПОСІБНИК.md','MathLab/_internal/licenses/inventory.json']
        for name in required:
            if name not in names or not archive.read(name):raise ValueError('Missing portable component: '+name)
        if not any(name.endswith('/qwindows.dll') for name in names):raise ValueError('Missing Windows Qt platform plugin')
        if not any(name.endswith('/python312.dll') for name in names):raise ValueError('Missing portable Python runtime')
        exe=archive.read('MathLab/MathLab.exe')
        if len(exe)<64 or exe[:2]!=b'MZ':raise ValueError('Not a Windows executable')
        pe_offset=struct.unpack_from('<I',exe,0x3c)[0]
        if pe_offset+6>len(exe) or exe[pe_offset:pe_offset+4]!=b'PE\0\0':raise ValueError('Missing PE header')
        if struct.unpack_from('<H',exe,pe_offset+4)[0]!=0x8664:raise ValueError('Executable is not Windows AMD64')
    return {'sha256':digest,'members':len(names),'windows_amd64':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path);parser.add_argument('checksums',type=Path)
    args=parser.parse_args()
    print(verify(args.archive,args.checksums))
