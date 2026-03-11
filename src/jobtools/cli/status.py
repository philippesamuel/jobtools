from datetime import datetime, timezone

import typer

from jobtools.manifest import load_manifest, save_manifest
from jobtools.models import ApplicationStatus
from jobtools.settings import settings


app = typer.Typer()


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
