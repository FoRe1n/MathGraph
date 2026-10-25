"""Independent mathematical regressions found during the 1.1 stabilization audit."""
from __future__ import annotations

import math

import numpy as np
import pytest

from graphmath.core.expressions import evaluate
from graphmath.core.laboratories import (
    LABS, explanation, formula_latex, markers, number, properties, suggested_view,
)


def values(key, **changes):
    return {**{control.name:control.default for control in LABS[key].controls}, **changes}


@pytest.mark.parametrize('coefficients,root', [
    ({'a':.1,'b':.6,'c':.9}, -3),       # .1(x+3)^2
    ({'a':-.1,'b':.6,'c':-.9}, 3),     # -.1(x-3)^2
    ({'a':.2,'b':-1.2,'c':1.8}, 3),    # .2(x-3)^2
])
def test_decimal_double_roots_match_vertex_range_explanation_and_markers(coefficients, root):
    result=properties('quadratic',coefficients)
    assert result['Нулі']==f'x = {str(root).replace("-","−")}'
    assert result['Вершина']==f'({str(root).replace("-","−")}; 0)'
    assert result['Область значень']==('[0; +∞)' if coefficients['a']>0 else '(−∞; 0]')
    marker=markers(coefficients)
    assert marker['vertex'][0]['y']==0
    assert marker['zeros'][0]['x']==root
    assert '; 0)' in explanation('quadratic',coefficients)
    assert 'e−' not in explanation('quadratic',coefficients)
    viewport=suggested_view('quadratic',coefficients)
    assert viewport[0]<root<viewport[1] and viewport[2]<0<viewport[3]


def test_nonzero_decimal_discriminants_are_not_rounded_into_double_roots():
    # .1x²+.6x+.8 = .1(x+2)(x+4), whereas .1x²+.6x+1 is always positive.
    assert properties('quadratic',{'a':.1,'b':.6,'c':.8})['Нулі']=='x = −4, −2'
    assert properties('quadratic',{'a':.1,'b':.6,'c':1})['Нулі']=='немає'


@pytest.mark.parametrize('value,expected',[
    (1e-100,'1e−100'),(-1e-100,'−1e−100'),(1e-12,'1e−12'),
    (-0.0,'0'),(0.0,'0'),(1e50,'1e+50'),
])
def test_small_nonzero_numbers_are_not_reported_as_zero(value,expected):
    assert number(value)==expected


@pytest.mark.parametrize('key,changes,expected',[
    ('logarithmic', {'a':.1,'b':.1,'h':0,'k':-5}, 'x = 1e−50'),
    ('logarithmic', {'a':.1,'b':.1,'h':3,'k':-5}, 'x = 3 + 1e−50'),
    ('logarithmic_scale', {'a':.1,'b':.1,'h':3,'k':-10,'d':-2}, 'x = 3 − 5e−101'),
    ('logarithmic_scale', {'a':.1,'b':.1,'h':0,'k':-10,'d':-1}, 'x = −1e−100'),
    ('logarithmic', {'a':1,'b':.1,'h':3,'k':-5}, 'x = 3 + 1e−05'),
])
def test_logarithmic_zeros_are_not_displayed_on_the_excluded_domain_boundary(key,changes,expected):
    result=properties(key,values(key,**changes))
    assert result['Нулі']==expected
    assert result['Нулі']!='x = '+number(changes['h'])
    # These unshifted exact solutions give log_(1/10)(10^-50)=50 or
    # log_(1/10)(10^-100)=100 before applying the specified scale and offset.
    if changes['h']==0:
        root=1e-50 if key=='logarithmic' else -1e-100
        np.testing.assert_allclose(evaluate(LABS[key].expression,[root],values(key,**changes)),[0],atol=1e-12)


def test_tiny_positive_exponential_intercept_stays_inside_its_reported_range():
    actual=properties('exponential_shift',values('exponential_shift',a=1,b=5,d=5,h=10,k=0))
    assert actual['Область значень']=='(0; +∞)'
    assert actual['Перетин із віссю y']=='(0; 1,126e−35)'
    assert math.pow(5,-50)>0


@pytest.mark.parametrize('key', ['vertex','cubic','absolute','exponential_shift'])
def test_zero_multiplier_explanations_do_not_promise_horizontal_graph_motion(key):
    actual=explanation(key,values(key,a=0))
    assert 'сталу функцію' in actual
    assert 'горизонтальні параметри не змінюють' in actual


@pytest.mark.parametrize('key',['sqrt','sqrt_left','sqrt_down'])
def test_zero_root_multiplier_explanation_retains_the_half_line_domain(key):
    actual=explanation(key,values(key,a=0,h=2,k=3))
    assert 'y = 3' in actual and 'b(x − h) ≥ 0' in actual
    assert properties(key,values(key,a=0,h=2,k=3))['Парність']=='ні парна, ні непарна'


def test_zero_log_and_tangent_explanations_preserve_undefined_points():
    assert 'd(x − h) > 0' in explanation('logarithmic_scale',values('logarithmic_scale',a=0))
    assert 'Виключені точки залишаються виключеними' in explanation('tan',values('tan',a=0))


@pytest.mark.parametrize('key',['sin','cos'])
def test_zero_trigonometric_multiplier_has_no_smallest_positive_period(key):
    assert 'найменшого додатного періоду немає' in explanation(key,values(key,a=0))


def test_inverse_template_title_matches_its_scale_coefficient():
    assert 'a/x' in LABS['inverse'].title
    assert 'k/x' not in LABS['inverse'].title
    assert LABS['inverse'].expression=='a/(x-h)+k'


def test_zero_square_is_the_x_axis():
    assert 'збігається з віссю x' in explanation('square',values('square',a=0))


@pytest.mark.parametrize('key,changes,domain,range_,parity',[
    ('linear',{'k':-2,'b':3},'ℝ','ℝ','ні парна, ні непарна'),
    ('direct',{'k':-2},'ℝ','ℝ','непарна'),
    ('constant',{'c':-3},'ℝ','{−3}','парна'),
    ('inverse',{'a':-2,'h':1,'k':3},'ℝ ∖ {1}','ℝ ∖ {3}','ні парна, ні непарна'),
    ('quadratic',{'a':-1,'b':4,'c':-3},'ℝ','(−∞; 1]','ні парна, ні непарна'),
    ('square',{'a':-2},'ℝ','(−∞; 0]','парна'),
    ('vertex',{'a':-2,'h':3,'k':4},'ℝ','(−∞; 4]','ні парна, ні непарна'),
    ('cubic',{'a':-2,'h':3,'k':4},'ℝ','ℝ','ні парна, ні непарна'),
    ('absolute',{'a':-2,'h':3,'k':4},'ℝ','(−∞; 4]','ні парна, ні непарна'),
    ('sqrt',{'a':-2,'b':-3,'h':2,'k':4},'(−∞; 2]','(−∞; 4]','ні парна, ні непарна'),
    ('sqrt_left',{'a':-2,'b':-3,'h':2,'k':4},'(−∞; 2]','(−∞; 4]','ні парна, ні непарна'),
    ('sqrt_down',{'a':-2,'b':-3,'h':2,'k':4},'(−∞; 2]','(−∞; 4]','ні парна, ні непарна'),
    ('exponential',{'a':-2,'b':.5,'c':3},'ℝ','(−∞; 3)','ні парна, ні непарна'),
    ('exponential_shift',{'a':-2,'b':.5,'d':-2,'h':1,'k':3},'ℝ','(−∞; 3)','ні парна, ні непарна'),
    ('logarithmic',{'a':-2,'b':.5,'h':1,'k':3},'(1; +∞)','ℝ','ні парна, ні непарна'),
    ('logarithmic_scale',{'a':-2,'b':.5,'d':-2,'h':1,'k':3},'(−∞; 1)','ℝ','ні парна, ні непарна'),
    ('sin',{'a':-2,'b':-3,'h':0,'k':1},'ℝ','[−1; 3]','ні парна, ні непарна'),
    ('cos',{'a':-2,'b':-3,'h':0,'k':1},'ℝ','[−1; 3]','парна'),
])
def test_independent_domains_ranges_and_parity_for_reflected_translated_families(key,changes,domain,range_,parity):
    # Expectations follow elementary algebra and the symmetry of each domain;
    # they are not derived by calling the expression implementation.
    actual=properties(key,values(key,**changes))
    assert actual['Область визначення']==domain
    assert actual['Область значень']==range_
    assert actual['Парність']==parity


def test_reflected_tangent_branch_direction_and_period():
    actual=properties('tan',values('tan',a=-2,b=-3,h=0,k=1))
    assert actual['Область визначення'].startswith('ℝ ∖ {')
    assert actual['Область значень']=='ℝ'
    assert actual['Монотонність']=='зростає між сусідніми асимптотами'
    assert actual['Період']=='1,047 (радіани)'
    assert actual['Парність']=='ні парна, ні непарна'


def test_vertical_relation_is_not_assigned_function_properties():
    actual=properties('vertical',values('vertical',c=-3))
    assert 'не є функцією y = f(x)' in actual['Відношення']
    assert actual['Перетин із віссю x']=='(−3; 0)'
    assert actual['Перетин із віссю y']=='немає'
    assert not {'Парність','Область визначення','Область значень','Монотонність'} & actual.keys()


@pytest.mark.parametrize('key,changes,zeros',[
    ('vertex',{'a':.3,'h':3,'k':-2.7},'x = 0, 6'),
    ('vertex',{'a':1.2,'h':1.5,'k':-2.7},'x = 0, 3'),
    ('vertex',{'a':2.5,'h':1.4,'k':-4.9},'x = 0, 2,8'),
    ('cubic',{'a':.1,'h':4,'k':6.4},'x = 0'),
    ('absolute',{'a':3,'h':.1,'k':-.3},'x = 0, 0,2'),
    ('absolute',{'a':.1,'h':3,'k':-.3},'x = 0, 6'),
    ('sqrt',{'a':.1,'b':1,'h':-9,'k':-.3},'x = 0'),
    ('sqrt_left',{'a':.5,'b':-.2,'h':.2,'k':-.1},'x = 0'),
    ('sqrt_down',{'a':-.5,'b':-.2,'h':.2,'k':.1},'x = 0'),
    ('inverse',{'a':.3,'h':.1,'k':3},'x = 0'),
    ('logarithmic_scale',{'a':1,'b':.1,'d':-.1,'h':.1,'k':-2},'x = 0'),
    ('logarithmic_scale',{'a':1,'b':.25,'d':-1,'h':.5,'k':-.5},'x = 0'),
    ('exponential_shift',{'a':.1,'b':.1,'d':1,'h':1,'k':-1},'x = 0'),
])
def test_exact_decimal_zero_roots_do_not_become_cancellation_residues(key,changes,zeros):
    actual=properties(key,values(key,**changes))
    assert actual['Нулі']==zeros
    assert actual['Перетин із віссю y']=='(0; 0)'
