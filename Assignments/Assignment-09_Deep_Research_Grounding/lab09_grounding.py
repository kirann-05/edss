"""
Lab 9 - Deep Research: ground & evidence.

Phase: C - Applied reliability
Goal: ground every output in cited, in-scope evidence.

Run:
    python lab09_grounding.py

Acceptance: every output maps to an in-scope source; ungrounded
candidates are rejected.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab_kit"))

from eds.agents.base import Evidence


def research(candidate: dict, source: str) -> Evidence:
    """for c in candidates: ev = research(c, source=...); ..."""
    has_source = bool(candidate.get("source_system"))
    return Evidence(
        source_system=candidate.get("source_system", "UNKNOWN"),
        scope=candidate.get("scope", "unspecified"),
        detail={"figure": candidate.get("figure")},
        in_scope=has_source and candidate.get("scope") == "verified institutional data",
    )


def main():
    print("=== Lab 9: grounding -- every candidate must carry real evidence ===\n")

    candidates = [
        {"figure": "institution_placement_percentage=84.2",
         "source_system": "Placement Cell CRM", "scope": "verified institutional data"},
        {"figure": "institution_publications_per_faculty=1.06",
         "source_system": "Research Office Registry", "scope": "verified institutional data"},
        {"figure": "institution_pass_percentage=99.9 (suspiciously high, no citation)",
         "scope": "unverified rumor"},  # no source_system -- must be rejected
    ]

    accepted, rejected = [], []
    for c in candidates:
        ev = research(c, source="verified institutional data")
        if not ev.in_scope:
            rejected.append((c, ev))
            continue
        c["evidence"] = ev.as_dict()
        accepted.append(c)

    print("Accepted (grounded) candidates:")
    for c in accepted:
        print(f"  - {c['figure']}  <- {c['evidence']['source_system']}")

    print("\nRejected (ungrounded) candidates:")
    for c, ev in rejected:
        print(f"  - {c['figure']}  (in_scope={ev.in_scope}, source='{ev.source_system}')")

    assert len(rejected) == 1 and "suspiciously high" in rejected[0][0]["figure"]
    assert all("evidence" in c for c in accepted)

    print("\nACCEPT: every accepted output maps to a real, in-scope source; "
          "the ungrounded candidate was rejected rather than kept.")


if __name__ == "__main__":
    main()
