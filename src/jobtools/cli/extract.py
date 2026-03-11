import asyncio
from datetime import datetime, timezone
from pathlib import Path

import typer

from jobtools.extractor import review_in_editor, run_extraction, save_extraction
from jobtools.manifest import load_manifest, save_manifest
from jobtools.settings import settings


app = typer.Typer()


@app.command()
def extract(
    app_id: int = typer.Argument(..., help="Application ID."),
    review: bool = typer.Option(settings.review, "--review/--no-review", "-r", help="Open result in $EDITOR before saving."),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Skip API call."),
) -> None:
    """Extract structured data from data/job-post-raw.md -> data/extraction.yaml."""
    manifest = load_manifest(settings.manifest_path)
    state = manifest.get(app_id)
    if not state:
        typer.secho(f"Error: application {app_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    app_dir = settings.base_path / state.folder_name
    md_path = app_dir / "data" / "job-post-raw.md"
    output_path = app_dir / "data" / "extraction.yaml"

    if not md_path.exists():
        typer.secho(f"Error: {md_path} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    jd_text = md_path.read_text(encoding="utf-8")
    typer.echo(f"-> JD: {md_path} ({len(jd_text)} chars)")
    typer.echo(f"-> Model: {settings.llm_model}")

    if dry_run:
        typer.secho("Dry-run: skipping API call.", fg=typer.colors.YELLOW)
        return

    typer.echo("-> Extracting...")
    result = asyncio.run(run_extraction(jd_text))
    typer.echo(f"   {result.company.name_short} | {result.job_title.short} | {result.company.sector}")

    if review:
        result = review_in_editor(result)

    save_extraction(result, output_path)

    # Update manifest with extraction path
    state.extraction_path = Path(state.folder_name) / "data" / "extraction.yaml"
    state.updated_at = datetime.now(timezone.utc)
    save_manifest(manifest, settings.manifest_path)
    typer.secho(f"Saved -> {output_path}", fg=typer.colors.GREEN)
