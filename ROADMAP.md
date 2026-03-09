# Roadmap

## Done

- `jt init` — crawl URL → LLM parse → cookiecutter scaffold → git init → manifest
- `jt extract` — JD md → structured `extraction.yaml` via LLM
- `jt tailor` — extraction + base tex → tailored tex via LLM (`--reference <id>`)
- `jt compile` — lualatex → 4 PDFs in `build/`
- `jt status` / `jt list` — manifest lifecycle tracking
- `jt open` — open folder in Finder/file manager
- `$EDITOR` review loop — generic, works for any Pydantic model
- Settings — pydantic-settings, `JT_` env prefix, `.env` support
- cookiecutter template — full folder structure, symlinks, git hook, language pruning

---

## Near-term

### Dependency injection refactor
The current test suite relies on `unittest.mock` patching — a code smell indicating
tight coupling between `cli.py` and concrete implementations. Introduce a service layer
with `Protocol`-based dependencies so tests use real fakes, not mocks.
See discussion in code review notes.

### `jt tailor --reference` similarity suggestion
Currently `--reference` requires manually knowing a good previous application ID.
`ExtractionResult` already contains `ats_keywords`, `company.sector`, `job_tasks` —
enough signal for cosine similarity (e.g. via `sentence-transformers` or simple TF-IDF)
to auto-suggest the most similar previous application as reference.

### Huntr.co bridge
Two possible flows:
- `jt init --huntr <huntr-job-url>` — crawl Huntr job page instead of raw URL
- Chrome extension clip → `jt init` picks up from Huntr API

### `jt status` — richer tracking
Add `applied_at`, `contact`, `portal_url` to `ApplicationState`.
Allow `jt status 1 submitted --note "sent via Workday"`.

---

## Later / maybe

- `jt archive <id>` — mark as closed, move folder to archive subfolder
- `jt stats` — summary: applications per month, sector breakdown, conversion rates
- Web UI — simple read-only dashboard over `manifest.yaml`
- Multi-profile support — `APPLICANT_PROFILE` currently hardcoded in `prompts.py`

