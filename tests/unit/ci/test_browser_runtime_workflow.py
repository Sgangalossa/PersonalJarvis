"""Contracts for dependency-aware browser runner selection."""

from pathlib import Path

import yaml


def test_windows_arm_browser_waits_for_reviewed_native_crypto() -> None:
    root = Path(__file__).resolve().parents[3]
    workflow = yaml.safe_load(
        (root / ".github/workflows/browser-runtime.yml").read_text(encoding="utf-8")
    )

    selector = workflow["jobs"]["select-matrix"]
    select_step = next(step for step in selector["steps"] if step.get("id") == "select")
    script = select_step["run"]
    assert "check_native_crypto_publication.py" in script
    assert 'portable=\'["ubuntu-latest"' in script
    assert 'complete=\'["ubuntu-latest"' in script
    assert "windows-11-arm" not in script.split("complete=", 1)[0]
    assert "workflow_dispatch" in script
    assert "exit 1" in script

    browser = workflow["jobs"]["browser"]
    assert browser["needs"] == "select-matrix"
    assert browser["strategy"]["matrix"]["os"] == (
        "${{ fromJSON(needs.select-matrix.outputs.os) }}"
    )
