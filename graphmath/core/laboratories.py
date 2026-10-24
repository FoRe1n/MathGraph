"""Deterministic school-level function laboratories, independent of Qt.

All functions remain ordinary version-1 GraphMath function records. The optional mode metadata is additive; old documents default to custom mode.
No code execution, external service or generated explanation is used.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
import math
from graphmath.persistence.projects import Function, Parameter, Project


@dataclass(frozen=True)
class Control:
    name: str
    label: str
    minimum: float
    maximum: float
    step: float
    default: float
    base: bool = False
    nonzero: bool = False

    def values(self) -> tuple[float, ...]:
        values = tuple(round(self.minimum+i*self.step, 8) for i in range(round((self.maximum-self.minimum)/self.step)+1))
        return tuple(v for v in values if (not self.base or (v>0 and not math.isclose(v,1))) and (not self.nonzero or v != 0))

    def clamp(self, value: float) -> float:
        if not math.isfinite(value):
            return self.default
        return min(self.values(), key=lambda v: (round(abs(v-value),8), -v))


@dataclass(frozen=True)
class Laboratory:
    key: str
    title: str
    expression: str
    latex: str
    controls: tuple[Control, ...]
    view: tuple[float,float,float,float]

    def make_function(self) -> Function:
        return Function(self.expression, parameters={c.name:Parameter(c.default,c.minimum,c.maximum,c.step,c.default) for c in self.controls})


LABS = {
    'quadratic': Laboratory('quadratic','Квадратична функція','a*x^2+b*x+c', r'a x^2+b x+c', (
        Control('a','a · напрям і форма',-5,5,.1,1),
        Control('b','b · положення вершини',-10,10,.1,0),
        Control('c','c · перетин із віссю y',-10,10,.1,0)),(-6,6,-3,9)),
    'exponential': Laboratory('exponential','Показникова функція','a*b^x+c',r'a\cdot b^x+c',(
        Control('a','a · масштаб і відбиття',-5,5,.1,1),
        Control('b','b · основа степеня',.1,5,.1,2,True),
        Control('c','c · зсув угору або вниз',-10,10,.1,0)),(-5,5,-2,8)),
    'logarithmic': Laboratory('logarithmic','Логарифмічна функція','a*log(x-h)/log(b)+k',r'a\cdot\log_b(x-h)+k',(
        Control('a','a · масштаб і відбиття',-5,5,.1,1),
        Control('b','b · основа логарифма',.1,5,.1,2,True),
        Control('h','h · зсув праворуч або ліворуч',-5,5,.1,0),
        Control('k','k · зсув угору або вниз',-5,5,.1,0)),(-2,10,-5,5)),
}


# The original three templates retain their expressions, controls and defaults.
# New templates share the same lightweight controls and ordinary function records.
A = Control('a', 'a · вертикальний масштаб і відбиття', -5, 5, .1, 1)
B = Control('b', 'b · горизонтальний масштаб і відбиття', -5, 5, .1, 1, nonzero=True)
H = Control('h', 'h · горизонтальний зсув (додатне — праворуч)', -10, 10, .1, 0)
K = Control('k', 'k · вертикальний зсув (додатне — вгору)', -10, 10, .1, 0)
C = Control('c', 'c · стала координата', -10, 10, .1, 0)
S = Control('k', 'k · нахил прямої', -5, 5, .1, 1)

def _lab(key, title, expression, latex, controls, view=(-6,6,-5,5)):
    return Laboratory(key, title, expression, latex, controls, view)

LABS.update({
    'linear': _lab('linear', 'Лінійна · kx + b', 'k*x+b', r'kx+b', (S, Control('b','b · перетин із віссю y',-10,10,.1,0))),
    'direct': _lab('direct', 'Пряма пропорційність · kx', 'k*x', r'kx', (S,)),
    'constant': _lab('constant', 'Стала · y = c', 'c', 'c', (C,)),
    'vertical': _lab('vertical', 'Вертикальна пряма · x = c', 'x=c', 'x=c', (C,)),
    'inverse': _lab('inverse', 'Обернена пропорційність · k/x', 'a/(x-h)+k', r'\frac{a}{x-h}+k', (A,H,K)),
    'square': _lab('square', 'Квадрат · ax²', 'a*x^2', r'ax^2', (A,),(-6,6,-3,9)),
    'vertex': _lab('vertex', 'Парабола · a(x − h)² + k', 'a*(x-h)^2+k', r'a(x-h)^2+k', (A,H,K),(-6,6,-3,9)),
    'cubic': _lab('cubic', 'Кубічна · a(x − h)³ + k', 'a*(x-h)^3+k', r'a(x-h)^3+k', (A,H,K)),
    'absolute': _lab('absolute', 'Модуль · a|x − h| + k', 'a*abs(x-h)+k', r'a|x-h|+k', (A,H,K)),
    'sqrt': _lab('sqrt', 'Корінь · √x', 'a*sqrt(b*(x-h))+k', r'a\sqrt{b(x-h)}+k', (A,B,H,K)),
    'sqrt_left': _lab('sqrt_left', 'Корінь · √(−x)', 'a*sqrt(b*(x-h))+k', r'a\sqrt{b(x-h)}+k', (A,Control('b',B.label,-5,5,.1,-1,nonzero=True),H,K)),
    'sqrt_down': _lab('sqrt_down', 'Корінь · −√x', 'a*sqrt(b*(x-h))+k', r'a\sqrt{b(x-h)}+k', (Control('a',A.label,-5,5,.1,-1),B,H,K)),
    'exponential_shift': _lab('exponential_shift', 'Показникова · зі зсувом', 'a*exp(log(b)*d*(x-h))+k', r'a\cdot b^{d(x-h)}+k', (A,Control('b','b · основа степеня',.1,5,.1,2,True),Control('d',B.label.replace('b','d'),-5,5,.1,1,nonzero=True),H,K)),
    'logarithmic_scale': _lab('logarithmic_scale', 'Логарифмічна · з масштабом x', 'a*log(d*(x-h))/log(b)+k', r'a\log_b(d(x-h))+k', (A,Control('b','b · основа логарифма',.1,5,.1,2,True),Control('d',B.label.replace('b','d'),-5,5,.1,1,nonzero=True),H,K)),
    **{key:_lab(key,title,f'a*{key}(b*(x-h))+k',latex,(A,B,H,K)) for key,title,latex in [
        ('sin','Синус',r'a\sin(b(x-h))+k'),('cos','Косинус',r'a\cos(b(x-h))+k'),('tan','Тангенс',r'a\tan(b(x-h))+k')]},
})

GROUPS = (
    ('Прості функції', ('linear','direct','constant','vertical','inverse')),
    ('Степеневі та кореневі', ('quadratic','square','vertex','cubic','absolute','sqrt','sqrt_left','sqrt_down')),
    ('Показникові та логарифмічні', ('exponential','exponential_shift','logarithmic','logarithmic_scale')),
    ('Тригонометричні', ('sin','cos','tan')),
)


def default_project() -> Project:
    function=LABS['quadratic'].make_function()
    return Project([function],list(LABS['quadratic'].view),selected=function.id,mode='quadratic')


def identify(function: Function | None) -> str:
    if function:
        for key,lab in LABS.items():
            if (function.expression == lab.expression and set(function.parameters)=={c.name for c in lab.controls}
                and all(math.isclose(function.parameters[c.name].minimum,c.minimum)
                        and math.isclose(function.parameters[c.name].maximum,c.maximum)
                        and math.isclose(function.parameters[c.name].step,c.step)
                        and math.isclose(function.parameters[c.name].initial,c.default) for c in lab.controls)):
                values={n:p.value for n,p in function.parameters.items()}
                if all(c.minimum <= values[c.name] <= c.maximum and math.isclose(c.clamp(values[c.name]),values[c.name],abs_tol=1e-8) and (not c.base or values[c.name]>0 and not math.isclose(values[c.name],1)) and (not c.nonzero or values[c.name] != 0) for c in lab.controls):
                    return key
    return 'custom'


def validate(key: str, values: dict[str,float]) -> None:
    for c in LABS[key].controls:
        value=values[c.name]
        if not math.isfinite(value) or not c.minimum <= value <= c.maximum or (c.base and (value<=0 or math.isclose(value,1))) or (c.nonzero and value == 0):
            raise ValueError('Основа має бути додатною та не дорівнювати 1; перевірте межі коефіцієнтів.')


def number(value: float, precision: int = 4) -> str:
    return f'{0 if abs(value)<1e-12 else value:.{precision}g}'.replace('-', '−').replace('.', ',')


def explanation(key: str, v: dict[str,float], precision: int = 4) -> str:
    n=lambda value:number(value,precision)
    validate(key,v)
    if key not in ('quadratic','exponential','logarithmic'):
        return template_explanation(key,v,precision)
    a,b=v['a'],v['b']
    if key=='quadratic':
        c=v['c']
        if a==0:
            return (f'a = 0: це пряма, а не парабола (нахил b = {n(b)}). '
                    if b else f'a = 0 і b = 0: маємо сталу функцію y = {n(c)}. ') + f'Графік перетинає вісь y у точці (0; {n(c)}).'
        shape='вужча за y = x²' if abs(a)>1 else 'ширша за y = x²' if abs(a)<1 else 'такої самої ширини, як y = x²'
        direction='вгору' if a>0 else 'вниз'
        return f'Парабола відкрита {direction} і {shape}. Вершина ≈ ({n(-b/(2*a))}; {n(c-b*b/(4*a))}), вісь симетрії: x ≈ {n(-b/(2*a))}. Зміна лише c рухає графік угору або вниз.'
    if key=='exponential':
        if a==0:
            return f'a = 0: маємо сталу функцію y = {n(v["c"])}. Основа b не змінює цей графік.'
        trend='зростає' if (b>1)==(a>0) else 'спадає'
        if a<0:
            base='зростаючу' if b>1 else 'спадну'
            cause=f'від’ємне a відбиває {base} криву bˣ (b = {n(b)})'
        else:
            cause=f'b = {n(b)} > 1 та a > 0' if b>1 else f'0 < b = {n(b)} < 1 та a > 0'
        return f'Функція {trend}: {cause}. Модуль a задає вертикальний масштаб, а c — зсув угору або вниз.'
    h,k=v['h'],v['k']
    if a==0:
        return f'a = 0: y = {n(k)}, але лише за x > {n(h)}. Аргумент логарифма x − h має залишатися додатним.'
    trend='зростає' if (b>1)==(a>0) else 'спадає'
    return f'Логарифм визначений лише за x > {n(h)}: його аргумент має бути додатним. Функція {trend} за цих a та b. Коефіцієнт h зсуває графік уздовж осі x, k — уздовж осі y.'


def details(key: str, values: dict[str,float] | None = None) -> str:
    if values is not None:
        return property_text(key,values)
    if key not in ('quadratic','exponential','logarithmic'):
        return template_explanation(key,{c.name:c.default for c in LABS[key].controls})
    return {
        'quadratic': 'Вершина має координати x₀ = −b/(2a), y₀ = c − b²/(4a), якщо a ≠ 0. Зміна b змінює обидві координати вершини, тому це не просто горизонтальний зсув. Модуль a задає розтягнення по вертикалі; знак a визначає напрям віток. Нулі — дійсні розв’язки ax² + bx + c = 0.',
        'exponential': 'Основа завжди додатна й не дорівнює 1. Наприклад, 2ˣ зростає, а 0,5ˣ спадає. За a < 0 напрям монотонності змінюється через відбиття відносно осі x. За a ≠ 0 пряма y = c — горизонтальна асимптота; перетин із віссю y має ординату a + c.',
        'logarithmic': 'Для логарифма потрібні b > 0, b ≠ 1 та x − h > 0. Точка (h + 1; k) завжди належить графіку. За a ≠ 0 пряма x = h — вертикальна асимптота. За b > 1 базовий логарифм зростає, за 0 < b < 1 — спадає; від’ємне a змінює цей напрям. Навіть за a = 0 початкова формула не визначена при x ≤ h.',
    }[key]


def markers(v: dict[str,float], precision: int = 4) -> dict:
    n=lambda value:number(value,precision)
    a,b,c=(v[n] for n in ['a','b','c'])
    result={'vertex':[], 'zeros':[], 'intercept':[{'x':0.,'y':c,'exact':f'(0; {n(c)})'}], 'symmetry':None}
    if a:
        x=-b/(2*a);y=c-b*b/(4*a)
        result['vertex']=[{'x':x,'y':y,'exact':f'Вершина ≈ ({n(x)}; {n(y)})'}]
        result['symmetry']=x
        # Slider decimals represent exact school coefficients; avoid losing a
        # double root to floating cancellation (e.g. .1*x²+.6*x+.9).
        exact_disc=Fraction(str(b))**2-4*Fraction(str(a))*Fraction(str(c))
        disc=float(exact_disc)
        if exact_disc>=0:
            # Stable quadratic roots avoid cancellation for disparate coefficients.
            if disc==0:
                roots=[x]
            else:
                q=-.5*(b+math.copysign(math.sqrt(disc),b))
                roots=[q/a,c/q] if q else [0.]
            result['zeros']=[{'x':r,'y':0.,'exact':f'Нуль ≈ ({n(r)}; 0)'} for r in roots]
    elif b:
        x=-c/b
        result['zeros']=[{'x':x,'y':0.,'exact':f'Нуль ≈ ({n(x)}; 0)'}]
    return result


def formula_latex(key: str, values: dict[str,float], precision: int = 5) -> str:
    """Numeric school notation without repeated symbolic simplification."""
    def n(value):return f'{abs(value):.{precision}g}'.replace('.', '{,}')
    def term(value, suffix='', first=False):
        if value==0:return ''
        sign='-' if value<0 else '' if first else '+'
        coefficient='' if suffix and abs(value)==1 else n(value)
        return sign+coefficient+suffix
    if key not in ('quadratic','exponential','logarithmic'):
        return template_formula(key,values,precision)
    a=values['a']
    if key=='quadratic':
        parts=[]
        for value,suffix in [(a,'x^{2}'),(values['b'],'x'),(values['c'],'')]:
            text=term(value,suffix,not parts)
            if text:parts.append(text)
        return ''.join(parts) or '0'
    base=n(values['b']);sign='-' if a<0 else ''
    factor='' if abs(a)==1 else n(a)+r'\cdot '
    if key=='exponential':
        main=sign+factor+r'\left('+base+r'\right)^{x}' if a else ''
        return main+term(values['c'],first=not main) or '0'
    h=values['h'];arg='x'+term(-h)
    if not a:
        k=values['k'];constant=('-' if k<0 else '')+n(k)
        signed_h=('-' if h<0 else '')+n(h)
        return constant+r'\quad (x>'+signed_h+')'
    main=sign+factor+r'\log_{'+base+r'}\left('+arg+r'\right)'
    return main+term(values['k'])


def suggested_view(key: str, values: dict[str,float]) -> list[float]:
    """A useful reset view; coefficient changes themselves never reset the view."""
    if key not in ('quadratic','exponential','logarithmic'):
        h=values.get('h',values.get('c',0) if key=='vertical' else 0)
        k=values.get('k',values.get('c',0) if key=='constant' else 0)
        return [h-6,h+6,k-5,k+5]
    a=values['a']
    if key=='quadratic':
        b,c=values['b'],values['c']
        if a:
            x=-b/(2*a);y=c-b*b/(4*a)
            return [x-6,x+6,y-3 if a>0 else y-9,y+9 if a>0 else y+3]
        ends=[-6*b+c,6*b+c]
        return [-6,6,min(ends)-3,max(ends)+3]
    if key=='exponential':
        c=values['c'];span=max(10,abs(a)*6)
        return [-5,5,c-span*(.2 if a>=0 else .8),c+span*(.8 if a>=0 else .2)]
    h,k=values['h'],values['k']
    span=max(5,abs(a*math.log(4)/math.log(values['b'])))
    return [h-2,h+10,k-span,k+span]


def template_explanation(key, v, precision=4):
    n=lambda x:number(x,precision)
    if key=='vertical':
        return f"Вертикальна пряма x = {n(v['c'])}. Це відношення, а не функція y = f(x): одному x відповідає багато y."
    if key in ('linear','direct'):
        slope=v['k']
        trend='зростає' if slope>0 else 'спадає' if slope<0 else 'є сталою'
        return f'Пряма {trend}. Коефіцієнт k задає нахил; додатне k піднімає пряму праворуч, від’ємне — опускає.'
    if key=='constant':return f"Для кожного x значення y = {n(v['c'])}. Пряма горизонтальна."
    if key=='inverse':return f"Дві вітки за a ≠ 0; x = {n(v['h'])} виключено з області визначення. h рухає графік праворуч, k — вгору. За a = 0 залишається горизонтальна пряма з виколотою точкою."
    text='Додатне h зсуває графік праворуч, додатне k — вгору. Модуль a задає вертикальний масштаб; від’ємне a відбиває графік відносно осі x перед зсувом.'
    if key=='square':return 'Знак a визначає напрям віток; |a| — вертикальний масштаб. Вершина (0; 0), якщо a ≠ 0.'
    if key.startswith('sqrt') or key in ('sin','cos','tan','exponential_shift','logarithmic_scale'):
        symbol='d' if key in ('exponential_shift','logarithmic_scale') else 'b'
        text+=f' Горизонтальний масштаб — 1/|{symbol}|; від’ємне {symbol} відбиває базовий графік відносно осі y перед зсувом.'
    if key in ('sin','cos','tan'):
        text+=' Кути вимірюються в радіанах.'
        text+=f" Період ≈ {n((math.pi if key=='tan' else 2*math.pi)/abs(v['b']))}." if v['a'] else ' За a = 0 формула стала на своїй області визначення.'
        if key=='tan':text+=' У точках b(x − h) = π/2 + nπ значення не існує; вітки не з’єднуються.'
    if key.startswith('sqrt'):text+=' Підкореневий вираз має бути невід’ємним.'
    if key=='logarithmic_scale':text+=' Аргумент d(x − h) має бути додатним, основа b > 0 та b ≠ 1.'
    if key=='exponential_shift':text+=' Основа b > 0 та b ≠ 1; за 0 < b < 1 базовий графік спадає.'
    return text


def properties(key: str, v: dict[str,float]) -> dict[str,str]:
    """Analytical properties of the actual coefficients, retaining formula domains.

    No symbolic solver runs in the slider path. Zero multipliers do not remove
    holes in rational, logarithmic, square-root or tangent expressions.
    """
    validate(key,v)
    n=number
    a=v.get('a',1);h=v.get('h',0);k=v.get('k',0);b=v.get('b',1)
    result={'Область визначення':'ℝ','Область значень':'ℝ'}
    even='парна';odd='непарна';neither='ні парна, ні непарна'
    parity=neither
    def constant(value):
        result['Область значень']='{'+n(value)+'}'
        result['Монотонність']='стала на області визначення'
    def trend(value):return 'зростає' if value>0 else 'спадає'
    def half(value,up,closed=False):
        return ('[' if closed else '(')+n(value)+'; +∞)' if up else '(−∞; '+n(value)+(']' if closed else ')')
    if key=='vertical':
        return {'Відношення':f"x = {n(v['c'])}; не є функцією y = f(x)",
                'Точки':f"({n(v['c'])}; y), де y ∈ ℝ",'Перетин із віссю x':f"({n(v['c'])}; 0)",
                'Перетин із віссю y':'уся пряма' if v['c']==0 else 'немає'}
    if key in ('linear','direct','constant'):
        slope=v.get('k',0) if key!='constant' else 0
        offset=v.get('b',0) if key!='constant' else v['c']
        if slope:
            result['Монотонність']=trend(slope)+' на ℝ'
            result['Нулі']='x = '+n(-offset/slope)
            parity=odd if offset==0 else neither
        else:
            constant(offset);parity='парна і непарна' if offset==0 else even
            result['Нулі']='усі x ∈ ℝ' if offset==0 else 'немає'
        result['Перетин із віссю y']=f'(0; {n(offset)})'
    elif key in ('quadratic','square','vertex','absolute'):
        if key=='quadratic':
            if a==0:
                offset=v['c']
                if b:
                    result['Монотонність']=trend(b)+' на ℝ'
                    result['Нулі']='x = '+n(-offset/b)
                    parity=odd if offset==0 else neither
                else:
                    constant(offset);parity='парна і непарна' if offset==0 else even
                    result['Нулі']='усі x ∈ ℝ' if offset==0 else 'немає'
                result['Перетин із віссю y']=f'(0; {n(offset)})'
                result['Парність']=parity
                return result
            h=-b/(2*a);k=v['c']-b*b/(4*a)
        if a==0:
            constant(k);parity='парна і непарна' if k==0 else even
        else:
            result['Область значень']=half(k,a>0,True)
            result['Монотонність']=f"{'спадає' if a>0 else 'зростає'} на (−∞; {n(h)}]; {'зростає' if a>0 else 'спадає'} на [{n(h)}; +∞)"
            result['Вершина']=f'({n(h)}; {n(k)})'
            parity=even if h==0 else neither
        if a and -k/a>=0:
            distance=-k/a if key=='absolute' else math.sqrt(-k/a)
            result['Нулі']='x = '+', '.join(n(x) for x in sorted({h-distance,h+distance}))
        else:result['Нулі']='усі x ∈ ℝ' if not a and k==0 else 'немає'
        y0=a*(abs(h) if key=='absolute' else h*h)+k
        result['Перетин із віссю y']=f'(0; {n(y0)})'
    elif key=='cubic':
        if not a:constant(k)
        else:
            result['Монотонність']=trend(a)+' на ℝ'
            root=math.copysign(abs(-k/a)**(1/3),-k/a)+h
            result['Нулі']='x = '+n(root)
        parity=('парна і непарна' if not k else even) if not a else odd if h==0 and k==0 else neither
        if not a:result['Нулі']='усі x ∈ ℝ' if k==0 else 'немає'
        result['Перетин із віссю y']=f'(0; {n(k-a*h**3)})'
    elif key=='inverse':
        result['Область визначення']='ℝ ∖ {'+n(h)+'}'
        if a:
            result['Область значень']='ℝ ∖ {'+n(k)+'}'
            result['Монотонність']=f"{trend(-a)} на кожному з інтервалів (−∞; {n(h)}) та ({n(h)}; +∞)"
            result['Асимптоти']=f'x = {n(h)}; y = {n(k)}'
        else:constant(k)
        parity=(odd if k==0 else neither) if a else ('парна і непарна' if k==0 else even)
        if h!=0:parity=neither
        result['Нулі']='x = '+n(h-a/k) if a and k else 'усі x з області визначення' if not a and k==0 else 'немає'
        result['Перетин із віссю y']='немає' if h==0 else f'(0; {n(k-a/h)})'
    elif key.startswith('sqrt'):
        result['Область визначення']=half(h,b>0,True)
        result['Область значень']=half(k,a>0,True)
        if not a:constant(k)
        else:result['Монотонність']=trend(a*b)+' на області визначення'
        if a and -k/a>=0:result['Нулі']='x = '+n(h+(-k/a)**2/b)
        else:result['Нулі']='усі x з області визначення' if not a and k==0 else 'немає'
        result['Перетин із віссю y']=f'(0; {n(a*math.sqrt(-b*h)+k)})' if -b*h>=0 else 'немає'
    elif key in ('exponential','exponential_shift'):
        if key=='exponential':k=v['c'];h=0;d=1
        else:d=v['d']
        if not a:
            constant(k);parity='парна і непарна' if k==0 else even
        else:
            result['Область значень']=half(k,a>0)
            result['Монотонність']=trend(a*math.log(b)*d)+' на ℝ'
            result['Асимптоти']='y = '+n(k)
        result['Нулі']='x = '+n(h+math.log(-k/a)/(math.log(b)*d)) if a and -k/a>0 else 'усі x ∈ ℝ' if not a and k==0 else 'немає'
        result['Перетин із віссю y']=f'(0; {n(a*b**(-d*h)+k)})'
    elif key in ('logarithmic','logarithmic_scale'):
        d=v.get('d',1)
        result['Область визначення']=half(h,d>0)
        if not a:constant(k)
        else:
            result['Монотонність']=trend(a*d/math.log(b))+' на області визначення'
            result['Асимптоти']='x = '+n(h)
        result['Нулі']='x = '+n(h+b**(-k/a)/d) if a else 'усі x з області визначення' if k==0 else 'немає'
        result['Перетин із віссю y']=f'(0; {n(a*math.log(-d*h)/math.log(b)+k)})' if -d*h>0 else 'немає'
    else:  # sin, cos, tan
        phase=b*h
        zero=lambda x:math.isclose(x,0,abs_tol=1e-10)
        if key=='tan':
            result['Область визначення']=f'ℝ ∖ {{h + (π/2 + nπ)/b : n ∈ ℤ}}; h = {n(h)}, b = {n(b)}'
            if a:
                result['Асимптоти']='x = h + (π/2 + nπ)/b, n ∈ ℤ'
                result['Монотонність']=trend(a*b)+' між сусідніми асимптотами'
                parity=odd if k==0 and zero(math.sin(2*phase)) else neither
            else:
                constant(k)
                if zero(math.sin(2*phase)):parity='парна і непарна' if k==0 else even
        else:
            result['Область значень']=f'[{n(k-abs(a))}; {n(k+abs(a))}]'
            if not a:constant(k);parity='парна і непарна' if k==0 else even
            else:
                result['Монотонність']=('зростає там, де a·b·cos(b(x − h)) > 0; спадає, де цей вираз < 0' if key=='sin' else 'зростає там, де −a·b·sin(b(x − h)) > 0; спадає, де цей вираз < 0')
                parity=even if zero(math.cos(phase) if key=='sin' else math.sin(phase)) else odd if k==0 and zero(math.sin(phase) if key=='sin' else math.cos(phase)) else neither
        if a:result['Період']=n((math.pi if key=='tan' else 2*math.pi)/abs(b))+' (радіани)'
        elif key=='tan':result['Період']=n(math.pi/abs(b))+' (через періодичні пропуски області визначення)'
        else:result['Період']='будь-яке додатне число; найменшого немає'
        if a:
            target=-k/a
            if key=='tan':result['Нулі']=f'x = h + (arctan({n(target)}) + nπ)/b, n ∈ ℤ'
            elif abs(target)>1:result['Нулі']='немає'
            elif key=='sin':result['Нулі']=f'x = h + ((−1)ⁿ arcsin({n(target)}) + nπ)/b, n ∈ ℤ'
            else:result['Нулі']=f'x = h + (±arccos({n(target)}) + 2nπ)/b, n ∈ ℤ'
        else:result['Нулі']='усі x з області визначення' if k==0 else 'немає'
        y0={'sin':math.sin,'cos':math.cos,'tan':math.tan}[key](-phase)*a+k
        result['Перетин із віссю y']='немає' if key=='tan' and zero(math.cos(phase)) else f'(0; {n(y0)})'
    result['Парність']=parity
    return result


def property_text(key, values):
    return LABS[key].title+'\n\nЧислові характеристики округлено до чотирьох значущих цифр.\n\n'+'\n'.join(f'{name}: {text}.' for name,text in properties(key,values).items())+'\n\n'+explanation(key,values)



def template_formula(key, v, precision=5):
    """Keep pedagogical transformation form; never simplify away domain holes."""
    def signed(value):return f'{value:.{precision}g}'.replace('.', '{,}')
    def addition(value):return ('+' if value>0 else '')+signed(value) if value else ''
    def factor(value):return '' if value==1 else '-' if value==-1 else signed(value)+r'\cdot '
    def argument(scale, shift):
        arg='x'+addition(-shift)
        if scale==1:return arg
        return factor(scale)+r'\left('+arg+r'\right)'
    if key=='vertical':return 'x='+signed(v['c'])
    if key=='constant':return signed(v['c'])
    if key in ('linear','direct'):
        slope=v['k'];offset=v.get('b',0)
        return ((factor(slope)+'x') if slope else '')+addition(offset) if slope else signed(offset)
    a=v['a'];h=v.get('h',0);k=v.get('k',0)
    arg='x'+addition(-h)
    if key=='inverse':main=r'\frac{'+signed(a)+'}{'+arg+'}'
    elif key in ('square','vertex','cubic'):
        power='3' if key=='cubic' else '2'
        main=factor(a)+(r'\left('+arg+r'\right)' if h else 'x')+'^{'+power+'}'
    elif key=='absolute':main=factor(a)+r'\left|'+arg+r'\right|'
    elif key.startswith('sqrt'):main=factor(a)+r'\sqrt{'+argument(v['b'],h)+'}'
    elif key in ('sin','cos','tan'):main=factor(a)+'\\'+key+r'\left('+argument(v['b'],h)+r'\right)'
    elif key=='exponential_shift':main=factor(a)+r'\left('+signed(v['b'])+r'\right)^{'+argument(v['d'],h)+'}'
    else:main=factor(a)+r'\log_{'+signed(v['b'])+r'}\left('+argument(v['d'],h)+r'\right)'
    return main+addition(k)
