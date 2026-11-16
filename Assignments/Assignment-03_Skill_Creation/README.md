# Assignment 3: Skill Creation (reusable plan and format skills)

Course: Agentic AI (26ECAC401), KLE Technological University
Worklet 15: Executive Decision Support System (EDSS)
Book phase: A, Foundations

## Objective

Package repeatable capability as reusable, schema-typed skills. The lab builds a plan (blueprint) skill and a formatting skill that renders the decision brief shell, both reusable across cases. The book's pitfall: keep skills case-agnostic and typed; hard-coding one case breaks reuse.

## Concept applied in EDSS

EDSS has to serve different review contexts, for example a quarterly Governing Council review and a NAAC re-accreditation snapshot. The same `plan_skill` must turn either request into a locked plan, and the same `format_decision_skill` must render either result into a document. Only the inputs change, never the code.

## Technical stack

- Python 3, standard library only (`dataclasses` with `frozen=True` for the locked plan)
- [`eds/skills.py`](../lab_kit/eds/skills.py)

## Implementation

Script: [`lab03_skills.py`](lab03_skills.py)

1. Defines two different cases: case 1 is the "Q1 FY26 Governing Council review" requested by the Registrar (all domains by default); case 2 is the "NAAC re-accreditation snapshot" requested by the Principal, limited to academic and research.
2. Calls `plan_skill(case_1)` and `plan_skill(case_2)`. The skill expands the inputs with defaults (domains, the six KPIs, the four constraints, a timestamp) and returns a frozen `Plan`, which matches the book's `expand(inputs).lock()`.
3. Tries to assign `plan_1.review_cycle = "tampered"` and shows that the frozen dataclass rejects it with `FrozenInstanceError`.
4. Builds two small result dicts and passes each to `format_decision_skill()`, which returns a `Document`; `Document.to_markdown()` renders the shell for each case.

Key pieces:

| Name | File | Role |
| --- | --- | --- |
| `Plan` | [`skills.py`](../lab_kit/eds/skills.py) | Frozen dataclass: review cycle, domains, KPIs, requester, constraints, created_at |
| `plan_skill(inputs) -> Plan` | [`skills.py`](../lab_kit/eds/skills.py) | Fills defaults and locks |
| `Document` | [`skills.py`](../lab_kit/eds/skills.py) | Title plus sections; renders to Markdown |
| `format_decision_skill(result, template) -> Document` | [`skills.py`](../lab_kit/eds/skills.py) | Renders a result; `template` is a label only in this kit |

## How to run

```bash
cd Assignments/Assignment-03_Skill_Creation
python lab03_skills.py
```

On Windows, set `set PYTHONIOENCODING=utf-8` first: the formatted titles contain a non-ASCII dash.

## Result / evidence

Acceptance (book): the same skill works for two different cases without code changes.

From [`output/run_log.txt`](output/run_log.txt):

```
Case 1 locked plan:
  review_cycle: Q1 FY26 Governing Council review
  domains: ['academic', 'research', 'placement', 'finance']
  requested_by: Registrar
...
Case 2 locked plan (same skill, different inputs):
  review_cycle: NAAC re-accreditation snapshot
  domains: ['academic', 'research']
  requested_by: Principal
...
Attempted mutation correctly rejected: FrozenInstanceError: cannot assign to field 'review_cycle'
...
ACCEPT: plan_skill() and format_decision_skill() ran unchanged over two different cases.
```

The two formatted shells in the log each contain a title and a "Summary" section with placeholder text; this lab tests the skill interface, not report content (real content arrives in Lab 7).

## In the full system

| | |
| --- | --- |
| Production code | [`app/agents/skills/plan_skill.py`](../../Course_Project/backend/app/agents/skills/plan_skill.py), [`app/agents/skills/options_skill.py`](../../Course_Project/backend/app/agents/skills/options_skill.py); each skill has a schema, a code-side check, and its prompt kept as data in [`app/agents/prompts.py`](../../Course_Project/backend/app/agents/prompts.py) |
| What it does there | Shows what the model is told, what comes back, and what the code checks |
| Proved by | [`tests/agents/test_plan_skill.py`](../../Course_Project/backend/tests/agents/test_plan_skill.py), [`test_options_skill.py`](../../Course_Project/backend/tests/agents/test_options_skill.py), [`test_prompts.py`](../../Course_Project/backend/tests/agents/test_prompts.py), [`test_real_model_skills.py`](../../Course_Project/backend/tests/agents/test_real_model_skills.py) |
