from datetime import datetime, timezone

import typer

from jobtools.cli.cli import app
from jobtools.manifest import load_manifest, save_manifest
from jobtools.settings import settings


@app.command()
def compile(
    app_id: int = typer.Argument(..., help="Application ID."),
    clean: bool = typer.Option(True, "--clean/--no-clean", "-c", help="Remove aux files after compile."),
) -> None:
    """Compile application files *.tex -> build/ via lualatex."""
    from jobtools.compiler import compile_pdf

    manifest = load_manifest(settings.manifest_path)
    state = manifest.get(app_id)
    if not state:
        typer.secho(f"Error: application {app_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    app_dir = settings.base_path / state.folder_name
    typer.echo(f"-> Compiling {state.folder_name} ...")

    try:
        compiled = compile_pdf(app_dir, state.pdf_names, clean=clean)
    except (FileNotFoundError, RuntimeError) as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

    state.updated_at = datetime.now(timezone.utc)
    save_manifest(manifest, settings.manifest_path)
    for role, pdf in compiled.items():
        typer.secho(f"   [{role}] {pdf.relative_to(settings.base_path)}", fg=typer.colors.GREEN)
    typer.secho(f"Done: {len(compiled)} PDF(s) in build/", fg=typer.colors.GREEN)
