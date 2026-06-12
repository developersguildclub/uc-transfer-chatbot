import ast
from pathlib import Path

model_path = Path(__file__).resolve().parents[1] / "model.py"
tree = ast.parse(model_path.read_text(), filename=str(model_path))
violations = []


def calls_model_init(node):
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            if child.func.id in {"get_chat_model", "init_chat_model"}:
                return True

    return False


for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        continue

    if calls_model_init(node):
        violations.append(node.lineno)

if violations:
    lines = ", ".join(str(line) for line in violations)
    raise SystemExit(f"chat model is initialized at import time on line(s): {lines}")
