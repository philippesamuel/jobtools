import typer

from jobtools.settings import settings

app = typer.Typer(
    name="config", 
    help="Inspect current configuration.", 
    no_args_is_help=True,
)

_CONFIG_KEYS = {
    "base_path": lambda: settings.base_path,
    "manifest_path": lambda: settings.manifest_path,
    "llm_model": lambda: settings.llm_model,
    "ollama_base_url": lambda: settings.ollama_base_url,
    "cookiecutter_template": lambda: settings.cookiecutter_template,
    "awesome_cv_dir": lambda: settings.awesome_cv_dir,
    "review": lambda: settings.review,
    "git_init": lambda: settings.git_init,
}


@app.command("show")
def config_show() -> None:
    """Print all current settings."""
    for key, getter in _CONFIG_KEYS.items():
        typer.echo(f"{key:<24} {getter()}")


@app.command("get")
def config_get(
    key: str = typer.Argument(..., help=f"One of: {', '.join(_CONFIG_KEYS)}"),
) -> None:
    """Print a single setting value (machine-readable, no newline)."""
    if key not in _CONFIG_KEYS:
        typer.secho(
            f"Unknown key '{key}'. Valid keys: {', '.join(_CONFIG_KEYS)}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    typer.echo(_CONFIG_KEYS[key](), nl=False)
