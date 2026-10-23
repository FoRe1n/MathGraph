# Mathematical engine API

The engine does not import Qt. Another desktop, Telegram or web interface can call:

```python
import numpy as np
from graphmath.core.expressions import parse, evaluate
from graphmath.plotting.sampling import sample
from graphmath.analysis.symbolic import analyze
from graphmath.persistence.projects import Project, save, load

expression = parse('a*x^2 - 4')
print(expression.parameters, expression.latex)
y = evaluate(expression.source, np.linspace(-3, 3, 100), {'a': 2})
x, y = sample('1/x', -5, 5, pixels=1000, yrange=(-8, 8))
# Render segments separated by NaN; never connect across NaN.
result = analyze('x^2-4')
save(Project(), 'example.graphmath')
```

## Security boundary

`ast.parse` reads source into syntax only. An allowlisted visitor constructs SymPy
objects directly. It accepts real numeric literals, supported binary/unary
operators, x, pi/e, one-letter parameters, and explicitly named function calls.
No attributes, subscripts, strings, collections, comprehensions, keyword calls,
imports, statements or Python `eval` on input are used. NumPy lambdify compiles
only expressions already built by this visitor. Original domain guards are kept
separately, including removable rational holes.

Input is bounded to 600 characters, 100 AST nodes, 18 visitor levels, six parameters,
constant powers up to 100 in magnitude and roots of order 2–15. The compiled and
render caches have 256 entries. Ordinary numerical evaluation is vectorized;
sampling uses 1,000–16,000 points depending on viewport width, midpoint checks,
denominator crossings and offscreen safeguards. A finite sampler cannot prove
continuity or detect every narrow/rapid feature.

## Symbolic work

`analyze` is synchronous for API consumers. Run it in a disposable worker process
with a wall-time limit for untrusted/complex requests, as the desktop Inspector
does (spawn context, 8 seconds, terminate on cancellation/change). A thread timeout
cannot reliably stop SymPy work. Host interfaces should add process memory quotas
and request rate limits appropriate to their deployment. No Telegram integration
is implemented in this version.

Results separate symbolic strings from floating coordinates. Unknown properties
are explicit. Monotonicity uses the actual domain. Finite exact roots are annotated;
infinite/implicit sets are not silently converted into guessed points. Removable
holes are excluded even after cancellation. Extrema use sufficient second-derivative
or one-sided cusp tests; a missing marker does not prove the absence of extrema.
Tangents in the GUI are finite-difference approximations with a one-sided slope check.

## Documents

`Project.to_dict()` uses `format: GraphMath`, `version: 1`. Load validates types,
colors, IDs, finite values, parameter limits, function count and viewport; files
are limited to 2 MB. Function text remains inert on load and is later checked by
the parser. Atomic same-directory replacement preserves an older save if writing
fails. Global settings belong to QSettings (Windows user registry), not the project.
