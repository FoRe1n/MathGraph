"""Viewport-aware sampling, isolated from the desktop renderer."""
from __future__ import annotations
import numpy as np
from graphmath.core.expressions import evaluate, denominator_values, tangent_arguments


def sample(source: str, xmin: float, xmax: float, parameters=None, *,
           pixels: int = 1200, yrange: tuple[float, float] = (-6, 6)) -> tuple[np.ndarray, np.ndarray]:
    """Oversample the visible range and break paths at domain gaps and poles.

    NaNs are explicit path separators; the renderer must use connect='finite'.
    Denominator sign crossings also catch translated trigonometric asymptotes.
    Midpoint checks catch unresolved spikes, and off-screen clipping prevents
    misleading bridges where both endpoints lie outside the visible y range.
    """
    count = min(16000, max(1000, int(pixels) * 3))
    x = np.linspace(xmin, xmax, count)
    y = evaluate(source, x, parameters)
    mid = (x[:-1] + x[1:]) / 2
    ym = evaluate(source, mid, parameters)
    span = max(1e-9, yrange[1] - yrange[0])
    bad = ~np.isfinite(ym) & np.isfinite(y[:-1]) & np.isfinite(y[1:])
    for d in denominator_values(source, x, parameters):
        bad |= ~np.isfinite(d[:-1]) | ~np.isfinite(d[1:])
        bad |= (np.signbit(d[:-1]) != np.signbit(d[1:])) | (d[:-1] == 0) | (d[1:] == 0)
    # Endpoint cosine signs alone miss an even number of tangent poles in a
    # sample interval. Phase bins retain every affine-phase branch boundary,
    # including at extreme zoom-out or large custom frequency values.
    for phase in tangent_arguments(source, x, parameters):
        with np.errstate(all="ignore"):
            branch = np.floor((phase + np.pi/2) / np.pi)
            bad |= (~np.isfinite(phase[:-1]) | ~np.isfinite(phase[1:])
                    | (branch[:-1] != branch[1:]))
    with np.errstate(all="ignore"):
        bad |= (np.abs(ym - (y[:-1] + y[1:]) / 2) > span * 0.5)
        bad |= (np.abs(np.diff(y)) > span * 3)
    y[np.flatnonzero(bad) + 1] = np.nan
    y[(y < yrange[0] - span * 5) | (y > yrange[1] + span * 5)] = np.nan
    return x, y
