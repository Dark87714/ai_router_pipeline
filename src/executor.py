import ast
import sys
import inspect
from io import StringIO
from typing import Any, Dict, List

class LogicExecutor:
    """
    Model 3 (The Executor / Reconstructor): Takes matched AST logic rules 
    and metadata from Model 2, verifies code syntax integrity, inspects 
    function signatures, injects parameters, and runs execution inside 
    a sandboxed namespace.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def validate_syntax(self, code_str: str) -> tuple[bool, str]:
        """
        Verifies that raw or reconstructed code parses into a valid Python AST.
        """
        try:
            ast.parse(code_str)
            return True, "SYNTAX_VALID"
        except SyntaxError as err:
            return False, f"SYNTAX_ERROR: {err}"

    def inspect_parameters(self, code_str: str) -> List[str]:
        """
        Parses AST to find parameter names for the top-level function or method.
        """
        try:
            tree = ast.parse(code_str)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    return [arg.arg for arg in node.args.args if arg.arg != 'self']
        except Exception:
            pass
        return []

    def prepare_execution_payload(self, match_result: Dict[str, Any], params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extracts raw code and AST metadata from a Router match, verifies syntax,
        inspects function parameter requirements, and prepares an execution payload.
        """
        raw_code = match_result.get("raw_code", "")
        rule_id = match_result.get("rule_id", "unknown_rule")
        metrics = match_result.get("metrics", {})

        is_valid, syntax_status = self.validate_syntax(raw_code)
        required_params = self.inspect_parameters(raw_code) if is_valid else []

        return {
            "rule_id": rule_id,
            "raw_code": raw_code,
            "ast_metrics": metrics,
            "syntax_valid": is_valid,
            "syntax_status": syntax_status,
            "required_params": required_params,
            "bound_params": params or {}
        }

    def execute_snippet(self, payload: Dict[str, Any], global_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes the matched code snippet inside an isolated context 
        and captures STDOUT, return values, or execution errors.
        """
        if not payload.get("syntax_valid", False):
            return {
                "success": False,
                "error": f"Cannot execute invalid AST: {payload.get('syntax_status')}",
                "output": ""
            }

        code_to_exec = payload["raw_code"]
        bound_params = payload.get("bound_params", {})

        exec_globals = global_context if global_context is not None else {}
        exec_globals.update(bound_params)
        exec_locals = {}

        buffer = StringIO()
        old_stdout = sys.stdout
        sys.stdout = buffer

        try:
            exec(code_to_exec, exec_globals, exec_locals)
            sys.stdout = old_stdout
            captured_output = buffer.getvalue()

            return {
                "success": True,
                "error": None,
                "output": captured_output.strip(),
                "defined_symbols": list(exec_locals.keys())
            }
        except Exception as e:
            sys.stdout = old_stdout
            return {
                "success": False,
                "error": f"RUNTIME_ERROR: {type(e).__name__} - {str(e)}",
                "output": buffer.getvalue().strip()
            }


if __name__ == "__main__":
    executor = LogicExecutor()
    sample_code = """
def calculate_square(number):
    result = number * number
    print(f"Square of {number} is {result}")
    return result
"""
    payload = executor.prepare_execution_payload(
        match_result={"rule_id": "math_rule", "raw_code": sample_code, "metrics": {}},
        params={"number": 5}
    )
    print("Payload Required Params:", payload["required_params"])
    result = executor.execute_snippet(payload)
    print("Execution Output:", result)