import typer

from .commands import init_app, default_callback

app = typer.Typer()

app.add_typer(init_app)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    return default_callback(ctx)
