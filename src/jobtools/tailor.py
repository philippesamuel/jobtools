from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent

from jobtools.models import ExtractionResult, TailoringResult
from jobtools.prompts import TAILORING_SYSTEM_PROMPT
from jobtools.settings import settings

# Files read as base context
_BASE_FILES = [
    "coverletter/coverletter-body.tex",
    "resume/{language}/summary.tex",
    "resume/{language}/experience.tex",
    "resume/{language}/skills.tex",
]


def load_base_templates(app_dir: Path, language: str) -> dict[str, str]:
    """Read base tex files from app_dir, return {filename: content}."""
    templates: dict[str, str] = {}
    for pattern in _BASE_FILES:
        rel = pattern.format(language=language)
        path = app_dir / rel
        if path.exists():
            templates[rel] = path.read_text(encoding="utf-8")
        else:
            templates[rel] = ""  # missing file — LLM will skip gracefully
    return templates


def _build_user_prompt(
    extraction: ExtractionResult,
    templates: dict[str, str],
) -> str:
    """Assemble the user message: extracted data + base templates."""
    parts = [
        "## Extracted Job Data\n",
        extraction.model_dump_json(indent=2),
        "\n\n## Base Templates\n",
    ]
    for filename, content in templates.items():
        parts.append(f"\n### {filename}\n```latex\n{content}\n```\n")
    return "\n".join(parts)


async def run_tailoring(
    extraction: ExtractionResult,
    app_dir: Path,
    language: str,
) -> TailoringResult:
    templates = load_base_templates(app_dir, language)
    user_prompt = _build_user_prompt(extraction, templates)

    agent: Agent[None, TailoringResult] = Agent(
        model=settings.llm_model,
        output_type=TailoringResult,
        system_prompt=TAILORING_SYSTEM_PROMPT,
    )
    result = await agent.run(user_prompt)
    return result.output


def save_tailored_files(
    result: TailoringResult,
    app_dir: Path,
    language: str,
) -> list[Path]:
    """Write tailored content back to the application folder. Returns written paths."""
    written: list[Path] = []

    mapping: list[tuple[str, str | None]] = [
        (f"coverletter/coverletter-body.tex", result.coverletter_body),
        (f"resume/{language}/summary.tex", result.summary),
        (f"resume/{language}/experience.tex", result.experience),
        (f"resume/{language}/skills.tex", result.skills),
    ]

    for rel_path, content in mapping:
        if content is None:
            continue
        path = app_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)

    return written