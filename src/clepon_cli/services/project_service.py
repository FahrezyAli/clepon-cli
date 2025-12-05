import secrets
import base64
import toml
import ast
from pathlib import Path
from typing import List
from rich.console import Console

from ..models import Function, FunctionArgument

err_console = Console(stderr=True)


def generate_project_token() -> str:
    """Generate a random base64 project token"""
    random_bytes = secrets.token_bytes(32)
    return base64.b64encode(random_bytes).decode("utf-8")


def store_token_in_toml(token: str, config_path: Path) -> None:
    """Store the project token in a TOML configuration"""
    config = {"project": {"token": token}}
    with open(config_path, "w") as config_file:
        toml.dump(config, config_file)


def find_python_files(directory: Path) -> List[Path]:
    """Recursively find all python files in directory and subdirectories"""
    return list(directory.rglob("*.py"))


def extract_function_info(node: ast.FunctionDef, filepath: str) -> Function:
    """Extract function information from an AST node"""
    # Generate unique identifier for the function
    func_id = f"{filepath}:{node.name}:{node.lineno}"

    # Extract source code
    source_lines = ast.get_source_segment(open(filepath).read(), node)
    if source_lines is None:
        # Fallback: try to reconstruct
        source_lines = ast.unparse(node)

    # Extract arguments
    arguments = []
    for i, arg in enumerate(node.args.args):
        arg_type = None
        if arg.annotation:
            arg_type = ast.unparse(arg.annotation)

        arguments.append(
            FunctionArgument(
                id=f"{func_id}:arg:{i}", argument_name=arg.arg, argument_type=arg_type
            )
        )

    # Extract return type
    output_type = None
    if node.returns:
        output_type = ast.unparse(node.returns)

    return Function(
        id=func_id,
        source_code=source_lines,
        input=arguments,
        output_type=output_type,
        file=filepath,
    )


def parse_python_file(filepath: Path) -> List[Function]:
    """Parse a Python file and extract all function definitions"""
    functions = []

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()

        tree = ast.parse(content, filename=str(filepath))

        # Walk through all nodes in the AST
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = extract_function_info(node, str(filepath))
                functions.append(func_info)

    except Exception as e:
        err_console.print(f"[red]Error parsing {filepath}: {e}[/red]")

    return functions
