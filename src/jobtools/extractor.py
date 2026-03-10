from __future__ import annotations

import io
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TypeVar

import typer
from pydantic import BaseModel, ValidationError
from pydantic_ai import Agent
from ruamel.yaml import YAML

from jobtools.models import ExtractionResult
from jobtools.prompts import EXTRACTION_SYSTEM_PROMPT
from jobtools.settings import settings

_yaml = YAML()
_yaml.default_flow_style = False
_yaml.allow_unicode = True
_yaml.preserve_quotes = True

T = TypeVar("T", bound=BaseModel)


# ── Core extraction ───────────────────────────────────────────────────────────

async def run_extraction(jd_text: str) -> ExtractionResult:
    agent: Agent[None, ExtractionResult] = Agent(
        model=settings.llm_model,
        output_type=ExtractionResult,
        system_prompt=EXTRACTION_SYSTEM_PROMPT,
    )
    result = await agent.run(jd_text)
    return result.output


# ── Editor review (generic) ───────────────────────────────────────────────────

def _model_to_yaml_str(obj: BaseModel) -> str:
    buf = io.StringIO()
    _yaml.dump(obj.model_dump(mode="json"), buf)
    return buf.getvalue()


def _open_in_editor(yaml_str: str) -> str:
    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "vim"))
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix="jt_review_", encoding="utf-8", delete=False
    ) as f:
        f.write(yaml_str)
        tmp_path = Path(f.name)

    typer.secho(f"\n-> Opening {tmp_path} in '{editor}' for review...", fg=typer.colors.CYAN)
    typer.secho("   Save and quit when done.", fg=typer.colors.CYAN)
    subprocess.run([editor, str(tmp_path)], check=True)

    edited = tmp_path.read_text(encoding="utf-8")
    tmp_path.unlink()
    return edited


def review_in_editor(obj: T) -> T:
    """
    Serialize *obj* to YAML, open $EDITOR, deserialize and validate back.
    Re-prompts on validation error. Returns the (possibly edited) model instance.
    Works with any Pydantic BaseModel subclass.
    """
    model_cls = type(obj)
    yaml_str = _model_to_yaml_str(obj)

    while True:
        yaml_str = _open_in_editor(yaml_str)
        try:
            data = _yaml.load(io.StringIO(yaml_str))
            result = model_cls.model_validate(data)
            typer.secho("   Validated.", fg=typer.colors.GREEN)
            return result
        except (ValueError, ValidationError) as e:
            typer.secho(f"\nValidation error:\n{e}", fg=typer.colors.RED)
            if not typer.confirm("Re-open editor to fix?", default=True):
                raise typer.Exit(1)


# ── Serialisation / Save ──────────────────────────────────────────────────────

def save_extraction(result: ExtractionResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = _model_to_yaml_str(result)
    output_path.write_text(yaml_str, encoding="utf-8")
    

def load_extraction(path: Path) -> ExtractionResult:
    data = _yaml.load(path.read_text(encoding="utf-8"))
    return ExtractionResult.model_validate(data)
