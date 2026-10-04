# Acceptance report

Written by `make acceptance` on 2026-10-04. Synthetic data (reference day 2026-10-01) and the canned model, so the same code gives the same numbers. 18 plans: every period, each with all four areas, each area alone, and placement with research. 113 graph runs in 1.2 seconds.

## Summary

| Measure | Result |
| --- | --- |
| Clean drafts that passed all nine checks first time | 18 of 18 (100 percent) |
| Fault trials (a fault that had something to break) | 94 |
| Caught on the first attempt | 94 of 94 (100 percent) |
| Caught by the check meant to catch it | 94 of 94 (100 percent) |
| Also failed an unrelated check | 0 of 94 (0 percent) |
| Repaired inside the budget of 3 attempts | 94 of 94 (100 percent) |
| Escalated to a person | 0 |
| Not applicable to the plan | 50, listed below, not counted as passes |

## By fault

| Fault | What it does | Meant to be caught by | Trials | Caught | By that check | Repaired | Attempts used |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A figure written by hand | A model writes a made-up percentage into an option. | V1 | 15 | 15 | 15 | 15 | 2 |
| A figure with no source | A KPI loses the records it was computed from. | V7 | 18 | 18 | 18 | 18 | 2 |
| A provisional figure called confirmed | Text describes a provisional record as confirmed. | V4 | 3 | 3 | 3 | 3 | 2 |
| An option with no risks | A model forgets to list the risks of an option. | V3 | 15 | 15 | 15 | 15 | 2 |
| A stale department hidden | The caveat about a stale department is left out. | V2, V8 | 3 | 3 | 3 | 3 | 2 |
| A shared paper counted twice | A publication shared by two departments is counted twice. | V9 | 9 | 9 | 9 | 9 | 2 |
| A miss hidden by rounding | A missed KPI is marked met because it rounds to the target. | V6 | 13 | 13 | 13 | 13 | 2 |
| A false claim of approval | The brief claims to be approved before anyone has approved it. | V5 | 18 | 18 | 18 | 18 | 2 |

## The retry budget

A model that writes a figure by hand on every attempt, whatever the diagnosis says, is stopped after 3 attempts and the draft goes to a person escalated, with the diagnosis. As required.

## Not applicable, and why

- A shared paper counted twice: nothing in this plan for it to act on, in 9 plans (2023-24, academic; 2023-24, placement; 2023-24, finance; 2024-25, academic; 2024-25, placement; 2024-25, finance; 2025-26, academic; 2025-26, placement; 2025-26, finance)
- A figure written by hand: nothing in this plan for it to act on, in 3 plans (2023-24, finance; 2024-25, finance; 2025-26, finance)
- An option with no risks: nothing in this plan for it to act on, in 3 plans (2023-24, finance; 2024-25, finance; 2025-26, finance)
- A provisional figure called confirmed: nothing in this plan for it to act on, in 15 plans (2023-24, all four areas; 2023-24, academic; 2023-24, research; 2023-24, placement; 2023-24, finance; 2023-24, placement and research; 2024-25, all four areas; 2024-25, academic; 2024-25, research; 2024-25, placement; 2024-25, finance; 2024-25, placement and research; 2025-26, academic; 2025-26, research; 2025-26, finance)
- A miss hidden by rounding: nothing in this plan for it to act on, in 5 plans (2023-24, finance; 2024-25, placement; 2024-25, finance; 2025-26, academic; 2025-26, finance)
- A stale department hidden: it changes nothing in this plan, in 15 plans (2023-24, all four areas; 2023-24, academic; 2023-24, research; 2023-24, placement; 2023-24, finance; 2023-24, placement and research; 2024-25, all four areas; 2024-25, academic; 2024-25, research; 2024-25, placement; 2024-25, finance; 2024-25, placement and research; 2025-26, academic; 2025-26, research; 2025-26, finance)

## What this does not show

- The repairs here are by the canned model, which follows the diagnosis. How often a real model repairs a draft is not measured: in `docs/evals` the local model never needed a repair.
- The eight faults are the ones we wrote. A model can fail in ways that are not on the list, which is why a person reviews every draft.
