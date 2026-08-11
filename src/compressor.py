import os
import ast
import textwrap
from pathlib import Path
from src.router_engine import RouterEngine

IGNORE_DIRS = {
    ".git", "__pycache__", ".venv", "venv", "env", 
    ".pytest_cache", "build", "dist", ".idea", ".vscode", "node_modules", "db"
}

class CodebaseCompressor:
    """
    Model 1 (The Codebase Compressor): Recursively scans Python codebases,
    extracts functions, methods, and classes, and compresses them into 
    vectorized AST logic rules in ChromaDB.
    """
    def __init__(self, router_engine: RouterEngine = None):
        self.router = router_engine if router_engine else RouterEngine()

    def _extract_snippets_from_file(self, file_path: str) -> list[tuple[str, str]]:
        """
        Parses a single Python file into individual function, class, 
        and method code blocks using AST line boundaries and dedent normalization.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            lines = source.splitlines()
            tree = ast.parse(source, filename=file_path)
        except (SyntaxError, UnicodeDecodeError, OSError):
            return []

        snippets = []
        rel_path = os.path.normpath(file_path)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    snippet_lines = lines[node.lineno - 1 : node.end_lineno]
                    
                    # Dedent removes leading class indentation so AST parsing succeeds standalone
                    raw_snippet = "\n".join(snippet_lines)
                    snippet_code = textwrap.dedent(raw_snippet)
                    
                    rule_id = f"{rel_path}::{node.name}"
                    snippets.append((rule_id, snippet_code))

        return snippets

    def compress_directory(self, root_dir: str) -> dict:
        """
        Recursively walks root_dir, extracts code fragments, and indexes 
        them into the Router database.
        """
        root_path = Path(root_dir)
        if not root_path.exists():
            raise FileNotFoundError(f"Target directory '{root_dir}' does not exist.")

        scanned_files = 0
        indexed_snippets = 0
        failed_snippets = 0

        for current_root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(current_root, file)
                    scanned_files += 1

                    snippets = self._extract_snippets_from_file(file_path)
                    for rule_id, raw_code in snippets:
                        try:
                            self.router.index_code_snippet(rule_id, raw_code)
                            indexed_snippets += 1
                        except Exception:
                            failed_snippets += 1

        return {
            "scanned_files": scanned_files,
            "indexed_snippets": indexed_snippets,
            "failed_snippets": failed_snippets
        }


if __name__ == "__main__":
    compressor = CodebaseCompressor()
    print("CodebaseCompressor initialized successfully.")