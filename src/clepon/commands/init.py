import typer
import json
import requests
from pathlib import Path
from rich.console import Console

from ..models import Project
from ..services import (
    generate_project_token,
    store_token_in_toml,
    find_python_files,
    parse_python_file,
)


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

    # Step 6: Send to vectorization API endpoint
    console.print("🔄 Sending data to API for vectorization...")
    api_endpoint = "http://127.0.0.1:8001/projects/vectorize"

    try:
        response = requests.post(
            api_endpoint,
            json=project_data.model_dump(),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()

        # Parse successful response
        result = response.json()
        console.print(
            f"✅ Successfully vectorized {result['processed_count']} functions"
        )
        console.print(f"📦 Project ID: {result['project_id'][:20]}...")
        console.print("🎉 Initialization complete!")

    except requests.exceptions.ConnectionError:
        err_console.print("❌ Error: Could not connect to API server")
        err_console.print(
            "   Please ensure the FastAPI server is running at http://127.0.0.1:8001"
        )
    except requests.exceptions.Timeout:
        err_console.print("❌ Error: API request timed out")
        err_console.print("   The server may be processing a large number of functions")
    except requests.exceptions.HTTPError as e:
        err_console.print(f"❌ API Error: {response.status_code}")
        err_console.print(f"   {response.text}")
    except Exception as e:
        err_console.print(f"❌ Unexpected error: {str(e)}")
