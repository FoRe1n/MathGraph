# Portable Windows build and release

Build on Windows x64, using Python 3.12 and the hash-locked Windows dependencies.
PyInstaller cannot produce a Windows executable from this Linux cloud machine.
The workflow `.github/workflows/windows.yml` is the authoritative recipe.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --require-hashes -r requirements-windows.lock
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m graphmath --smoke-test
.venv\Scripts\python scripts/collect_licenses.py build/licenses
.venv\Scripts\python -m PyInstaller --noconfirm --clean GraphMath.spec
.venv\Scripts\python scripts/verify_distribution.py dist/GraphMath
dist\GraphMath\GraphMath.exe --smoke-test --smoke-output artifacts/frozen-smoke
Compress-Archive dist/GraphMath GraphMath-v1.0.0-Windows-x64.zip
```

The onedir bundle dynamically loads Qt libraries, includes platform plugins,
Matplotlib math fonts, Python, NumPy/SymPy, documentation and full dependency
license notices. Keep the complete folder together. It uses a windowed bootloader
without a terminal. The multiprocessing entry point is guarded and freeze-aware.
Smoke mode starts the actual application offscreen, checks the analysis subprocess,
round-trips a project, exports three formats and writes explicit results. Native
interactive QA on Windows remains distinct from this automated startup test.

Pushes and pull requests build a downloadable workflow artifact. Pushing tag
`v1.0.0` additionally publishes **GraphMath v1.0.0** with the ZIP and SHA256SUMS,
only after tests and the frozen smoke check succeed. The build job has read-only
repository access; only the release job receives `contents: write`. Credentials
are supplied by GitHub, never embedded. Existing releases are not overwritten.

Lock refresh (requires uv) is intentional and reviewable:

```bash
uv pip compile pyproject.toml --extra dev --python-version 3.12 --python-platform windows --generate-hashes --output-file requirements-windows.lock
uv pip compile pyproject.toml --extra dev --python-version 3.12 --python-platform linux --generate-hashes --output-file requirements-linux.lock
```

If organization policies block Actions or publishing, an administrator must enable
the required workflow/token permission. Do not substitute an untested ZIP or label
a Linux binary as a Windows build. Code signing and a Windows installer are future
work; the initial release is a portable unsigned ZIP.
