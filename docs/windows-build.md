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
Copy-Item LICENSE,THIRD_PARTY_NOTICES.md dist/MathLab/
Copy-Item docs/user-guide.uk.md dist/MathLab/ПОСІБНИК.md
Compress-Archive dist/MathLab MathLab-v1.1.1-Windows-x64.zip
$hash = (Get-FileHash MathLab-v1.1.1-Windows-x64.zip -Algorithm SHA256).Hash.ToLower()
"$hash  MathLab-v1.1.1-Windows-x64.zip" | Set-Content -Encoding ascii SHA256SUMS.txt
.venv\Scripts\python scripts/verify_release_zip.py MathLab-v1.1.1-Windows-x64.zip SHA256SUMS.txt
```

PyInstaller cannot cross-compile Linux to Windows. The GitHub Actions workflow
uses Windows 2022 x64, runs all tests, offscreen interaction benchmarks, laboratory
and analysis startup checks, and captures real application screenshots. It builds
a windowed onedir bundle, verifies qwindows.dll, mathematical fonts, Ukrainian Qt
translations and license files, then runs the frozen EXE before making the ZIP.
Failure prevents release publication.

Pull requests build validation artifacts. After native Windows checks pass for the reviewed source,
tag **mathlab-v1.1.1** publishes **MathLab v1.1.1** and
`MathLab-v1.1.1-Windows-x64.zip` plus SHA256SUMS and `MathLab-v1.1.1-validation.zip`. The latter
contains Windows test XML, benchmarks, source/frozen smoke results and real Qt
screenshots. Existing MathLab v1.1.0/v1.0.0 and GraphMath v1.0.0 releases remain
unchanged. The build job has read-only repository permission; only
the release job receives `contents: write`. Existing releases are not overwritten.

The complete extracted folder is required; users double-click MathLab.exe without
Python or a terminal. Libraries and LGPL components stay dynamically replaceable.
Code signing, hardware FPS and physical Windows 10/11 visual QA are outside the
automated offscreen checks. The build is unsigned.
