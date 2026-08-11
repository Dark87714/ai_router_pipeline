import ast
import multiprocessing
import traceback
from typing import Dict, Any, List, Tuple


FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", 
    "urllib", "requests", "http", "ftplib", "pathlib", "builtins"
}

FORBIDDEN_BUILTINS = {
    "eval", "exec", "open", "__import__", "globals", 
    "locals", "compile", "getattr", "setattr", "delattr"
}

FORBIDDEN_ATTRIBUTES = {
    "__subclasses__", "__bases__", "__class__", "__mro__", "__builtins__"
}


class ASTSecurityVisitor(ast.NodeVisitor):
    """AST Inspector to detect unsafe module imports, dangerous calls, and sandbox escape vectors."""
    
    def __init__(self):
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            module_base = alias.name.split('.')[0]
            if module_base in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden module import '{alias.name}' detected.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            module_base = node.module.split('.')[0]
            if module_base in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden module import from '{node.module}' detected.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_BUILTINS:
            self.violations.append(f"Forbidden built-in function call '{node.func.id}()' detected.")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in FORBIDDEN_ATTRIBUTES:
            self.violations.append(f"Forbidden attribute access '{node.attr}' detected.")
        self.generic_visit(node)


def _sandboxed_worker(raw_code: str, params: Dict[str, Any], return_dict: Dict[str, Any]):
    """Isolated process worker executing Python code within a restricted global scope."""
    try:
        exec_scope = {}
        if params:
            exec_scope.update(params)

        exec(raw_code, exec_scope)

        defined_symbols = {
            k: str(v) for k, v in exec_scope.items()
            if not k.startswith("__") and not callable(v) and not isinstance(v, type)
        }

        return_dict["success"] = True
        return_dict["error"] = None
        return_dict["defined_symbols"] = defined_symbols

    except Exception as e:
        return_dict["success"] = False
        return_dict["error"] = f"{type(e).__name__}: {str(e)}"
        return_dict["defined_symbols"] = {}


class LogicExecutor:
    """Model 3 Engine: Validates AST syntax, security constraints, parameter signatures, and executes sandboxed logic."""

    def validate_syntax(self, raw_code: str) -> Tuple[bool, str]:
        """Parses Python code to check for AST syntax validity."""
        try:
            ast.parse(raw_code)
            return True, "SYNTAX_VALID"
        except SyntaxError as se:
            return False, f"SyntaxError at line {se.lineno}: {se.msg}"

    def validate_security(self, raw_code: str) -> Tuple[bool, List[str]]:
        """Scans code AST against security policies."""
        try:
            tree = ast.parse(raw_code)
            visitor = ASTSecurityVisitor()
            visitor.visit(tree)
            is_safe = len(visitor.violations) == 0
            return is_safe, visitor.violations
        except Exception as e:
            return False, [f"Security validation failed to parse snippet: {str(e)}"]

    def inspect_parameters(self, raw_code: str) -> List[str]:
        """Detects required undefined top-level variable names in code snippet."""
        try:
            tree = ast.parse(raw_code)
            defined_names = set()
            used_names = set()

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    defined_names.add(node.name)
                elif isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Store):
                        defined_names.add(node.id)
                    elif isinstance(node.ctx, ast.Load):
                        used_names.add(node.id)

            required_params = sorted(list(used_names - defined_names - set(dir(__builtins__))))
            return required_params
        except Exception:
            return []

    def prepare_execution_payload(
        self, 
        match_result: Dict[str, Any], 
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Constructs and validates the execution payload prior to running."""
        rule_id = match_result.get("rule_id", "unknown_rule")
        raw_code = match_result.get("raw_code", "")

        syntax_valid, syntax_status = self.validate_syntax(raw_code)
        is_safe, security_violations = self.validate_security(raw_code)
        required_params = self.inspect_parameters(raw_code)

        if not syntax_valid:
            status_msg = f"SYNTAX_INVALID: {syntax_status}"
        elif not is_safe:
            status_msg = f"SECURITY_VIOLATION: {'; '.join(security_violations)}"
        else:
            status_msg = "SYNTAX_VALID"

        return {
            "rule_id": rule_id,
            "raw_code": raw_code,
            "syntax_valid": syntax_valid and is_safe,
            "syntax_status": status_msg,
            "security_safe": is_safe,
            "security_violations": security_violations,
            "required_params": required_params,
            "provided_params": params or {}
        }

    def execute_snippet(self, payload: Dict[str, Any], timeout_seconds: float = 3.0) -> Dict[str, Any]:
        """Executes snippet inside a separate process with a strict timeout boundary."""
        if not payload.get("syntax_valid", False):
            return {
                "success": False,
                "error": f"Execution aborted: Security or Syntax violations ({payload.get('security_violations')})",
                "defined_symbols": {}
            }

        raw_code = payload["raw_code"]
        params = payload["provided_params"]

        manager = multiprocessing.Manager()
        return_dict = manager.dict()

        process = multiprocessing.Process(
            target=_sandboxed_worker,
            args=(raw_code, params, return_dict)
        )

        process.start()
        process.join(timeout=timeout_seconds)

        if process.is_alive():
            process.terminate()
            process.join()
            return {
                "success": False,
                "error": f"TimeoutError: Execution exceeded time limit of {timeout_seconds}s.",
                "defined_symbols": {}
            }

        return {
            "success": return_dict.get("success", False),
            "error": return_dict.get("error", "Unknown worker error"),
            "defined_symbols": dict(return_dict.get("defined_symbols", {}))
        }