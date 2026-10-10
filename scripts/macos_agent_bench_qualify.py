"""Validate a version-bound MacAgentBench receipt bundle against native readiness."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jarvis.cu.macos_bench import macagentbench_scenarios
from jarvis.cu.macos_qualification import (
    build_macos_qualification_guide,
    build_macos_receipt_bundle_template,
    build_macos_receipt_scenario_template,
    evaluate_macos_qualification,
    evaluate_macos_receipt_envelope,
    macos_receipt_contract_id,
)
from jarvis.cu.macos_readiness import probe_macos_readiness


def _print(payload: dict[str, Any], *, pretty: bool) -> None:
    print(json.dumps(payload, indent=2 if pretty else None, sort_keys=True))


async def _run(receipts_path: Path, *, pretty: bool) -> int:
    try:
        receipts_text = await asyncio.to_thread(receipts_path.read_text, encoding="utf-8")
        bundle = json.loads(receipts_text)
    except (OSError, json.JSONDecodeError) as exc:
        _print({"error": f"could not read receipt JSON: {exc}"}, pretty=pretty)
        return 2
    if not isinstance(bundle, dict) or set(bundle) != {
        "receipt_contract_id",
        "receipts",
    }:
        _print(
            {
                "error": (
                    "receipt JSON must be a bundle with exactly "
                    "receipt_contract_id and receipts"
                )
            },
            pretty=pretty,
        )
        return 2
    contract_id = bundle["receipt_contract_id"]
    receipts = bundle["receipts"]
    if not isinstance(contract_id, str) or not isinstance(receipts, dict):
        _print(
            {
                "error": (
                    "receipt_contract_id must be a string and receipts "
                    "must be an object keyed by scenario ID"
                )
            },
            pretty=pretty,
        )
        return 2

    readiness = await probe_macos_readiness()
    qualification = evaluate_macos_qualification(
        readiness,
        receipts,
        receipt_contract_id=contract_id,
    )
    _print(qualification.to_dict(), pretty=pretty)
    return 0 if qualification.native_qualification_complete else 1


async def _run_scenario(receipt_path: Path, scenario_id: str, *, pretty: bool) -> int:
    try:
        receipt_text = await asyncio.to_thread(receipt_path.read_text, encoding="utf-8")
        receipt = json.loads(receipt_text)
    except (OSError, json.JSONDecodeError) as exc:
        _print({"error": f"could not read receipt JSON: {exc}"}, pretty=pretty)
        return 2
    try:
        result = evaluate_macos_receipt_envelope(scenario_id, receipt)
    except ValueError as exc:
        _print({"error": str(exc)}, pretty=pretty)
        return 2
    _print(result.to_dict(), pretty=pretty)
    return 0 if result.receipt_valid and result.evaluation.passed else 1


async def _run_assemble(receipts_dir: Path, *, pretty: bool) -> int:
    try:
        receipt_paths = sorted(
            path for path in receipts_dir.iterdir() if path.suffix.casefold() == ".json"
        )
    except OSError as exc:
        _print({"error": f"could not list receipt directory: {exc}"}, pretty=pretty)
        return 2
    if not receipt_paths:
        _print({"error": "receipt directory contains no JSON envelopes"}, pretty=pretty)
        return 2

    try:
        receipt_texts = await asyncio.gather(
            *(
                asyncio.to_thread(path.read_text, encoding="utf-8")
                for path in receipt_paths
            )
        )
        envelopes = [
            (path, json.loads(text))
            for path, text in zip(receipt_paths, receipt_texts, strict=True)
        ]
    except (OSError, json.JSONDecodeError) as exc:
        _print({"error": f"could not read receipt envelope: {exc}"}, pretty=pretty)
        return 2

    receipts: dict[str, object] = {}
    for path, envelope in envelopes:
        if not isinstance(envelope, dict):
            _print({"error": f"{path.name}: receipt envelope must be an object"}, pretty=pretty)
            return 2
        scenario_id = envelope.get("scenario_id")
        if type(scenario_id) is not str:
            _print({"error": f"{path.name}: scenario_id must be a string"}, pretty=pretty)
            return 2
        if scenario_id in receipts:
            _print({"error": f"duplicate receipt scenario: {scenario_id}"}, pretty=pretty)
            return 2
        try:
            result = evaluate_macos_receipt_envelope(scenario_id, envelope)
        except ValueError as exc:
            _print({"error": f"{path.name}: {exc}"}, pretty=pretty)
            return 2
        if not result.receipt_valid or not result.evaluation.passed:
            failures = "; ".join(result.evaluation.failures)
            _print(
                {"error": f"{path.name}: receipt did not pass: {failures}"},
                pretty=pretty,
            )
            return 1
        receipts[scenario_id] = envelope["receipt"]

    expected_ids = {scenario.id for scenario in macagentbench_scenarios()}
    missing = sorted(expected_ids - set(receipts))
    unexpected = sorted(set(receipts) - expected_ids)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected: {', '.join(unexpected)}")
        _print({"error": "receipt set is incomplete (" + "; ".join(details) + ")"}, pretty=pretty)
        return 2

    _print(
        {
            "receipt_contract_id": macos_receipt_contract_id(),
            "receipts": receipts,
        },
        pretty=pretty,
    )
    return 0


async def _run_capture_status(receipts_dir: Path, *, pretty: bool) -> int:
    try:
        receipt_paths = sorted(
            path for path in receipts_dir.iterdir() if path.suffix.casefold() == ".json"
        )
    except OSError as exc:
        _print({"error": f"could not list receipt directory: {exc}"}, pretty=pretty)
        return 2

    expected_ids = {scenario.id for scenario in macagentbench_scenarios()}
    scenario_status: dict[str, dict[str, object]] = {}
    file_issues: list[dict[str, str]] = []
    unexpected_files: list[str] = []
    for path in receipt_paths:
        try:
            receipt_text = await asyncio.to_thread(path.read_text, encoding="utf-8")
            envelope = json.loads(receipt_text)
        except (OSError, json.JSONDecodeError) as exc:
            file_issues.append(
                {"file": path.name, "status": "invalid", "error": str(exc)}
            )
            continue
        if not isinstance(envelope, dict):
            file_issues.append(
                {
                    "file": path.name,
                    "status": "invalid",
                    "error": "receipt envelope must be an object",
                }
            )
            continue
        scenario_id = envelope.get("scenario_id")
        if type(scenario_id) is not str:
            file_issues.append(
                {
                    "file": path.name,
                    "status": "invalid",
                    "error": "scenario_id must be a string",
                }
            )
            continue
        if scenario_id not in expected_ids:
            unexpected_files.append(path.name)
            continue
        if scenario_id in scenario_status:
            file_issues.append(
                {
                    "file": path.name,
                    "status": "invalid",
                    "error": f"duplicate receipt scenario: {scenario_id}",
                }
            )
            scenario_status[scenario_id]["status"] = "invalid"
            continue
        try:
            result = evaluate_macos_receipt_envelope(scenario_id, envelope)
        except ValueError as exc:
            scenario_status[scenario_id] = {
                "file": path.name,
                "status": "invalid",
                "failures": [str(exc)],
            }
            continue
        scenario_status[scenario_id] = {
            "file": path.name,
            "status": (
                "passed"
                if result.receipt_valid and result.evaluation.passed
                else "failed"
            ),
            "failures": list(result.evaluation.failures),
        }

    for scenario_id in expected_ids - set(scenario_status):
        scenario_status[scenario_id] = {
            "file": None,
            "status": "missing",
            "failures": [],
        }
    ordered_status = {
        scenario_id: scenario_status[scenario_id]
        for scenario_id in sorted(expected_ids)
    }
    counts = {
        status: sum(
            entry["status"] == status for entry in ordered_status.values()
        )
        for status in ("passed", "failed", "invalid", "missing")
    }
    capture_complete = (
        counts["passed"] == len(expected_ids)
        and not file_issues
        and not unexpected_files
    )
    _print(
        {
            "receipt_contract_id": macos_receipt_contract_id(),
            "capture_complete": capture_complete,
            "native_qualification_complete": False,
            "counts": counts,
            "scenarios": ordered_status,
            "file_issues": file_issues,
            "unexpected_files": unexpected_files,
        },
        pretty=pretty,
    )
    return 0 if capture_complete else 1


def _run_init_capture(receipts_dir: Path, *, pretty: bool) -> int:
    scenarios = macagentbench_scenarios()
    try:
        receipts_dir.mkdir(parents=True)
        receipt_files = []
        for scenario in scenarios:
            receipt_path = receipts_dir / f"{scenario.id}.json"
            receipt_path.write_text(
                json.dumps(
                    build_macos_receipt_scenario_template(scenario.id),
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            receipt_files.append(receipt_path.name)
    except FileExistsError:
        _print(
            {
                "error": (
                    "capture directory already exists; refusing to overwrite "
                    f"{receipts_dir}"
                )
            },
            pretty=pretty,
        )
        return 2
    except OSError as exc:
        _print(
            {"error": f"could not initialize capture directory: {exc}"},
            pretty=pretty,
        )
        return 2

    _print(
        {
            "receipt_contract_id": macos_receipt_contract_id(),
            "receipt_directory": str(receipts_dir),
            "receipt_files": receipt_files,
            "native_qualification_complete": False,
        },
        pretty=pretty,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "receipts",
        type=Path,
        nargs="?",
        help="versioned receipt bundle JSON generated by --template",
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="print a version-bound, fail-closed receipt bundle template",
    )
    parser.add_argument(
        "--guide",
        action="store_true",
        help="print every live criterion and required receipt field",
    )
    parser.add_argument(
        "--scenario",
        help="validate one version-bound receipt envelope before assembling the full bundle",
    )
    parser.add_argument(
        "--scenario-template",
        metavar="ID",
        help="print a version-bound, fail-closed receipt envelope for one scenario",
    )
    parser.add_argument(
        "--assemble",
        type=Path,
        metavar="DIRECTORY",
        help="assemble a complete bundle from passing version-bound receipt envelopes",
    )
    parser.add_argument(
        "--init-capture",
        type=Path,
        metavar="DIRECTORY",
        help="create a new directory with one version-bound envelope per scenario",
    )
    parser.add_argument(
        "--capture-status",
        type=Path,
        metavar="DIRECTORY",
        help="report progress for every version-bound scenario envelope",
    )
    parser.add_argument("--pretty", action="store_true", help="indent the JSON output")
    args = parser.parse_args()
    modes = sum(
        (
            args.template,
            args.guide,
            args.scenario is not None,
            args.scenario_template is not None,
            args.assemble is not None,
            args.init_capture is not None,
            args.capture_status is not None,
        )
    )
    if modes > 1:
        parser.error(
            "--template, --guide, --scenario, --scenario-template, --assemble, "
            "--init-capture and --capture-status are mutually exclusive"
        )
    if args.template:
        if args.receipts is not None:
            parser.error("receipts cannot be supplied with --template")
        _print(build_macos_receipt_bundle_template(), pretty=True)
        return 0
    if args.guide:
        if args.receipts is not None:
            parser.error("receipts cannot be supplied with --guide")
        _print(build_macos_qualification_guide(), pretty=True)
        return 0
    if args.init_capture is not None:
        if args.receipts is not None:
            parser.error("receipts cannot be supplied with --init-capture")
        return _run_init_capture(args.init_capture, pretty=args.pretty)
    if args.capture_status is not None:
        if args.receipts is not None:
            parser.error("receipts cannot be supplied with --capture-status")
        return asyncio.run(
            _run_capture_status(args.capture_status, pretty=args.pretty)
        )
    if args.assemble is not None:
        if args.receipts is not None:
            parser.error("receipts cannot be supplied with --assemble")
        return asyncio.run(_run_assemble(args.assemble, pretty=args.pretty))
    if args.scenario_template is not None:
        if args.receipts is not None:
            parser.error("receipts cannot be supplied with --scenario-template")
        try:
            payload = build_macos_receipt_scenario_template(args.scenario_template)
        except ValueError as exc:
            parser.error(str(exc))
        _print(payload, pretty=True)
        return 0
    if args.scenario is not None:
        if args.receipts is None:
            parser.error("receipts is required with --scenario")
        return asyncio.run(_run_scenario(args.receipts, args.scenario, pretty=args.pretty))
    if args.receipts is None:
        parser.error(
            "receipts is required unless --template, --guide, --scenario-template, "
            "--assemble, --init-capture or --capture-status is used"
        )
    return asyncio.run(_run(args.receipts, pretty=args.pretty))


if __name__ == "__main__":
    raise SystemExit(main())
