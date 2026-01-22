from pathlib import Path

import typer
from rich.console import Console

from .commands import analyze_app, init_app
from .config import CONFIG_FILENAME
from .services import analyze_diff, get_git_diff, read_token_from_toml, run_tests

console = Console()
err_console = Console(stderr=True)

app = typer.Typer()

app.add_typer(analyze_app)
app.add_typer(init_app)


@app.callback(invoke_without_command=True)
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

    # Step 4: Send diff to API for function extraction
    console.print("🚀 Sending diff to Clepon API for function extraction...")
    analyze_diff(project_token, diff_output)

    # Step 5: Run unittest automatically
    console.print("\n🧪 Running unit tests...")
    run_tests()
