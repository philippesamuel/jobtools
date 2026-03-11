"""
Smoke tests — verify CLI wiring only.
No external calls, no LLM, no filesystem side effects.
Survive the cli.py → cli/ refactor unchanged.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from jobtools.cli import app

runner = CliRunner()


def invoke(*args: str):
    return runner.invoke(app, list(args))


# ── top-level ─────────────────────────────────────────────────────────────────

def test_help():
    r = invoke("--help")
    assert r.exit_code == 0
    assert "Usage" in r.output


# ── commands ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cmd", [
    ["init", "--help"],
    ["extract", "--help"],
    ["tailor", "--help"],
    ["compile", "--help"],
    ["status", "--help"],
    ["list", "--help"],
    ["open", "--help"],
    ["config", "show", "--help"],
    ["config", "get", "--help"],
])
def test_command_help(cmd):
    r = invoke(*cmd)
    assert r.exit_code == 0, f"`jt {' '.join(cmd)}` failed:\n{r.output}"


# ── config get — unknown key ──────────────────────────────────────────────────

def test_config_get_unknown_key():
    r = invoke("config", "get", "nonexistent_key")
    assert r.exit_code != 0