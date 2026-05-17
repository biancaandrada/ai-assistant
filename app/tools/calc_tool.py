import ast
import operator as op

from .base import Tool

# Safe AST-based evaluator — no eval()
_BIN = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.Mod: op.mod, ast.Pow: op.pow,
    ast.FloorDiv: op.floordiv,
}
_UN = {ast.UAdd: op.pos, ast.USub: op.neg}


def _safe_eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        return _BIN[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UN:
        return _UN[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


class CalcTool(Tool):
    name = "calc"
    description = "Evaluate an arithmetic expression. Input: e.g. '7*(3+1)'."

    async def run(self, action_input: str) -> str:
        try:
            tree = ast.parse(action_input, mode="eval")
            return str(_safe_eval(tree))
        except Exception as e:
            return f"calc error: {e}"
