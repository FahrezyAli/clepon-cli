import typer

from .commands import init_app

app = typer.Typer()

app.add_typer(init_app)
