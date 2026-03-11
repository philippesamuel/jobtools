import typer

from .init import app as init_app
from .cli import app as cli_app

app = typer.Typer(
    name="jt",
    help="Job application CLI.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    )

app.add_typer(init_app)
app.add_typer(cli_app)
