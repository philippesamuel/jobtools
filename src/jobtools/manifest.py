from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from jobtools.models import ApplicationState, Manifest

_yaml = YAML()
_yaml.default_flow_style = False
_yaml.preserve_quotes = True


def load_manifest(path: Path) -> Manifest:
    if not path.exists():
        return Manifest()
    with path.open("r", encoding="utf-8") as fh:
        raw = _yaml.load(fh) or {}
    return Manifest.model_validate(raw)


def save_manifest(manifest: Manifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        _yaml.dump(manifest.model_dump(mode="json"), fh)


def append_application(state: ApplicationState, manifest_path: Path) -> None:
    manifest = load_manifest(manifest_path)
    # Replace if id already exists (idempotent re-init)
    manifest.applications = [
        a for a in manifest.applications if a.id != state.id
    ]
    manifest.applications.append(state)
    manifest.applications.sort(key=lambda a: a.id)
    save_manifest(manifest, manifest_path)