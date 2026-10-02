# PROGRESS

Update at the end of every session. Keep it short and true.

## Lab status

| Lab | Topic | Status | Notes |
| --- | --- | --- | --- |
| 1 | Planner loop (clarify, plan, revise) | not started | |
| 2 | Tool-using agent, KPI engine | not started | |
| 3 | Reusable skills | not started | |
| 4 | Memory and retrieval | not started | |
| 5 | MCP connector | not started | |
| 6 | Runtime, audit, checkpoints | not started | |
| 7 | Full node graph | not started | |
| 8 | Parallel fan-out and merge | not started | |
| 9 | Grounding and evidence | not started | |
| 10 | Validate, diagnose, repair | not started | |
| 11 | Acceptance suite as gate | not started | |
| 12 | Governance, approval, rollback | not started | |
| 13 | Framework specialists | not started | |
| 14 | Capstone and deployment | not started | |

## Decisions confirmed by Kiran

C1 to C4 in docs/DECISIONS.md (repo path, OrbStack, FakeLLM until Day 4, lab grading format to be checked). D2 to D4 still provisional. D13 to D21 are review findings with proposed defaults, awaiting Kiran.

## Dependencies added (with reason)

None yet.

## Environment (Day 0, 2026-10-03)

| Tool | State |
| --- | --- |
| Xcode license | Not accepted. Blocks `/usr/bin/python3`, `/usr/bin/make` and Homebrew. Kiran must run `sudo xcodebuild -license accept` |
| Python 3.12, uv | Missing, install via Homebrew after the license |
| pnpm | Missing, install via Homebrew after the license |
| OrbStack | Missing, install via Homebrew cask after the license |
| Ollama | Not needed until Day 4 (FakeLLM until then) |
| Node | v26.6.0 from Homebrew. Confirm Next.js supports it, otherwise pin 22 LTS |
| git, gh | OK, gh logged in as kirann-05 |
| Machine | Apple Silicon, 16 GB RAM, 185 GB free |

## Session log

| Date | Goal | Done | Next |
| --- | --- | --- | --- |
| 2026-10-03 | Day 0: review pack, environment, repo | Pack reviewed, repo created at ~/Claude/edss with docs as first commit, decisions C1 to C4 recorded, review findings D13 to D21 logged | Kiran accepts Xcode license, then install uv, Python 3.12, pnpm, OrbStack. Confirm D13 to D21. Then Day 1 |
