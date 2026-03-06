from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class CompanySector(StrEnum):
    ENERGY = "energy"
    CHEMICAL = "chemical"
    INDUSTRIAL = "industrial"
    PROCESS = "process"
    DATA_ENG = "data-eng"
    DATA = "data"
    SOFTWARE = "software"
    ACADEMIC = "academic"
    RESEARCH = "research"
    OTHER = "other"


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


# ---------------------------------------------------------------------------
# Extraction sub-models
# ---------------------------------------------------------------------------
class JobTitle(BaseModel):
    full: str = Field(description="Exact job title from the ad, including gender suffix if present.")
    short: str = Field(description="Natural shortened form, e.g. 'Berater für Datenintegration'.")


class WorkModel(BaseModel):
    remote: bool = Field(default=False, description="True if Remote / Home Office explicitly mentioned.")
    hybrid: bool = Field(default=False, description="True if hybrid work model explicitly mentioned.")
    flexible: bool = Field(default=False, description="True if flexible working hours explicitly mentioned.")


class CandidateProfile(BaseModel):
    required: list[str] = Field(default_factory=list, description="Hard requirements from the 'Profil' section.")
    nice_to_have: list[str] = Field(default_factory=list, description="Preferred / soft requirements.")


class CompanyInfo(BaseModel):
    name_full: str = Field(description="Full legal company name.")
    name_short: str = Field(description="Common short name.")
    sector: CompanySector = Field(description="Industry sector of the company.")
    address: Optional[str] = Field(default=None, description="Full address if present in the JD.")
    contact_person: Optional[str] = Field(default=None, description="Named recruiter / contact person if mentioned.")
    culture_signals: list[str] = Field(default_factory=list, description="Phrases signalling company culture.")


class ApplicationInfo(BaseModel):
    method: str = Field(default="Webformular", description="How to apply: Webformular, E-Mail, etc.")
    requirements: list[str] = Field(default_factory=list, description="File format, size limits, etc.")
    reference_code: str = Field(default="", description="Job reference code if present.")
    deadline: Optional[str] = Field(default=None)
    salary: Optional[str] = Field(default=None, description="Salary band / Entgeltgruppe if mentioned.")


# ---------------------------------------------------------------------------
# ExtractionResult  (Step 1 — pure facts, no generated text)
# ---------------------------------------------------------------------------
class ExtractionResult(BaseModel):
    """Pure facts extracted from the job description. No generated text."""

    # provenance
    source_url: str = Field(description="URL the JD was scraped from.")
    scraped_at: datetime = Field(description="When the page was fetched.")
    language: Literal["de", "en"] = Field(description="Language of the job description.")

    # content
    job_title: JobTitle
    company: CompanyInfo
    work_model: WorkModel
    job_tasks: list[str] = Field(
        description=(
            "Tasks from the 'Aufgaben' section. "
            "Plain German infinitive form, verb at end. "
            "GOOD: 'Anforderungen analysieren'. BAD: 'Analyse der Anforderungen'."
        )
    )
    candidate_profile: CandidateProfile
    ats_keywords: list[str] = Field(
        description="ATS-relevant keywords in original JD phrasing."
    )
    application: ApplicationInfo

    model_config = {"title": "ExtractionResult"}


# ---------------------------------------------------------------------------
# Cookiecutter context  (variables passed to template)
# ---------------------------------------------------------------------------
class CookiecutterContext(BaseModel):
    app_id: int = Field(description="Auto-incremented application ID.")
    company_short: str = Field(description="Slug-safe short company name.")
    job_title_short: str = Field(description="Slug-safe short job title.")
    language: Literal["de", "en"]
    source_url: str


# ---------------------------------------------------------------------------
# ApplicationState  (manifest entry)
# ---------------------------------------------------------------------------
class ApplicationState(BaseModel):
    id: int
    folder_name: str = Field(description="Relative folder name under BASE_PATH, e.g. '0001.BASF_Data-Engineer'.")
    status: ApplicationStatus = ApplicationStatus.DRAFT
    source_url: Optional[str]
    language: Literal["de", "en"]
    company_short: str
    job_title_short: str
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    extraction_path: Optional[Path] = Field(
        default=None,
        description="Relative path from BASE_PATH to extraction.yaml.",
    )


# ---------------------------------------------------------------------------
# TailoringResult  (Step 2 — generated tex content)
# ---------------------------------------------------------------------------


class TailoringResult(BaseModel):
    """
    Step 2 output — surgically tailored tex snippets.
    Each field is the full content of the corresponding .tex file.
    """
    coverletter_body: str = Field(description="Full content of coverletter-body.tex")
    summary: str = Field(description="Full content of summary.tex")
    experience: str = Field(description="Full content of experience.tex")
    skills: Optional[str] = Field(
        default=None,
        description="Full content of skills.tex. None if unchanged."
    )



# ---------------------------------------------------------------------------
# Manifest  (root of manifest.yaml)
# ---------------------------------------------------------------------------
class Manifest(BaseModel):
    applications: list[ApplicationState] = Field(default_factory=list)

    def next_id(self) -> int:
        if not self.applications:
            return 1
        return max(a.id for a in self.applications) + 1

    def get(self, app_id: int) -> Optional[ApplicationState]:
        return next((a for a in self.applications if a.id == app_id), None)
    