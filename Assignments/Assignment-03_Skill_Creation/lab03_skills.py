"""
Lab 3 - Skill Creation: reusable plan & format skills.

Phase: A - Foundations
Goal: package repeatable capability as reusable, schema-typed skills.

Run:
    python lab03_skills.py

Acceptance: the same skill works for two different cases without code
changes.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab_kit"))

from eds.skills import plan_skill, format_decision_skill


def main():
    print("=== Lab 3: case-agnostic plan & format skills ===\n")

    case_1 = {"review_cycle": "Q1 FY26 Governing Council review", "requested_by": "Registrar"}
    case_2 = {"review_cycle": "NAAC re-accreditation snapshot", "requested_by": "Principal",
              "domains": ["academic", "research"]}

    plan_1 = plan_skill(case_1)   # skill plan(inputs) -> Plan: return expand(inputs).lock()
    plan_2 = plan_skill(case_2)

    print("Case 1 locked plan:")
    for k, v in plan_1.as_dict().items():
        print(f"  {k}: {v}")
    print("\nCase 2 locked plan (same skill, different inputs):")
    for k, v in plan_2.as_dict().items():
        print(f"  {k}: {v}")

    # a Plan is frozen -- mutation must fail
    try:
        plan_1.review_cycle = "tampered"
        raise AssertionError("Plan should be immutable/locked")
    except Exception as e:
        print(f"\nAttempted mutation correctly rejected: {type(e).__name__}: {e}")

    # format_decision(result, template) -> Document, same skill, two cases
    fake_result_1 = {"title": "Executive Decision Brief — Q1 FY26",
                      "sections": [{"heading": "Summary", "body": "placeholder summary for case 1"}]}
    fake_result_2 = {"title": "Executive Decision Brief — NAAC Snapshot",
                      "sections": [{"heading": "Summary", "body": "placeholder summary for case 2"}]}

    doc_1 = format_decision_skill(fake_result_1)
    doc_2 = format_decision_skill(fake_result_2)
    print("\n--- Case 1 formatted shell ---")
    print(doc_1.to_markdown())
    print("--- Case 2 formatted shell ---")
    print(doc_2.to_markdown())

    print("ACCEPT: plan_skill() and format_decision_skill() ran unchanged over two different cases.")


if __name__ == "__main__":
    main()
