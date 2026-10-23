# MathLab portable Windows build

Build on Windows x64 with Python 3.12 and the existing hash-locked dependency set.
The internal package and spec filename remain compatible with GraphMath:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --require-hashes -r requirements-windows.lock
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m graphmath --smoke-test
.venv\Scripts\python scripts/collect_licenses.py build/licenses
.venv\Scripts\python -m PyInstaller --noconfirm --clean GraphMath.spec
.venv\Scripts\python scripts/verify_distribution.py dist/MathLab
dist\MathLab\MathLab.exe --smoke-test --smoke-output artifacts/frozen-smoke
Compress-Archive dist/MathLab MathLab-v1.0.0-Windows-x64.zip
```

PyInstaller cannot cross-compile Linux to Windows. The GitHub Actions workflow
uses Windows 2022 x64, runs all tests, offscreen interaction benchmarks, laboratory
and analysis startup checks, and captures real application screenshots. It builds
a windowed onedir bundle, verifies qwindows.dll, mathematical fonts, Ukrainian Qt
translations and license files, then runs the frozen EXE before making the ZIP.
Failure prevents release publication.

Pull requests build validation artifacts. After validated changes are merged,
tag **mathlab-v1.0.0** publishes **MathLab v1.0.0** and
`MathLab-v1.0.0-Windows-x64.zip` plus SHA256SUMS. The old `v1.0.0` tag and GraphMath
release are not changed. The build job has read-only repository permission; only
the release job receives `contents: write`. Existing releases are not overwritten.

The complete extracted folder is required; users double-click MathLab.exe without
Python or a terminal. Libraries and LGPL components stay dynamically replaceable.
Code signing, hardware FPS and physical Windows 10/11 visual QA are outside the
automated offscreen checks. The build is unsigned.
