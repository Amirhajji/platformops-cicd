import pytest

from simulator.expr import Expression, ExprError


def evaluate(text):
    values = {"a": 6.0, "b": 4.0}
    levels = {("node", "m"): [1.0, 2.0, 6.0], ("cluster", "m"): [5.0]}
    return Expression(text).evaluate(
        values.__getitem__, lambda level, metric: levels[level, metric])


@pytest.mark.parametrize("text, expected", [
    ("a + b * 2", 14),
    ("(a + b) * 2", 20),
    ("a - b / 2", 4),
    ("a / 5e6 * 100", 6.0 / 5e6 * 100),
    ("sum('node', 'm')", 9),
    ("avg('node', 'm') + 1", 4),
    ("ref('cluster', 'm')", 5),
])
def test_allowed(text, expected):
    assert evaluate(text) == expected


def test_collects_references():
    expression = Expression("a + avg('node', 'm')")
    assert expression.names == {"a"}
    assert expression.level_refs == {("node", "m")}


@pytest.mark.parametrize("text", [
    "eval('1')",
    "exec('1')",
    "__import__('os')",
    "__import__('os').system('dir')",
    "import os",
    "open('file')",
    "a.real",
    "a.__class__",
    "().__class__",
    "a[0]",
    "max('node', 'm')",
    "count('node', 'm')",
    "sum('node')",
    "sum('node', m)",
    "sum('node', 'm', 'x')",
    "sum(level='node', metric='m')",
    "a ** 2",
    "a // 2",
    "a % 2",
    "a < 2",
    "a and b",
    "a if b else 1",
    "lambda: 1",
    "[a for a in b]",
    "'text'",
    "True",
    "f'{a}'",
    "(a := 1)",
    "a; b",
    "",
])
def test_rejected(text):
    with pytest.raises(ExprError):
        Expression(text)


def test_ref_needs_one_resource():
    with pytest.raises(ExprError):
        evaluate("ref('node', 'm')")
