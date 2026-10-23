"""Fail packaging if runtime, resources, licenses or Qt's platform plugin is missing."""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv)>1 else 'dist/GraphMath')
windows = sys.platform == 'win32'
required = [root / ('GraphMath.exe' if windows else 'GraphMath'),
            root / '_internal' / 'LICENSE', root / '_internal' / 'THIRD_PARTY_NOTICES.md',
            root / '_internal' / 'licenses' / 'inventory.json']
for path in required:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f'Missing required packaged file: {path}')
platform_plugin = 'qwindows.dll' if windows else 'libqoffscreen.so'
if not list(root.rglob(platform_plugin)):
    raise SystemExit(f'Missing Qt platform plugin: {platform_plugin}')
if not list(root.rglob('DejaVuSans.ttf')):
    raise SystemExit('Missing MathText fonts')
print('Verified executable, Qt platform plugin, MathText fonts and notices.')
