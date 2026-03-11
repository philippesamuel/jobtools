import asyncio
from datetime import datetime, timezone

import typer

from jobtools.extractor import load_extraction, review_in_editor
from jobtools.manifest import load_manifest, save_manifest
from jobtools.settings import settings
from jobtools.tailor import check_language_mismatch, load_base_templates, run_tailoring, save_tailored_files


app = typer.Typer()


@app.command()
def tailor(
    app_id: int = typer.Argument(..., help="Application ID."),
    reference: int = typer.Option(None, "--reference", "-ref", help="Use tex files from this app ID as base."),
    review: bool = typer.Option(False, "--review", "-r", help="Open result in $EDITOR before saving."),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Skip API call."),
) -> None:
    """Tailor coverletter-body, summary, experience, skills via LLM."""
    manifest = load_manifest(settings.manifest_path)
    state = manifest.get(app_id)
    if not state:
        typer.secho(f"Error: application {app_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not state.extraction_path:
        typer.secho(f"Error: run `jt extract {app_id}` first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Load extraction
    extraction_path = settings.base_path / state.extraction_path
    extraction = load_extraction(extraction_path)

    # Resolve base template source
    app_dir = settings.base_path / state.folder_name
    if reference:
        ref_state = manifest.get(reference)
        if not ref_state:
            typer.secho(f"Error: reference {reference} not found.", fg=typer.colors.RED)
            raise typer.Exit(1)
        base_dir = settings.base_path / ref_state.folder_name
        base_lang = ref_state.language
        typer.echo(f"-> Reference: {ref_state.folder_name}")
    else:
        base_dir = app_dir
        base_lang = state.language

    check_language_mismatch(base_lang, state.language, base_dir.name)
    typer.echo(f"-> Base: {base_dir.name} ({base_lang})")
    typer.echo(f"-> Model: {settings.llm_model}")

    if dry_run:
        templates = load_base_templates(base_dir, base_lang)
        for f, content in templates.items():
            typer.echo(f"   {f} ({len(content)} chars)")
        typer.secho("Dry-run: skipping API call.", fg=typer.colors.YELLOW)
        return

    typer.echo("-> Tailoring...")
    result = asyncio.run(run_tailoring(extraction, base_dir, base_lang))

    if review:
        result = review_in_editor(result)

    written = save_tailored_files(result, app_dir, state.language)
    for path in written:
        typer.echo(f"   wrote {path.relative_to(settings.base_path)}")

    state.updated_at = datetime.now(timezone.utc)
    save_manifest(manifest, settings.manifest_path)
    typer.secho(f"Tailored: {state.folder_name}", fg=typer.colors.GREEN)
