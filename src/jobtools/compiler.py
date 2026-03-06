from __future__ import annotations

import subprocess
from pathlib import Path

import typer

_AUX_EXTENSIONS = {".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk", ".synctex.gz"}
BUILD_DIR = "build"

# Fixed tex locations relative to app_dir
_TEX_FILES: dict[str, str] = {
    "master":      "main.tex",
    "coverletter": "coverletter/coverletter.tex",
    "resume":      "resume/resume.tex",
    "attachments": "attachments/attachments.tex",
}


def compile_pdf(
    app_dir: Path,
    pdf_names: dict[str, str],
    clean: bool = True,
) -> dict[str, Path]:
    """
    Compile all 4 tex documents via lualatex (2 passes each).
    pdf_names: {role: jobname} — comes from ApplicationState.pdf_names.
    Returns {role: pdf_path}.
    """
    build_dir = app_dir / BUILD_DIR
    build_dir.mkdir(exist_ok=True)

    compiled: dict[str, Path] = {}
    for role, rel_tex in _TEX_FILES.items():
        tex_path = app_dir / rel_tex
        if not tex_path.exists():
            typer.secho(f"   [skip] {rel_tex} not found", fg=typer.colors.YELLOW)
            continue

        jobname = pdf_names[role]
        typer.echo(f"   [{role}] {rel_tex} -> {jobname}.pdf")
        _run_lualatex(tex_path, build_dir, jobname, passes=2)

        pdf_path = build_dir / f"{jobname}.pdf"
        if not pdf_path.exists():
            raise FileNotFoundError(f"Expected PDF not found: {pdf_path}")
        compiled[role] = pdf_path

    if clean:
        _cleanup_aux(build_dir)

    return compiled


def _run_lualatex(
    tex_path: Path,
    build_dir: Path,
    jobname: str,
    passes: int = 2,
) -> None:
    cmd = [
        "lualatex",
        "--interaction=nonstopmode",
        f"--output-directory={build_dir}",
        f"--jobname={jobname}",
        str(tex_path),
    ]
    for i in range(1, passes + 1):
        typer.echo(f"      pass {i}/{passes} ...")
        result = subprocess.run(cmd, cwd=tex_path.parent, capture_output=True, text=True)
        if result.returncode != 0:
            for line in result.stdout.splitlines():
                if line.startswith("!"):
                    typer.secho(f"      {line}", fg=typer.colors.RED)
            raise RuntimeError(f"lualatex failed on {tex_path.name} pass {i}")


def _cleanup_aux(build_dir: Path) -> None:
    removed = [f.name for f in build_dir.iterdir() if f.suffix in _AUX_EXTENSIONS]
    for name in removed:
        (build_dir / name).unlink()
    if removed:
        typer.echo(f"   cleaned: {', '.join(removed)}")