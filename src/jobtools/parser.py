from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator
from pydantic_ai import Agent

from jobtools.settings import settings


class ParsedMeta(BaseModel):
    """Minimal metadata needed to scaffold the folder — parsed before full extraction."""
    company_short: str
    job_title_short: str
    language: Literal["de", "en"]

    @field_validator("company_short", "job_title_short", mode="after")
    @classmethod
    def slugify(cls, v: str) -> str:
        return _slugify(v)


_SYSTEM = """\
Extract three fields from the job description:
- company_short: short company name, CamelCase, no spaces (e.g. "BASF", "McKinsey", "StromnetzBerlin")
- job_title_short: short job title, CamelCase, no spaces (e.g. "DataEngineer", "TechAnalyst", "Berater")
- language: "de" if the JD is primarily German, "en" if English

Return ONLY valid JSON matching the schema. No explanation.
"""


def _slugify(s: str) -> str:
    """
    Filesystem-safe slug:
    1. Unicode normalize to NFKD, encode to ASCII (drops umlauts accents etc.)
    2. Replace remaining non-alphanumeric chars with nothing
    3. Collapse multiple underscores/dashes
    """
    # NFKD + ASCII transliteration (Müller → Muller, Ü → U)
    normalized = unicodedata.normalize("NFKD", s)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    # Strip anything that isn't alphanumeric, dash, or underscore
    cleaned = re.sub(r"[^\w\-]", "", ascii_str)
    # Collapse runs of _ or -
    cleaned = re.sub(r"[-_]{2,}", "_", cleaned)
    return cleaned.strip("_-")


def parse_meta(md_path: Path) -> ParsedMeta:
    content = md_path.read_text(encoding="utf-8")
    # Truncate — we only need the first ~3000 chars for meta parsing
    snippet = content[:3000]

    agent: Agent[None, ParsedMeta] = Agent(
        model=settings.llm_model,
        system_prompt=_SYSTEM,
        output_type=ParsedMeta,
    )
    result = agent.run_sync(snippet)
    return result.output