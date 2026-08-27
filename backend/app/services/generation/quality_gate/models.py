from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class GateAction(StrEnum):
    """What to do with a content variant after the quality gate (architecture doc 4.5)."""

    PASS = "pass"
    FLAG = "flag"  # let it through to review, but flagged (e.g. duplicate, minor compliance)
    REGENERATE_IMAGE = "regenerate_image"  # image-caption misalignment
    REJECT = "reject"  # never reaches a human (safety / halal failure)


# Higher = more severe. The gate's overall action is the most severe failing
# check's action.
_SEVERITY: dict[GateAction, int] = {
    GateAction.PASS: 0,
    GateAction.FLAG: 1,
    GateAction.REGENERATE_IMAGE: 2,
    GateAction.REJECT: 3,
}


class CheckResult(BaseModel):
    name: str
    passed: bool
    score: float | None = None
    reason: str | None = None
    # The action to take if this check FAILS (ignored when passed).
    fail_action: GateAction = GateAction.FLAG


class QualityGateResult(BaseModel):
    """Pass/fail of every check plus the aggregated action (plan Module 16)."""

    action: GateAction
    checks: list[CheckResult] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.action == GateAction.PASS

    @property
    def failures(self) -> list[CheckResult]:
        return [check for check in self.checks if not check.passed]


def aggregate_action(checks: list[CheckResult]) -> GateAction:
    """The most severe failing check's action, or PASS if nothing failed."""
    action = GateAction.PASS
    for check in checks:
        if not check.passed and _SEVERITY[check.fail_action] > _SEVERITY[action]:
            action = check.fail_action
    return action
