import os
import ast
import sys

project_path = r"c:\Users\skhjp\OneDrive\Desktop\backend\backend\backend"
standard_libs = set([
    "os", "sys", "re", "math", "random", "datetime", "json", "asyncio", 
    "urllib", "typing", "collections", "itertools", "functools", "pathlib", 
    "logging", "time", "multiprocessing", "threading", "uuid", "hashlib",
    "base64", "csv", "io", "copy", "decimal", "shutil", "enum", "ast", "subprocess"
])

imports = set()

for root, dirs, files in os.walk(project_path):
    if "venv" in root or "__pycache__" in root or "migrations" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=filepath)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.add(alias.name.split('.')[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.add(node.module.split('.')[0])
                except Exception as e:
                    pass

external_imports = imports - standard_libs - {"app", "tests"}
print("External imports found:", sorted(external_imports))
