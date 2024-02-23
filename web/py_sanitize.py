import ast
from typing import Any, List

class SecurityError(Exception): pass

class PySanitizer(ast.NodeVisitor):
    def __init__(self,
                 allowed_functions: List[str],
                 allowed_names: List[str]) -> None:
        self.allowed_functions = allowed_functions
        self.allowed_names = allowed_names
        super().__init__()

    def visit_Constant(self, node: ast.Constant) -> Any:
        if type(node.value) not in (int, float, bool, str):
            raise SecurityError('Invalid Constant')

    # For compat with Python 3.7 :(
    def visit_Num(self, node: ast.Num) -> Any:
        if type(node.n) not in (int, float):
            raise SecurityError('Invalid Num')
    def visit_Str(self, node: ast.Str) -> Any:
        if type(node.s) != str:
            raise SecurityError('Invalid Str')
    def visit_NameConstant(self, node: ast.NameConstant) -> Any:
        if node.value not in (True, False):
            raise SecurityError('Invalid NameConstant')

    def visit_Call(self, node: ast.Call) -> Any:
        if (isinstance(node.func, ast.Name) and
            len(node.keywords) == 0 and
            node.func.id in self.allowed_functions):
            for x in node.args:
                self.visit(x)
        else:
            raise SecurityError(f'Illegal function invocation in {repr(ast.unparse(node))}')

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id not in self.allowed_names:
            raise SecurityError(f'Name {repr(node.id)} not allowed')

    def generic_visit(self, node: ast.AST) -> Any:
        allowed_types = (ast.boolop, ast.operator, ast.unaryop, ast.cmpop,
                         ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare,
                         ast.IfExp,
                         ast.Expression,
                         ast.List, ast.Set, ast.Tuple,
                         ast.expr_context)
        if isinstance(node, allowed_types):
            super().generic_visit(node)
        else:
            raise SecurityError(f'{repr(type(node).__name__)} not allowed')

    def safe_compile(self, code: str):
        expr = ast.parse(code, mode='eval')
        self.visit(expr)
        if not isinstance(expr, ast.Expression):
            raise SecurityError
        return compile(expr, filename='<input>', mode='eval')

    def safe_eval(self, code, locals):
        if type(code) == str:
            code = self.safe_compile(code)
        return eval(code, { '__builtins__': {} }, locals)
