# Review with the professor: what to say

About 12 minutes, then questions. Every number here was re-run on 2026-10-26. The live demo steps, with exact on-screen labels, are in `docs/DEMO.md`; this page is only what to say around them.

## Before you walk in

- [ ] `make demo` running in one terminal tab, showing "EDSS is ready". Chrome on http://127.0.0.1:3000 at 125 percent zoom, on the sign-in page.
- [ ] A second terminal tab in the repo folder, for `make check` and `make demo-reset`.
- [ ] The review pack page open in another tab (the link Claude sent), at "Test runs".
- [ ] Charger plugged in, Do Not Disturb on.

## 1. What it is (30 seconds)

"EDSS is a decision support system for university leadership. Four agents gather each department's academic, research, placement and finance data in parallel. Plain code turns that into institution KPIs against targets. A language model drafts options for every KPI that is off target. Nine checks gate the draft and repair what fails, and only then does a named person, the Principal or Registrar, approve it. Everything is versioned, audited and can be rolled back."

## 2. Proof it works (1 minute)

Show the review pack, "Every suite, run today".

"Before showing it live, here is the evidence. 1,392 automated tests pass: backend, web app and 18 browser tests. A browser walks the whole demo script on its own. I inject eight kinds of fault, like a made-up number or a hidden stale department, into 18 different plans: 94 trials, every one caught by the check meant to catch it and repaired. 98 percent of the backend code runs under a test. And a fresh copy of the code builds into containers and works from scratch."

Optional, if he wants to see it run: in the second tab type `make check`. It takes about a minute. Keep talking while it runs.

## 3. Live demo (7 minutes)

Follow `docs/DEMO.md` steps 1 to 9. The one line for each:

1. Data health: "Before any KPI, the system says what the data cannot support."
2. A vague request: "It asks before it plans, and I edit the plan before anything runs."
3. Four agents: "They work at the same time. It is measured from the run's own events."
4. Placement: "74.96 shows as 75.0, the same as the target, and it is still marked missed. Status is decided on the exact value."
5. The brief: "The model wrote the words. Every number is a reference the engine filled in, and each one opens to its source record."
6. Break it: "I inject a hand-written number. Check V1 catches it, only that part is redone, and all nine pass."
7. Principal approves: "A named person edits and approves. If they type a number by hand, the same check stops them."
8. Roll back: "It needs a reason, deletes nothing, and the audit chain still verifies."
9. HOD: "A head of department sees only their own department, enforced by the server, not just hidden on screen."

## 4. The rules it keeps (1 minute)

"Three rules matter most. The model never writes a number. Nothing is published without a named approver. And real data never leaves this machine: a cloud model is refused in code once the data is real. The model runs locally, and the demo uses canned drafts so it is fast and the same every time. I have measured a real 4 billion parameter model on this laptop: its drafts passed all nine checks, 9 of 9."

## 5. Real data (1 minute)

"The real-data path is built: templates, a loader that checks every row and refuses bad ones with a reason, and a reconciliation report. The office said they may only be able to give CO and PO attainment, department level. I tested exactly that: it loads, gives the two CO and PO KPIs, and shows the other eleven as missing, never as zero. So a pilot with one department's CO and PO data works today."

Then ask him:

1. Is the synthetic-data demo enough for the evaluation, or do you want a run on real data too?
2. If real data: is one department's CO and PO data acceptable as the pilot, and could you make the request to the department?
3. Can IQAC give the official KPI definitions and targets? All 13 are placeholders now and the system says so on every screen.

## 6. Close (20 seconds)

"What is left is not code: the university's data, IQAC's definitions, and a GPU server and hosting for production. The runbook for the IT cell is written."

## If he asks

**Why agents, not a dashboard with SQL?** A dashboard shows numbers. This plans from a plain request, drafts options, checks itself, and hands a person a decision with the evidence attached.

**How do you stop it making up numbers?** It never writes one. It writes references like `{{kpi:PL_PCT}}` that the engine fills in, and check V1 refuses any number typed by hand.

**Is the MCP connector real?** Yes. Every agent read goes through an MCP server with a token for that run's areas only. A read outside them is refused and audited. The tests prove the same KPIs come out through MCP and directly.

**Why LangGraph?** It gives parallel fan-out, checkpoints so a run survives a restart, and a built-in pause for the human approval step.

**What is the weakest part?** Three things, said plainly: the KPI definitions are placeholders until IQAC; the API runs as one process, which is fine for one university but not for many copies behind a load balancer; and a small local model is weak at reading vague requests, so rules read them first and a person reviews every plan.

**How do you know the tests are enough?** Coverage is measured at 98 percent, and for the checks that matter I broke the code on purpose and watched exactly that test fail. Reading what coverage missed found real bugs, which are fixed.

**Where are the labs?** `docs/LABS.md` maps all 14 labs to where they live in the code, what to show, and the test that proves each.

## If something breaks

- Stuck screen: `make demo-reset` in the second tab, sign in again, carry on. 2 seconds.
- Server crashed: Ctrl-C, then `DEMO_SKIP_BUILD=1 make demo`. About 5 seconds.
- Laptop fails: the screenshots of every step are in the review pack.
