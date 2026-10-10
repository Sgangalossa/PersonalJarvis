"""MacAgentBench CLI bundle assembly."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from jarvis.cu.macos_bench import macagentbench_scenarios
from jarvis.cu.macos_qualification import build_macos_receipt_scenario_template
from scripts import macos_agent_bench_qualify as cli


@pytest.mark.asyncio
async def test_assemble_requires_one_passing_envelope_per_scenario(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    def passing_result(scenario_id: str, _envelope: object) -> SimpleNamespace:
        return SimpleNamespace(
            scenario_id=scenario_id,
            receipt_valid=True,
            evaluation=SimpleNamespace(passed=True, failures=()),
        )

    monkeypatch.setattr(cli, "evaluate_macos_receipt_envelope", passing_result)
    for scenario in macagentbench_scenarios():
        envelope = build_macos_receipt_scenario_template(scenario.id)
        (tmp_path / f"{scenario.id}.json").write_text(
            json.dumps(envelope), encoding="utf-8"
        )

    assert await cli._run_assemble(tmp_path, pretty=False) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["receipt_contract_id"] == cli.macos_receipt_contract_id()
    assert set(payload["receipts"]) == {
        scenario.id for scenario in macagentbench_scenarios()
    }


@pytest.mark.asyncio
async def test_assemble_rejects_an_incomplete_receipt_set(tmp_path, capsys) -> None:
    scenario = macagentbench_scenarios()[0]
    envelope = build_macos_receipt_scenario_template(scenario.id)
    (tmp_path / f"{scenario.id}.json").write_text(
        json.dumps(envelope), encoding="utf-8"
    )

    assert await cli._run_assemble(tmp_path, pretty=False) == 1
    payload = json.loads(capsys.readouterr().out)
    assert "did not pass" in payload["error"]


@pytest.mark.asyncio
async def test_assemble_rejects_duplicate_scenario_envelopes(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    scenario = macagentbench_scenarios()[0]
    envelope = build_macos_receipt_scenario_template(scenario.id)

    def passing_result(scenario_id: str, _envelope: object) -> SimpleNamespace:
        return SimpleNamespace(
            scenario_id=scenario_id,
            receipt_valid=True,
            evaluation=SimpleNamespace(passed=True, failures=()),
        )

    monkeypatch.setattr(cli, "evaluate_macos_receipt_envelope", passing_result)
    for name in ("one.json", "two.json"):
        (tmp_path / name).write_text(json.dumps(envelope), encoding="utf-8")

    assert await cli._run_assemble(tmp_path, pretty=False) == 2
    assert "duplicate receipt scenario" in json.loads(capsys.readouterr().out)["error"]



def test_init_capture_creates_one_bound_envelope_per_scenario(
    tmp_path, capsys
) -> None:
    receipts_dir = tmp_path / "receipts"

    assert cli._run_init_capture(receipts_dir, pretty=False) == 0

    scenarios = macagentbench_scenarios()
    expected_names = sorted(f"{scenario.id}.json" for scenario in scenarios)
    assert sorted(path.name for path in receipts_dir.iterdir()) == expected_names
    for scenario in scenarios:
        envelope = json.loads(
            (receipts_dir / f"{scenario.id}.json").read_text(encoding="utf-8")
        )
        assert envelope["receipt_contract_id"] == cli.macos_receipt_contract_id()
        assert envelope["scenario_id"] == scenario.id

    payload = json.loads(capsys.readouterr().out)
    assert payload["receipt_contract_id"] == cli.macos_receipt_contract_id()
    assert sorted(payload["receipt_files"]) == expected_names
    assert payload["native_qualification_complete"] is False


def test_init_capture_refuses_to_overwrite_existing_directory(
    tmp_path, capsys
) -> None:
    receipts_dir = tmp_path / "receipts"
    receipts_dir.mkdir()
    sentinel = receipts_dir / "keep.txt"
    sentinel.write_text("original", encoding="utf-8")

    assert cli._run_init_capture(receipts_dir, pretty=False) == 2

    assert sentinel.read_text(encoding="utf-8") == "original"
    assert list(receipts_dir.iterdir()) == [sentinel]
    assert "refusing to overwrite" in json.loads(capsys.readouterr().out)["error"]
