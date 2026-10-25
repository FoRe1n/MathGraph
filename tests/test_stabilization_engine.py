"""Independent regressions for parser domains and ordinary symbolic analysis."""
import math

import numpy as np
import pytest

from graphmath.analysis.symbolic import UNKNOWN, analyze
from graphmath.core.expressions import ExpressionError, evaluate, parse, relation_x


@pytest.mark.parametrize('source', ['1/(1-1)', '0^(-1)', 'log(x,2-1)', 'log(x,sqrt(4)/2)'])
def test_constant_arithmetic_cannot_hide_invalid_domains(source):
    with pytest.raises(ExpressionError):
        parse(source)


@pytest.mark.parametrize('source,expected', [
    ('x^(1/2+1/2)', [-8, -1, 0, 1, 8]),
    ('x^(1/3)', [-2, -1, 0, 1, 2]),
    ('x^(2/3)', [4, 1, 0, 1, 4]),
    ('root(x,1+2)', [-2, -1, 0, 1, 2]),
])
def test_constant_power_arithmetic_and_real_odd_roots(source, expected):
    np.testing.assert_allclose(evaluate(source, [-8, -1, 0, 1, 8]), expected, atol=1e-12)


def test_negative_odd_rational_power_retains_the_hole():
    np.testing.assert_allclose(evaluate('x^(-1/3)', [-8, -1, 1, 8]), [-.5, -1, 1, .5])
    assert np.isnan(evaluate('x^(-1/3)', [0])).all()


@pytest.mark.parametrize('source', ['x^0.5', 'x^(1/2)', 'x^(-1/2)'])
def test_even_roots_still_exclude_negative_arguments(source):
    assert np.isnan(evaluate(source, [-4, -1])).all()


@pytest.mark.parametrize('source', ['1/a', '1/(a-a)', 'a^(-1)'])
def test_parameter_only_division_returns_undefined_points_without_python_errors(source):
    assert np.isnan(evaluate(source, [-1, 0, 1], {'a': 0})).all()


@pytest.mark.parametrize('source,parameters', [
    ('x=log(c)', {'c': -1}), ('x=sqrt(c)', {'c': -1}),
    ('x=1/c', {'c': 0}), ('x=0*log(c)', {'c': -1}),
])
def test_vertical_coordinates_respect_original_domains(source, parameters):
    assert relation_x(source, parameters) is None


def test_vertical_coordinate_does_not_use_symbolic_substitution(monkeypatch):
    from graphmath.core.expressions import Expression
    monkeypatch.setattr(Expression, 'substitute', lambda *a, **kw: (_ for _ in ()).throw(AssertionError('symbolic work in refresh')))
    assert relation_x('x=2*c+1', {'c': 3}) == 7


@pytest.mark.parametrize('source', ['sin(x)', 'cos(x)', 'sin(3*x)+2'])
def test_oscillating_limits_are_not_horizontal_asymptotes(source):
    result = analyze(source)
    assert result['horizontal'] == []
    assert result['properties']['Область визначення'] == 'ℝ'


def test_true_finite_oscillating_limit_is_still_an_asymptote():
    assert analyze('sin(x)/x')['horizontal'] == [{'value': 0., 'exact': '0'}]


@pytest.mark.parametrize('other,parameters', [
    ('a*log(x)', {'a': 0}), ('a*sqrt(x-1)', {'a': 0}),
    ('a*log(-x)', {'a': 0}),
])
def test_intersections_preserve_the_second_formulas_domain(other, parameters):
    result = analyze('x', {}, other, parameters)
    assert result['intersections'] == []
    assert result['properties']['Перетини з другою функцією'] == '∅'


def test_intersections_inside_restricted_domain_remain_available():
    result = analyze('x-2', {}, 'a*sqrt(x-1)', {'a': 0})
    assert result['intersections'] == [{'x': 2., 'y': 0., 'exact': '(2, 0)'}]


def test_odd_root_analysis_reports_ordinary_derivative_limitations():
    result = analyze('root(x,3)')
    assert result['properties']['Похідна'] == UNKNOWN
    assert result['derivative_latex'] is None
    assert 'DiracDelta' not in str(result['display_properties'])



@pytest.mark.parametrize('source', ['sin(x)', 'cos(x)', 'sin(3*x)+2'])
def test_single_period_inequality_results_are_not_presented_as_global_sets(source):
    result = analyze(source)
    assert result['properties']['Зростає'] == UNKNOWN
    assert result['properties']['Спадає'] == UNKNOWN


def test_tangent_monotonicity_with_global_solver_result_is_preserved():
    result = analyze('tan(x)')
    assert result['properties']['Зростає'] == result['properties']['Область визначення']
    assert result['properties']['Спадає'] == '∅'


def test_surrogate_input_is_a_friendly_expression_error():
    with pytest.raises(ExpressionError):
        parse('x+\ud800')


def test_generated_solver_set_tokens_are_localized():
    from graphmath.analysis.symbolic import _visible_text
    assert _visible_text('Intersection(Reals, ImageSet(Integers))') == 'Перетин(ℝ, Образ множини(ℤ))'


def test_worker_retains_developer_diagnostics_and_sends_friendly_error(caplog):
    from graphmath.analysis.symbolic import worker
    class Connection:
        def __init__(self):self.sent=[];self.closed=False
        def send(self, value):self.sent.append(value)
        def close(self):self.closed=True
    connection=Connection()
    worker(connection,'sin(',{},None,None)
    assert connection.sent == [{'error': UNKNOWN}]
    assert connection.closed
    assert 'Symbolic analysis failed' in caplog.text
    assert caplog.records[-1].exc_info is not None



def test_tangent_phase_metadata_is_numeric_and_cached(monkeypatch):
    from graphmath.core.expressions import tangent_arguments, _compiled
    phases=tangent_arguments('tan(a*(x-h))',[0,1],{'a':2000,'h':.3})
    np.testing.assert_allclose(phases[0],[-600,1400])
    before=_compiled.cache_info().hits
    tangent_arguments('tan(a*(x-h))',[2],{'a':2000,'h':.3})
    assert _compiled.cache_info().hits>before



def test_infinity_formatting_does_not_corrupt_algebraic_root_names():
    import sympy as sp
    from graphmath.analysis.symbolic import _text
    x=sp.Symbol('x')
    text=_text(sp.CRootOf(x**5-x-1,0))
    assert 'CRootOf' in text and '∞' not in text



@pytest.mark.parametrize('source', ['x^2', 'sin('])
def test_worker_shutdown_does_not_retry_a_closed_result_channel(source):
    from graphmath.analysis.symbolic import worker
    class ClosedConnection:
        def __init__(self):self.attempts=0;self.closed=False
        def send(self, payload):self.attempts+=1;raise BrokenPipeError('closed')
        def close(self):self.closed=True
    connection=ClosedConnection()
    worker(connection,source,{},None,None)
    assert connection.attempts == 1 and connection.closed


@pytest.mark.parametrize('source', [
    '1/((((10^100)^100)^100)^100)',
    '1/((((1.0001^100)^100)^100)^100)',
    '1/((((((1000000000000+1)/1000000000000)^100)^100)^100)^100)',
    '(10^100)^10',
    '(10^(-100))^10',
])
def test_constant_resource_guards_reject_expansion_and_numeric_overflow(source):
    with pytest.raises(ExpressionError, match='Стала частина'):
        parse(source)


@pytest.mark.parametrize('source,expected', [
    ('(1.0001^100)*x', [1.0001**100, 2*1.0001**100]),
    ('1.000000000001^x', [1.000000000001, 1.000000000001**2]),
    ('log(x,0.999999)', [0., math.log(2)/math.log(.999999)]),
    ('(10^100)*x', [1e100, 2e100]),
    ('(10^(-100))*x', [1e-100, 2e-100]),
])
def test_common_finite_numeric_expressions_remain_supported(source, expected):
    np.testing.assert_allclose(evaluate(source, [1,2]), expected, rtol=1e-12, atol=0)


@pytest.mark.parametrize('source', ['1/sin(x)', '1/tan(x)'])
def test_represented_trigonometric_zeros_are_undefined(source):
    assert np.isnan(evaluate(source, [0, np.pi, -np.pi])).all()
    assert np.isfinite(evaluate(source, [1,2])).all()


@pytest.mark.parametrize('source', ['1e-14/sin(1e-14*x)', '1e-14/tan(1e-14*x)'])
def test_valid_small_angle_reciprocals_are_not_erased(source):
    np.testing.assert_allclose(evaluate(source, [1,2,-1]), [1,.5,-1], rtol=1e-12)


def test_cosine_pole_guard_preserves_resolvable_nearby_values():
    assert np.isnan(evaluate('1/cos(x)', [np.pi/2])).all()
    assert np.isfinite(evaluate('1/cos(x)', [np.pi/2-1e-14])).all()


def test_constant_expansion_guard_in_a_time_and_memory_limited_subprocess():
    import subprocess
    import sys
    from pathlib import Path
    code = '''
import os,sys
from graphmath.core.expressions import parse,evaluate,ExpressionError
if sys.platform == 'linux':
    import resource
    size=int(open('/proc/self/statm').read().split()[0])*os.sysconf('SC_PAGE_SIZE')
    resource.setrlimit(resource.RLIMIT_AS,(size+128*1024*1024,size+128*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(2,2))
try:
    source='1/((((10^100)^100)^100)^100)'
    parse(source)
    evaluate(source,[1])
except ExpressionError:
    print('rejected')
else:
    raise AssertionError('resource guard was not applied')
'''
    result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).parents[1],
                          capture_output=True,text=True,timeout=8)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'rejected'



def test_absolute_value_cannot_reset_the_exact_constant_budget():
    source='(1000000000000+1)/1000000000000'
    for _ in range(6):source=f'abs(({source})^30)'
    with pytest.raises(ExpressionError,match='Стала частина'):
        parse(source)



@pytest.mark.parametrize('source', ['tan(sqrt(-1))', '1/sin(sqrt(-1))', '1/tan(sqrt(-1))'])
def test_nonreal_trigonometric_arguments_remain_undefined_without_phase_errors(source):
    assert np.isnan(evaluate(source,[0,1])).all()
