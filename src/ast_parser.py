import ast

class LogicExtractor(ast.NodeTransformer):
    """
    Transforms an AST into normalized structural logic by abstracting 
    identifiers, types, constants, classes, and exception handling.
    """
    def visit_FunctionDef(self, node):
        node.name = "FUNC"
        node.returns = None
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant)):
            node.body.pop(0)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        node.name = "FUNC"
        node.returns = None
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant)):
            node.body.pop(0)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        node.name = "CLASS"
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant)):
            node.body.pop(0)
        self.generic_visit(node)
        return node

    def visit_arg(self, node):
        node.arg = "ARG"
        node.annotation = None
        return node

    def visit_Name(self, node):
        node.id = "VAR"
        return node

    def visit_Constant(self, node):
        node.value = "VAL"
        return node

    def visit_ExceptHandler(self, node):
        if node.name:
            node.name = "ERR_VAR"
        self.generic_visit(node)
        return node

    def visit_Import(self, node):
        for alias in node.names:
            alias.name = "MODULE"
            alias.asname = "ALIAS" if alias.asname else None
        return node

    def visit_ImportFrom(self, node):
        node.module = "MODULE"
        for alias in node.names:
            alias.name = "SYM"
            alias.asname = "ALIAS" if alias.asname else None
        return node


class SemanticDescriptorVisitor(ast.NodeVisitor):
    """
    Translates AST structural nodes, function names, and docstrings 
    into natural-language structural descriptors.
    """
    def __init__(self):
        self.descriptors = []

    def visit_ClassDef(self, node):
        self.descriptors.append(f"class definition {node.name}")
        doc = ast.get_docstring(node)
        if doc:
            self.descriptors.append(doc)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.descriptors.append(f"function definition {node.name}")
        doc = ast.get_docstring(node)
        if doc:
            self.descriptors.append(doc)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.descriptors.append(f"async asynchronous function definition coroutine {node.name}")
        doc = ast.get_docstring(node)
        if doc:
            self.descriptors.append(doc)
        self.generic_visit(node)

    def visit_With(self, node):
        self.descriptors.append("context manager with block file resource statement")
        self.generic_visit(node)

    def visit_Try(self, node):
        self.descriptors.append("try block error handling exception")
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.descriptors.append("except handler catch error")
        self.generic_visit(node)

    def visit_For(self, node):
        self.descriptors.append("for loop iteration")
        self.generic_visit(node)

    def visit_While(self, node):
        self.descriptors.append("while loop condition")
        self.generic_visit(node)

    def visit_If(self, node):
        self.descriptors.append("conditional if statement branch")
        self.generic_visit(node)

    def visit_Match(self, node):
        self.descriptors.append("match case pattern matching conditional branch")
        self.generic_visit(node)

    def visit_ListComp(self, node):
        self.descriptors.append("list comprehension iteration map filter")
        self.generic_visit(node)

    def visit_DictComp(self, node):
        self.descriptors.append("dictionary comprehension key value mapping")
        self.generic_visit(node)

    def visit_SetComp(self, node):
        self.descriptors.append("set comprehension unique iteration")
        self.generic_visit(node)

    def visit_Raise(self, node):
        self.descriptors.append("raise exception error")
        self.generic_visit(node)

    def visit_Return(self, node):
        self.descriptors.append("return value statement")
        self.generic_visit(node)

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Mod):
            self.descriptors.append("modulo remainder operation even odd check")
        self.generic_visit(node)


def calculate_ast_depth(node) -> int:
    """Calculates the maximum depth of an AST tree."""
    if not isinstance(node, ast.AST):
        return 0
    children = [calculate_ast_depth(child) for child in ast.iter_child_nodes(node)]
    return 1 + max(children, default=0)


def calculate_complexity(tree) -> int:
    """Calculates structural decision complexity based on branching nodes."""
    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert, ast.Match)):
            complexity += 1
    return complexity


def parse_code_to_logic(source_code: str) -> tuple[str, str, dict]:
    """
    Parses Python source code and returns:
    1. Dense AST dump string
    2. Natural language structural description
    3. Structural metadata dictionary (node_count, depth, complexity)
    """
    try:
        tree = ast.parse(source_code)
        
        node_count = sum(1 for _ in ast.walk(tree))
        depth = calculate_ast_depth(tree)
        complexity = calculate_complexity(tree)
        
        metrics = {
            "node_count": node_count,
            "depth": depth,
            "complexity": complexity
        }

        descriptor_visitor = SemanticDescriptorVisitor()
        descriptor_visitor.visit(tree)
        semantic_descriptor = " ".join(descriptor_visitor.descriptors)

        transformer = LogicExtractor()
        transformed_tree = transformer.visit(tree)
        ast_dump = ast.dump(transformed_tree, annotate_fields=False)

        return ast_dump, semantic_descriptor, metrics
    except SyntaxError as e:
        return f"SYNTAX_ERROR: {e}", "", {"node_count": 0, "depth": 0, "complexity": 0}


if __name__ == "__main__":
    sample = """
async def fetch_data(urls):
    \"\"\"Fetch list of URLs concurrently.\"\"\"
    return [url for url in urls if url.startswith('https')]
"""
    ast_str, desc, metrics = parse_code_to_logic(sample)
    print("--- AST DUMP ---")
    print(ast_str)
    print("\n--- DESCRIPTORS ---")
    print(desc)
    print("\n--- METRICS ---")
    print(metrics)