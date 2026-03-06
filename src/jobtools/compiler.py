from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import typer

_AUX_EXTENSIONS = {".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk", ".synctex.gz"}

BUILD_DIR = "build"


def find_master_tex(app_dir: Path) -> Path:
    """Find the master .tex file (top-level, not in subdirs)."""
    candidates = list(app_dir.glob("*.tex"))
    if not candidates:
        raise FileNotFoundError(f"No .tex file found in {app_dir}")
    if len(candidates) > 1:
        # Prefer file matching Bewerbung_* or Application_*
        for prefix in ("Bewerbung_", "Application_"):
            match = [f for f in candidates if f.name.startswith(prefix)]
            if match:
                return match[0]
    return candidates[0]


def compile_pdf(app_dir: Path, clean: bool = True) -> Path:
    """
    Run lualatex twice on the master .tex file.
    Output PDF lands in app_dir/build/.
    Returns path to the generated PDF.
    """
    master_tex = find_master_tex(app_dir)
    build_dir = app_dir / BUILD_DIR
    build_dir.mkdir(exist_ok=True)

    cmd = [
        "lualatex",
        "--interaction=nonstopmode",
        f"--output-directory={build_dir}",
        str(master_tex),
    ]

    typer.echo(f"   lualatex pass 1/2 ...")
    result1 = subprocess.run(cmd, cwd=app_dir, capture_output=True, text=True)
    if result1.returncode != 0:
        _print_lualatex_error(result1.stdout)
        raise RuntimeError("lualatex pass 1 failed")

    typer.echo(f"   lualatex pass 2/2 ...")
    result2 = subprocess.run(cmd, cwd=app_dir, capture_output=True, text=True)
    if result2.returncode != 0:
        _print_lualatex_error(result2.stdout)
        raise RuntimeError("lualatex pass 2 failed")

    pdf_path = build_dir / master_tex.with_suffix(".pdf").name
    if not pdf_path.exists():
        raise FileNotFoundError(f"Expected PDF not found: {pdf_path}")

    if clean:
        _cleanup_aux(build_dir)

    return pdf_path


def _cleanup_aux(build_dir: Path) -> None:
    removed = []
    for f in build_dir.iterdir():
        if f.suffix in _AUX_EXTENSIONS:
            f.unlink()
            removed.append(f.name)
    if removed:
        typer.echo(f"   cleaned: {', '.join(removed)}")


def _print_lualatex_error(stdout: str) -> None:
    # Surface the first error line from lualatex output
    for line in stdout.splitlines():
        if line.startswith("!"):
            typer.secho(f"   {line}", fg=typer.colors.RED)