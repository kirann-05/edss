"""
Lab 4 - Memory & Retrieval: state vs stored.

Phase: A - Foundations
Goal: separate short-term run state from long-term stored knowledge.

Run:
    python lab04_memory.py

Acceptance: for a given task, retrieval returns correctly-tagged
candidates and similar prior items.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab_kit"))

from eds.memory import RunState, LongTermStore


def main():
    print("=== Lab 4: short-term run state vs long-term store ===\n")

    # short-term: the in-flight draft, never persisted
    state = RunState(request={"review_cycle": "Q1 FY26"})
    state.set_draft({"institution_placement_percentage": 76.3, "status": "draft"})
    print(f"state.draft (short-term, this run only): {state.draft}")

    # long-term: history of prior published executive reports
    history = LongTermStore()
    history.add("2025-Q4", tags=["placement", "quarterly"],
                text="Q4 FY25 executive report: placement percentage 74.1, below target",
                payload={"placement_pct": 74.1, "review_cycle": "Q4 FY25"})
    history.add("2025-Q3", tags=["finance", "quarterly"],
                text="Q3 FY25 executive report: budget utilization 88%, on track",
                payload={"budget_utilization": 0.88, "review_cycle": "Q3 FY25"})
    history.add("2025-NAAC", tags=["academic", "accreditation"],
                text="NAAC snapshot FY25: pass percentage and CO/PO attainment reviewed",
                payload={"review_cycle": "NAAC FY25"})

    by_tag = history.retrieve_by_tags(["quarterly"])
    print(f"\nretrieve(store, tags=['quarterly']) -> {[it.id for it in by_tag]}")
    assert {"2025-Q4", "2025-Q3"} == {it.id for it in by_tag}

    by_similarity = history.retrieve_by_similarity(
        "placement percentage executive report this quarter", k=2)
    print(f"retrieve(history, embed(candidate), k=2) -> "
          f"{[it.id for it in by_similarity]}")
    assert by_similarity and by_similarity[0].id == "2025-Q4", (
        "the placement-themed prior report should rank first by similarity")

    print("\nACCEPT: tag filter and similarity search both returned correctly-matched prior items; "
          "state.draft never touched the long-term store.")


if __name__ == "__main__":
    main()
