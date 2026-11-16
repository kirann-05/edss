"""
Lab 1 - Agent vs Chatbot: the decision-brief planner loop.

Phase: A - Foundations
Goal: establish the agent loop (clarify -> plan -> revise) instead of a
one-shot chatbot answer.

Run:
    python lab01_planner_loop.py

Acceptance: given a vague request, the loop asks at least two
clarifying questions and yields a coherent, editable plan.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab_kit"))

from eds.coordinator import Coordinator


def scripted_user_answers(question: str) -> str:
    """Stands in for a real human in this notebook-style demo."""
    if "review cycle" in question:
        return "Q1 FY26 Governing Council review"
    if "domains" in question:
        return "academic,research,placement,finance"
    return "unspecified"


def main():
    vague_request = {}  # a genuinely vague, one-shot-chatbot-unfriendly request

    print("=== Lab 1: planner loop (clarify -> plan -> revise) ===\n")
    print(f"Incoming request: {vague_request!r}\n")

    clarified = Coordinator.clarify(vague_request, questioner=scripted_user_answers)
    asked = clarified.pop("_clarifying_questions_asked")
    print(f"Clarifying questions asked ({len(asked)}):")
    for q in asked:
        print(f"  - {q}")
    assert len(asked) >= 2, "acceptance check failed: fewer than 2 clarifying questions asked"

    # normalize the domains answer into a list the plan skill expects
    if isinstance(clarified.get("domains"), str):
        clarified["domains"] = [d.strip() for d in clarified["domains"].split(",")]

    coordinator = Coordinator()
    plan = coordinator.build_plan(clarified)
    print("\nProposed plan:")
    for k, v in plan.as_dict().items():
        print(f"  {k}: {v}")

    # revise: leadership asks to narrow scope to academic + finance only
    revised = coordinator.revise_plan(plan, {"domains": ["academic", "finance"]})
    print("\nRevised plan (leadership narrowed scope to academic + finance):")
    for k, v in revised.as_dict().items():
        print(f"  {k}: {v}")

    print("\nACCEPT: >=2 clarifying questions asked, and a coherent, editable plan was produced.")


if __name__ == "__main__":
    main()
