"""Fail packaging if runtime, resources, licenses or Qt's platform plugin is missing."""
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv)>1 else 'dist/MathLab')
windows = sys.platform == 'win32'
required = [root / (root.name+'.exe' if windows else root.name),
            root / '_internal' / 'LICENSE', root / '_internal' / 'THIRD_PARTY_NOTICES.md',
            root / '_internal' / 'licenses' / 'inventory.json']
for path in required:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f'Missing required packaged file: {path}')
platform_plugin = 'qwindows.dll' if windows else 'libqoffscreen.so'
if not list(root.rglob(platform_plugin)):
    raise SystemExit(f'Missing Qt platform plugin: {platform_plugin}')
if any(not list(root.rglob(name)) for name in ('DejaVuSans.ttf','DejaVuSans-Bold.ttf','DejaVuSans-Oblique.ttf','DejaVuSans-BoldOblique.ttf')):
    raise SystemExit('Missing MathText fonts')
for name in ('Inter-Regular.ttf','Inter-Medium.ttf','Inter-SemiBold.ttf','Inter-OFL.txt','icon.ico'):
    if not any(path.is_file() and path.stat().st_size for path in root.rglob(name)):
        raise SystemExit('Missing application resource: '+name)
print('Verified executable, Qt platform plugin, Inter/MathText fonts, icon and notices.')

if not list(root.rglob('qtbase_uk.qm')):
    raise SystemExit('Missing Ukrainian Qt dialog translations')
