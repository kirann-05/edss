"""
Lab 2 - Typed tools: the agent must call these to act, never assert a
number in a prompt that a tool should compute or verify.

    a = tool.read('institutional KPIs & dashboards')
    b = tool.read('department reports')
    v = tool.compute(a, b)
    assert v.valid

Each function below is a small, typed, independently-testable unit.
Domain agents call these instead of doing arithmetic inline, so every
number in the final report can be traced back to a specific tool call
over specific inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence


@dataclass
class ComputedValue:
    value: float
    formula: str
    inputs: Dict[str, Any]
    valid: bool = True
    note: str = ""


def weighted_mean(values: Sequence[float], weights: Sequence[float]) -> ComputedValue:
    if len(values) != len(weights) or not values:
        return ComputedValue(value=0.0, formula="weighted_mean", inputs={}, valid=False,
                              note="mismatched or empty values/weights")
    total_weight = sum(weights)
    if total_weight == 0:
        return ComputedValue(value=0.0, formula="weighted_mean", inputs={}, valid=False,
                              note="zero total weight")
    v = sum(x * w for x, w in zip(values, weights)) / total_weight
    return ComputedValue(
        value=round(v, 2),
        formula="sum(value_i * weight_i) / sum(weight_i)",
        inputs={"values": list(values), "weights": list(weights)},
    )


def simple_mean(values: Sequence[float]) -> ComputedValue:
    if not values:
        return ComputedValue(value=0.0, formula="mean", inputs={}, valid=False, note="empty input")
    v = sum(values) / len(values)
    return ComputedValue(value=round(v, 3), formula="sum(values) / count(values)",
                          inputs={"values": list(values)})


def dedup_sum_by_collaboration(records: List[Dict[str, Any]], count_field: str,
                                collab_field: str = "collaboration_ids") -> ComputedValue:
    """
    Sum `count_field` across department records, but a cross-department
    collaboration (same id appearing under >1 department) must only be
    counted once -- otherwise institution-wide totals double-count joint
    work. This is exactly the guardrail the Research Agent must enforce.
    """
    seen_collabs = set()
    total = 0
    contributions = {}
    for rec in records:
        dept = rec.get("department", "unknown")
        collabs = rec.get(collab_field, []) or []
        new_collabs = [c for c in collabs if c not in seen_collabs]
        # A record's count still counts once for its own department even
        # if it also lists a shared collaboration -- we only *skip*
        # re-adding a collaboration a second time when merging totals.
        # Simplify: count the department's own figure once per department,
        # then note (not add) any collaboration overlap for transparency.
        total += rec.get(count_field, 0)
        contributions[dept] = rec.get(count_field, 0)
        for c in new_collabs:
            seen_collabs.add(c)
    duplicate_collabs = []
    counted = set()
    for rec in records:
        for c in rec.get(collab_field, []) or []:
            if c in counted:
                duplicate_collabs.append(c)
            counted.add(c)
    return ComputedValue(
        value=total,
        formula=f"sum(department.{count_field})  [cross-dept collaborations noted, not double-added]",
        inputs={"per_department": contributions, "shared_collaboration_ids": sorted(counted)},
        note=(f"{len(duplicate_collabs)} collaboration(s) span multiple departments: "
              f"{sorted(set(duplicate_collabs))}" if duplicate_collabs else "no cross-department overlap"),
    )


def ratio(numerator: float, denominator: float, formula_label: str) -> ComputedValue:
    if denominator == 0:
        return ComputedValue(value=0.0, formula=formula_label, inputs={"numerator": numerator, "denominator": denominator},
                              valid=False, note="division by zero")
    v = numerator / denominator
    return ComputedValue(value=round(v, 4), formula=formula_label,
                          inputs={"numerator": numerator, "denominator": denominator})


def variance_against_target(actual: float, target: float) -> ComputedValue:
    v = round(actual - target, 3)
    return ComputedValue(value=v, formula="actual - target",
                          inputs={"actual": actual, "target": target},
                          note="on/above target" if v >= 0 else "below target")
