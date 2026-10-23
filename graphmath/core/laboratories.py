"""Deterministic school-level function laboratories, independent of Qt.

All functions remain ordinary version-1 GraphMath function records. The optional mode metadata is additive; old documents default to custom mode.
No code execution, external service or generated explanation is used.
"""
from __future__ import annotations
from dataclasses import dataclass
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

    def values(self) -> tuple[float, ...]:
        values = tuple(round(self.minimum+i*self.step, 8) for i in range(round((self.maximum-self.minimum)/self.step)+1))
        return tuple(v for v in values if not self.base or (v>0 and not math.isclose(v,1)))

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
                if all(c.minimum <= values[c.name] <= c.maximum and math.isclose(c.clamp(values[c.name]),values[c.name],abs_tol=1e-8) and (not c.base or values[c.name]>0 and not math.isclose(values[c.name],1)) for c in lab.controls):
                    return key
    return 'custom'


def validate(key: str, values: dict[str,float]) -> None:
    for c in LABS[key].controls:
        value=values[c.name]
        if not math.isfinite(value) or not c.minimum <= value <= c.maximum or (c.base and (value<=0 or math.isclose(value,1))):
            raise ValueError('Основа має бути додатною та не дорівнювати 1; перевірте межі коефіцієнтів.')


def number(value: float, precision: int = 4) -> str:
    return f'{0 if abs(value)<1e-12 else value:.{precision}g}'.replace('-', '−').replace('.', ',')


def explanation(key: str, v: dict[str,float], precision: int = 4) -> str:
    n=lambda value:number(value,precision)
    validate(key,v)
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


def details(key: str) -> str:
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
        disc=b*b-4*a*c
        if disc>=0:
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
