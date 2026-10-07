"""Physical-Mac qualification preflight contracts."""
from __future__ import annotations

from jarvis.cu.macos_bench import macagentbench_scenarios
from jarvis.cu.macos_qualification import build_macos_qualification_preflight
from jarvis.cu.macos_readiness import MacOSReadinessReport, ReadinessCheck


def _report(*checks: ReadinessCheck) -> MacOSReadinessReport:
    return MacOSReadinessReport(
        platform="darwin", ready=all(row.ok for row in checks), checks=checks
    )


def test_preflight_binds_observed_checks_without_claiming_live_qualification() -> None:
    report = _report(
        ReadinessCheck("semantic:ax-tree", True, "ready"),
        ReadinessCheck("actuation:backend", True, "ready"),
        ReadinessCheck("handoff:hardware-input", True, "ready"),
        ReadinessCheck("permission:screen_recording", True, "ready"),
        ReadinessCheck("permission:accessibility", True, "ready"),
        ReadinessCheck("permission:event_posting", True, "ready"),
    )

    bundle = build_macos_qualification_preflight(report)

    assert [row.scenario_id for row in bundle.scenarios] == [
        scenario.id for scenario in macagentbench_scenarios()
    ]
    assert all(row.all_checks_ready for row in bundle.scenarios)
    assert bundle.native_qualification_complete is False
    assert bundle.to_dict()["native_qualification_complete"] is False


def test_preflight_reports_missing_required_check_per_scenario() -> None:
    bundle = build_macos_qualification_preflight(
        _report(ReadinessCheck("semantic:ax-tree", True, "ready"))
    )
    takeover = next(
        row for row in bundle.scenarios if row.scenario_id == "physical-user-takeover"
    )

    assert takeover.all_checks_ready is False
    missing = {check.id: check for check in takeover.checks}
    assert missing["handoff:hardware-input"].ok is False
    assert missing["handoff:hardware-input"].detail == "required readiness check was not reported"
