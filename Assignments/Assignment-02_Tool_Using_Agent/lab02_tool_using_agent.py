"""
Lab 2 - Tool-Using Agent: call data & compute.

Phase: A - Foundations
Goal: give the agent tools it must call to act, rather than answering
from memory.

Run:
    python lab02_tool_using_agent.py

Acceptance: key numbers and lookups always go through tools, never
hand-done in the prompt.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab_kit"))

from eds.connector import StubConnector
from eds import tools


def main():
    print("=== Lab 2: typed tools over real data ===\n")
    connector = StubConnector()
    connector.request_access("placement", authorized_by="Registrar (demo)")

    # a = tool.read('institutional KPIs & dashboards')
    a = connector.read("institutional KPIs & dashboards")
    print(f"tool.read('institutional KPIs & dashboards') -> {len(a)} KPI definitions")

    # b = tool.read('department reports')
    b = connector.read("department reports", domain="placement")
    print(f"tool.read('department reports', domain='placement') -> {len(b)} department records")

    # v = tool.compute(a, b); assert v.valid
    total_eligible = sum(r["eligible_students"] for r in b)
    total_placed = sum(r["placed_students"] for r in b)
    v = tools.ratio(total_placed, total_eligible, "sum(placed_students) / sum(eligible_students)")
    print(f"\ntool.compute(...) -> placement % = {v.value:.2%}  (formula: {v.formula})")
    assert v.valid, "computed value should be valid for well-formed inputs"

    # demonstrate the tool rejecting a malformed computation instead of the
    # agent silently guessing a number
    bad = tools.ratio(5, 0, "x / 0")
    print(f"\ntool.compute on a malformed input -> valid={bad.value if bad.valid else None}, "
          f"valid={bad.valid}, note='{bad.note}'")
    assert not bad.valid, "division-by-zero must be caught by the tool, not asserted in a prompt"

    print("\nACCEPT: every figure above came from tool.read/tool.compute, none were hand-asserted.")


if __name__ == "__main__":
    main()
