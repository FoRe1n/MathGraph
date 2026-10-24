"""Exact symbolic analysis. Call in a time-limited process for untrusted input."""
from __future__ import annotations
import math
import sympy as sp
from sympy.calculus.util import continuous_domain, function_range
from graphmath.core.expressions import parse, X, ExpressionError

UNKNOWN = "Не вдалося визначити автоматично."


def _safe(call):
    try:
        value = call()
        if isinstance(value, sp.ConditionSet) or getattr(value, "has", lambda *_: False)(sp.ConditionSet):
            return None
        return value
    except (NotImplementedError, ValueError, TypeError, ZeroDivisionError, RecursionError):
        return None


def _text(value):
    return UNKNOWN if value is None else sp.sstr(sp.simplify(value)).replace("oo", "∞").replace("EmptySet", "∅").replace("Reals", "ℝ")


def _finite_points(values, expr, domain):
    result = []
    if isinstance(values, sp.FiniteSet):
        for x in values:
            if x.is_real and domain.contains(x) == sp.true:
                y = sp.simplify(expr.subs(X, x))
                if y.is_finite and y.is_real:
                    result.append({"x": float(x), "y": float(y), "exact": f"({_text(x)}, {_text(y)})"})
    return result


def analyze(source: str, parameters: dict[str, float] | None = None,
            other: str | None = None, other_parameters: dict[str, float] | None = None) -> dict:
    """Exact sets are distinguished from numerical annotation coordinates.

    The original denominator/log/root guards retain removable holes even if
    symbolic simplification cancels factors. Unsupported properties stay unknown.
    """
    parsed = parse(source)
    if parsed.relation:
        raise ExpressionError("Вертикальна пряма — відношення, а не функція y = f(x).")
    subs = {sp.Symbol(n, real=True): sp.Rational(str((parameters or {}).get(n, 1))) for n in parsed.parameters}
    expr = parsed.symbolic.subs(subs)
    domain = _safe(lambda: continuous_domain(expr, X, sp.S.Reals))
    if domain is not None:
        for denominator in parsed.denominators:
            roots = _safe(lambda d=denominator: sp.solveset(d.subs(subs), X, domain=sp.S.Reals))
            if roots is None:
                domain = None
                break
            domain = domain - roots
        for items, relation in [(parsed.nonnegative, lambda a: a >= 0), (parsed.positive, lambda a: a > 0)]:
            for guard in items:
                allowed = _safe(lambda g=guard: sp.solve_univariate_inequality(relation(g.subs(subs)), X, relational=False))
                if allowed is None:
                    domain = None
                    break
                domain = domain.intersect(allowed) if domain is not None else None
    real_domain = domain if domain is not None else sp.S.Reals
    zeros = _safe(lambda: sp.solveset(expr, X, domain=real_domain)) if domain is not None else None
    derivative = _safe(lambda: sp.diff(expr, X))
    # Range must respect holes and disconnected components. Ask SymPy directly.
    value_range = _safe(lambda: function_range(expr, X, domain)) if domain is not None else None
    intercept = None
    if domain is not None and domain.contains(0) == sp.true:
        intercept = _safe(lambda: expr.subs(X, 0))
    critical = _safe(lambda: sp.solveset(derivative, X, domain=real_domain)) if derivative is not None and domain is not None else None
    extrema = []
    if isinstance(critical, sp.FiniteSet):
        for point in critical:
            if domain.contains(point) != sp.true:
                continue
            second = _safe(lambda: sp.diff(expr, X, 2).subs(X, point))
            kind = "мінімум" if second is not None and second.is_positive else "максимум" if second is not None and second.is_negative else None
            if kind:
                candidates = _finite_points(sp.FiniteSet(point), expr, domain)
                extrema.extend([{**p, "kind": kind} for p in candidates])
    # Include a cusp only when two exact one-sided derivative limits prove a turn.
    for absolute in expr.atoms(sp.Abs):
        cusps = _safe(lambda a=absolute: sp.solveset(a.args[0], X, domain=real_domain))
        if isinstance(cusps, sp.FiniteSet) and derivative is not None:
            for point in cusps:
                left = _safe(lambda: sp.limit(derivative, X, point, dir="-"))
                right = _safe(lambda: sp.limit(derivative, X, point, dir="+"))
                if left is not None and right is not None:
                    kind = "мінімум" if left.is_negative and right.is_positive else "максимум" if left.is_positive and right.is_negative else None
                    if kind:
                        extrema.extend([{**p, "kind": kind} for p in _finite_points(sp.FiniteSet(point), expr, real_domain)])
    increasing = _safe(lambda: sp.solve_univariate_inequality(derivative > 0, X, relational=False).intersect(real_domain)) if derivative is not None and domain is not None else None
    decreasing = _safe(lambda: sp.solve_univariate_inequality(derivative < 0, X, relational=False).intersect(real_domain)) if derivative is not None and domain is not None else None
    vertical, horizontal = [], []
    # Boundary candidates plus denominator roots; nonfinite sets are reported as unknown.
    candidates = _safe(lambda: domain.boundary) if domain is not None else None
    vertical_known = isinstance(candidates, sp.FiniteSet) or candidates is sp.S.EmptySet
    if isinstance(candidates, sp.FiniteSet):
        for point in candidates:
            if point.is_finite:
                limits = [_safe(lambda direction=direction: sp.limit(expr, X, point, dir=direction)) for direction in ["-", "+"]]
                if any(v in (sp.oo, -sp.oo) for v in limits):
                    vertical.append({"value": float(point), "exact": _text(point)})
    for infinity in [sp.oo, -sp.oo]:
        if domain is None:
            continue
        # There must actually be domain points arbitrarily far in this direction.
        endpoint = _safe(lambda: domain.sup if infinity == sp.oo else domain.inf)
        if endpoint != infinity:
            continue
        limit = _safe(lambda inf=infinity: sp.limit(expr, X, inf))
        if limit is not None and limit.is_real and limit.is_finite:
            if not any(p["exact"] == _text(limit) for p in horizontal):
                horizontal.append({"value": float(limit), "exact": _text(limit)})
    intersections = []
    intersection_text = "Оберіть другу видиму функцію."
    if other:
        second_parsed = parse(other)
        if second_parsed.relation:
            raise ExpressionError("Для перетинів оберіть дві функції y = f(x).")
        other_values = {n: (other_parameters or {}).get(n, 1) for n in second_parsed.parameters}
        second = second_parsed.substitute(other_values)
        second_domain = _safe(lambda: continuous_domain(second, X, sp.S.Reals))
        if second_domain is not None and domain is not None:
            for d in second_parsed.denominators:
                roots = _safe(lambda d=d: sp.solveset(d.subs({sp.Symbol(k, real=True): v for k, v in other_values.items()}), X, domain=sp.S.Reals))
                if roots is not None:
                    second_domain = second_domain - roots
            roots = _safe(lambda: sp.solveset(expr - second, X, domain=domain.intersect(second_domain)))
            intersections = _finite_points(roots, expr, domain.intersect(second_domain))
            intersection_text = _text(roots)
    result = {
        "properties": {
            "Область визначення": _text(domain), "Область значень": _text(value_range),
            "Нулі / перетини Ox": _text(zeros), "Перетин Oy": _text(intercept),
            "Похідна": _text(derivative), "Зростає": _text(increasing), "Спадає": _text(decreasing),
            "Локальні екстремуми": "; ".join(f'{p["kind"]}: {p["exact"]}' for p in extrema) or UNKNOWN,
            "Вертикальні асимптоти": ", ".join("x = " + p["exact"] for p in vertical) or ("∅" if vertical_known else UNKNOWN),
            "Горизонтальні асимптоти": ", ".join("y = " + p["exact"] for p in horizontal) or UNKNOWN,
            "Перетини з другою функцією": intersection_text,
        },
        "zeros": _finite_points(zeros, expr, real_domain) if domain is not None else [],
        "extrema": extrema, "vertical": vertical, "horizontal": horizontal,
        "intersections": intersections,
        "derivative_latex": sp.latex(derivative) if derivative is not None else None,
    }
    display=dict(result['properties'])
    for label,value in [('Область визначення',domain),('Область значень',value_range),
                        ('Нулі / перетини Ox',zeros),('Перетин Oy',intercept),
                        ('Похідна',derivative),('Зростає',increasing),('Спадає',decreasing)]:
        display[label]=UNKNOWN if value is None else sp.pretty(sp.simplify(value),use_unicode=True,wrap_line=False)
    result['display_properties']=display
    return result


def worker(connection, source, parameters, other, other_parameters):
    """Process entry point; no GUI imports, supports Windows spawn/frozen builds."""
    try:
        connection.send({"result": analyze(source, parameters, other, other_parameters)})
    except Exception:
        connection.send({"error": UNKNOWN})
    finally:
        connection.close()
