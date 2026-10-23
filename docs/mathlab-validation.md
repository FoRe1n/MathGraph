# MathLab validation

Baseline: stable GraphMath `v1.0.0`, commit
`e62c843ad458a3a6ee77712c869cf984fc8d86fc`. All **81** baseline tests passed before
modification. The old release, tag and project history remain intact. Development
uses `feature/mathlab-v1`; native Windows checks and a PR precede merging/release.

## Source checks

The expanded suite covers old behavior and laboratory-specific mathematics,
coefficient constraints and degeneracy, explanations, domain gaps, roots, axis
coordinate mapping, cache reuse, slider object reuse, undo/redo, save/load, legacy
JSON, mode persistence, PNG/SVG/PDF, themes, Ukrainian dialog translation and close
confirmation. The original test cases were retained; the old default workspace is
now an explicit fixture because the initial application screen intentionally changed.
`2x` moved from rejected to accepted syntax and is tested numerically; ambiguous
`xy` and hostile syntax remain rejected.

Old documents default to custom mode and display all their saved curves. The
optional `mode` field is additive within version 1; function records are unchanged.
This avoids guessing a workspace mode from a user's old formula. The legacy
fixture round-trips all original payload fields, including an independent slider,
a hidden function, non-default color and non-default viewport.

Actual Qt screenshots of initial quadratic, markers, exponential, logarithmic,
custom, dark, narrow, settings and export screens are in
`docs/screenshots/mathlab/`. They were inspected for text clipping, formulas, graph
orientation, domain shading and control placement. The left pane scrolls at narrow
heights. These are application captures, not generated mockups.

See `docs/mathlab-performance.md` and `docs/performance/` for actual measurements.
The native Windows workflow also records benchmarks, real workspace captures,
source and frozen startup evidence in its validation artifact. Publication status
is recorded after CI and asset verification complete. Physical Windows desktop
interaction and hardware FPS are separate from offscreen validation.

## Main implementation files

- `graphmath/ui/canvas.py`, `graphmath/ui/grid.py`: bounded grid, cache, sampling
  scheduling, cursor behavior, active/idle rendering.
- `graphmath/ui/window.py`, `learning.py`, `dialogs.py`, `theme.py`, `editor.py`:
  retained workspace with learning modes, simplified controls, history coalescing,
  localized dialogs, readable theme and old custom editor.
- `graphmath/core/laboratories.py`: controls, safe bases, formulas, deterministic
  explanations, reset views and calculated markers.
- `graphmath/core/expressions.py`: additive safe school-notation normalization.
- `graphmath/analysis/symbolic.py`, `ui/inspector.py`: readable mathematical display
  alongside the unchanged programmatic analysis properties.
- `graphmath/persistence/projects.py`: optional validated mode metadata; unchanged
  version-1 mathematical records and atomic writes.
- `graphmath/app/main.py`, `localization.py`, `resources/qtbase_uk.qm`: MathLab
  branding, Ukrainian Qt translations, expanded smoke mode.
- `GraphMath.spec`, `.github/workflows/windows.yml`, `scripts/verify_distribution.py`:
  MathLab.exe packaging, native tests, resources, screenshots and release checks.
- `scripts/benchmark_interaction.py`, `capture_mathlab_qa.py`, regression tests and
  fixtures: repeatable performance and functional/visual evidence.

## Validated PR candidate

All **147 tests passed** locally after the final changes. Source smoke passed all
three learning modes, project serialization, preserved background analysis and
PNG/SVG/PDF export. A Linux onedir MathLab build passed required-resource validation
and frozen startup, including the symbolic subprocess. Native Windows and release
verification are performed by the PR/tag workflows rather than inferred from Linux.

The final offscreen five-function pan + forced raster median was **13.792 ms**
(p95 14.791 ms); wheel + raster median **13.223 ms**. A 5,000-step interaction run
kept one curve/cache entry and showed **zero RSS growth** after settling and garbage
collection (16.99 seconds of scripted interaction). It is not an hours-long test.

A custom formula with the same algebraic form as a laboratory retains its own parameter bounds. Entering a laboratory creates an independent record when those bounds differ; this is covered by core and GUI regression tests.

Decimal discriminants are computed as exact rational values before numerical marker coordinates, preventing a false missing double root from floating cancellation. Coincident vertex/root/intercept markers share one visible point. Both cases have regressions.

## Published Windows release

[PR #1](https://github.com/FoRe1n/MathGraph/pull/1) was merged through GitHub after
native Windows checks passed on final feature commit
`fa5a144fd69561f6c20226742f09bfe270cbe11a`. Release tag `mathlab-v1.0.0` points to
merge commit `708df641ea73f8dac1082340beca5bed8de38938`.

[Release workflow 39990444777](https://github.com/FoRe1n/MathGraph/actions/runs/39990444777)
completed the full Windows build and publication successfully: 147 tests,
benchmarks, actual Qt captures, source smoke, resource verification, frozen
MathLab.exe smoke and ZIP packaging. GitHub confirms the public non-draft
[MathLab v1.0.0 release](https://github.com/FoRe1n/MathGraph/releases/tag/mathlab-v1.0.0)
with the Windows ZIP and SHA256SUMS uploaded.

Anonymous HTTP download returned 200 for the complete **92,892,697-byte** ZIP.
All **1,497 entries** passed ZIP CRC verification. The PE header identifies
**Windows AMD64**; qwindows.dll, mathematical fonts, Ukrainian Qt translations,
LGPL text and the license inventory are present. Published SHA256:

```
9ef73711314b5782d917c95740ea3834cff93d290465bf76478420227f90f3be
```

The GraphMath `v1.0.0` tag remains at
`e62c843ad458a3a6ee77712c869cf984fc8d86fc`, and its original ZIP remains uploaded.
The feature branch and full commit history are retained. Main includes current
release documentation and visual QA captures driven through the real coefficient
controls; the screenshot driver resets the viewport to show the chosen vertex.

Remaining limits: builds are unsigned; physical Windows desktop interaction,
hardware/compositor FPS and hours-long memory behavior were not measured here.
The 5,000-step offscreen memory observation is reported with its actual duration.
Symbolic analysis retains its eight-second limit, and a finite numerical sampler
cannot resolve every arbitrarily narrow or high-frequency feature.
