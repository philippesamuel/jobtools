from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import typer
from pydantic import ValidationError
from pydantic_ai import Agent
from ruamel.yaml import YAML

from jobtools.models import ExtractionResult
from jobtools.prompts import EXTRACTION_SYSTEM_PROMPT
from jobtools.settings import settings

_yaml = YAML()
_yaml.default_flow_style = False
_yaml.allow_unicode = True
_yaml.preserve_quotes = True


# ── Core extraction ───────────────────────────────────────────────────────────

async def run_extraction(jd_text: str) -> ExtractionResult:
    agent: Agent[None, ExtractionResult] = Agent(
        model=settings.llm_model,
        output_type=ExtractionResult,
        system_prompt=EXTRACTION_SYSTEM_PROMPT,
    )
    result = await agent.run(jd_text)
    return result.output


# ── Editor review ─────────────────────────────────────────────────────────────

def open_in_editor(yaml_str: str) -> str:
    """Write yaml_str to a temp file, open $EDITOR, return edited content."""
    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "vim"))
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix="jd_extract_", encoding="utf-8", delete=False
    ) as f:
        f.write(yaml_str)
        tmp_path = Path(f.name)

    typer.secho(f"\n-> Opening {tmp_path} in '{editor}' for review...", fg=typer.colors.CYAN)
    typer.secho("   Save and quit when done.", fg=typer.colors.CYAN)
    subprocess.run([editor, str(tmp_path)], check=True)

    edited = tmp_path.read_text(encoding="utf-8")
    tmp_path.unlink()
    return edited


def validate_edited_yaml(edited: str) -> ExtractionResult:
    """Parse edited YAML and validate against ExtractionResult. Re-prompts on error."""
    while True:
        try:
            import io
            data = _yaml.load(io.StringIO(edited))
            return ExtractionResult.model_validate(data)
        except (ValueError, ValidationError) as e:
            typer.secho(f"\nValidation error:\n{e}", fg=typer.colors.RED)
            if not typer.confirm("Re-open editor to fix?", default=True):
                raise typer.Exit(1)
            edited = open_in_editor(edited)


# ── Serialisation ─────────────────────────────────────────────────────────────

def result_to_yaml_str(result: ExtractionResult) -> str:
    import io
    buf = io.StringIO()
    _yaml.dump(result.model_dump(mode="json"), buf)
    return buf.getvalue()


# ── Save ──────────────────────────────────────────────────────────────────────

def save_extraction(result: ExtractionResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = result_to_yaml_str(result)
    output_path.write_text(yaml_str, encoding="utf-8")