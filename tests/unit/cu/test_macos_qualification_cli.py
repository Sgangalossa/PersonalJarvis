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
