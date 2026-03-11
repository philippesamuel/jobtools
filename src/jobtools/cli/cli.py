from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import typer

from jobtools.extractor import review_in_editor, run_extraction, save_extraction
from jobtools.manifest import load_manifest, save_manifest
from jobtools.models import ApplicationStatus
from jobtools.settings import settings


app = typer.Typer()

# ── extract ───────────────────────────────────────────────────────────────────
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


# ── tailor ────────────────────────────────────────────────────────────────────

@app.command()
def tailor(
    app_id: int = typer.Argument(..., help="Application ID."),
    reference: int = typer.Option(None, "--reference", "-ref", help="Use tex files from this app ID as base."),
    review: bool = typer.Option(False, "--review", "-r", help="Open result in $EDITOR before saving."),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Skip API call."),
) -> None:
    """Tailor coverletter-body, summary, experience, skills via LLM."""
    from ruamel.yaml import YAML as _YAML
    from jobtools.models import ExtractionResult
    from jobtools.tailor import check_language_mismatch, load_base_templates, run_tailoring, save_tailored_files

    manifest = load_manifest(settings.manifest_path)
    state = manifest.get(app_id)
    if not state:
        typer.secho(f"Error: application {app_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not state.extraction_path:
        typer.secho(f"Error: run `jt extract {app_id}` first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Load extraction
    _yaml = _YAML()
    extraction_path = settings.base_path / state.extraction_path
    extraction = ExtractionResult.model_validate(
        _yaml.load(extraction_path.read_text(encoding="utf-8"))
    )

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


# ── compile ───────────────────────────────────────────────────────────────────

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



# ── open ─────────────────────────────────────────────────────────────────────

@app.command(name="open")
def open_folder(app_id: int = typer.Argument(..., help="Application ID.")) -> None:
    """Open application folder in Finder (macOS) or file manager."""
    import subprocess as _sp
    import sys

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


# ── status ────────────────────────────────────────────────────────────────────

@app.command()
def status(
    app_id: int = typer.Argument(..., help="Application ID."),
    new_status: ApplicationStatus = typer.Argument(..., help="New status value."),
) -> None:
    """Update application status in manifest."""
    manifest = load_manifest(settings.manifest_path)
    state = manifest.get(app_id)
    if not state:
        typer.secho(f"Error: application {app_id} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)
    state.status = ApplicationStatus(new_status)
    state.updated_at = datetime.now(timezone.utc)
    save_manifest(manifest, settings.manifest_path)
    typer.secho(f"{app_id} -> {new_status}", fg=typer.colors.GREEN)


# ── list ──────────────────────────────────────────────────────────────────────

@app.command(name="list")
def list_apps(
    status_filter: str = typer.Option(None, "--status", "-s", help="Filter by status."),
) -> None:
    """List all applications from manifest."""
    manifest = load_manifest(settings.manifest_path)
    apps = manifest.applications
    if status_filter:
        apps = [a for a in apps if a.status == status_filter]
    if not apps:
        typer.echo("No applications found.")
        return
    for a in apps:
        typer.echo(
            f"{a.id:04d}  {a.status:<12}  {a.company_short:<20}  {a.job_title_short}"
        )


if __name__ == "__main__":
    app()
