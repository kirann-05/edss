# Assignment 12: Safety and Governance (approval, evaluation, rollback)

Course: Agentic AI (26ECAC401), KLE Technological University
Worklet 15: Executive Decision Support System (EDSS)
Book phase: D, Governance and capstone

## Objective

Add confidentiality, approval, evaluation and rollback. Access control, the executive/leadership approval gate as a hard stop, evaluation metrics, versioning and one-click rollback turn the draft into a governed, reversible release. The book's pitfall: confidentiality and rollback are requirements, not extras.

## Concept applied in EDSS

The human authority for this worklet is the Executive/Leadership: Principal, Director, Registrar or Governing Council. In EDSS nothing is published without a `Decision` from one of those roles. An approver may approve as-is or approve with edits (for example adding a leadership note); each publish becomes a new numbered version, never an overwrite. A metric is recorded per release, and any earlier version can be restored. Department-level data access is guarded separately by the connector's access grants (Lab 5).

## Technical stack

- Python 3, standard library only (`json`, `pathlib`, `dataclasses`)
- [`eds/governance.py`](../lab_kit/eds/governance.py): `HumanGate`, `Decision`, `Governance`, `PublishedVersion`
- Published versions written as JSON files

## Implementation

Script: [`lab12_governance.py`](lab12_governance.py)

1. Builds and validates a full draft (graph run plus self-healing, as in Labs 7 and 10).
2. Unauthorised approver: `HumanGate.review(..., role="Clerk", decision="approve")` raises `UnauthorizedRoleError` because "Clerk" is not in `APPROVED_ROLES`.
3. Publish without approval: `governance.publish()` with a `Decision` whose decision is `"reject"` raises `ApprovalRequiredError`.
4. Real approval: the Registrar approves; `publish()` sets `status="approved"`, records approver, role and comment, and stores version 1. `record_metric("kpis_below_target", ...)` records an evaluation metric.
5. Edited approval: the Principal approves with the edit `{"leadership_note": "Escalate placement gap to Deans."}`. This is stored as version 2, and the script asserts the note is in the content.
6. Prints the version history.
7. Rollback: `governance.rollback(to_version=1)` copies version 1's content into a new version 3 with `restored_from_version=1`. The script asserts that the leadership note from version 2 is gone.

Key pieces:

| Name | File | Role |
| --- | --- | --- |
| `APPROVED_ROLES` | [`governance.py`](../lab_kit/eds/governance.py) | Principal, Director, Registrar, Governing Council |
| `HumanGate.review` | [`governance.py`](../lab_kit/eds/governance.py) | Hard stop: refuses any other role |
| `Decision.approved` | [`governance.py`](../lab_kit/eds/governance.py) | True only for "approve" or "edit" |
| `Governance.publish` | [`governance.py`](../lab_kit/eds/governance.py) | Applies edits, versions, writes `v<N>_<run_id>.json` |
| `Governance.rollback` | [`governance.py`](../lab_kit/eds/governance.py) | Restores an old version as a new version |
| `Governance.record_metric`, `history` | [`governance.py`](../lab_kit/eds/governance.py) | Metrics and version list |

## How to run

```bash
cd Assignments/Assignment-12_Safety_and_Governance
python lab12_governance.py
```

On Windows, if the console shows encoding errors, run `set PYTHONIOENCODING=utf-8` first.

## Result / evidence

Acceptance (book): only executive/leadership-approved results publish; any release rolls back cleanly.

From [`output/run_log.txt`](output/run_log.txt):

```
Correctly rejected unauthorized approver: 'Clerk' is not an authorized approver for an executive report. Authorized roles: ['Director', 'Governing Council', 'Principal', 'Registrar']
Correctly rejected publish-without-approval: Cannot publish: decision was 'reject', not an approval.

Published version 1 by Dr. A. Sharma (Registrar)
Published version 2 (edited) by Principal Rao
...
Rolled back to content of v1, recorded as new v3 (restored_from_version=1)

ACCEPT: only approved results published; unauthorized/unapproved attempts were rejected; rollback restored a prior version cleanly.
```

Output files in [`output/published/`](output/published/):

- [`v1_5713abe0.json`](output/published/v1_5713abe0.json) and [`v2_5713abe0.json`](output/published/v2_5713abe0.json): versions 1 and 2 from the logged run (`run_id` 5713abe0). Version 2 is slightly larger (22,600 vs 22,528 bytes) because it contains the leadership note.
- There is no `v3` file: `rollback()` keeps the restored version in memory and in `history()`, but only `publish()` writes files.

The approval and rollback rules are also covered by kit tests `test_governance_rejects_unapproved_publish`, `test_governance_rejects_unauthorized_role` and `test_rollback_restores_prior_version_content` in [`../lab_kit/tests/test_pipeline.py`](../lab_kit/tests/test_pipeline.py).

## In the full system

| | |
| --- | --- |
| Production code | [`app/governance/service.py`](../../Course_Project/backend/app/governance/service.py), [`app/core/rbac.py`](../../Course_Project/backend/app/core/rbac.py) |
| What it does there | The Principal edits and approves; the Reports page compares versions and rolls back with a reason; a HOD sees only their own department |
| Proved by | [`tests/governance/test_governance.py`](../../Course_Project/backend/tests/governance/test_governance.py), [`tests/api/test_scoping.py`](../../Course_Project/backend/tests/api/test_scoping.py), [`tests/api/test_authorization.py`](../../Course_Project/backend/tests/api/test_authorization.py), and the browser tests |
