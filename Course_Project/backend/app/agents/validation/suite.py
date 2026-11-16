"""Runs the nine checks and returns one report (Lab 10, Lab 11)."""

from app.agents.models import BriefDocument, CheckResult, ValidationReport
from app.agents.validation.checks import CHECKS, ValidationContext


def validate(doc: BriefDocument, ctx: ValidationContext, attempt: int = 1) -> ValidationReport:
    """Pure: it reads the brief and changes nothing. The same brief always gives the same report."""
    results = []
    for check_id, name, check in CHECKS:
        violations = tuple(check(doc, ctx))
        results.append(
            CheckResult(id=check_id, name=name, passed=not violations, violations=violations)
        )
    return ValidationReport(
        passed=all(r.passed for r in results), checks=tuple(results), attempt=attempt
    )


__all__ = ["ValidationContext", "validate"]
