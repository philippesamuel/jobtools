import typer

app = typer.Typer(name="jt", help="Job application CLI.")


@app.command()
def init(url: str = typer.Argument(..., help="Job posting URL.")) -> None:
    """Scaffold a new application from a URL."""
    raise NotImplementedError


@app.command()
def extract(app_id: int = typer.Argument(..., help="Application ID.")) -> None:
    """Extract structured data from job-post-raw.md."""
    raise NotImplementedError


@app.command()
def tailor(app_id: int = typer.Argument(..., help="Application ID.")) -> None:
    """Generate draft .tex files via LLM."""
    raise NotImplementedError


@app.command()
def compile(app_id: int = typer.Argument(..., help="Application ID.")) -> None:
    """Compile lualatex → PDF bundle."""
    raise NotImplementedError


@app.command()
def status(
    app_id: int = typer.Argument(..., help="Application ID."),
    new_status: str = typer.Argument(..., help="New status value."),
) -> None:
    """Update application status in manifest."""
    raise NotImplementedError


@app.command(name="list")
def list_apps() -> None:
    """List all applications from manifest."""
    raise NotImplementedError


if __name__ == "__main__":
    app()