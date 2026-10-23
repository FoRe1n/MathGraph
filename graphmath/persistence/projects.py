"""Strict, versioned JSON documents. No Qt dependency and no executable input."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path
import re
import tempfile
import os
import uuid

COLORS = ["#4868D8", "#D15C46", "#248568", "#A65AB5", "#BF871C", "#398FA4", "#CB5681", "#6E7C3F", "#825DD0", "#946B45"]


@dataclass
class Parameter:
    value: float = 1
    minimum: float = -5
    maximum: float = 5
    step: float = 0.1
    initial: float = 1


@dataclass
class Function:
    expression: str = "x^2"
    color: str = COLORS[0]
    visible: bool = True
    parameters: dict[str, Parameter] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass
class Project:
    functions: list[Function] = field(default_factory=lambda: [Function("x^2 - 4"), Function("sin(x)", COLORS[1])])
    view: list[float] = field(default_factory=lambda: [-8, 8, -5, 7])
    grid: bool = True
    axes: bool = True
    selected: str | None = None
    mode: str = "custom"

    def to_dict(self):
        return {"format": "GraphMath", "version": 1, **asdict(self)}


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e12:
        raise ValueError("Некоректне числове значення у проєкті.")
    return float(value)


def from_dict(data: dict) -> Project:
    try:
        if data.get("format") != "GraphMath" or type(data.get("version")) is not int or data["version"] != 1:
            raise ValueError("Непідтримуваний формат або версія проєкту.")
        if not isinstance(data["functions"], list) or len(data["functions"]) > 100:
            raise ValueError("Проєкт підтримує до 100 функцій.")
        functions, ids = [], set()
        for item in data["functions"]:
            source, color, visible = item["expression"], item["color"], item["visible"]
            if not isinstance(source, str) or len(source) > 600 or not re.fullmatch(r"#[0-9a-fA-F]{6}", color) or type(visible) is not bool:
                raise ValueError("Некоректний запис функції.")
            identifier = item["id"]
            if not isinstance(identifier, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", identifier) or identifier in ids:
                raise ValueError("Некоректний ідентифікатор функції.")
            ids.add(identifier)
            params = {}
            if not isinstance(item.get("parameters", {}), dict) or len(item.get("parameters", {})) > 6:
                raise ValueError("Некоректні параметри.")
            for name, p in item.get("parameters", {}).items():
                if not re.fullmatch("[a-df-wyz]", name):
                    raise ValueError("Некоректне ім’я параметра.")
                p = Parameter(**{k: _number(p[k]) for k in ("value", "minimum", "maximum", "step", "initial")})
                if not p.minimum <= p.value <= p.maximum or not p.minimum <= p.initial <= p.maximum or not 0 < p.step <= p.maximum - p.minimum:
                    raise ValueError("Перевірте діапазон параметра.")
                if (p.maximum - p.minimum) / p.step > 100000:
                    raise ValueError("Забагато кроків параметра.")
                params[name] = p
            functions.append(Function(source, color, visible, params, identifier))
        view = [_number(v) for v in data["view"]]
        if len(view) != 4 or view[0] >= view[1] or view[2] >= view[3]:
            raise ValueError("Некоректний діапазон графіка.")
        if any(type(data.get(k, True)) is not bool for k in ["grid", "axes"]):
            raise ValueError("Некоректні налаштування графіка.")
        selected = data.get("selected")
        if selected is not None and selected not in ids:
            raise ValueError("Вибрана функція відсутня у проєкті.")
        mode=data.get('mode','custom')
        if mode not in ('custom','quadratic','exponential','logarithmic'):
            raise ValueError('Невідомий режим математичного проєкту.')
        return Project(functions, view, data.get("grid", True), data.get("axes", True), selected, mode)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Пошкоджений файл математичного проєкту.") from exc


def save(project: Project, path: str | Path):
    """Atomic replacement: a failed write leaves the previous project intact."""
    path = Path(path)
    payload = json.dumps(from_dict(project.to_dict()).to_dict(), ensure_ascii=False, indent=2, allow_nan=False)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as stream:
            temporary = stream.name
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def load(path: str | Path) -> Project:
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError("Файл проєкту завеликий (максимум 2 МБ).")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Файл має містити дані математичного проєкту.")
        return from_dict(data)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise ValueError("Не вдалося прочитати JSON проєкту.") from exc
