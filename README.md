# jobtools

Personal CLI for end-to-end job application management.  
Crawl → Extract → Tailor → Compile → Track.

---

## Requirements

- Python 3.12+ (see [NOTES.md](NOTES.md))
- [`uv`](https://docs.astral.sh/uv/)
- `lualatex` (e.g. via MacTeX / TeX Live)
- [`awesome-cv`](https://github.com/posquit0/Awesome-CV) — cloned locally
- Ollama or API access to an LLM (default: `devstral-small-2`)

---

## Installation

```bash
uv tool install git+https://github.com/philippesamuel/jobtools
jobtools --help
```

Install the cookiecutter template separately:

```bash
git clone https://github.com/philippesamuel/cookiecutter-jobapp ~/.config/jobtools/cookiecutter-jobapp
```

---

## Configuration

Copy `.env.example` to `.env` and adjust:

```bash
cp .env.example .env
```

All settings use the `JT_` prefix and can be overridden via env vars or `.env`:

| Variable | Default | Description |
|---|---|---|
| `JT_BASE_PATH` | `~/...GoogleDrive.../03_Bewerbungen` | Local GDrive folder |
| `JT_LLM_MODEL` | `ollama:devstral-small-2:24b-cloud` | pydantic-ai model string |
| `JT_AWESOME_CV_DIR` | `~/Developer/philippe-awesome-cv` | awesome-cv repo path |
| `JT_COOKIECUTTER_TEMPLATE` | `~/.config/jobtools/cookiecutter-jobapp` | Template path |
| `JT_REVIEW` | `true` | Open `$EDITOR` after LLM steps |
| `JT_GIT_INIT` | `true` | `git init` on scaffold |
| `JT_ATTACHMENTS` | *(4 Zeugnisse)* | JSON dict of attachment symlinks |

---

## Commands

### `jt init <url>`

Scaffold a new application from a job posting URL.

```bash
jt init https://stepstone.de/job/123
jt init https://stepstone.de/job/123 --no-review
```

**Flow:**

1. Crawl URL → `job-post-raw.html` + `job-post-raw.md`
2. LLM parses company, title, language
3. Optional `$EDITOR` review of parsed metadata
4. cookiecutter scaffolds folder + `git init` + symlinks
5. Manifest entry written to `manifest.yaml`

**Output folder:**

```
0001.BASF_DataEngineer/
├── main.tex
├── assets -> ~/Developer/awesome-cv/assets
├── awesome-cv.cls -> ~/Developer/awesome-cv/awesome-cv.cls
├── attachments/
│   ├── attachments.tex
│   └── *.pdf -> (symlinks to Zeugnisse)
├── coverletter/
│   ├── coverletter.tex
│   └── coverletter-body.tex
├── resume/
│   ├── de/
│   │   ├── summary.tex
│   │   ├── experience.tex
│   │   ├── skills.tex
│   │   ├── education.tex
│   │   └── honors.tex
│   └── resume.tex
└── data/
    ├── job-post-raw.html
    ├── job-post-raw.md
    └── extraction.yaml
```

---

### `jt extract <id>`

Extract structured data from `job-post-raw.md` → `data/extraction.yaml`.

```bash
jt extract 1
jt extract 1 --review
jt extract 1 --dry-run
```

---

### `jt tailor <id>`

Generate tailored LaTeX drafts from base templates + extraction data.

```bash
jt tailor 1
jt tailor 1 --reference 3     # use folder 0003 as base templates
jt tailor 1 --review
jt tailor 1 --dry-run
```

Modifies: `coverletter-body.tex`, `summary.tex`, `experience.tex`, `skills.tex` (if needed).  
Never modifies: `education.tex`, `honors.tex`.

---

### `jt compile <id>`

Compile all documents via lualatex → `build/`.

```bash
jt compile 1
jt compile 1 --no-clean       # keep aux files for debugging
```

**Output:**

```
build/
├── Bewerbung_BASF.pdf
├── Anschreiben_BASF.pdf
├── Lebenslauf_BASF.pdf
└── Bewerbung_Anlagen_BASF.pdf
```

---

### `jt status <id> <status>`

```bash
jt status 1 submitted
jt status 1 interview
```

Valid values: `draft` · `submitted` · `interview` · `offer` · `rejected` · `withdrawn`

---

### `jt list`

```bash
jt list
jt list --status interview
```

---

### `jt open <id>`

Open application folder in Finder (macOS) / file manager (Linux).

```bash
jt open 1
```

---

## Typical workflow

```bash
jt init https://company.com/jobs/123
jt extract 1
jt tailor 1 --reference 3
jt compile 1
jt status 1 submitted
```

---

## Project structure

```
jobtools/
├── src/jobtools/
│   ├── settings.py       # pydantic-settings, JT_ prefix
│   ├── models.py         # all Pydantic models
│   ├── prompts.py        # LLM system prompts
│   ├── crawler.py        # Playwright page fetch
│   ├── parser.py         # LLM meta parse (company/title/lang)
│   ├── manifest.py       # manifest.yaml load/save
│   ├── extractor.py      # LLM extraction + editor review
│   ├── tailor.py         # LLM tailoring
│   ├── compiler.py       # lualatex compile
│   └── cli.py            # typer app
└── tests/
```
