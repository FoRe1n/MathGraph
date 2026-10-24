# MathLab 1.1 validation

Development branch: `feature/mathlab-v1.1`. Baseline: MathLab 1.0.0,
`1a7ad4b6bf33a9d42bffd1143ea69b4d86837fa6`. Existing release tags and assets
are preserved. The application was extended in place; the dependency lockfiles,
parser allowlist, raster grid, interaction timers and ordinary version-1 project
records remain in use.

## Function library and mathematics

Twenty templates in one grouped selector cover linear/direct/constant functions,
vertical relations, inverse proportionality, standard/square/vertex quadratics,
cubic, absolute value, three square-root orientations, original and transformed
exponentials/logarithms, sine, cosine and tangent. Negative scales and valid bases
below one are supported. Standard quadratic b remains a polynomial coefficient;
the separate vertex form teaches horizontal translation through h.

The transformation templates retain their displayed form instead of applying
symbolic rewrites to the numeric preview. Horizontal scaling is reciprocal to the
absolute multiplier inside the argument. Positive h moves right; positive k moves
up. Exponential/logarithmic base b is distinguished from argument multiplier d.
Trig angles are radians. Current-coefficient properties account for constants,
restricted domains even with a zero multiplier, reflected domains, parity,
monotonicity, intercepts, asymptotes and periods. Numeric properties are rounded.

Vertical `x=c` relations have an explicit parser flag and a separate two-point
viewport-spanning renderer using reused graphics. They cannot be evaluated as y
values or sent to ordinary function analysis. They participate in project I/O,
visibility, colors, fitting and scene export. The parser remains an allowlisted
AST parser; no Python eval was introduced. Tangent guards now recognize numeric
representations of its poles, while the existing sampling breaks remain intact.

## User interface and compatibility

The original visual workspace, original laboratories, settings, custom multiple
functions, colors, show/hide, analysis subprocess, undo/redo, themes and export
paths are retained. Beginner examples update the current expression immediately;
custom symbolic parameters generate sliders, while x remains independent.
Advanced syntax buttons and coordinate ranges are collapsed initially. Coordinate
inspection is optional. Range minima/maxima are validated before applying.
Coefficient changes reuse controls and preserve the current viewport.

Version-1 legacy projects still load without migration. New template mode names
are additive in the current reader; old MathLab readers cannot open new mode
names or interpret the new vertical relation syntax. This is backward reading
compatibility, not a claim that v1.0 can render every new v1.1 project.

## Local checks

Python 3.12.14, Linux x64, PySide6 6.8.3, Qt offscreen:

- All 147 baseline tests passed before implementation.
- All 282 current tests passed, including the original suite and additional
  template points, slope signs, vertical orientation, root/log domains, vertices,
  horizontal/vertical transformations, periodicity, poles, parity, actual Qt
  controls, custom parameters, coordinate ranges, version-1 roundtrips, legacy
  fixture compatibility and PNG/SVG/PDF export.
- Source smoke passed for all 20 modes, project I/O, all three export formats,
  light/dark workspaces and the preserved analysis subprocess.
- Actual Qt screenshots were reviewed for transformation notation, slider values,
  the custom editor and graph orientation. These are offscreen desktop checks;
  physical pointer input, desktop compositing and Windows display behavior are
  not measured here.
- The Windows release archive verifier has negative tests for wrong architecture,
  missing runtime and changed archive checksum. It verifies CRCs, safe member
  paths, portable resources, bundled Python 3.12/Qt and the AMD64 PE header.

Reproduce from the checkout with `.venv/bin/python -m pytest -q` and
`.venv/bin/python -m graphmath --smoke-test --smoke-output artifacts/smoke`.
Use `QT_QPA_PLATFORM=offscreen` without a desktop display. No account or API key
is needed to run the application.

## Performance comparison

Both versions used the same hash-locked environment and unchanged benchmark
script. The baseline source came from `git archive`, not a new Git worktree.
An initial sequential comparison used 30 actions per scenario and 5,000 extended
interaction steps. Its timings were variable, so four further runs alternated
v1.0, v1.1, v1.1, v1.0, using 60 actions and 400 extended steps. No test suite or
application smoke check ran concurrently with those four comparison runs.

Ranges of the two run medians (milliseconds), rather than a selected best run:

| Workload | v1.0 | v1.1 |
| --- | ---: | ---: |
| Quadratic pan + raster | 10.445–10.648 | 9.788–10.815 |
| Exponential pan + raster | 9.773–10.275 | 10.215–11.003 |
| Logarithmic pan + raster | 9.475–10.169 | 9.587–10.055 |
| Five functions pan + raster | 18.012–18.053 | 17.335–20.608 |
| Five functions wheel + raster | 17.834–18.332 | 17.358–18.477 |
| Five functions idle forced raster | 19.949–20.158 | 20.273–38.306 |
| Learning slider + raster | 3.819–4.121 | 3.917–4.510 |
| Custom slider + raster | 2.991–3.175 | 2.821–3.433 |

Panning and slider medians are broadly comparable across these runs, with visible
shared-machine variability. One v1.1 run had larger forced-paint and slider-tail
spikes (learning-slider p95 24.413 ms, maximum 92.244 ms). These results do not
establish a statistically significant speedup, a guaranteed latency bound or
hardware desktop smoothness. The renderer still reuses graphics and sampling;
there is no sampling or serialization regression in the dedicated pan tests.

Nearby pans made zero new sampling calls in every scenario in every run. Both
5,000-step sessions retained one curve and one cache entry, with 24,576 bytes of
RSS growth each. Final RSS was 204,419,072 bytes for v1.0 and 204,546,048 bytes for v1.1. This is bounded state in the measured workload,
not a claim about leak-free operation over hours.

Full raw records: [v1.0 extended](performance/mathlab-v1.0-onboarding.json),
[v1.1 extended](performance/mathlab-v1.1.json), [v1.0 A](performance/mathlab-v1-a.json),
[v1.1 A](performance/mathlab-v1.1-a.json), [v1.1 B](performance/mathlab-v1.1-b.json),
[v1.0 B](performance/mathlab-v1-b.json). Forced-raster offscreen timings are not
desktop FPS, compositor latency or a GPU measurement.

## Windows release

The existing native Windows Actions workflow now targets
`MathLab-v1.1.0-Windows-x64.zip`, runs the full tests and source/frozen smoke checks,
and verifies the release archive before uploading it. Publication is gated on
the build job. The workflow also runs for the development branch so Windows
validation can finish before a release tag is created.

The final release workflow for source commit
`11822ffa4b39abddfd8dbe9a2a06bcd388ed982b` completed successfully:
[Windows build and release](https://github.com/FoRe1n/MathGraph/actions/runs/40106809725).
It passed version/dependency checks, the complete tests, benchmark, source smoke,
screenshot capture, native PyInstaller build, resource verification, frozen smoke,
ZIP verification, upload and release publication.

Published [MathLab v1.1.0](https://github.com/FoRe1n/MathGraph/releases/tag/mathlab-v1.1.0):
[portable Windows ZIP](https://github.com/FoRe1n/MathGraph/releases/download/mathlab-v1.1.0/MathLab-v1.1.0-Windows-x64.zip).
The public ZIP and SHA256SUMS.txt were downloaded without a GitHub login and
independently checked with `scripts/verify_release_zip.py`: all 1,506 members passed
CRC validation; the bundled Python/Qt runtime and AMD64 PE executable were present.

SHA256: `de47f8457ab768c42fc4658af81bd3e6bcb45e294086fdcd4dc3b14f50456894`.

The existing MathLab v1.0.0 and GraphMath v1.0.0 tag objects remained unchanged
(`91e7ad593948947c88c5a3e5fddf87c3f61d5cdb` and
`1f8b5055c3f56b5cf3a5556e4f82f1a380b1d7eb`, respectively). Main was not reset,
merged or force-pushed. The release was built from the dedicated development
branch. Windows checks use real Qt offscreen and the frozen executable; manual
hardware desktop testing and code signing remain outside this validation.
