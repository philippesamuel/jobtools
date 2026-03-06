from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent

from jobtools.settings import settings


class ParsedMeta(BaseModel):
    """Minimal metadata needed to scaffold the folder — parsed before full extraction."""
    company_short: str
    job_title_short: str
    language: str  # "de" | "en"


_SYSTEM = """\
Extract three fields from the job description:
- company_short: slug-safe short company name, CamelCase, no spaces (e.g. "BASF", "McKinsey")
- job_title_short: slug-safe short job title, CamelCase, no spaces (e.g. "DataEngineer", "Berater")
- language: "de" if the JD is primarily German, "en" if English

Return ONLY valid JSON matching the schema. No explanation.
"""


def _slugify(s: str) -> str:
    """Remove characters unsafe for folder names."""
    s = re.sub(r"[^\w\-]", "", s.replace(" ", "_"))
    return s


def parse_meta(md_path: Path) -> ParsedMeta:
    content = md_path.read_text(encoding="utf-8")
    # Truncate — we only need the first ~3000 chars for meta parsing
    snippet = content[:3000]

    agent: Agent[None, ParsedMeta] = Agent(
        model=settings.llm_model,
        system_prompt=_SYSTEM,
        result_type=ParsedMeta,
    )
    result = agent.run_sync(snippet)
    meta = result.data
    # Sanitize for filesystem
    meta.company_short = _slugify(meta.company_short)
    meta.job_title_short = _slugify(meta.job_title_short)
    return meta