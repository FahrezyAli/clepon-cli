import typer
import json
from rich.console import Console
from pathlib import Path

from ..config import CONFIG_FILENAME
from ..models import Project
from ..services import read_token_from_toml, get_git_diff, parse_diff_output

console = Console()
err_console = Console(stderr=True)


def callback(ctx: typer.Context):
    """
    Default command: Extract functions from latest git commit
    """
    # If a subcommand was invoked, don't run the default behavior
    if ctx.invoked_subcommand is not None:
        return

    console.print("🔍 Checking for new functions in latest commit...")

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

    # Step 3: Get git diff from latest commit
    console.print("📊 Getting git diff from latest commit...")
    diff_output = get_git_diff()

    if not diff_output:
        err_console.print("ℹ️  No changes found in latest commit")
        raise typer.Exit(0)

    # Step 4: Extract functions from diff
    console.print("🔎 Extracting functions from diff...")
    functions = parse_diff_output(diff_output)

    if not functions:
        err_console.print("ℹ️  No new functions found in latest commit")
        raise typer.Exit(0)

    console.print(f"✅ Extracted {len(functions)} new/modified functions")

    # Step 5: Write output to JSON
    project_data = Project(project_token=project_token, functions=functions)

    output_path = pwd / "diff_functions.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(project_data.model_dump(), f, indent=2)

    console.print(f"✅ Wrote output to {output_path}")
    console.print("🎉 Complete!")

    # TODO: Send to API endpoint
    # api_endpoint = "https://your-api.com/functions/diff"
    # response = requests.post(
    #     api_endpoint,
    #     json=project_data.model_dump(),
    #     headers={"Content-Type": "application/json"}
    # )
