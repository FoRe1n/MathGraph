"""Analytical and desktop regressions for the NMT curriculum templates."""
import math
from pathlib import Path
import numpy as np
import pytest
from PySide6.QtCore import QSettings, Qt
from graphmath.core.expressions import evaluate, parse, relation_x, ExpressionError
from graphmath.core.laboratories import LABS, properties, explanation, formula_latex, validate, identify
from graphmath.persistence.projects import Project, save, load
from graphmath.plotting.sampling import sample


def values(key, **changes):
    return {**{c.name:c.default for c in LABS[key].controls},**changes}


@pytest.mark.parametrize('key,x,expected',[
    ('linear',[-1,0,2],[-1,0,2]),('direct',[-2,0,3],[-2,0,3]),
    ('constant',[-3,0,7],[0,0,0]),('inverse',[-2,1,2],[-.5,1,.5]),
    ('square',[-2,0,3],[4,0,9]),('vertex',[-2,0,3],[4,0,9]),
    ('cubic',[-2,0,3],[-8,0,27]),('absolute',[-2,0,3],[2,0,3]),
    ('sqrt',[0,1,4],[0,1,2]),('sqrt_left',[-4,-1,0],[2,1,0]),
    ('sqrt_down',[0,1,4],[0,-1,-2]),
    ('exponential_shift',[-1,0,2],[.5,1,4]),
    ('logarithmic_scale',[.5,1,4],[-1,0,2]),
    ('sin',[0,math.pi/2,math.pi],[0,1,0]),
    ('cos',[0,math.pi/2,math.pi],[1,0,-1]),
    ('tan',[-math.pi/4,0,math.pi/4],[-1,0,1]),
])
def test_template_points(key,x,expected):
    np.testing.assert_allclose(evaluate(LABS[key].expression,x,values(key)),expected,atol=1e-12)


@pytest.mark.parametrize('key',list(LABS))
def test_every_template_roundtrip_explanation_and_preview(key,tmp_path):
    f=LABS[key].make_function();p=Project([f],list(LABS[key].view),selected=f.id,mode=key)
    path=tmp_path/(key+'.graphmath');save(p,path);restored=load(path)
    assert restored.to_dict()==p.to_dict()
    assert identify(restored.functions[0])==key
    assert properties(key,values(key)) and explanation(key,values(key)) and formula_latex(key,values(key))
    # Extremal and zero coefficients are valid classroom states, too.
    for c in LABS[key].controls:
        for value in (c.values()[0], c.values()[-1], 0):
            if value not in c.values():continue
            v=values(key,**{c.name:value})
            assert properties(key,v) and explanation(key,v)


@pytest.mark.parametrize('key',['linear','direct'])
def test_slopes(key):
    v=values(key,k=-2)
    assert 'спадає' in properties(key,v)['Монотонність']
    np.testing.assert_allclose(evaluate(LABS[key].expression,[-1,1],v),[2,-2])


@pytest.mark.parametrize('key',['vertex','cubic','absolute','sqrt','sin','cos','tan','exponential_shift','logarithmic_scale','inverse'])
def test_translations_scaling_and_reflections(key):
    base=values(key);moved=values(key,a=-2,h=3,k=4)
    xs=np.array([.2,.4,.7,1.2])
    np.testing.assert_allclose(evaluate(LABS[key].expression,xs+3,moved),
                               -2*evaluate(LABS[key].expression,xs,base)+4,atol=1e-10)


@pytest.mark.parametrize('key',['sqrt','sqrt_left','sqrt_down'])
def test_root_domains_and_horizontal_reflection(key):
    v=values(key,b=-2,h=3,k=1)
    assert np.isnan(evaluate(LABS[key].expression,[3.1,4],v)).all()
    np.testing.assert_allclose(evaluate(LABS[key].expression,[3,1],v),[1,1+2*v['a']])
    assert properties(key,v)['Область визначення']=='(−∞; 3]'


def test_reflected_log_domain_and_zero_multiplier():
    v=values('logarithmic_scale',d=-2,h=3,a=0,k=4)
    np.testing.assert_allclose(evaluate(LABS['logarithmic_scale'].expression,[1,2],v),[4,4])
    assert np.isnan(evaluate(LABS['logarithmic_scale'].expression,[3,4],v)).all()
    assert properties('logarithmic_scale',v)['Область визначення']=='(−∞; 3)'


@pytest.mark.parametrize('key',['exponential_shift','logarithmic_scale'])
@pytest.mark.parametrize('base',[0,1,-1,float('nan')])
def test_transformed_base_validation(key,base):
    with pytest.raises(ValueError):validate(key,values(key,b=base))


@pytest.mark.parametrize('key',['sqrt','sin','cos','tan','exponential_shift','logarithmic_scale'])
def test_horizontal_scale_never_zero(key):
    name='d' if key.endswith(('shift','scale')) else 'b'
    c=next(c for c in LABS[key].controls if c.name==name)
    assert 0 not in c.values() and c.clamp(0)!=0
    with pytest.raises(ValueError):validate(key,values(key,**{name:0}))


def test_vertical_relation_is_never_a_y_function():
    expr=parse('x = c');assert expr.relation and expr.parameters==('c',)
    assert relation_x('x=c',{'c':-3})==-3
    with pytest.raises(ExpressionError):evaluate('x=c',[0,1],{'c':3})
    with pytest.raises(ExpressionError):parse('x=x+1')
    with pytest.raises(ExpressionError):parse('x=__import__("os")')
    assert 'Парність' not in properties('vertical',values('vertical'))


@pytest.mark.parametrize('key,changes,parity',[
    ('vertex',{},'парна'),('vertex',{'h':3},'ні парна, ні непарна'),
    ('cubic',{},'непарна'),('cubic',{'k':2},'ні парна, ні непарна'),
    ('absolute',{},'парна'),('inverse',{},'непарна'),
    ('inverse',{'h':2},'ні парна, ні непарна'),
    ('sqrt',{},'ні парна, ні непарна'),('linear',{'k':-2},'непарна'),
    ('sin',{},'непарна'),('cos',{},'парна'),('tan',{},'непарна'),
    ('sin',{'h':1},'ні парна, ні непарна'),
    ('constant',{},'парна і непарна'),('constant',{'c':3},'парна'),
])
def test_actual_parity(key,changes,parity):
    assert properties(key,values(key,**changes))['Парність']==parity


@pytest.mark.parametrize('key',['inverse','tan'])
def test_discontinuity_paths_are_broken(key):
    v=values(key,h=.37)
    xx,yy=sample(LABS[key].expression,-5,5,v,pixels=1800)
    poles=[.37] if key=='inverse' else [.37+math.pi/2+n*math.pi for n in range(-2,2)]
    for pole in poles:
        if not xx[0]<pole<xx[-1]:continue
        i=np.searchsorted(xx,pole)
        assert np.isnan(yy[max(0,i-1):i+2]).any()
    if key=='tan':assert np.isnan(evaluate(LABS[key].expression,[.37+math.pi/2],v)).all()


@pytest.fixture
def window(qtbot,tmp_path):
    from graphmath.ui.window import MainWindow
    w=MainWindow(QSettings(str(tmp_path/'nmt.ini'),QSettings.IniFormat))
    qtbot.addWidget(w,before_close_func=lambda w:setattr(w,'confirm_discard',lambda:True))
    w.show();qtbot.wait(200)
    return w


def choose(w,key):w.mode_selector.setCurrentIndex(w.mode_selector.findData(key))


@pytest.mark.parametrize('key',list(LABS))
def test_real_ui_templates(window,qtbot,key):
    choose(window,key);qtbot.wait(180)
    assert window.mode==key and identify(window.current_function())==key
    assert window.learning.formula.pixmap() is not None and not window.learning.formula.pixmap().isNull()
    assert window.learning.numeric.pixmap() is not None and not window.learning.numeric.pixmap().isNull()
    view=window.canvas.current_view();controls={k:id(c) for k,c in window.learning.controls.items()}
    c=next(iter(window.learning.controls.values()));c.slider.setValue(c.slider.maximum())
    qtbot.wait(180)
    np.testing.assert_allclose(window.canvas.current_view(),view)
    assert controls=={k:id(c) for k,c in window.learning.controls.items()}
    assert window.canvas.curves[window.project.selected].getData()[0].size>0


def test_range_validation_and_coordinate_inspection(window,qtbot):
    assert window.range_panel.isHidden()
    before=window.canvas.current_view()
    for field,value in zip(window.range_fields.values(),[2,-2,-3,3]):field.setValue(value)
    assert not window.apply_ranges()
    np.testing.assert_allclose(window.canvas.current_view(),before)
    for field,value in zip(window.range_fields.values(),[-2,4,-3,8]):field.setValue(value)
    assert window.apply_ranges()
    np.testing.assert_allclose(window.canvas.current_view(),[-2,4,-3,8])
    window.inspect_x.setValue(2);window.inspect_coordinate();assert '4' in window.inspect_result.text()
    window.reset_view();assert window.canvas.current_view()!=[-2,4,-3,8]


def test_beginner_examples_parameters_and_management(window,qtbot):
    choose(window,'custom')
    for expression,button in window.example_buttons.items():
        qtbot.mouseClick(button,Qt.LeftButton)
        assert window.current_function().expression==expression
        assert parse(expression)
    window.use_example('a*(x-h)^2+k')
    assert set(window.current_function().parameters)=={'a','h','k'}
    assert window.current_function().parameters['h'].value==0
    assert window.parameter_layout.count()==4  # heading and three sliders, no x slider
    f=window.current_function();window.visibility(f.id,False);assert not window.canvas.curves[f.id].isVisible()
    window.visibility(f.id,True);window.recolor(f.id,'#123456');assert f.color=='#123456'
    count=len(window.project.functions);window.add_function();assert len(window.project.functions)==count+1
    window.remove_function(window.project.selected);assert len(window.project.functions)==count


@pytest.mark.parametrize('suffix',['png','svg','pdf'])
def test_vertical_render_export_and_fit(window,qtbot,tmp_path,suffix):
    from graphmath.plotting.export import export_graph
    choose(window,'vertical');window.lab_coefficient_changed('c',3)
    window.canvas.flush_refresh();xx,yy=window.canvas.curves[window.project.selected].getData()
    np.testing.assert_allclose(xx,[3,3]);np.testing.assert_allclose(yy,window.canvas.current_view()[2:])
    window.canvas.fit_selected();qtbot.wait(200)
    assert window.canvas.current_view()[0]<3<window.canvas.current_view()[1]
    export_graph(window.canvas,str(tmp_path/f'vertical.{suffix}'))
    assert (tmp_path/f'vertical.{suffix}').stat().st_size>100
    window.investigate();assert 'відношення' in window.inspector.status.text()


def test_degenerate_standard_quadratic_uses_full_original_slope_range():
    result=properties('quadratic',{'a':0,'b':10,'c':-10})
    assert result['Нулі']=='x = 1' and result['Монотонність']=='зростає на ℝ'


def test_numeric_formula_preserves_readable_transformation_form():
    formula=formula_latex('vertex',values('vertex',h=3,k=2))
    assert 'x-3' in formula and '0{,}333' not in formula
    assert formula_latex('vertical',values('vertical',c=-3))=='x=-3'



def test_analysis_rejects_vertical_relations_as_functions():
    from graphmath.analysis.symbolic import analyze
    with pytest.raises(ExpressionError,match='відношення'):analyze('x=c',{'c':3})
    with pytest.raises(ExpressionError,match='дві функції'):analyze('x^2',other='x=c',other_parameters={'c':3})


def test_invalid_comparison_formula_is_reported_safely(window):
    choose(window,'custom');window.add_function()
    invalid=window.current_function();window.edit_function(invalid.id,'sin(')
    window.select(window.project.functions[0].id)
    window.inspector.other.setCurrentIndex(window.inspector.other.findData(invalid.id))
    window.investigate()
    assert 'дужки' in window.inspector.status.text()
    assert window.inspector.process is None



def test_custom_vertical_relation_label_is_not_a_function(window):
    choose(window,'custom');window.use_example('x = 3')
    row=window.rows[window.project.selected]
    assert row.kind_label.text()=='Відношення x = c'
    assert 'f(x)' not in window.active_label.text()
    window.use_example('x^2');assert row.kind_label.text().startswith('f')
