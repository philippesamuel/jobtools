# Notes

Technical decisions, known issues, and workarounds.

---

## Known Issues

### cookiecutter + chardet 7.x (`NameError: unicode`)

**Symptom:**
```
NameError: name 'unicode' is not defined
```
in `binaryornot/helpers.py` during `jt init`.

**Root cause:**
`binaryornot 0.4.4` (last released 2017, a transitive cookiecutter dependency) was
written against `chardet 3.x` behaviour where `detect()` always returned a string
encoding. In `chardet 7.x`, `detect()` can return `None` for both encoding and
confidence when fed unrecognisable binary data. `binaryornot` has no guard against
`None`, and its Python 2 fallback (`unicode()`) is dead code on Python 3.

**Fix:**
1. Pin `chardet<7` in `pyproject.toml`
2. Add `_copy_without_render` to `cookiecutter.json` for any binary files in the template

**Track upstream:** https://github.com/cookiecutter/cookiecutter/issues/2197

---

### Python version

Requires Python **3.12+**.

---

## Design Decisions

### `ruamel.yaml` over `pyyaml`
`ruamel.yaml` preserves unicode, key order, and formatting on round-trips.
`pyyaml` was used in the original `generate_data.py` script — replaced during
integration into `jobtools`.

### Single `manifest.yaml` at `BASE_PATH` root
Flat list of `ApplicationState` entries. Easier to query than per-job state files.
No file locking — concurrent `jt` invocations could corrupt it. Acceptable for
personal single-user use. Document if this ever becomes shared.

### `review_in_editor` as a generic
All LLM output passes through a shared `review_in_editor(obj: T) -> T` in
`extractor.py`. Works for any `BaseModel` subclass — currently used for
`ParsedMeta` (in `init`) and `ExtractionResult` / `TailoringResult`.
Controlled via `JT_REVIEW` env var or `--review/--no-review` per command.

### `education.tex` / `honors.tex` not tailored
These files change rarely enough that automating them adds noise without value.
`jt tailor` only modifies `coverletter-body.tex`, `summary.tex`, `experience.tex`,
and optionally `skills.tex`.

### lualatex `--jobname` for PDF naming
PDF files are named via lualatex's `--jobname` flag rather than post-compile rename.
Names are derived from `ApplicationState.pdf_names` (stored in manifest at `init` time),
which mirrors the language-conditional naming from `cookiecutter.json`.

### `_slugify` unicode handling
`parser.py` uses `unicodedata.normalize("NFKD")` + ASCII encoding to transliterate
German umlauts and other non-ASCII characters into filesystem-safe slugs.
`Müller & Söhne` → `Muller_Sohne`. Runs as a Pydantic field validator on `ParsedMeta`.

### Tests — monkey patching (known smell)
The current `test_init.py` uses `unittest.mock.patch` to stub external dependencies.
This works but indicates tight coupling in `cli.py`. A service layer with
`Protocol`-based dependency injection is planned (see ROADMAP.md) to replace
patching with proper fakes.