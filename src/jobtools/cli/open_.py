import sys
import subprocess as _sp

import typer

from jobtools.manifest import load_manifest
from jobtools.settings import settings


app = typer.Typer()


@app.command(name="open")
def open_folder(app_id: int = typer.Argument(..., help="Application ID.")) -> None:
    """Open application folder in Finder (macOS) or file manager."""

    manifest = load_manifest(settings.manifest_path)
    state = manifest.get(app_id)
    if not state:
        typer.secho(f"Error: application {app_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    app_dir = settings.base_path / state.folder_name
    if not app_dir.exists():
        typer.secho(f"Error: folder not found: {app_dir}", fg=typer.colors.RED)
        raise typer.Exit(1)

    opener = "open" if sys.platform == "darwin" else "xdg-open"
    _sp.run([opener, str(app_dir)])
