# MathLab Windows builds

Build on Windows x64 with Python 3.12 and the existing hash-locked dependencies.
The internal package and spec filename remain compatible with GraphMath. Version
1.1.5 provides a single-file EXE and preserves the known-working folder ZIP.
PyInstaller cannot cross-compile Linux to Windows.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --require-hashes -r requirements-windows.lock
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m graphmath --smoke-test
.venv\Scripts\python scripts/collect_licenses.py build/licenses

# Existing portable folder format
.venv\Scripts\python -m PyInstaller --noconfirm --clean GraphMath.spec
.venv\Scripts\python scripts/verify_distribution.py dist/MathLab

# Single executable; separate output/cache so the folder build is preserved
$env:GRAPHMATH_ONEFILE = '1'
.venv\Scripts\python -m PyInstaller --noconfirm --clean --distpath dist-onefile --workpath build/onefile GraphMath.spec
Remove-Item Env:GRAPHMATH_ONEFILE
.venv\Scripts\python scripts/verify_onefile.py dist-onefile/MathLab.exe

# Execute both formats twice, outside the checkout, without external Python
.venv\Scripts\python scripts/verify_frozen_app.py --onedir dist/MathLab/MathLab.exe --onefile dist-onefile/MathLab.exe --version 1.1.5

Copy-Item LICENSE,THIRD_PARTY_NOTICES.md dist/MathLab/
Copy-Item docs/user-guide.uk.md dist/MathLab/ПОСІБНИК.md
Compress-Archive -Path dist/MathLab -DestinationPath MathLab-v1.1.5-Windows-x64.zip
Copy-Item dist-onefile/MathLab.exe MathLab-v1.1.5-Windows-x64-OneFile.exe
$names = @('MathLab-v1.1.5-Windows-x64.zip', 'MathLab-v1.1.5-Windows-x64-OneFile.exe')
$sums = foreach ($name in $names) {
    $hash = (Get-FileHash $name -Algorithm SHA256).Hash.ToLower()
    "$hash  $name"
}
$sums | Set-Content -Encoding ascii SHA256SUMS.txt
.venv\Scripts\python scripts/verify_release_zip.py MathLab-v1.1.5-Windows-x64.zip SHA256SUMS.txt
.venv\Scripts\python scripts/verify_onefile.py MathLab-v1.1.5-Windows-x64-OneFile.exe --checksums SHA256SUMS.txt
```

The GitHub Actions workflow uses Windows Server 2022 x64. It runs all tests,
offscreen interaction benchmarks, source smoke and actual Qt screenshots at
100%, 125% and 150% display scaling before building both distributions. Package
checks verify the AMD64 executable, Python runtime, Qt Windows platform plugin,
Inter and mathematical fonts, icon, Ukrainian translations, dependency modules
and licenses. The one-file verifier opens the embedded PyInstaller archive and
validates its members; this structural inspection does not replace native launch.
An isolated checkout of the published v1.1.4 tag runs through the same unchanged
benchmark drivers, locked dependencies and runner before the final source, with
30 interaction actions, 400 prolonged steps and 20 extended actions per scenario.
Baseline and final JSON files remain separate; shared-runner variability is not
treated as a guaranteed performance bound.

The native execution check launches each format twice from a new temporary working
directory: first with the offscreen Qt backend, then with the real Windows platform
plugin. The ready and smoke results record and verify the actual backend, so the
second launch checks that qwindows.dll can initialize rather than only checking
that its file is present. Only Windows directories remain on PATH; PYTHONPATH and PYTHONHOME are
removed. Smoke tests exercise all twenty templates, actual coefficient controls,
plotting, analysis subprocess, project saving/loading, glyphs and PNG/SVG/PDF
export. Persistent smoke settings/projects go to the explicitly supplied output
directory, outside the extracted bundle, and must survive exit. Normal settings
continue to use native `QSettings("GraphMath", "GraphMath")` storage in the user's
Windows registry; project files use the user's chosen location. Resources resolve
relative to bundled modules in development and frozen builds. No persistent user
data is written to PyInstaller's `_MEI...` extraction directory. The check also
verifies the one-file temporary bundle is removed after normal shutdown.

`artifacts/packaged-validation/summary.json` records process-start-to-first-ready-
window latency for each launch. This includes one-file extraction and imports;
it excludes the subsequent smoke workload. Compare folder versus single-file
within the same backend; the first/second launches use different backends and are
not a controlled cold/warm disk or antivirus cache comparison. One-file
startup may be slower than the folder build because resources must be extracted
on every launch. Unsigned applications may trigger antivirus reputation warnings;
CI does not establish behavior for every antivirus product.

Pull requests and branch pushes build validation artifacts. The reviewed source
is released only after successful native checks. Tag **mathlab-v1.1.5** publishes:

- `MathLab-v1.1.5-Windows-x64-OneFile.exe`: one downloadable executable; no external
  Python or support folder is needed for execution.
- `MathLab-v1.1.5-Windows-x64.zip`: extract the complete folder and launch
  `MathLab.exe`; keep its `_internal` directory alongside it.
- `SHA256SUMS.txt`: checksums for both application formats.
- `MathLab-v1.1.5-validation.zip`: tests, benchmarks, source/frozen smoke results,
  resource reports, startup measurements and actual Qt screenshots.

The build job has read-only repository permission; only the gated release job
receives `contents: write`. Existing releases and tags are never overwritten.
Publication and actual native results are recorded in the release audit only
after independently downloading the assets.

Both formats use the same dynamically linked Qt libraries and resource files.
The one-file bootloader extracts those libraries temporarily; the folder ZIP
keeps them separately replaceable for LGPL users. Source and the build recipe
above remain available for rebuilding either distribution. The bundled notices
include Qt, Python, dependency and Inter SIL Open Font License information.
Physical Windows 11 monitor/DPI/compositor behavior, code signing, antivirus
reputation and hardware FPS remain outside automated offscreen verification.
