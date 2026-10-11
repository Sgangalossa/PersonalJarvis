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


@pytest.mark.asyncio
async def test_capture_status_reports_all_placeholder_failures(
    tmp_path, capsys
) -> None:
    receipts_dir = tmp_path / "receipts"
    assert cli._run_init_capture(receipts_dir, pretty=False) == 0
    capsys.readouterr()

    assert await cli._run_capture_status(receipts_dir, pretty=False) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"] == {
        "passed": 0,
        "failed": len(macagentbench_scenarios()),
        "invalid": 0,
        "missing": 0,
    }
    assert payload["capture_complete"] is False
    assert payload["native_qualification_complete"] is False


@pytest.mark.asyncio
async def test_capture_status_reports_complete_passing_set(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    receipts_dir = tmp_path / "receipts"
    assert cli._run_init_capture(receipts_dir, pretty=False) == 0
    capsys.readouterr()

    def passing_result(scenario_id: str, _envelope: object) -> SimpleNamespace:
        return SimpleNamespace(
            scenario_id=scenario_id,
            receipt_valid=True,
            evaluation=SimpleNamespace(passed=True, failures=()),
        )

    monkeypatch.setattr(cli, "evaluate_macos_receipt_envelope", passing_result)

    assert await cli._run_capture_status(receipts_dir, pretty=False) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"]["passed"] == len(macagentbench_scenarios())
    assert payload["capture_complete"] is True
    assert payload["native_qualification_complete"] is False


@pytest.mark.asyncio
async def test_capture_status_collects_invalid_and_remaining_results(
    tmp_path, capsys
) -> None:
    receipts_dir = tmp_path / "receipts"
    assert cli._run_init_capture(receipts_dir, pretty=False) == 0
    capsys.readouterr()
    first = macagentbench_scenarios()[0]
    (receipts_dir / f"{first.id}.json").write_text("{", encoding="utf-8")

    assert await cli._run_capture_status(receipts_dir, pretty=False) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"]["missing"] == 1
    assert payload["counts"]["failed"] == len(macagentbench_scenarios()) - 1
    assert payload["file_issues"][0]["file"] == f"{first.id}.json"
    assert len(payload["scenarios"]) == len(macagentbench_scenarios())


@pytest.mark.asyncio
async def test_assemble_writes_complete_bundle_without_overwrite(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    receipts_dir = tmp_path / "receipts"
    receipts_dir.mkdir()
    output_path = tmp_path / "bundle.json"

    def passing_result(scenario_id: str, _envelope: object) -> SimpleNamespace:
        return SimpleNamespace(
            scenario_id=scenario_id,
            receipt_valid=True,
            evaluation=SimpleNamespace(passed=True, failures=()),
        )

    monkeypatch.setattr(cli, "evaluate_macos_receipt_envelope", passing_result)
    for scenario in macagentbench_scenarios():
        envelope = build_macos_receipt_scenario_template(scenario.id)
        (receipts_dir / f"{scenario.id}.json").write_text(
            json.dumps(envelope), encoding="utf-8"
        )

    assert (
        await cli._run_assemble(
            receipts_dir,
            pretty=True,
            output_path=output_path,
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    bundle = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["bundle_path"] == str(output_path)
    assert summary["native_qualification_complete"] is False
    assert bundle["receipt_contract_id"] == cli.macos_receipt_contract_id()
    original = output_path.read_bytes()

    assert (
        await cli._run_assemble(
            receipts_dir,
            pretty=True,
            output_path=output_path,
        )
        == 2
    )
    assert output_path.read_bytes() == original
    assert "refusing to overwrite" in json.loads(capsys.readouterr().out)["error"]


@pytest.mark.asyncio
async def test_qualify_capture_validates_directory_before_live_readiness(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    receipts_dir = tmp_path / "receipts"
    assert cli._run_init_capture(receipts_dir, pretty=False) == 0
    capsys.readouterr()
    expected_ids = {scenario.id for scenario in macagentbench_scenarios()}
    readiness = SimpleNamespace(ready=True)
    observed: dict[str, object] = {}

    def passing_result(scenario_id: str, _envelope: object) -> SimpleNamespace:
        return SimpleNamespace(
            scenario_id=scenario_id,
            receipt_valid=True,
            evaluation=SimpleNamespace(passed=True, failures=()),
        )

    async def probe_readiness() -> SimpleNamespace:
        observed["readiness_called"] = True
        return readiness

    def evaluate(readiness_report, receipts, *, receipt_contract_id):
        observed["readiness"] = readiness_report
        observed["receipt_ids"] = set(receipts)
        observed["contract_id"] = receipt_contract_id
        return SimpleNamespace(
            native_qualification_complete=True,
            to_dict=lambda: {"native_qualification_complete": True},
        )

    monkeypatch.setattr(cli, "evaluate_macos_receipt_envelope", passing_result)
    monkeypatch.setattr(cli, "probe_macos_readiness", probe_readiness)
    monkeypatch.setattr(cli, "evaluate_macos_qualification", evaluate)

    assert await cli._run_qualify_capture(receipts_dir, pretty=False) == 0

    assert observed == {
        "readiness_called": True,
        "readiness": readiness,
        "receipt_ids": expected_ids,
        "contract_id": cli.macos_receipt_contract_id(),
    }
    assert json.loads(capsys.readouterr().out) == {
        "native_qualification_complete": True
    }


@pytest.mark.asyncio
async def test_qualify_capture_does_not_probe_readiness_for_invalid_capture(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    receipt_path = tmp_path / "invalid.json"
    receipt_path.write_text("{", encoding="utf-8")

    async def unexpected_readiness_probe() -> None:
        raise AssertionError("readiness must not run for invalid capture evidence")

    monkeypatch.setattr(cli, "probe_macos_readiness", unexpected_readiness_probe)

    assert await cli._run_qualify_capture(tmp_path, pretty=False) == 2
    assert "could not read receipt envelope" in json.loads(
        capsys.readouterr().out
    )["error"]
