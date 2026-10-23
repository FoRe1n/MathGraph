import numpy as np
import pytest
from graphmath.core.expressions import parse, evaluate, ExpressionError
from graphmath.plotting.sampling import sample


@pytest.mark.parametrize('source,x,expected', [
    ('y = x^2 - 4', [-2,0,2], [0,-4,0]), ('2*x+3', [-1,0,2], [1,3,7]),
    ('x^3-x', [-2,0,2], [-6,0,6]), ('2^x', [-1,0,2], [.5,1,4]),
    ('sqrt(x)', [0,1,4], [0,1,2]), ('root(x,3)', [-8,0,27], [-2,0,3]),
    ('log(x,2)', [1,2,8], [0,1,3]), ('ln(x)', [1,np.e], [0,1]),
    ('1/x', [-2,1,2], [-.5,1,.5]), ('sin(x)', [0,np.pi/2], [0,1]),
    ('cos(x)', [0,np.pi], [1,-1]), ('tan(x)', [0,np.pi/4], [0,1]),
    ('abs(x)', [-2,0,2], [2,0,2]), ('exp(x)', [0,1], [1,np.e]),
    ('pi*x', [0,1], [0,np.pi]), ('−x^2', [2], [-4]),
])
def test_function_families(source, x, expected):
    np.testing.assert_allclose(evaluate(source, x), expected, atol=1e-10)


@pytest.mark.parametrize('source', [
    '__import__("os")', 'x.__class__', '[x]', '(lambda:1)()', 'open("file")',
    'sin(x, x)', 'unknown(x)', 'x[0]', 'True', '1e999', '2x', 'x;',
    'x if x else 0', '{1:2}', 'log(x,1)', 'log(x,-2)', 'root(x,0)',
    '1/0', 'x^1000', 'x^(x+1)', 'sin(x, a=1)', 'x//2', '',
])
def test_restricted_parser(source):
    with pytest.raises(ExpressionError):
        parse(source)


def test_parameters_are_local():
    assert parse('a*x^2+b*x+c').parameters == ('a','b','c')
    np.testing.assert_allclose(evaluate('a*x^2+b*x+c', [0,1,2], {'a':2,'b':-1,'c':3}), [3,4,9])
    np.testing.assert_allclose(evaluate('a*x', [2], {'a':1}), [2])
    np.testing.assert_allclose(evaluate('a*x', [2], {'a':3}), [6])


@pytest.mark.parametrize('source,invalid', [('sqrt(x)', [-2,-1]), ('log(x)', [-1,0]), ('1/x', [0]), ('x/x', [0]), ('(x^2-1)/(x-1)', [1])])
def test_domain_holes(source, invalid):
    assert np.isnan(evaluate(source, invalid)).all()


@pytest.mark.parametrize('source,pole', [('1/x',0), ('1/(x-0.123)',.123), ('1/(x-0.123)^2',.123), ('tan(x)', np.pi/2), ('tan(3*x+1)', (np.pi/2-1)/3)])
def test_discontinuity_paths(source, pole):
    x, y = sample(source, pole-.5, pole+.5, pixels=1000)
    # No adjacent finite points may straddle the actual pole.
    crossing = (x[:-1] < pole) & (x[1:] > pole)
    assert crossing.any()
    assert not np.any(np.isfinite(y[:-1][crossing]) & np.isfinite(y[1:][crossing]))


def test_sampling_domain_and_constant():
    x, y = sample('sqrt(x)', -2, 2)
    assert np.isnan(y[x<0]).all()
    assert np.isfinite(y[x>0]).all()
    np.testing.assert_allclose(evaluate('3', np.array([1,2,3])), [3,3,3])


def test_ten_functions_and_bounded_cache():
    for n in range(10):
        np.testing.assert_allclose(evaluate(f'x^{n}', [1,2]), [1,2**n])
    assert parse.cache_info().maxsize == 256


def test_parser_complexity_limits():
    for source in ['x+' * 400 + 'x', 'sin(' * 30 + 'x' + ')' * 30]:
        with pytest.raises(ExpressionError):
            parse(source)
