from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import typer
from cookiecutter.main import cookiecutter

from jobtools.manifest import append_application, load_manifest, save_manifest
from jobtools.models import ApplicationState, ApplicationStatus
from jobtools.settings import settings

app = typer.Typer(name="jt", help="Job application CLI.")


# ── init ─────────────────────────────────────────────────────────────────────

@app.command()
def init(
    url: str = typer.Argument(..., help="Job posting URL."),
    review: bool = typer.Option(False, "--review", "-r", help="Review parsed meta in $EDITOR before scaffolding."),
) -> None:
    """Scaffold a new application from a URL."""
    from jobtools.crawler import fetch_page
    from jobtools.extractor import review_in_editor
    from jobtools.parser import parse_meta

    # 1. Determine next id
    manifest = load_manifest(settings.manifest_path)
    app_id = manifest.next_id()

    typer.echo(f"[1/5] Fetching {url} ...")
    tmp_data = settings.base_path / f".tmp_{app_id}"
    html_path, md_path = fetch_page(url, tmp_data)

    typer.echo("[2/5] Parsing company / title / language ...")
    meta = parse_meta(md_path)
    typer.echo(f"      -> company={meta.company_short}  title={meta.job_title_short}  lang={meta.language}")

    if review:
        meta = review_in_editor(meta)

    typer.echo("[3/5] Scaffolding folder ...")
    folder_name = f"{app_id:04d}.{meta.company_short}_{meta.job_title_short}"
    cookiecutter(
        str(settings.cookiecutter_template),
        no_input=True,
        output_dir=str(settings.base_path),
        extra_context={
            "app_id": app_id,
            "company_short": meta.company_short,
            "job_title_short": meta.job_title_short,
            "language": meta.language,
            "source_url": url,
            "folder_name": folder_name,
        },
    )

    typer.echo("[4/5] Moving crawled files ...")
    data_dir = settings.base_path / folder_name / "data"
    (tmp_data / "job-post-raw.html").rename(data_dir / "job-post-raw.html")
    (tmp_data / "job-post-raw.md").rename(data_dir / "job-post-raw.md")
    tmp_data.rmdir()

    typer.echo("[5/5] Updating manifest ...")
    state = ApplicationState(
        id=app_id,
        folder_name=folder_name,
        status=ApplicationStatus.DRAFT,
        source_url=url,
        language=meta.language,  # type: ignore[arg-type]
        company_short=meta.company_short,
        job_title_short=meta.job_title_short,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    append_application(state, settings.manifest_path)
    typer.secho(f"\nCreated: {folder_name}", fg=typer.colors.GREEN)


# ── extract ───────────────────────────────────────────────────────────────────

@app.command()
def extract(
    app_id: int = typer.Argument(..., help="Application ID."),
    review: bool = typer.Option(False, "--review", "-r", help="Open result in $EDITOR before saving."),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Skip API call."),
) -> None:
    """Extract structured data from job-post-raw.md -> data/extraction.yaml."""
    from jobtools.extractor import review_in_editor, run_extraction, save_extraction

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
    from jobtools.extractor import review_in_editor
    from jobtools.models import ExtractionResult
    from jobtools.tailor import load_base_templates, run_tailoring, save_tailored_files

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
def compile(app_id: int = typer.Argument(..., help="Application ID.")) -> None:
    """Compile lualatex -> PDF bundle."""
    raise NotImplementedError


# ── status ────────────────────────────────────────────────────────────────────

@app.command()
def status(
    app_id: int = typer.Argument(..., help="Application ID."),
    new_status: str = typer.Argument(..., help="New status value."),
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
