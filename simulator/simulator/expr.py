"""Safe evaluator for the expressions of derived metrics.

Allowed: numbers, + - * /, parentheses, metric ids of the same resource, and
avg('level', 'metric'), sum('level', 'metric'), ref('level', 'metric').
Everything else is rejected when the expression is parsed.
"""
from __future__ import annotations

import ast
import math
import operator
from typing import Callable

# get(metric) -> value of the metric on the current resource
GetValue = Callable[[str], float]
# get_level(level, metric) -> values of the metric on every resource of the level
GetLevel = Callable[[str, str], list[float]]
Evaluator = Callable[[GetValue, GetLevel], float]


class ExprError(ValueError):
    """The expression uses something that is not allowed."""


def _avg(values: list[float]) -> float:
    return math.fsum(values) / len(values)


def _ref(values: list[float]) -> float:
    if len(values) != 1:
        raise ExprError("ref() needs a level with exactly one resource")
    return values[0]


_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
# fsum, because the result of the built-in sum() depends on the Python version.
_FUNCTIONS = {"avg": _avg, "sum": math.fsum, "ref": _ref}


class Expression:
    def __init__(self, text: str) -> None:
        self.text = text
        self.names: set[str] = set()  # metrics of the same resource
        self.level_refs: set[tuple[str, str]] = set()  # (level, metric)
        try:
            tree = ast.parse(text, mode="eval")
        except SyntaxError as error:
            raise ExprError(f"invalid expression {text!r}") from error
        self.evaluate: Evaluator = self._compile(tree.body)

    def _compile(self, node: ast.AST) -> Evaluator:
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
            return lambda get, get_level: value
        if isinstance(node, ast.Name):
            name = node.id
            self.names.add(name)
            return lambda get, get_level: get(name)
        if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
            apply = _OPERATORS[type(node.op)]
            left, right = self._compile(node.left), self._compile(node.right)
            return lambda get, get_level: apply(
                left(get, get_level), right(get, get_level))
        if isinstance(node, ast.Call):
            return self._compile_call(node)
        raise ExprError(f"{type(node).__name__} is not allowed in {self.text!r}")

    def _compile_call(self, node: ast.Call) -> Evaluator:
        if not (isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS):
            raise ExprError(f"only avg, sum and ref can be called in {self.text!r}")
        arguments = [arg.value for arg in node.args
                     if isinstance(arg, ast.Constant) and isinstance(arg.value, str)]
        if len(node.args) != 2 or len(arguments) != 2 or node.keywords:
            raise ExprError(f"{node.func.id} needs (level, metric) in {self.text!r}")
        function = _FUNCTIONS[node.func.id]
        level, metric = arguments
        self.level_refs.add((level, metric))
        return lambda get, get_level: function(get_level(level, metric))
