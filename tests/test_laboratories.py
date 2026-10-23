import math
import numpy as np
import pytest
from graphmath.core.laboratories import LABS,default_project,identify,explanation,markers,validate
from graphmath.core.expressions import evaluate,parse,ExpressionError
from graphmath.persistence.projects import save,load


def values(key):return {c.name:c.default for c in LABS[key].controls}


def test_default_quadratic():
    p=default_project();f=p.functions[0]
    assert identify(f)=='quadratic'
    assert [f.parameters[n].value for n in ['a','b','c']]==[1,0,0]
    np.testing.assert_allclose(evaluate(f.expression,[0,1,2,-2],values('quadratic')),[0,1,4,4])


@pytest.mark.parametrize('a,b,c,expected',[(2,0,0,[0,2,8]),(-1,0,0,[0,-1,-4]),(0,2,1,[1,3,5]),(0,0,3,[3,3,3]),(1,2,-3,[-3,0,5])])
def test_quadratic_changes(a,b,c,expected):
    np.testing.assert_allclose(evaluate(LABS['quadratic'].expression,[0,1,2],{'a':a,'b':b,'c':c}),expected)


@pytest.mark.parametrize('base',[.1,.5,.9,1.1,2,5])
def test_exponential_and_logarithmic_values(base):
    e=values('exponential');e['b']=base
    np.testing.assert_allclose(evaluate(LABS['exponential'].expression,[0,1,2],e),[1,base,base**2])
    l=values('logarithmic');l.update(b=base,h=2,k=3,a=-2)
    np.testing.assert_allclose(evaluate(LABS['logarithmic'].expression,[3,2+base],l),[3,1],atol=1e-10)
    assert np.isnan(evaluate(LABS['logarithmic'].expression,[-1,0,2],l)).all()


@pytest.mark.parametrize('base',[-2,0,1,float('nan')])
@pytest.mark.parametrize('key',['exponential','logarithmic'])
def test_invalid_bases(key,base):
    v=values(key);v['b']=base
    with pytest.raises(ValueError):validate(key,v)


def test_base_controls_never_produce_one():
    for key in ['exponential','logarithmic']:
        c=next(c for c in LABS[key].controls if c.name=='b')
        assert 1 not in c.values() and min(c.values())>0
        assert c.clamp(1)==1.1
        assert c.clamp(-2)>0


def test_explanations_respect_sign_and_degeneracy():
    q=values('quadratic');q.update(a=-2,b=4,c=3)
    assert 'вниз' in explanation('quadratic',q)
    assert 'x ≈ 1' in explanation('quadratic',q)
    assert 'горизонталь' not in explanation('quadratic',q)
    q['a']=0
    assert 'не парабола' in explanation('quadratic',q)
    for base,a,trend in [(2,1,'зростає'),(.5,1,'спадає'),(2,-1,'спадає'),(.5,-1,'зростає')]:
        e=values('exponential');e.update(a=a,b=base)
        assert f'Функція {trend}' in explanation('exponential',e)
        l=values('logarithmic');l.update(a=a,b=base)
        assert f'Функція {trend}' in explanation('logarithmic',l)
    l.update(a=0,h=2)
    assert 'лише за x > 2' in explanation('logarithmic',l)
    assert np.isnan(evaluate(LABS['logarithmic'].expression,[1,2],l)).all()


def test_quadratic_markers():
    m=markers({'a':1,'b':-4,'c':3})
    assert m['vertex'][0]['x']==2 and m['vertex'][0]['y']==-1
    assert m['symmetry']==2
    assert {p['x'] for p in m['zeros']}=={1,3}
    assert markers({'a':0,'b':2,'c':1})['zeros'][0]['x']==-.5
    assert not markers({'a':0,'b':0,'c':1})['zeros']


@pytest.mark.parametrize('key',list(LABS))
def test_lab_project_uses_unchanged_format(key,tmp_path):
    p=default_project();f=LABS[key].make_function();p.functions.append(f);p.selected=f.id
    path=tmp_path/'навчання.graphmath';save(p,path)
    restored=load(path)
    assert restored.to_dict()==p.to_dict()
    assert restored.to_dict()['version']==1
    assert identify(restored.functions[-1])==key


@pytest.mark.parametrize('source',['2x+1','x²−4','(x+1)(x-1)','x⁻¹','2sin(x)','2π*x'])
def test_safe_school_notation(source):
    assert np.isfinite(evaluate(source,[1,2])).all()


@pytest.mark.parametrize('source',['xy','sin x','x.__class__','2__import__("os")','x[0]'])
def test_ambiguous_or_unsafe_input_remains_rejected(source):
    with pytest.raises(ExpressionError):parse(source)


def test_numeric_math_preview_notation():
    from graphmath.core.laboratories import formula_latex
    assert formula_latex('quadratic',{'a':1,'b':0,'c':0})=='x^{2}'
    assert formula_latex('quadratic',{'a':0,'b':2,'c':-1})=='2x-1'
    assert r'\log_{2}' in formula_latex('logarithmic',values('logarithmic'))
    l=values('logarithmic');l.update(a=0,h=2,k=-1)
    assert 'x>2' in formula_latex('logarithmic',l)


def test_reset_views_follow_current_function():
    from graphmath.core.laboratories import suggested_view
    for a in [-2,1]:
        v={'a':a,'b':-4,'c':-8};view=suggested_view('quadratic',v)
        x=-v['b']/(2*a);y=v['c']-v['b']**2/(4*a)
        assert view[0]<x<view[1] and view[2]<y<view[3]
    view=suggested_view('logarithmic',{'a':-2,'b':.5,'h':4,'k':5})
    assert view[0]<4<view[1] and view[2]<5<view[3]


def test_custom_coefficient_bounds_are_not_mistaken_for_lab_defaults():
    from graphmath.persistence.projects import Function,Parameter
    f=Function('a*x^2+b*x+c',parameters={n:Parameter() for n in ['a','b','c']})
    assert identify(f)=='custom'
