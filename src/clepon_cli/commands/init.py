import typer
import json
from rich.console import Console

from ..models import Project
from ..services import *

console = Console()
err_console = Console(stderr=True)

app = typer.Typer()


@app.command()
def init():
    """Initialize the project and extract all Python functions"""
    console.print("🚀 Initializing Clepon Function Extractor")

    # Step 1: Generate project token
    project_token = generate_project_token()
    console.print(f"✅ Generated project token: {project_token[:20]}")

    # Step 2: Store token in TOML configuration
    pwd = Path.cwd()
    config_path = pwd / "clepon.toml"
    store_token_in_toml(project_token, config_path)
    console.print(f"✅ Stored project token in {config_path}")

    # Step 3: Find all Python files in the current directory
    python_files = find_python_files(pwd)
    console.print(f"✅ Found {len(python_files)} Python files")

    # Step 4: Extract function from all Python files
    all_functions = []
    for python_file in python_files:
        console.print(f"📄 Parsing {python_file.relative_to(pwd)}...")
        functions = parse_python_file(python_file)
        all_functions.extend(functions)

    console.print(f"✅ Extracted {len(all_functions)} functions from all Python files")

    # Step 5: Create project data
    project_data = Project(project_token=project_token, functions=all_functions)

    # Step 6: Write to JSON file (for debugging for now instead of API call)
    output_path = pwd / "project_data.json"
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(project_data.model_dump(), json_file)

    console.print(f"✅ Project data written to {output_path}")
    console.print("🎉 Initialization complete!")

    # TODO: Send to API endpoint
    # api_endpoint = "https://api.example.com/projects"
    # response = request.post(
    #   apt_endpoint,
    #   json=project_data.model_dump(),
    #   headers={"Content-Type": "application/json"}
    # )
