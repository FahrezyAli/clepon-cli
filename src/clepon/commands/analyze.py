from pathlib import Path
import typer
import requests
from rich.console import Console

from ..config import CONFIG_FILENAME, API_BASE_URL
from ..services import read_token_from_toml

console = Console()
err_console = Console(stderr=True)

app = typer.Typer()


@app.command()
def analyze():
    """Analyze the project and return a the project report as MD file"""
    console.print("🔍 Analyzing the project...")

    # Step 1: Check if clepon.toml exists
    pwd = Path.cwd()
    config_path = pwd / CONFIG_FILENAME

    if not config_path.exists():
        err_console.print(
            f"❌ Error: {CONFIG_FILENAME} not found in current directory!"
        )
        err_console.print("Please run 'clepon init' first to initialize the project.")
        raise typer.Exit(1)

    # Step 2: Read token from toml file
    try:
        project_token = read_token_from_toml(config_path)
        console.print(f"✅ Found project token: {project_token[:20]}...")
    except Exception as e:
        err_console.print(f"❌ Error reading token: {e}")
        raise typer.Exit(1)

    # Step 3: Call the project report endpoint
    try:
        console.print("📊 Fetching project report from Clepon API...")
        response = requests.post(
            f"{API_BASE_URL}/projects/{project_token}/report",
            json={
                "llm_provider": "gemini",
                "llm_model": "gemini-2.0-flash",
                "temperature": 0.7,
                "max_contexts": 100,
            },
            timeout=1800,
        )
        response.raise_for_status()
        report_md = response.text

        # Step 4: Save the report as a markdown file
        report_path = pwd / "clepon_project_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)

        console.print(f"✅ Project report saved to {report_path.resolve()}")
    except requests.RequestException as e:
        err_console.print(f"❌ Error fetching project report: {e}")
        raise typer.Exit(1)
