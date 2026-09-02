import ast
import math
import operator
import re
from typing import Any, Dict, List, Optional, Union

# Safe binary and unary operators
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Safe mathematical functions
_SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": math.pow,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "ceil": math.ceil,
    "floor": math.floor,
}

# Safe constants
_SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _clean_expression(expr: str) -> str:
    """
    Cleans financial formatting from math expressions (removes $, commas in numbers, etc.).
    Example: '$143,733 - $5,975 * 3' -> '143733 - 5975 * 3'
    """
    if not isinstance(expr, str):
        return str(expr)
    
    cleaned = expr.strip()
    # Strip currency signs
    cleaned = cleaned.replace("$", "").replace("€", "").replace("£", "")
    
    # Remove commas between digits (e.g. 143,733 -> 143733)
    cleaned = re.sub(r'(?<=\d),(?=\d)', '', cleaned)
    
    return cleaned


def _eval_ast_node(node: ast.AST) -> Any:
    """Recursively and safely evaluates an AST node."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")

    elif isinstance(node, ast.Name):
        if node.id in _SAFE_CONSTANTS:
            return _SAFE_CONSTANTS[node.id]
        raise ValueError(f"Undefined variable: {node.id}")

    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
        left = _eval_ast_node(node.left)
        right = _eval_ast_node(node.right)
        
        # Guard against massive exponentiation memory attacks
        if op_type is ast.Pow:
            if abs(right) > 1000:
                raise ValueError("Exponent too large (max 1000)")
            if abs(left) > 1e10 and right > 10:
                raise ValueError("Result too large")
                
        return _SAFE_OPERATORS[op_type](left, right)

    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _eval_ast_node(node.operand)
        return _SAFE_OPERATORS[op_type](operand)

    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only named function calls are allowed")
        func_name = node.func.id
        if func_name not in _SAFE_FUNCTIONS:
            raise ValueError(f"Unsupported function call: {func_name}")
        
        args = [_eval_ast_node(arg) for arg in node.args]
        return _SAFE_FUNCTIONS[func_name](*args)

    elif isinstance(node, ast.List):
        return [_eval_ast_node(elem) for elem in node.elts]

    elif isinstance(node, ast.Tuple):
        return tuple(_eval_ast_node(elem) for elem in node.elts)

    elif isinstance(node, ast.Expression):
        return _eval_ast_node(node.body)

    raise ValueError(f"Unsupported AST syntax: {type(node).__name__}")


def evaluate_expression(expression: str) -> Dict[str, Any]:
    """
    Safely parses and evaluates an arithmetic or financial math expression.
    """
    try:
        cleaned_expr = _clean_expression(expression)
        parsed_ast = ast.parse(cleaned_expr, mode="eval")
        result = _eval_ast_node(parsed_ast.body)
        
        # Round floating point noise
        if isinstance(result, float):
            result = round(result, 6)
            if result.is_integer():
                result = int(result)

        formatted = f"{result:,.2f}" if isinstance(result, (int, float)) else str(result)
        return {
            "success": True,
            "expression": expression,
            "cleaned_expression": cleaned_expr,
            "result": result,
            "formatted": formatted,
        }
    except Exception as e:
        return {
            "success": False,
            "expression": expression,
            "error": str(e),
        }


class CalculatorTool:
    """
    Deterministic Calculator Tool compatible with Anthropic Claude Tool Calling format.
    """
    name: str = "calculate"
    description: str = (
        "Deterministic arithmetic and financial calculation engine. Use this tool for ALL "
        "mathematical calculations, financial ratios, breakeven thresholds, compounding, "
        "cost additions, unit economics, and percentages instead of relying on mental arithmetic. "
        "Supports standard arithmetic (+, -, *, /, %, **), parentheses, and math functions (round, abs, min, max, sqrt, log)."
    )

    def to_param(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "The mathematical or financial expression to evaluate. "
                            "Examples: '143733 - 5975 * 3', '5975 / 0.666', '(50000 - 32000) / 50000 * 100', "
                            "'round(86400 / 12000, 1)', '20.52 * 1.30 * 40 * 4.33'."
                        )
                    }
                },
                "required": ["expression"]
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.to_param()

    def execute(self, expression: str, **kwargs) -> Dict[str, Any]:
        return evaluate_expression(expression)

    def run(self, expression: str, **kwargs) -> Dict[str, Any]:
        return evaluate_expression(expression)

    def __call__(self, expression: str, **kwargs) -> Dict[str, Any]:
        return evaluate_expression(expression)


# Singleton tool instance
calculator_tool = CalculatorTool()
