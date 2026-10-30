# MathLab 1.1.5

An offline Ukrainian mathematics laboratory for high school students, evolved
incrementally from GraphMath in the existing **FoRe1n/MathGraph** repository.
Choose a function, move its coefficients, and see both the curve and an explanation.

![MathLab quadratic laboratory on Windows](docs/screenshots/mathlab-1.1.5-windows/startup.png)

## MathLab 1.1 changes

The existing workspace now includes a grouped **Оберіть функцію** selector with
20 templates: linear/direct/constant, vertical relations, inverse proportionality,
quadratic standard/square/vertex forms, cubic, absolute value, three square-root
orientations, original and transformed exponential/logarithmic forms, sine, cosine
and tangent. Original laboratories and version-1 projects remain supported.

Transformation controls explain horizontal and vertical movement; trigonometric
angles use radians. **Докладніше** reports properties for the current coefficients,
including degenerate cases. Vertical `x=c` relations render separately and are never
evaluated as `y=f(x)`. Tangent and rational paths retain discontinuity separators.

**Власна функція** offers clickable examples and automatic parameter sliders.
Coordinate ranges and point inspection live in the collapsed **Діапазон координат**
panel. Changing coefficients preserves zoom and pan. Existing multiple-function
editing, analysis, colors, visibility, history, themes and exports remain available.

Version 1.1.5 adds focused typography and packaging polish: bundled OFL-licensed
Inter, clearer coefficient/explanation spacing, distinct nonselectable dropdown
headings and a verified single-file EXE alongside the portable ZIP. The redundant
introductory instruction is removed. Mathematical algorithms, graph interaction,
custom editing and all twenty templates remain unchanged.
See the [polish audit, measurements and limits](docs/mathlab-v1.1.5-polish.md).
The previous [v1.1.4 stabilization audit](docs/mathlab-v1.1.4-audit.md) documents
the mathematical and reliability corrections retained by this version.

## Windows distribution

- **[Single-file MathLab v1.1.5 EXE](https://github.com/FoRe1n/MathGraph/releases/download/mathlab-v1.1.5/MathLab-v1.1.5-Windows-x64-OneFile.exe)** — 92.95 MB; run directly, with no support folder.
- **[Portable MathLab v1.1.5 ZIP](https://github.com/FoRe1n/MathGraph/releases/download/mathlab-v1.1.5/MathLab-v1.1.5-Windows-x64.zip)** — 95.29 MB; extract the entire folder and launch **MathLab.exe** beside `_internal`.

Neither format requires Python. One-file startup extracts libraries temporarily;
settings and saved projects stay outside that directory. On the native Windows
runner, launch to a prepared window took **4.86 s** for one-file and **3.36 s** for
the folder build using the normal Windows Qt plugin. These are individual CI
observations, with uncontrolled OS/antivirus cache state.

[Release, checksums and validation evidence](https://github.com/FoRe1n/MathGraph/releases/tag/mathlab-v1.1.5).
[Native Windows CI](https://github.com/FoRe1n/MathGraph/actions/runs/40896864509)
passed **511 tests**, comparable benchmarks and **101 real Qt captures** at
100/125/150% device scaling. Both packaged formats passed offscreen and real
Windows-plugin smoke checks outside the checkout with Python removed from PATH.
The public EXE/ZIP/evidence were independently downloaded and verified: SHA256,
all 1,574 ZIP entries, embedded modules/fonts/licences, AMD64 executables and
Windows icon resources. Native screenshots render readable Ukrainian text.

These checks used Windows Server 2022. Physical Windows 11 monitor/ClearType,
antivirus reputation and hardware FPS remain unverified. Builds are unsigned.
The audit records measured typography/layout costs, including slower theme
changes; it makes no blanket performance-improvement claim.

The [v1.1.4](https://github.com/FoRe1n/MathGraph/releases/tag/mathlab-v1.1.4) and
[v1.1.0](https://github.com/FoRe1n/MathGraph/releases/tag/mathlab-v1.1.0) releases
are preserved. Intermediate v1.1.1–v1.1.3 stabilization releases are superseded;
use v1.1.5 for testing.

### Preserved MathLab 1.0 release

**[Download MathLab v1.0.0 for Windows x64 (ZIP)](https://github.com/FoRe1n/MathGraph/releases/download/mathlab-v1.0.0/MathLab-v1.0.0-Windows-x64.zip)**
([release notes and SHA256](https://github.com/FoRe1n/MathGraph/releases/tag/mathlab-v1.0.0)).
Extract the entire folder and double-click **MathLab.exe**. Python is not required.

[Native Windows release CI](https://github.com/FoRe1n/MathGraph/actions/runs/39990444777)
passed all 147 tests, offscreen benchmarks, source/frozen smoke checks and resource
verification. The public ZIP was downloaded without authentication and its SHA256,
all ZIP entries and Windows AMD64 executable header were independently verified.

The original [GraphMath v1.0.0 release](https://github.com/FoRe1n/MathGraph/releases/tag/v1.0.0)
and its tag remain available. Internal `graphmath` imports, the expression engine,
PyQtGraph, NumPy/SymPy, existing analysis and project format are retained.

## Learning workspace

- **Quadratic:** y = ax² + bx + c; correct vertex, symmetry, intercept and degenerate
  cases, with optional graph markers.
- **Exponential:** y = a·bˣ + c; positive base excluding 1, growth/decay, reflection
  and translation explained from the actual coefficient values.
- **Logarithmic:** y = a·log_b(x − h) + k; safe bases, explicit x > h domain and
  shaded excluded region, shifts and reflection.
- **Custom functions:** the existing multiple-function editor, independent
  parameters, analysis, annotations, undo/redo, colors and visibility remain.
  Safe school notation includes `x²`, `2x`, `2(x+1)` and explicit `2*x`.

The graph dominates a light workspace. Five toolbar actions, readable formulas,
short Ukrainian explanations, adjustable sliders and a compact settings dialog
replace the former editor-first default. Dark mode remains available. No account,
API key, server or Internet connection is needed for ordinary use.

## Compatibility and performance

Old `.graphmath` files retain formulas, colors, parameters, visibility and ranges.
Version 1 remains in use; optional `mode` metadata defaults to `custom` for old
files. Old GraphMath readers ignore this additive field. No project migration is
required. The original regression cases remain in the test suite, with a dedicated
legacy workspace fixture and additional learning-mode tests.

Raster profiling identified axis/grid painting as a major cost. MathLab uses a
bounded grid, cached overscan samples, reused graphics, fast active interaction and
idle refinement. JSON history and formula previews are coalesced. Cursor inspection
is optional and no longer creates repeated tooltips or large crosshairs.
See [measurements and limitations](docs/mathlab-performance.md); no 60 FPS claim is made.

## Development

Python 3.12 is the reproducible build target; internal package and CLI remain
`graphmath` for compatibility. Run from the existing checkout:

```bash
python -m venv .venv
# Linux
.venv/bin/python -m pip install --require-hashes -r requirements-linux.lock
.venv/bin/python -m graphmath
# Windows PowerShell
.venv\Scripts\python -m pip install --require-hashes -r requirements-windows.lock
.venv\Scripts\python -m graphmath
```

Tests: `python -m pytest -q`. Source/frozen smoke mode:
`python -m graphmath --smoke-test --smoke-output artifacts/smoke`.
It checks all laboratories, the preserved analysis worker, project I/O and exports.
Real Qt screenshots: `python scripts/capture_stabilization_qa.py`.
Reproducible interaction measurements: `python scripts/benchmark_interaction.py`
and `python scripts/benchmark_stabilization.py`.
Headless Linux selects `QT_QPA_PLATFORM=offscreen`; an interactive desktop needs a
display and the usual Qt system libraries. PyInstaller's `GraphMath.spec` filename
is retained; its default distribution is now `MathLab`.

- [Ukrainian user guide](docs/user-guide.uk.md)
- [Architecture and engine API](docs/engine.md)
- [MathLab validation and changed files](docs/mathlab-validation.md)
- [Performance measurements](docs/mathlab-performance.md)
- [Final v1.1.4 stabilization audit](docs/mathlab-v1.1.4-audit.md)
- [v1.1.5 typography and single-file validation](docs/mathlab-v1.1.5-polish.md)
- [Windows build and release](docs/windows-build.md)
- [Original GraphMath validation](docs/validation.md)

Original code is MIT licensed. [Third-party notices](THIRD_PARTY_NOTICES.md) cover
Qt/PySide6 LGPL components, mathematical fonts and other dependencies. Libraries
remain dynamically replaceable in the portable distribution. Builds are unsigned.
