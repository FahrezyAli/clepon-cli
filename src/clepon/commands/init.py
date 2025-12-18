from pathlib import Path
from rich.console import Console
import typer


from ..models import Project
from ..services import (
    generate_project,
    find_python_files,
    parse_python_file,
    vectorize_project,
    generate_tests,
    run_tests,
)


console = Console()
err_console = Console(stderr=True)

app = typer.Typer()


@app.command()
def init():
    """Initialize the project and extract all Python functions"""
    pwd = Path.cwd()

    # Step 1: Create project via POST /projects
    console.print("🚀 Initializing Clepon Function Extractor")
    project_id = generate_project()

    # Step 2: Find all Python files in the current directory
    python_files = find_python_files(pwd)
    console.print(f"✅ Found {len(python_files)} Python files")

    # Step 3: Extract functions from all Python files
    all_functions = []
    for python_file in python_files:
        console.print(f"📄 Parsing {python_file.relative_to(pwd)}...")
        functions = parse_python_file(python_file)
        all_functions.extend(functions)

    console.print(f"✅ Extracted {len(all_functions)} functions from all Python files")

    # Step 4: Create project data and send to vectorization API endpoint
    project_data = Project(project_token=project_id, functions=all_functions)
    console.print("🔄 Sending data to API for vectorization...")
    vectorize_project(project_data)

    # Step 5: Generate tests
    console.print("\n🧪 Generating unit tests...")
    generate_tests(project_id)

    # Step 7: Run unittest automatically
    console.print("\n🧪 Running unit tests...")
    run_tests()
