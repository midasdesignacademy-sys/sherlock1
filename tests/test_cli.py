"""
CLI tests for SHERLOCK (Fase 1): investigate, health, clear.
"""

import pytest
from pathlib import Path
from typer.testing import CliRunner

from main import app

runner = CliRunner()


def test_cli_health():
    """Health command runs (may fail if Neo4j/spaCy not available)."""
    result = runner.invoke(app, ["health"])
    assert result.exit_code in (0, 1)
    assert "SHERLOCK" in result.output or "Health" in result.output or "spaCy" in result.output


def test_cli_investigate_no_dir():
    """Investigate with non-existent dir exits with error."""
    result = runner.invoke(app, ["investigate", "--docs", "/nonexistent/path/xyz"])
    assert result.exit_code != 0


def test_cli_investigate_empty_dir(tmp_path):
    """Investigate with empty dir exits without running pipeline."""
    result = runner.invoke(app, ["investigate", "--docs", str(tmp_path)])
    assert result.exit_code == 0
    assert "No files" in result.output or "SHERLOCK" in result.output
