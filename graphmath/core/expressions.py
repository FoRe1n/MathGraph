"""Restricted mathematical AST -> SymPy. Never evaluate user source as Python."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
import re
import io
import tokenize
import math
from decimal import Decimal

import numpy as np
import sympy as sp

X = sp.Symbol("x", real=True)
MAX_LENGTH = 600
MAX_NODES = 100
MAX_DEPTH = 18


MAX_CONSTANT_BITS = 4096


def _check_constant_resources(node):
    """Bound existing numeric grammar before SymPy can expand exact constants.

    A short nested power can otherwise request trillions of integer digits.
    Float estimates bound magnitude; an independent bit-cost bound also catches
    huge exact fractions close to one. Variable expressions stay symbolic.
    """
    message = 'Стала частина виразу надто велика або складна. Спростіть числа та степені.'
    def visit(item):
        if isinstance(item, ast.Constant) and type(item.value) in (int,float):
            try:
                value=float(item.value)
                numerator,denominator=Decimal(str(item.value)).as_integer_ratio()
            except (ValueError,OverflowError):
                raise ExpressionError(message) from None
            return value, max(abs(numerator).bit_length(),denominator.bit_length()), True
        if isinstance(item,ast.Name):
            return ({'pi':math.pi,'e':math.e}.get(item.id),64,item.id in ('pi','e'))
        if isinstance(item,ast.Call):
            children=[visit(child) for child in item.args]
        else:
            children=[visit(child) for child in ast.iter_child_nodes(item) if not isinstance(child,(ast.operator,ast.unaryop,ast.expr_context))]
        if not children or not all(child[2] for child in children):return None,0,False
        values=[child[0] for child in children];cost=sum(child[1] for child in children)+1
        value=None
        try:
            if isinstance(item,ast.UnaryOp):
                value=values[0] if isinstance(item.op,ast.UAdd) else -values[0]
            elif isinstance(item,ast.BinOp):
                left,right=values
                if isinstance(item.op,ast.Pow):
                    if right is not None:cost=max(1,children[0][1])*max(1,math.ceil(abs(right)))+children[1][1]
                    if cost>MAX_CONSTANT_BITS:raise ExpressionError(message)
                    value=math.pow(left,right)
                    if value==0 and left!=0:raise ExpressionError(message)
                elif isinstance(item.op,ast.Add):value=left+right
                elif isinstance(item.op,ast.Sub):value=left-right
                elif isinstance(item.op,ast.Mult):
                    value=left*right
                    if value==0 and left!=0 and right!=0:raise ExpressionError(message)
                elif isinstance(item.op,ast.Div):
                    value=left/right
                    if value==0 and left!=0:raise ExpressionError(message)
            elif isinstance(item,ast.Call) and isinstance(item.func,ast.Name):
                name=item.func.id
                arities={'sqrt':(1,),'root':(2,),'log':(1,2),'ln':(1,),'sin':(1,),'cos':(1,),'tan':(1,),'abs':(1,),'exp':(1,)}
                if name not in arities or len(values) not in arities[name]:return None,cost,False
                if name in ('log','ln'):
                    value=math.log(values[0]) if len(values)==1 else math.log(values[0])/math.log(values[1])
                elif name=='root':
                    value=math.copysign(abs(values[0])**(1/values[1]),values[0]) if int(values[1])%2 else math.pow(values[0],1/values[1])
                elif name in ('sin','cos','tan','sqrt','exp','abs'):
                    value=abs(values[0]) if name=='abs' else getattr(math,name)(values[0])
                else:return None,cost,False
        except ExpressionError:
            raise
        except (ValueError,ZeroDivisionError,TypeError):
            # Ordinary domain validation supplies the useful mathematical error.
            value=None
        except OverflowError:
            raise ExpressionError(message) from None
        if cost>MAX_CONSTANT_BITS or value is not None and not math.isfinite(value):raise ExpressionError(message)
        return value,cost,True
    visit(node)


class ExpressionError(ValueError):
    """A safe, user-readable input error."""


@dataclass(frozen=True)
class Expression:
    source: str
    symbolic: sp.Expr
    parameters: tuple[str, ...]
    denominators: tuple[sp.Expr, ...]
    nonnegative: tuple[sp.Expr, ...]
    positive: tuple[sp.Expr, ...]
    relation: bool = False

    @property
    def latex(self) -> str:
        return ("x=" if self.relation else "") + sp.latex(self.symbolic)

    def substitute(self, values: dict[str, float]) -> sp.Expr:
        return self.symbolic.subs({sp.Symbol(k, real=True): v for k, v in values.items()})


class _Parser:
    def __init__(self):
        self.denominators: list[sp.Expr] = []
        self.nonnegative: list[sp.Expr] = []
        self.positive: list[sp.Expr] = []
        self.parameters: set[str] = set()

    def denominator(self, expression: sp.Expr):
        """Retain zero factors, including even poles too small for jump heuristics."""
        if expression not in self.denominators:
            self.denominators.append(expression)
        if isinstance(expression, sp.Mul):
            for factor in expression.args:
                self.denominator(factor)
        elif isinstance(expression, sp.Pow) and expression.exp.is_number and expression.exp != 0:
            self.denominator(expression.base)
        elif isinstance(expression, sp.Abs):
            self.denominator(expression.args[0])
        elif expression.is_polynomial(X):
            # Expanded numeric squares have even poles too: a sign test on the
            # quadratic alone cannot see them. Add its linear root factor once,
            # during cached parsing, without solving or factoring per frame.
            polynomial = sp.Poly(expression, X)
            if polynomial.degree() == 2:
                a, b, c = polynomial.all_coeffs()
                if all(coefficient.is_Rational for coefficient in (a, b, c)) and b*b-4*a*c == 0:
                    self.denominator(2*a*X+b)

    def visit(self, node: ast.AST, depth: int = 0) -> sp.Expr:
        if depth > MAX_DEPTH:
            raise ExpressionError("Вираз надто вкладений. Спростіть його.")
        child = lambda n: self.visit(n, depth + 1)
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float) or not np.isfinite(node.value) or abs(node.value) > 1e12:
                raise ExpressionError("Число має бути скінченним і не більшим за 10¹².")
            return sp.Integer(node.value) if type(node.value) is int else sp.Rational(str(node.value))
        if isinstance(node, ast.Name):
            if node.id in {"x", "pi", "e"}:
                return {"x": X, "pi": sp.pi, "e": sp.E}[node.id]
            if re.fullmatch("[a-df-wyz]", node.id):
                self.parameters.add(node.id)
                return sp.Symbol(node.id, real=True)
            raise ExpressionError("Дозволено x, pi, e та однолітерні параметри a–z.")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = child(node.operand)
            return value if isinstance(node.op, ast.UAdd) else sp.Mul(-1, value, evaluate=False)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            left, right = child(node.left), child(node.right)
            if isinstance(node.op, ast.Add):
                return sp.Add(left, right, evaluate=False)
            if isinstance(node.op, ast.Sub):
                return sp.Add(left, sp.Mul(-1, right, evaluate=False), evaluate=False)
            if isinstance(node.op, ast.Mult):
                return sp.Mul(left, right, evaluate=False)
            if isinstance(node.op, ast.Div):
                # Constant arithmetic must be reduced before checking its domain.
                # Keep variable expressions unevaluated to retain removable holes.
                if not right.free_symbols:
                    right = right.doit()
                if right.is_zero is True:
                    raise ExpressionError("Ділення на нуль не визначено.")
                self.denominator(right)
                return sp.Mul(left, sp.Pow(right, -1, evaluate=False), evaluate=False)
            # Numeric exponents only: bounded complexity and predictable real domains.
            if right.free_symbols or sp.count_ops(right) > 3:
                if right != X:
                    raise ExpressionError("Степінь: число від −100 до 100 або x (наприклад 2^x).")
            else:
                right = right.doit()
                if right.is_real is not True or right.is_finite is not True:
                    raise ExpressionError("Показник степеня має бути скінченним дійсним числом.")
                if abs(float(right)) > 100:
                    raise ExpressionError("Показник степеня має бути від −100 до 100.")
            if right.is_negative:
                if not left.free_symbols and left.doit().is_zero is True:
                    raise ExpressionError("Ділення на нуль не визначено.")
                self.denominator(left)
            if right.is_Rational and right.q % 2 == 1 and right.q != 1:
                # School real powers with an odd denominator use the real root,
                # rather than the complex principal branch of Python/SymPy Pow.
                return sp.sign(left)**right.p * sp.Abs(left)**right
            if right.is_integer is not True and right != X:
                self.nonnegative.append(left)
            return sp.Pow(left, right, evaluate=False)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            name = node.func.id
            arities = {"sqrt": (1,), "root": (2,), "log": (1, 2), "ln": (1,),
                       "sin": (1,), "cos": (1,), "tan": (1,), "abs": (1,), "exp": (1,)}
            if name not in arities or len(node.args) not in arities[name]:
                raise ExpressionError("Невідома функція або неправильна кількість аргументів.")
            args = [child(n) for n in node.args]
            a = args[0]
            if name == "sqrt":
                self.nonnegative.append(a)
                return sp.Pow(a, sp.Rational(1, 2), evaluate=False)
            if name == "root":
                n = args[1].doit()
                if not n.is_Integer or not 2 <= n <= 15:
                    raise ExpressionError("Порядок кореня: ціле число від 2 до 15.")
                if n % 2 == 0:
                    self.nonnegative.append(a)
                    return sp.Pow(a, 1 / n, evaluate=False)
                return sp.sign(a) * sp.Abs(a) ** (1 / n)
            if name in {"log", "ln"}:
                self.positive.append(a)
                if len(args) == 2:
                    b = args[1].doit()
                    if b.free_symbols or b.is_real is not True or b.is_finite is not True or not (b > 0) or b == 1:
                        raise ExpressionError("Основа логарифма: додатне число, відмінне від 1.")
                    return sp.Mul(sp.log(a, evaluate=False), 1 / sp.log(b), evaluate=False)
                return sp.log(a, evaluate=False)
            if name == "tan":
                self.denominator(sp.cos(a))
            fn = {"sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "abs": sp.Abs, "exp": sp.exp}[name]
            return fn(a, evaluate=False)
        raise ExpressionError("Використовуйте лише числа, x, математичні операції та дозволені функції.")


def normalize(source: str) -> str:
    """Unambiguous school notation; unknown names remain intact for rejection."""
    text=source.strip().replace('−','-').replace('×','*').replace('·','*').replace('÷','/').replace('π','pi')
    superscripts=str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻','0123456789-')
    text=re.sub(r'[⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+',lambda m:'**('+m.group().translate(superscripts)+')',text)
    text=text.replace('^','**')
    if re.match(r'^y\s*=',text):text=text.split('=',1)[1].strip()
    try:
        tokens=[t for t in tokenize.generate_tokens(io.StringIO(text).readline)
                if t.type not in (tokenize.ENDMARKER,tokenize.NEWLINE,tokenize.NL)]
        output=[]
        for i,token in enumerate(tokens):
            if i:
                previous=tokens[i-1]
                implicit=(previous.type==tokenize.NUMBER and (token.type==tokenize.NAME or token.string=='(')
                          or previous.string==')' and (token.type in (tokenize.NAME,tokenize.NUMBER) or token.string=='(')
                          or previous.type==tokenize.NAME and len(previous.string)==1 and token.string=='(')
                if implicit:output.append('*')
            output.append(token.string)
        return ' '.join(output)
    except UnicodeError:
        raise ExpressionError('Вираз містить неприпустимі символи. Введіть формулу заново.') from None
    except (tokenize.TokenError,IndentationError):
        raise ExpressionError('Перевірте дужки та знаки операцій.') from None


@lru_cache(maxsize=256)
def parse(source: str) -> Expression:
    """Parse explicit multiplication, ^ or ** powers, and an optional y= prefix."""
    if not isinstance(source, str) or not source.strip():
        raise ExpressionError("Введіть функцію, наприклад x^2 − 4.")
    if len(source) > MAX_LENGTH:
        raise ExpressionError("Вираз задовгий (максимум 600 символів).")
    relation = bool(re.match(r"^x\s*=",source.strip()))
    normalized = normalize(source.strip().split("=",1)[1] if relation else source)
    try:
        tree = ast.parse(normalized, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
            raise ExpressionError("Забагато операцій. Спростіть вираз.")
        _check_constant_resources(tree.body)
        parser = _Parser()
        symbolic = parser.visit(tree.body)
        if len(parser.parameters) > 6:
            raise ExpressionError("Максимум шість параметрів у функції.")
        if relation and X in symbolic.free_symbols:
            raise ExpressionError("Для вертикальної прямої введіть x = число або параметр, без x праворуч.")
        return Expression(source, symbolic, tuple(sorted(parser.parameters)), tuple(parser.denominators),
                          tuple(parser.nonnegative), tuple(parser.positive), relation)
    except ExpressionError:
        raise
    except (SyntaxError, ValueError, TypeError, OverflowError, RecursionError, ZeroDivisionError):
        raise ExpressionError("Перевірте дужки, числа та знаки операцій. Множення записуйте як *.") from None


@lru_cache(maxsize=256)
def _compiled(source: str):
    expression = parse(source)
    symbols = [X] + [sp.Symbol(n, real=True) for n in expression.parameters]
    # The expression has already been constructed solely through the allowlisted AST.
    fn = sp.lambdify(symbols, expression.symbolic, modules="numpy", cse=False)
    guards=[]
    phases=[]
    for base_kind,items in [("denominator",expression.denominators),("nonnegative",expression.nonnegative),("positive",expression.positive)]:
        for item in items:
            kind=base_kind
            phase=None
            if kind=="denominator" and item.func in (sp.cos,sp.sin,sp.tan):
                kind="cos_pole" if item.func==sp.cos else "sin_pole"
                phase=sp.lambdify(symbols,item.args[0],modules="numpy")
                phases.append((phase,0. if kind=="cos_pole" else np.pi/2))
            guards.append((kind,sp.lambdify(symbols,item,modules="numpy"),phase))
    return expression,fn,guards,phases


def _real_phase(value):
    value=np.asarray(value)
    if np.iscomplexobj(value):
        value=np.where(np.abs(value.imag)<1e-12,value.real,np.nan)
    return np.asarray(value,dtype=float)


def _at_trigonometric_zero(phase, cosine):
    phase=_real_phase(phase)
    offset=np.pi/2 if cosine else 0.
    nearest=offset+np.rint((phase-offset)/np.pi)*np.pi
    tolerance=2*np.maximum(np.abs(np.spacing(phase)),np.abs(np.spacing(nearest)))
    # A phase too coarse to resolve a fraction of a period cannot establish a
    # zero. In particular, do not erase valid tiny-angle sine/tangent values.
    return np.isfinite(phase)&(tolerance<np.pi/16)&(np.abs(phase-nearest)<=tolerance)


def _evaluate_compiled(expression, fn, guards, x, parameters):
    """Shared real-domain evaluation for y functions and vertical coordinates."""
    xx = np.asarray(x, dtype=float)
    values = parameters or {}
    # NumPy scalars preserve NaN/Inf semantics for parameter-only divisions;
    # Python float division by zero would escape before domain guards can run.
    args = [xx] + [np.float64(values.get(n, 1.0)) for n in expression.parameters]
    with np.errstate(all="ignore"):
        result = np.asarray(fn(*args))
        if np.iscomplexobj(result):
            result = np.where(np.abs(result.imag) < 1e-12, result.real, np.nan)
        result = np.array(np.broadcast_to(result, xx.shape), dtype=float, copy=True)
        valid = np.isfinite(result)
        for kind, guard, phase in guards:
            v = np.asarray(guard(*args))
            if np.iscomplexobj(v):
                valid &= np.abs(v.imag) < 1e-12
                v = v.real
            valid &= np.isfinite(v)
            if phase is not None:
                valid &= ~_at_trigonometric_zero(phase(*args),kind=="cos_pole")
            else:
                valid &= (v != 0) if kind == "denominator" else ((v >= 0) if kind == "nonnegative" else (v > 0))
        return np.where(valid, result, np.nan)


def evaluate(source: str, x, parameters: dict[str, float] | None = None) -> np.ndarray:
    """Evaluate real values; undefined points are NaN, including removable holes."""
    expression, fn, guards, _ = _compiled(source)
    if expression.relation:
        raise ExpressionError("Вертикальна пряма — це відношення x = c, а не функція y = f(x).")
    return _evaluate_compiled(expression, fn, guards, x, parameters)


def denominator_values(source: str, x, parameters: dict[str, float] | None = None):
    expression, _, guards, _ = _compiled(source)
    xx = np.asarray(x, dtype=float)
    args = [xx] + [np.float64((parameters or {}).get(n, 1)) for n in expression.parameters]
    with np.errstate(all="ignore"):
        return [np.broadcast_to(_real_phase(fn(*args)), xx.shape)
                for kind, fn, _ in guards if kind in ("denominator", "cos_pole", "sin_pole")]


def tangent_arguments(source: str, x, parameters: dict[str, float] | None = None):
    """Cached phases of cosine poles, for separating distinct tangent branches.

    Endpoint cosine signs alone miss an even number of poles in a sample segment.
    Phase-bin comparisons let the sampler recognize these undersampled crossings
    without solving equations or rebuilding symbolic expressions during a drag.
    """
    expression, _, _, phases = _compiled(source)
    xx = np.asarray(x, dtype=float)
    args = [xx] + [np.float64((parameters or {}).get(n, 1)) for n in expression.parameters]
    with np.errstate(all="ignore"):
        return [np.broadcast_to(_real_phase(fn(*args))-offset, xx.shape) for fn,offset in phases]


def relation_x(source: str, parameters: dict[str,float] | None = None) -> float | None:
    """Return the x coordinate of a vertical relation, never a y value."""
    expression, fn, guards, _ = _compiled(source)
    if not expression.relation:return None
    value=float(_evaluate_compiled(expression, fn, guards, 0., parameters))
    return value if np.isfinite(value) else None
