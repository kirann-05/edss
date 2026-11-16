# Assignment 9: Deep Research (ground and evidence)

Course: Agentic AI (26ECAC401), KLE Technological University
Worklet 15: Executive Decision Support System (EDSS)
Book phase: C, Applied reliability

## Objective

Ground every output in cited, in-scope evidence. For each candidate figure the agent builds an evidence record grounded in verified institutional data, so validity is auditable and out-of-scope content cannot slip through. The book's pitfall: require a real source; a plausible-sounding but ungrounded item must be rejected, not kept.

## Concept applied in EDSS

A number in front of the Governing Council is only useful if leadership can trace where it came from. In EDSS each candidate figure is researched against the scope "verified institutional data". A figure with a named source system inside that scope is accepted and carries its evidence record. A figure without a source, or from an unverified scope, is rejected. The same `Evidence` record type is what every domain agent attaches in the full pipeline, and the validation check "every figure cites its source" reads it.

## Technical stack

- Python 3, standard library only
- `Evidence` dataclass from [`eds/agents/base.py`](../lab_kit/eds/agents/base.py)
- The pipeline-level check `_check_every_figure_cites_source` in [`eds/validation.py`](../lab_kit/eds/validation.py)

## Implementation

Script: [`lab09_grounding.py`](lab09_grounding.py)

1. Defines three candidate figures:
   - placement percentage 84.2 from "Placement Cell CRM", scope "verified institutional data"
   - publications per faculty 1.06 from "Research Office Registry", same scope
   - pass percentage 99.9, with no `source_system` and scope "unverified rumor"
2. `research(candidate, source)` builds an `Evidence` record. `in_scope` is true only when the candidate has a source system and its scope equals "verified institutional data". A missing source becomes `"UNKNOWN"`.
3. Loops over the candidates, following the book's pseudocode: if `not ev.in_scope`, reject; otherwise attach `c["evidence"] = ev.as_dict()` and accept.
4. Asserts that exactly one candidate (the uncited 99.9) was rejected and that every accepted candidate carries evidence.

Key pieces:

| Name | File | Role |
| --- | --- | --- |
| `Evidence` | [`agents/base.py`](../lab_kit/eds/agents/base.py) | `source_system`, `scope`, `detail`, `in_scope` |
| `research()` | [`lab09_grounding.py`](lab09_grounding.py) | Builds the evidence record and decides scope |
| `_check_every_figure_cites_source` | [`validation.py`](../lab_kit/eds/validation.py) | Fails the draft if any domain or KPI result lacks a `source_system` |

Note: the three candidates are written into the script as test inputs. They are not the figures the pipeline computes from the stub data (for example, Lab 2 computes placement as 74.77%). The lab tests the accept/reject rule, not the values.

## How to run

```bash
cd Assignments/Assignment-09_Deep_Research_Grounding
python lab09_grounding.py
```

On Windows, if the console shows encoding errors, run `set PYTHONIOENCODING=utf-8` first.

## Result / evidence

Acceptance (book): every output maps to an in-scope source; ungrounded candidates are rejected.

From [`output/run_log.txt`](output/run_log.txt):

```
Accepted (grounded) candidates:
  - institution_placement_percentage=84.2  <- Placement Cell CRM
  - institution_publications_per_faculty=1.06  <- Research Office Registry

Rejected (ungrounded) candidates:
  - institution_pass_percentage=99.9 (suspiciously high, no citation)  (in_scope=False, source='UNKNOWN')

ACCEPT: every accepted output maps to a real, in-scope source; the ungrounded candidate was rejected rather than kept.
```

The pipeline-level version is covered by the kit test `test_validation_fails_when_a_domain_drops_its_evidence` in [`../lab_kit/tests/test_pipeline.py`](../lab_kit/tests/test_pipeline.py).

## In the full system

| | |
| --- | --- |
| Production code | Reference tokens `{{kpi:...}}` and `{{fact:...}}` in [`app/agents/tokens.py`](../../Course_Project/backend/app/agents/tokens.py), enforced by validation check V1 in [`app/agents/validation/checks.py`](../../Course_Project/backend/app/agents/validation/checks.py) |
| What it does there | In a brief, clicking any figure opens its source record with the system, reference and as-of date |
| Proved by | [`tests/agents/test_tokens.py`](../../Course_Project/backend/tests/agents/test_tokens.py), [`tests/agents/test_validation.py`](../../Course_Project/backend/tests/agents/test_validation.py) |
