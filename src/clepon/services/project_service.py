import ast
import subprocess
from pathlib import Path
from typing import List
import typer
import toml
import requests
from rich.console import Console

from ..models import Function, FunctionArgument, Project
from ..config import CONFIG_FILENAME, API_BASE_URL

console = Console()
err_console = Console(stderr=True)


def generate_project() -> str:
    pwd = Path.cwd()
    config_path = pwd / CONFIG_FILENAME

    project_name = pwd.name
    console.print(f"📁 Project name: {project_name}")

    console.print("🔄 Creating project on API...")

    project_name = pwd.name
    console.print(f"📁 Project name: {project_name}")

    try:
        response = requests.post(
            f"{API_BASE_URL}/projects",
            json={"name": project_name},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()

        project_info = response.json()
        project_id = project_info["id"]
        console.print(f"✅ Created project with ID: {project_id[:20]}...")

        # Store project_id in TOML configuration
        config = {"project": {"id": project_id, "name": project_name}}
        with open(config_path, "w", encoding="utf-8") as config_file:
            toml.dump(config, config_file)
        console.print(f"✅ Stored project configuration in {config_path}")

        return project_id

    except requests.exceptions.ConnectionError as exc:
        err_console.print("❌ Error: Could not connect to API server")
        err_console.print(
            f"   Please ensure the API server is accessible at {API_BASE_URL}"
        )
        raise typer.Exit(1) from exc

    except requests.exceptions.Timeout as exc:
        err_console.print("❌ Error: API request timed out")
        raise typer.Exit(1) from exc

    except requests.exceptions.HTTPError as exc:
        err_console.print(f"❌ API Error: {response.status_code}")  # type: ignore
        err_console.print(f"   {response.text}")  # type: ignore
        raise typer.Exit(1) from exc

    except Exception as exc:
        err_console.print(f"❌ Unexpected error: {str(exc)}")
        raise typer.Exit(1) from exc


def read_token_from_toml(config_path: Path) -> str:
    """Read the project token from the .toml file"""
    with open(config_path, "r", encoding="utf-8") as f:
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
    with open(filepath, "r", encoding="utf-8") as file:
        source = file.read()

    source_lines = ast.get_source_segment(source, node)

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

    except OSError as exc:
        err_console.print(f"[red]Error parsing {filepath}: {exc}[/red]")

    return functions


def vectorize_project(project_data: Project):
    try:
        response = requests.post(
            f"{API_BASE_URL}/projects/vectorize",
            json=project_data.model_dump(),
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        response.raise_for_status()

        # Parse successful response
        result = response.json()
        console.print(
            f"✅ Successfully vectorized {result['processed_count']} functions"
        )
        console.print(f"📦 Project ID: {result['project_id'][:20]}...")

    except requests.exceptions.ConnectionError as exc:
        err_console.print("❌ Error: Could not connect to API server")
        err_console.print(
            f"   Please ensure the API server is accessible at {API_BASE_URL}"
        )
        raise typer.Exit(1) from exc

    except requests.exceptions.Timeout as exc:
        err_console.print("❌ Error: API request timed out")
        err_console.print("   The server may be processing a large number of functions")
        raise typer.Exit(1) from exc

    except requests.exceptions.HTTPError as exc:
        err_console.print(f"❌ API Error: {response.status_code}")  # type: ignore
        err_console.print(f"   {response.text}")  # type: ignore
        raise typer.Exit(1) from exc

    except Exception as exc:
        err_console.print(f"❌ Unexpected error during vectorization: {str(exc)}")
        raise typer.Exit(1) from exc


def generate_tests(project_id: str):
    pwd = Path.cwd()

    try:
        response = requests.post(
            f"{API_BASE_URL}/test-generator/{project_id}/generate",
            json={
                "llm_provider": "gemini",
                "llm_model": "gemini-2.0-flash",
                "temperature": 0.7,
            },
            headers={"Content-Type": "application/json"},
            timeout=1800,  # 30 minutes for test generation
        )
        response.raise_for_status()

        test_results = response.json()
        console.print(f"✅ Generated {test_results['generated']} test files")
        console.print(f"   Total functions: {test_results['total_functions']}")
        if test_results["failed"] > 0:
            console.print(f"   ⚠️  Failed: {test_results['failed']}")

        tests_dir = pwd / "tests"
        tests_dir.mkdir(exist_ok=True)

        for filename, test_file in test_results["tests"].items():
            test_path = tests_dir / filename
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_file["content"])
            console.print(f"📝 Wrote test file: tests/{filename}")

        console.print(f"✅ All test files written to {tests_dir}")

    except requests.exceptions.ConnectionError as exc:
        err_console.print(
            "❌ Error: Could not connect to API server for test generation"
        )
        err_console.print(
            f"   Please ensure the API server is accessible at {API_BASE_URL}"
        )
        raise typer.Exit(1) from exc

    except requests.exceptions.Timeout as exc:
        err_console.print("❌ Error: Test generation request timed out")
        err_console.print("   The LLM may be taking longer than expected")
        raise typer.Exit(1) from exc

    except requests.exceptions.HTTPError as exc:
        err_console.print(
            f"❌ API Error during test generation: {response.status_code}"  # type: ignore
        )
        err_console.print(f"   {response.text}")  # type: ignore
        raise typer.Exit(1) from exc

    except Exception as exc:
        err_console.print(f"❌ Unexpected error during test generation: {str(exc)}")
        raise typer.Exit(1) from exc


def run_tests():
    pwd = Path.cwd()

    try:
        result = subprocess.run(
            ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
            capture_output=True,
            text=True,
            cwd=pwd,
        )

        # Display test output
        if result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr)

        if result.returncode == 0:
            console.print("\n✅ All tests passed!")
        else:
            console.print(f"\n⚠️  Some tests failed (exit code: {result.returncode})")

    except Exception as e:
        err_console.print(f"❌ Error running tests: {str(e)}")
        err_console.print(
            "   You can manually run tests with: python -m unittest discover -s tests"
        )

    console.print("\n🎉 Initialization complete!")


def get_git_diff() -> str:
    """Get the git diff of the latest commit"""
    # First check if we're in a git repository
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"], capture_output=True, check=True
        )

    except subprocess.CalledProcessError as exc:
        console.print("❌ Error: Not a git repository!")
        console.print("Please initialize git first: git init")
        raise typer.Exit(1) from exc

    # Check if there are any commits
    try:
        subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, check=True)

    except subprocess.CalledProcessError as exc:
        console.print("❌ Error: No commits found in repository!")
        console.print("Please make at least one commit first.")
        raise typer.Exit(1) from exc

    # Check if there's a previous commit (HEAD~1)
    try:
        subprocess.run(["git", "rev-parse", "HEAD~1"], capture_output=True, check=True)

    except subprocess.CalledProcessError as exc:
        console.print("❌ Error: Only one commit exists!")
        console.print("Please make at least one more commit to compare.")
        console.print("Alternatively, use 'git diff HEAD' to see uncommitted changes.")
        raise typer.Exit(1) from exc
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


def analyze_diff(project_id: str, diff_output: str):
    pwd = Path.cwd()

    try:
        response = requests.post(
            f"{API_BASE_URL}/commit-analyzer/{project_id}/analyze",
            json={
                "diff_text": diff_output,
                "llm_provider": "gemini",
                "llm_model": "gemini-2.0-flash",
                "temperature": 0.7,
            },
            headers={"Content-Type": "application/json"},
            timeout=1800,  # 30 minutes for analysis
        )
        response.raise_for_status()

        test_results = response.json()
        console.print(f"✅ Generated {test_results['generated']} test files")
        console.print(f"   Total functions: {test_results['total_functions']}")
        if test_results["failed"] > 0:
            console.print(f"   ⚠️  Failed: {test_results['failed']}")

        tests_dir = pwd / "tests"
        tests_dir.mkdir(exist_ok=True)

        for filename, test_file in test_results["tests"].items():
            test_path = tests_dir / filename
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_file["content"])
            console.print(f"📝 Wrote test file: tests/{filename}")

        console.print(f"✅ All test files written to {tests_dir}")

    except requests.exceptions.ConnectionError as exc:
        err_console.print(
            "❌ Error: Could not connect to API server for test generation"
        )
        err_console.print(
            f"   Please ensure the API server is accessible at {API_BASE_URL}"
        )
        raise typer.Exit(1) from exc

    except requests.exceptions.Timeout as exc:
        err_console.print("❌ Error: Test generation request timed out")
        err_console.print("   The LLM may be taking longer than expected")
        raise typer.Exit(1) from exc

    except requests.exceptions.HTTPError as exc:
        err_console.print(
            f"❌ API Error during test generation: {response.status_code}"  # type: ignore
        )
        err_console.print(f"   {response.text}")  # type: ignore
        raise typer.Exit(1) from exc

    except Exception as exc:
        err_console.print(f"❌ Unexpected error during test generation: {str(exc)}")
        raise typer.Exit(1) from exc
