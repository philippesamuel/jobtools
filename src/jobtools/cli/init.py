import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import html2text
import typer
from cookiecutter.main import cookiecutter

from jobtools.crawler import fetch_page
from jobtools.extractor import (
    load_extraction,
    review_in_editor,
    run_extraction,
    save_extraction,
)
from jobtools.manifest import append_application, load_manifest
from jobtools.models import ApplicationState, ApplicationStatus
from jobtools.settings import settings
from jobtools.utils import slugify


app = typer.Typer()


@app.command()
def init(
    url: Optional[str] = typer.Argument(None, help="Job posting URL."),
    from_file: Optional[Path] = typer.Option(None, "--from-file", "-f"),
    from_extraction: Optional[Path] = typer.Option(None, "--from-extraction", "-e"),
    review: bool = typer.Option(
        settings.review,
        "--review/--no-review",
        "-r",
        help="Review extraction in $EDITOR before scaffolding.",
    ),
) -> None:
    """Scaffold a new application from a URL."""
    # guard: exactly one source
    sources = [x for x in [url, from_file, from_extraction] if x]
    if len(sources) != 1:
        typer.secho(
            "Provide exactly one of: URL, --from-file, --from-extraction",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    manifest = load_manifest(settings.manifest_path)
    app_id = manifest.next_id()
    tmp_data = settings.base_path / f".tmp_{app_id}"

    # Step 1: get md_text (or skip)
    if url:
        typer.echo(f"[1/4] Fetching {url} ...")
        _, md_path = fetch_page(url, tmp_data)
        md_text = md_path.read_text(encoding="utf-8")
    elif from_file:
        typer.echo(f"[1/4] Reading {from_file} ...")
        md_text = _read_as_markdown(from_file)  # html→md if needed
    # else: skip to step 2b

    # Step 2: extract (or load)
    if from_extraction:
        typer.echo(f"[1/4] Reading {from_extraction} ...")
        extraction = load_extraction(from_extraction)
    else:
        typer.echo(f"[2/4] Extracting job data ...")
        extraction = asyncio.run(run_extraction(md_text))
        typer.echo(
            f"      -> {extraction.company.name_short} | {extraction.job_title.short} | {extraction.language}"
        )

    if review:
        extraction = review_in_editor(extraction)

    typer.echo("[3/4] Scaffolding folder ...")
    company_short = slugify(extraction.company.name_short)
    job_title_slug = slugify(extraction.job_title.short)
    job_title_short = extraction.job_title.short
    _lang = extraction.language
    folder_name = f"{app_id:04d}.{company_short}_{job_title_slug}"

    # Resolve contact_person — fall back to language-appropriate default
    contact_person = (
        extraction.company.contact_person
        or ("Personalabteilung" if _lang == "de" else "Hiring Manager")
    )
    # Resolve address lines — fall back to company name only
    company_address = extraction.company.address

    cookiecutter(
        str(settings.cookiecutter_template),
        no_input=settings.cookiecutter_no_input,
        output_dir=str(settings.base_path),
        extra_context={
            "app_id": app_id,
            "language": _lang,
            "job_title_short": job_title_short,
            "job_title_slug": job_title_slug,
            "company_short": company_short,
            "contact_person": contact_person,
            "company_address": company_address,
            "reference_code": extraction.application.reference_code or "",
            "source_url": url or extraction.source_url or str(from_file or from_extraction),
            "folder_name": folder_name,
        },
    )

    typer.echo("[4/4] Moving crawled files + updating manifest ...")
    data_dir = settings.base_path / folder_name / "data"
    if url:
        (tmp_data / "job-post-raw.html").rename(data_dir / "job-post-raw.html")
        (tmp_data / "job-post-raw.md").rename(data_dir / "job-post-raw.md")
        tmp_data.rmdir()
    if from_file:
        shutil.copy(from_file, data_dir / from_file.name)
    # Save extraction.yaml directly into the scaffolded folder
    save_extraction(extraction, data_dir / "extraction.yaml")

    state = ApplicationState(
        id=app_id,
        folder_name=folder_name,
        status=ApplicationStatus.DRAFT,
        source_url=url,
        language=_lang,
        company_short=company_short,
        job_title_short=job_title_short,
        app_name="Bewerbung" if _lang == "de" else "Application",
        letter_name="Anschreiben" if _lang == "de" else "Cover-Letter",
        resume_name="Lebenslauf" if _lang == "de" else "Resume",
        attach_name="Anlagen" if _lang == "de" else "Attachments",
        extraction_path=Path(folder_name) / "data" / "extraction.yaml",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    append_application(state, settings.manifest_path)
    typer.secho(f"\nCreated: {folder_name}", fg=typer.colors.GREEN)


def _read_as_markdown(file: str | Path) -> str:
    content = file.read_text(encoding="utf-8")
    if file.suffix.lower() in (".html", ".htm"):
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = True
        converter.ignore_tables = False
        converter.body_width = 0  # no line wrapping
        return converter.handle(content)
    return content
