from __future__ import annotations

import subprocess
from pathlib import Path

import typer

_AUX_EXTENSIONS = {".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk", ".synctex.gz"}
BUILD_DIR = "build"

# Cookiecutter-derived name prefixes per document type
# Matches: {app_name}_{company}.tex, {letter_name}_{company}.tex, etc.
_DOC_PREFIXES = ("Bewerbung_", "Application_")
_LETTER_PREFIXES = ("Anschreiben_", "Cover-Letter_")
_RESUME_PREFIXES = ("Lebenslauf_", "Resume_")
_ATTACHMENTS_PREFIXES = ("Anlagen_", "Attachments_")

_ALL_PREFIXES = _DOC_PREFIXES + _LETTER_PREFIXES + _RESUME_PREFIXES + _ATTACHMENTS_PREFIXES


def find_tex_files(app_dir: Path) -> dict[str, Path]:
    """
    Find all top-level .tex files by their cookiecutter-derived prefix.
    Returns {role: path} where role in {master, coverletter, resume, attachments}.
    """
    found: dict[str, Path] = {}
    prefix_map = {
        "master": _DOC_PREFIXES,
        "coverletter": _LETTER_PREFIXES,
        "resume": _RESUME_PREFIXES,
        "attachments": _ATTACHMENTS_PREFIXES,
    }
    for tex in app_dir.glob("*.tex"):
        for role, prefixes in prefix_map.items():
            if any(tex.name.startswith(p) for p in prefixes):
                found[role] = tex
                break
    return found


def compile_pdf(app_dir: Path, clean: bool = True) -> dict[str, Path]:
    """
    Compile all top-level .tex files via lualatex (2 passes each).
    Returns {role: pdf_path} for all successfully compiled documents.
    """
    build_dir = app_dir / BUILD_DIR
    build_dir.mkdir(exist_ok=True)

    tex_files = find_tex_files(app_dir)
    if not tex_files:
        raise FileNotFoundError(f"No recognised .tex files found in {app_dir}")

    compiled: dict[str, Path] = {}
    for role, tex_path in tex_files.items():
        typer.echo(f"   [{role}] {tex_path.name}")
        _run_lualatex(tex_path, build_dir, passes=2)
        pdf = build_dir / tex_path.with_suffix(".pdf").name
        if not pdf.exists():
            raise FileNotFoundError(f"Expected PDF not found: {pdf}")
        compiled[role] = pdf

    if clean:
        _cleanup_aux(build_dir)

    return compiled


def _run_lualatex(tex_path: Path, build_dir: Path, passes: int = 2) -> None:
    cmd = [
        "lualatex",
        "--interaction=nonstopmode",
        f"--output-directory={build_dir}",
        str(tex_path),
    ]
    for i in range(1, passes + 1):
        typer.echo(f"      pass {i}/{passes} ...")
        result = subprocess.run(cmd, cwd=tex_path.parent, capture_output=True, text=True)
        if result.returncode != 0:
            for line in result.stdout.splitlines():
                if line.startswith("!"):
                    typer.secho(f"      {line}", fg=typer.colors.RED)
            raise RuntimeError(f"lualatex failed on {tex_path.name} (pass {i})")


def _cleanup_aux(build_dir: Path) -> None:
    removed = [f.name for f in build_dir.iterdir() if f.suffix in _AUX_EXTENSIONS]
    for name in removed:
        (build_dir / name).unlink()
    if removed:
        typer.echo(f"   cleaned: {', '.join(removed)}")