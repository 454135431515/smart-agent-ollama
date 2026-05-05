import ast

from pydantic import BaseModel, Field

from app.registry import tool

_MAX_EXPR_LEN = 200
_MAX_POW_EXP = 100

_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow)
_ALLOWED_UNARYOPS = (ast.USub, ast.UAdd)


def _safe_eval(expr: str) -> float:
    if len(expr) > _MAX_EXPR_LEN:
        raise ValueError(f"Expression too long (max {_MAX_EXPR_LEN} chars).")

    tree = ast.parse(expr, mode="eval")

    def _visit(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _visit(node.body)
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise ValueError(f"Unsupported operation: constant {node.value!r}")
            return float(node.value)
        if isinstance(node, ast.BinOp):
            if not isinstance(node.op, _ALLOWED_BINOPS):
                raise ValueError(f"Unsupported operation: {type(node.op).__name__}")
            left = _visit(node.left)
            right = _visit(node.right)
            if isinstance(node.op, ast.Pow) and right > _MAX_POW_EXP:
                raise ValueError(f"Exponent too large (max {_MAX_POW_EXP}).")
            ops = {
                ast.Add: lambda a, b: a + b,
                ast.Sub: lambda a, b: a - b,
                ast.Mult: lambda a, b: a * b,
                ast.Div: lambda a, b: a / b,
                ast.Mod: lambda a, b: a % b,
                ast.Pow: lambda a, b: a**b,
            }
            return ops[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, _ALLOWED_UNARYOPS):
                raise ValueError(f"Unsupported operation: {type(node.op).__name__}")
            operand = _visit(node.operand)
            return -operand if isinstance(node.op, ast.USub) else operand
        raise ValueError(f"Unsupported operation: {type(node).__name__}")

    return _visit(tree)


class CalculatorArgs(BaseModel):
    expression: str = Field(description="Math expression to evaluate, e.g. '2+2' or '100 * 92.5'")


@tool(
    name="calculator",
    description="Mathematical calculator. Provide a valid math expression.",
    args_model=CalculatorArgs,
)
def calculator(expression: str) -> str:
    try:
        expression = expression.replace(",", ".")
        result = _safe_eval(expression)
        return str(result)
    except (ValueError, ZeroDivisionError) as error:
        return f"Calculation error: {error}"
    except SyntaxError:
        return "Calculation error: invalid expression syntax."
