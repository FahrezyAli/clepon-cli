import typer
import secrets
import base64
import toml
import ast
import subprocess
from pathlib import Path
from typing import List
from rich.console import Console

from ..models import Function, FunctionArgument

console = Console()
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


def read_token_from_toml(config_path: Path) -> str:
    """Read the project token from the .toml file"""
    with open(config_path, "r") as f:
        config = toml.load(f)
    return config["project"]["token"]


def find_python_files(directory: Path) -> List[Path]:
    files = directory.rglob("*.py")
    return [
        f
        for f in files
        if not any(part.startswith(".") for part in f.relative_to(directory).parts)
    ]


def extract_function_info_from_file(node: ast.FunctionDef, filepath: str) -> Function:
    """Extract function information from an AST node"""
    # Generate unique identifier for the function
    filename = Path(filepath).name

    func_id = f"{filename}:{node.name}:{node.lineno}"

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
        file=filename,
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
                func_info = extract_function_info_from_file(node, str(filepath))
                functions.append(func_info)

    except Exception as e:
        err_console.print(f"[red]Error parsing {filepath}: {e}[/red]")

    return functions


def get_git_diff() -> str:
    """Get the git diff of the latest commit"""
    # First check if we're in a git repository
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"], capture_output=True, check=True
        )
    except subprocess.CalledProcessError:
        console.print("❌ Error: Not a git repository!")
        console.print("Please initialize git first: git init")
        raise typer.Exit(1)

    # Check if there are any commits
    try:
        subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        console.print("❌ Error: No commits found in repository!")
        console.print("Please make at least one commit first.")
        raise typer.Exit(1)

    # Check if there's a previous commit (HEAD~1)
    try:
        subprocess.run(["git", "rev-parse", "HEAD~1"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        console.print("❌ Error: Only one commit exists!")
        console.print("Please make at least one more commit to compare.")
        console.print("Alternatively, use 'git diff HEAD' to see uncommitted changes.")
        raise typer.Exit(1)

    # Now get the actual diff
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Error running git diff: {e}")
        console.print(f"stderr: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
        raise typer.Exit(1)


def extract_function_info_from_diff(
    node: ast.FunctionDef, filepath: str, source_code: str
) -> Function:
    """Extract function information from an AST node with provided source"""
    # Generate unique ID
    filename = Path(filepath).name

    func_id = f"{filename}:{node.name}:{node.lineno}"

    # Extract source code for this specific function
    source_lines = ast.get_source_segment(source_code, node)
    if source_lines is None:
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
        file=filename,
    )


def parse_diff_output(diff_output: str) -> List[Function]:
    """Extract function definitions from git diff output"""
    functions = []

    # Parse diff to find added Python code
    lines = diff_output.split("\n")
    current_file = None
    added_code_blocks = []
    current_block = []

    for line in lines:
        # Track which file we're looking at
        if line.startswith("+++ b/"):
            current_file = line[6:]
            if not current_file.endswith(".py"):
                current_file = None

        # Collect added lines (lines starting with +)
        elif line.startswith("+") and not line.startswith("+++") and current_file:
            # Remove the + prefix
            code_line = line[1:]
            current_block.append(code_line)

        # When we hit a non-added line, process the accumulated block
        elif current_block and current_file:
            added_code_blocks.append((current_file, "\n".join(current_block)))
            current_block = []

    # Don't forget the last block
    if current_block and current_file:
        added_code_blocks.append((current_file, "\n".join(current_block)))

    # Extract functions from added code blocks
    for filepath, code_block in added_code_blocks:
        try:
            tree = ast.parse(code_block)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = extract_function_info_from_diff(
                        node, filepath, code_block
                    )
                    functions.append(func_info)
        except SyntaxError:
            # Code block might be incomplete, skip it
            continue

    return functions
