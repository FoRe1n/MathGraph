import pytest
from graphmath.analysis.symbolic import analyze


def test_quadratic_exact_analysis():
    r = analyze('x^2-4')
    assert r['properties']['Область визначення'] == 'ℝ'
    assert r['properties']['Нулі / перетини Ox'] == '{-2, 2}'
    assert {(p['x'],p['y']) for p in r['zeros']} == {(-2,0),(2,0)}
    assert r['extrema'][0]['kind'] == 'мінімум'
    assert r['extrema'][0]['y'] == -4
    assert r['properties']['Похідна'] == '2*x'


@pytest.mark.parametrize('source,domain', [('sqrt(x)','Interval(0, ∞)'), ('log(x)','Interval.open(0, ∞)'), ('1/x','Union(Interval.open(-∞, 0), Interval.open(0, ∞))')])
def test_real_domains(source,domain):
    assert analyze(source)['properties']['Область визначення'] == domain


def test_rational_asymptotes_and_holes():
    r = analyze('1/x')
    assert r['vertical'] == [{'value':0,'exact':'0'}]
    assert r['horizontal'] == [{'value':0,'exact':'0'}]
    hole = analyze('x/x')
    assert '0' in hole['properties']['Область визначення']
    assert hole['properties']['Перетин Oy'].startswith('Не вдалося')
    assert not hole['zeros']
    assert not hole['vertical']


def test_intersections_and_parameters():
    r = analyze('a*x^2', {'a':2}, '2', {})
    assert {p['x'] for p in r['intersections']} == {-1,1}


def test_absolute_value_extremum():
    r=analyze('abs(x)')
    assert any(p['kind']=='мінімум' and p['x']==0 for p in r['extrema'])
