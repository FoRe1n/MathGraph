# MathLab performance investigation

## Baseline and method

Stable GraphMath: `v1.0.0`, commit `e62c843ad458a3a6ee77712c869cf984fc8d86fc`.
The baseline suite passed all 81 cases before changes. The stable release is
preserved. Work proceeds on `feature/mathlab-v1` and is validated through a PR.

`cProfile` showed raster painting dominated the synthetic drag workload. In the
initial profile, AxisItem/QPicture replay consumed about 10.1 seconds of a 13.0-second
profile, while numerical sampling of ten functions was already around milliseconds.
A controlled five-function AA comparison measured roughly 106 ms with antialiasing
and 77 ms without it; changing AA alone did not solve the grid cost.

## Changes supported by that evidence

- Replace the full-plane axis grid with a bounded direct-paint coordinate grid.
  Axis items retain tick labels and independent horizontal/vertical axes.
- Use lightweight raster curve rendering during pan, wheel and slider interaction;
  restore antialiasing and refine after 140 ms of inactivity. OpenGL stays disabled:
  there is no hardware display here on which to establish a stable improvement.
- Cache samples over an extended x interval, retaining NaN separators, domain
  guards and pole breaks. Reuse only when the expression, parameter values,
  viewport width and sampling scale remain suitable. Zoom and substantial range
  changes invalidate the cache. Slider edits update only their function.
- Upload curve data only on a cache miss. Graphics objects are reused.
- Throttle view notifications; remove JSON serialization from the pan path.
  Coalesce slider history into edits instead of serializing every tick.
- Disable cursor inspection by default. Optional tracking is throttled and uses
  a small point and status text, with no large crosshair or recurring tooltip.
- Reuse slider widgets; debounce the numeric MathText preview. Symbolic work remains
  in the existing disposable worker process with its eight-second timeout.

## Reproducible measurements

Run `python scripts/benchmark_interaction.py --frames 30 --session-steps 5000`.
The JSON records numerical batches, idle raster paint, pan actions, actual Qt wheel
events, slider response, CPU time, RSS, startup and graphics/cache object counts.
`MATHLAB_BENCH_SOURCE` can select a stable source archive. For example:

```bash
mkdir /tmp/graphmath-stable
# Run from a clean existing checkout; this does not create a Git worktree.
git archive v1.0.0 | tar -x -C /tmp/graphmath-stable
MATHLAB_BENCH_SOURCE=/tmp/graphmath-stable .venv/bin/python scripts/benchmark_interaction.py --frames 30 --session-steps 400 --output artifacts/baseline.json
.venv/bin/python scripts/benchmark_interaction.py --frames 30 --session-steps 400 --output artifacts/mathlab.json
```

Initial comparable Linux x64 / Python 3.12 offscreen measurements, 30 actions each:

| Workload (median milliseconds) | GraphMath | MathLab |
| --- | ---: | ---: |
| One quadratic, pan + raster | 43.631 | 7.266 |
| One exponential, pan + raster | 51.540 | 6.406 |
| One logarithm, pan + raster | 38.944 | 5.946 |
| Five functions, pan + raster | 81.485 | 17.213 |
| Five functions, wheel + raster | 75.872 | 13.811 |
| Custom coefficient response + raster | 44.263 | 1.760 |
| Imports, window and first event | 1013.053 | 949.922 |

Nearby MathLab pans performed zero new numerical sampling calls during the measured
30-action batches. The 400-step session retained one curve and one cache entry;
RSS increased about 49 KB after settling and garbage collection. This is evidence
of bounded state in that workload, not proof of leak-free operation over hours.
The final benchmark JSON and native Windows CI benchmark are separate evidence.

These timings include an explicit raster grab after event processing, which can
cause a second paint. They are useful comparisons and **are not measured desktop
FPS**. Hardware input, the Windows compositor and GPU performance are unverified
by Linux offscreen runs. Native Windows CI also uses offscreen Qt and records its
own measurements in the validation artifact. No claim of 60 FPS is made.

Final follow-up: five-function pan + forced raster **13.792 ms median**, **14.791 ms
p95**; wheel + raster **13.223 ms median**; learning slider response **2.109 ms
median**. The 5,000-step scripted interaction took 16.99 seconds, with one curve,
one sample cache entry, and RSS 204,394,496 bytes both before and after settling.
Full final measurements are in `docs/performance/mathlab-final.json`.
