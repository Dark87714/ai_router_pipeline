import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from app import app
from src.ast_parser import parse_code_to_logic

client = TestClient(app)

def test_health_check():
    """Verify endpoint availability and database status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_compress_invalid_path():
    """Verify error handling when passed a non-existent directory."""
    response = client.post(
        "/compress", 
        json={"repo_path": "./non_existent_folder_xyz", "clear_existing": False}
    )
    assert response.status_code == 400


def test_compress_codebase():
    """Model 1: Verify directory crawling and AST indexing."""
    response = client.post("/compress", json={"repo_path": ".", "clear_existing": True})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["metrics"]["scanned_files"] > 0


def test_route_text_and_code_modes():
    """Model 2: Tests text intent search and code snippet query search."""
    client.post("/compress", json={"repo_path": ".", "clear_existing": True})
    
    # Text mode query
    res_text = client.post(
        "/route", 
        json={"query": "parse python source code", "top_k": 1, "mode": "text"}
    )
    assert res_text.status_code == 200
    assert res_text.json()["status"] == "MATCHES_FOUND"

    # Code mode query (using exact indexed snippet to pass strict 0.20 threshold)
    exact_code_snippet = """def calculate_ast_depth(node) -> int:
    if not isinstance(node, ast.AST):
        return 0
    children = [calculate_ast_depth(child) for child in ast.iter_child_nodes(node)]
    return 1 + max(children, default=0)"""
    
    res_code = client.post(
        "/route", 
        json={"query": exact_code_snippet, "top_k": 1, "mode": "code"}
    )
    assert res_code.status_code == 200
    assert res_code.json()["status"] == "MATCHES_FOUND"


def test_route_code_syntax_error():
    """Model 2: Tests routing code queries containing syntax errors."""
    res = client.post(
        "/route", 
        json={"query": "def broken_syntax(:", "top_k": 1, "mode": "code"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "SYNTAX_ERROR"


def test_execute_logic_paths():
    """Model 3: Tests successful execution, runtime exceptions, and syntax rejections."""
    # 1. Successful execution
    valid_payload = {
        "match_payload": {
            "rule_id": "test_rule",
            "raw_code": "def sample_func(val):\n    print(f'Val: {val}')\nsample_func(target_val)",
            "metrics": {}
        },
        "params": {"target_val": 42}
    }
    res_valid = client.post("/execute", json=valid_payload)
    assert res_valid.status_code == 200
    assert res_valid.json()["execution_result"]["success"] is True

    # 2. Runtime exception capture
    error_payload = {
        "match_payload": {
            "rule_id": "err_rule",
            "raw_code": "x = 1 / 0",
            "metrics": {}
        }
    }
    res_err = client.post("/execute", json=error_payload)
    assert res_err.status_code == 200
    assert res_err.json()["execution_result"]["success"] is False
    assert "ZeroDivisionError" in res_err.json()["execution_result"]["error"]

    # 3. Invalid syntax payload rejection
    invalid_syntax_payload = {
        "match_payload": {
            "rule_id": "bad_syntax",
            "raw_code": "def bad_syntax(:",
            "metrics": {}
        }
    }
    res_invalid = client.post("/execute", json=invalid_syntax_payload)
    assert res_invalid.status_code == 422


def test_ast_parser_uncovered_node_visitors():
    """Directly triggers classes, async functions, imports, and comprehensions in AST parser."""
    code_sample = """
import os
from math import sqrt

class ParserTestClass:
    \"\"\"Sample class docstring.\"\"\"
    async def async_handler(self, data):
        try:
            dict_comp = {k: v for k, v in [("key", "val")]}
            set_comp = {x for x in [1, 2]}
            remainder = 10 % 3
            return data
        except Exception as err:
            raise err
"""
    ast_dump, desc, metrics = parse_code_to_logic(code_sample)
    assert "class definition" in desc
    assert "async asynchronous function" in desc
    assert "dictionary comprehension" in desc
    assert "modulo remainder" in desc


def test_compressor_skips_syntax_error_files():
    """Model 1: Verifies parser graceful handling of unparseable python files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        bad_file = os.path.join(temp_dir, "invalid.py")
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("def unparseable_code(:")

        response = client.post("/compress", json={"repo_path": temp_dir, "clear_existing": False})
        assert response.status_code == 200
        assert response.json()["metrics"]["scanned_files"] == 1
        assert response.json()["metrics"]["indexed_snippets"] == 0