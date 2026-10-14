"""Side-effect-free preflight bundle for a physical MacAgentBench pass."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, fields
from typing import Any, get_type_hints

from .macos_bench import (
    BrowserDesktopHandoffReceipt,
    CrossWindowHandoffReceipt,
    FocusTypeLandingReceipt,
    HandoffCancellationReceipt,
    MacAgentBenchEvaluation,
    PermissionDegradationReceipt,
    PhysicalTakeoverReceipt,
    PromptInjectionResistanceReceipt,
    SemanticTargetHitReceipt,
    StaleTargetRefusalReceipt,
    evaluate_browser_desktop_handoff,
    evaluate_cross_window_handoff,
    evaluate_focus_type_landing,
    evaluate_handoff_cancellation,
    evaluate_permission_degradation,
    evaluate_physical_takeover,
    evaluate_prompt_injection_resistance,
    evaluate_semantic_target_hit,
    evaluate_stale_target_refusal,
    macagentbench_scenarios,
)
from .macos_readiness import MacOSReadinessReport, ReadinessCheck


@dataclass(frozen=True)
class ScenarioPreflight:
    """Current native prerequisites for one live-gated benchmark scenario."""

    scenario_id: str
    live_required: bool
    all_checks_ready: bool
    checks: tuple[ReadinessCheck, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MacOSQualificationPreflight:
    """Read-only evidence bundle; never a claim of native qualification."""

    readiness: MacOSReadinessReport
    scenarios: tuple[ScenarioPreflight, ...]
    receipt_contract_id: str
    native_qualification_complete: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "readiness": self.readiness.to_dict(),
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "receipt_contract_id": self.receipt_contract_id,
            "native_qualification_complete": self.native_qualification_complete,
        }


@dataclass(frozen=True)
class ScenarioQualification:
    """Sanitized result for one supplied live receipt."""

    scenario_id: str
    receipt_valid: bool
    evaluation: MacAgentBenchEvaluation

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "receipt_valid": self.receipt_valid,
            "evaluation": self.evaluation.to_dict(),
        }


@dataclass(frozen=True)
class MacOSQualificationReport:
    """Aggregate result that fails closed outside a ready macOS host."""

    readiness: MacOSReadinessReport
    scenarios: tuple[ScenarioQualification, ...]
    unexpected_receipt_ids: tuple[str, ...]
    receipt_contract_id: str
    receipt_contract_matches: bool
    native_qualification_complete: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "readiness": self.readiness.to_dict(),
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "unexpected_receipt_ids": self.unexpected_receipt_ids,
            "receipt_contract_id": self.receipt_contract_id,
            "receipt_contract_matches": self.receipt_contract_matches,
            "native_qualification_complete": self.native_qualification_complete,
        }


_RECEIPT_EVALUATORS: dict[
    str,
    tuple[type[Any], Callable[[Any], MacAgentBenchEvaluation]],
] = {
    "physical-user-takeover": (PhysicalTakeoverReceipt, evaluate_physical_takeover),
    "semantic-target-hit": (SemanticTargetHitReceipt, evaluate_semantic_target_hit),
    "stale-target-refusal": (StaleTargetRefusalReceipt, evaluate_stale_target_refusal),
    "focus-type-landing": (FocusTypeLandingReceipt, evaluate_focus_type_landing),
    "cross-window-handoff": (CrossWindowHandoffReceipt, evaluate_cross_window_handoff),
    "browser-to-desktop-handoff": (
        BrowserDesktopHandoffReceipt,
        evaluate_browser_desktop_handoff,
    ),
    "handoff-cancellation": (HandoffCancellationReceipt, evaluate_handoff_cancellation),
    "permission-degradation": (
        PermissionDegradationReceipt,
        evaluate_permission_degradation,
    ),
    "prompt-injection-resistance": (
        PromptInjectionResistanceReceipt,
        evaluate_prompt_injection_resistance,
    ),
}


def macos_receipt_contract_id() -> str:
    """Fingerprint the scenario and receipt schema used by live qualification."""
    contract: list[dict[str, Any]] = []
    scenarios = {scenario.id: scenario for scenario in macagentbench_scenarios()}
    for scenario_id in sorted(_RECEIPT_EVALUATORS):
        scenario = scenarios[scenario_id]
        receipt_type, _ = _RECEIPT_EVALUATORS[scenario_id]
        type_hints = get_type_hints(receipt_type)
        contract.append(
            {
                "scenario": scenario.to_dict(),
                "receipt_fields": [
                    [field.name, type_hints[field.name].__name__]
                    for field in fields(receipt_type)
                ],
            }
        )
    encoded = json.dumps(
        contract,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_macos_receipt_bundle_template() -> dict[str, Any]:
    """Return a version-bound, evaluator-failing live receipt bundle."""
    return {
        "receipt_contract_id": macos_receipt_contract_id(),
        "receipts": build_macos_receipt_template(),
    }


def build_macos_receipt_scenario_template(scenario_id: str) -> dict[str, Any]:
    """Return one version-bound, evaluator-failing live receipt envelope."""
    if scenario_id not in _RECEIPT_EVALUATORS:
        raise ValueError(f"unknown MacAgentBench scenario: {scenario_id}")
    return {
        "receipt_contract_id": macos_receipt_contract_id(),
        "scenario_id": scenario_id,
        "receipt": build_macos_receipt_template()[scenario_id],
    }


def _invalid_evaluation(scenario_id: str, failure: str) -> MacAgentBenchEvaluation:
    return MacAgentBenchEvaluation(
        scenario_id=scenario_id,
        passed=False,
        failures=(failure,),
    )


def _parse_receipt(scenario_id: str, raw: object) -> tuple[Any | None, str | None]:
    receipt_type, _ = _RECEIPT_EVALUATORS[scenario_id]
    if not isinstance(raw, Mapping):
        return None, "live receipt must be a JSON object"

    receipt_fields = fields(receipt_type)
    expected = {field.name for field in receipt_fields}
    supplied = set(raw)
    missing = sorted(expected - supplied)
    unexpected = sorted(supplied - expected)
    if missing:
        return None, f"live receipt is missing field(s): {', '.join(missing)}"
    if unexpected:
        return None, f"live receipt has unexpected field(s): {', '.join(unexpected)}"

    type_hints = get_type_hints(receipt_type)
    for field in receipt_fields:
        expected_type = type_hints[field.name]
        if type(raw[field.name]) is not expected_type:
            return None, (
                f"live receipt field {field.name!r} must be "
                f"{expected_type.__name__}"
            )
    return receipt_type(**raw), None


def evaluate_macos_receipt(
    scenario_id: str,
    raw: object,
) -> ScenarioQualification:
    """Validate and evaluate one live receipt before assembling the full bundle."""
    if scenario_id not in _RECEIPT_EVALUATORS:
        raise ValueError(f"unknown MacAgentBench scenario: {scenario_id}")

    receipt, validation_error = _parse_receipt(scenario_id, raw)
    if validation_error is not None:
        evaluation = _invalid_evaluation(scenario_id, validation_error)
    else:
        _, evaluator = _RECEIPT_EVALUATORS[scenario_id]
        evaluation = evaluator(receipt)
    return ScenarioQualification(
        scenario_id=scenario_id,
        receipt_valid=validation_error is None,
        evaluation=evaluation,
    )


def evaluate_macos_receipt_envelope(
    scenario_id: str,
    raw: object,
) -> ScenarioQualification:
    """Validate a version-bound single-scenario envelope and its receipt."""
    if scenario_id not in _RECEIPT_EVALUATORS:
        raise ValueError(f"unknown MacAgentBench scenario: {scenario_id}")
    if not isinstance(raw, Mapping) or set(raw) != {
        "receipt_contract_id",
        "scenario_id",
        "receipt",
    }:
        raise ValueError(
            "single receipt JSON must contain exactly receipt_contract_id, "
            "scenario_id and receipt"
        )
    envelope_scenario_id = raw["scenario_id"]
    if type(envelope_scenario_id) is not str or envelope_scenario_id != scenario_id:
        raise ValueError("single receipt scenario_id does not match --scenario")
    contract_id = raw["receipt_contract_id"]
    if type(contract_id) is not str:
        raise ValueError("single receipt receipt_contract_id must be a string")
    if contract_id != macos_receipt_contract_id():
        raise ValueError("single receipt contract ID does not match the current contract")
    return evaluate_macos_receipt(scenario_id, raw["receipt"])


def build_macos_qualification_preflight(
    report: MacOSReadinessReport,
) -> MacOSQualificationPreflight:
    """Bind one readiness snapshot to every live scenario without posting input."""
    observed = {check.id: check for check in report.checks}
    scenarios: list[ScenarioPreflight] = []
    for scenario in macagentbench_scenarios():
        checks = tuple(
            observed.get(
                check_id,
                ReadinessCheck(
                    id=check_id,
                    ok=False,
                    detail="required readiness check was not reported",
                ),
            )
            for check_id in scenario.readiness_checks
        )
        scenarios.append(
            ScenarioPreflight(
                scenario_id=scenario.id,
                live_required=scenario.live_required,
                all_checks_ready=all(check.ok for check in checks),
                checks=checks,
            )
        )
    return MacOSQualificationPreflight(
        readiness=report,
        scenarios=tuple(scenarios),
        receipt_contract_id=macos_receipt_contract_id(),
    )


def build_macos_receipt_template() -> dict[str, dict[str, bool | int | str]]:
    """Return a typed, fail-closed JSON template for every live scenario."""
    placeholders: dict[type[Any], bool | int | str] = {
        bool: False,
        int: 0,
        str: "",
    }
    template: dict[str, dict[str, bool | int | str]] = {}
    for scenario in macagentbench_scenarios():
        receipt_type, _ = _RECEIPT_EVALUATORS[scenario.id]
        type_hints = get_type_hints(receipt_type)
        template[scenario.id] = {
            field.name: placeholders[type_hints[field.name]]
            for field in fields(receipt_type)
        }
    return template


def build_macos_qualification_guide() -> dict[str, Any]:
    """Describe live evidence requirements from the authoritative contracts."""
    template = build_macos_receipt_template()
    scenarios: list[dict[str, Any]] = []
    for scenario in macagentbench_scenarios():
        receipt_type, _ = _RECEIPT_EVALUATORS[scenario.id]
        type_hints = get_type_hints(receipt_type)
        scenarios.append(
            {
                **scenario.to_dict(),
                "receipt_fields": [
                    {
                        "name": field.name,
                        "json_type": type_hints[field.name].__name__,
                        "placeholder": template[scenario.id][field.name],
                    }
                    for field in fields(receipt_type)
                ],
            }
        )
    return {
        "receipt_contract_id": macos_receipt_contract_id(),
        "native_qualification_complete": False,
        "scenarios": scenarios,
    }


def evaluate_macos_qualification(
    report: MacOSReadinessReport,
    receipts: Mapping[str, object],
    *,
    receipt_contract_id: str | None = None,
) -> MacOSQualificationReport:
    """Validate every live receipt against current side-effect-free readiness."""
    preflight = build_macos_qualification_preflight(report)
    expected_ids = {scenario.id for scenario in macagentbench_scenarios()}
    unexpected_ids = tuple(sorted(set(receipts) - expected_ids))
    scenarios: list[ScenarioQualification] = []

    for scenario in macagentbench_scenarios():
        if scenario.id not in receipts:
            scenarios.append(
                ScenarioQualification(
                    scenario_id=scenario.id,
                    receipt_valid=False,
                    evaluation=_invalid_evaluation(
                        scenario.id,
                        "live receipt is missing",
                    ),
                )
            )
            continue

        scenarios.append(evaluate_macos_receipt(scenario.id, receipts[scenario.id]))

    native_ready = (
        report.platform == "darwin"
        and report.ready
        and all(scenario.all_checks_ready for scenario in preflight.scenarios)
    )
    current_contract_id = macos_receipt_contract_id()
    contract_matches = receipt_contract_id == current_contract_id
    complete = (
        native_ready
        and contract_matches
        and not unexpected_ids
        and all(scenario.evaluation.passed for scenario in scenarios)
    )
    return MacOSQualificationReport(
        readiness=report,
        scenarios=tuple(scenarios),
        unexpected_receipt_ids=unexpected_ids,
        receipt_contract_id=current_contract_id,
        receipt_contract_matches=contract_matches,
        native_qualification_complete=complete,
    )


__all__ = [
    "MacOSQualificationPreflight",
    "MacOSQualificationReport",
    "ScenarioQualification",
    "ScenarioPreflight",
    "build_macos_qualification_guide",
    "build_macos_qualification_preflight",
    "build_macos_receipt_bundle_template",
    "build_macos_receipt_scenario_template",
    "build_macos_receipt_template",
    "evaluate_macos_receipt",
    "evaluate_macos_receipt_envelope",
    "evaluate_macos_qualification",
    "macos_receipt_contract_id",
]
