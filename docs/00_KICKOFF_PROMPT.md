# Kickoff prompt for the first Claude Code session

Put this pack's contents in an empty project folder (for example `edss/`), run `git init`, open Claude Code in that folder, and paste the prompt below.

---

Read CLAUDE.md first, then docs/SPEC.md, docs/ARCHITECTURE.md, docs/DATA_CONTRACT.md, docs/BUILD_PLAN.md, docs/DECISIONS.md, docs/UI_SPEC.md and docs/source/chapter15.md in full. Do not write any code yet.

Then reply with three things:

1. Environment check. Run the Day 0 checks from docs/BUILD_PLAN.md on this machine and tell me exactly what is missing or out of date.
2. Review. List anything in the docs that is ambiguous, contradictory, risky for a 3 week solo build, or weaker than it sounds. Be direct. Also list the library APIs you plan to use (LangGraph, LangChain, MCP SDK, Next.js) and confirm you will check the current official docs for each before using them.
3. Day 1 plan. Restate Day 1 from docs/BUILD_PLAN.md as concrete steps with the commands you will run and the tests that will prove it works.

Wait for my go. After my go, execute Day 1 as a vertical slice, run the tests, update PROGRESS.md and docs/VIVA_NOTES.md, commit, and tell me what to look at. Follow the working agreement in CLAUDE.md: present options when a choice has real trade-offs, never converge silently, and never claim something works until you have run it.

---

## Per-day prompt after that

"Read PROGRESS.md and docs/BUILD_PLAN.md. State today's goal and the acceptance test. Do it, run the tests, update PROGRESS.md and VIVA_NOTES.md, commit, and report what changed and what is weak."

## If a session gets long

Ask Claude Code to summarise state into PROGRESS.md, then start a fresh session with the per-day prompt. The docs carry the context, not the chat.
