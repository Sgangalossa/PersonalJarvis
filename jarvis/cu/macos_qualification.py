"""Side-effect-free preflight bundle for a physical MacAgentBench pass."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .macos_bench import macagentbench_scenarios
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
    native_qualification_complete: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "readiness": self.readiness.to_dict(),
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "native_qualification_complete": self.native_qualification_complete,
        }


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
    return MacOSQualificationPreflight(readiness=report, scenarios=tuple(scenarios))


__all__ = [
    "MacOSQualificationPreflight",
    "ScenarioPreflight",
    "build_macos_qualification_preflight",
]
