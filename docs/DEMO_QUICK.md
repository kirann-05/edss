# Demo, quick version (12 minutes, real model)

Read this in the car. The full detail is in `docs/DEMO.md`; this is only what to click and say.
The screens are busy, so each step says what to look at and what to ignore.

## Before you walk in (5 minutes)

1. Terminal 1: `OLLAMA_NUM_PARALLEL=4 ollama serve` (skip if it is already running).
2. Terminal 2: `ollama run qwen3.5:4b "hi"`, wait for the answer, then `/bye`. This loads the model.
3. Terminal 3, in the repo folder: `LLM_PROVIDER=ollama LLM_MODEL=qwen3.5:4b make demo`
4. Wait for "EDSS is ready". The banner must say **Drafts: ollama**. If it says fake, stop and redo step 3.
5. Chrome, one tab: http://127.0.0.1:3000. Zoom 125 percent (Cmd and +). Wi-Fi off is fine.
6. Keep one spare terminal open for `make demo-reset` (goes back to the start in 2 seconds).

If the model misbehaves at any point: Ctrl-C, run `make demo` (canned, instant), carry on from the same step. Say nothing about it unless asked.

## What you are proving, in one sentence

Four agents read university data through a governed connector, a rules engine (not the model) computes every number, the model only drafts the words, nine checks gate the draft, and a named person approves. Everything is logged and reversible.

## The walk

### 1. Sign in and data health (2 min)
- Click **Registrar**. Look only at the top line: "Current approved report, version 1". Ignore the grids below.
- Click **Open data health**. Point at three things: CIVIL placement "Stale, 150 days", MECH research "No record", BIOTECH finance "pending reconciliation".
- Say: "Before any KPI, the system says what the data cannot support. Stale data is used but flagged. Missing data is left out, never counted as zero. This is synthetic data with these problems planted on purpose, and it all runs on this laptop."

### 2. Ask in plain words (2 min)
- Menu: **New brief**. Click the example **Prepare the leadership brief**, then **Start**.
- It asks three questions with "Why I ask". Click **2025-26**, **All four areas**, **Governing Council review**, then **Continue**.
- A plan appears. Untick **Curriculum compliance**, click **Save changes** (it becomes Revision 2).
- Say: "The request was too vague, so it asked exactly what it needed. The plan is only a proposal. I edited it. Nothing runs until I lock it."

### 3. Run it with the real model (2 min)
- Click **Lock plan and start**. This is the live model moment: it takes 20 to 60 seconds.
- Watch the timeline fill in. Point at the four agents (Academic, Research, Placement, Finance) and "Validation, attempt 1, All nine checks passed".
- Say while it runs: "Four agents work at the same time through an MCP connector with a token that opens only this plan's areas. Every read is a row in the audit log. The language model is a local Qwen 4B on this laptop. No data leaves the machine."
- When it says "waiting for a person", click through to the brief.

### 4. The number the model never touches (2 min)
- Menu: **Dashboard**, click **Placement percentage**.
- It reads 75.0 against a target of 75.0 and is marked **Missed**. Exact figure 74.96.
- Say: "A miss is never hidden by rounding. The institution figure is built from totals (937 of 1,250), not by averaging departments, which would wrongly say 75.7. The model writes the words; every figure is filled in afterwards from the engine. Each number opens down to the source record."

### 5. Open the brief and approve it (2 min)
- Menu: **Review queue**, open the brief you just made.
- Look at: the options with their risks, the status badges on provisional figures, and the green nine checks.
- Sign out (your name, top right), click **Principal**. Open the same brief, click **Approve**. If it asks, tick the acknowledgement.
- Say: "Agents draft and flag. A named person decides. The reviewer can edit or send back, and an edit goes through the same nine checks."

### 6. Rollback and audit (1 min)
- Menu: **Reports**, roll back to version 1 with a reason. Menu: **Audit**, click verify.
- Say: "Nothing is deleted. A rollback moves a pointer and needs a reason. The log is hash-chained, so changing any past entry breaks the chain."

### 7. A head of department (1 min)
- Sign out, click **Head of Department (CSE)**. They see institution KPIs but only CSE detail.
- Say: "That is enforced on the server, not by hiding things on the page."

### Close (30 seconds)
- Say: "Real data is waiting on the university. The list of what we need is in docs/PENDING.md. When it arrives nothing in the agents, engine or screens changes: the exports go in a folder with a manifest and the same ingestion path reads them."

## Do not do

- Do not break a brief on purpose live (the "inject fault" button). With the real model the outcome is not guaranteed. If asked, say: "94 of 94 injected faults were caught in testing" and show `docs/technical/results/2026-10-27/acceptance-report.md`.
- Do not switch between the real and canned model mid-walk.
- Do not open Admin or press "Refresh data" during a run.

## Numbers to quote if asked

- 1,392 automated tests (1,136 backend, 238 web, 18 browser), all passing. 98 percent backend coverage.
- 94 of 94 injected faults caught and repaired. Parallel agents 4.0 times faster than one at a time.
- Real model (Qwen 3.5, 4B, local): one area 21 s, full brief 55 s, all nine checks passed first try. Option drafts 9 of 9 pass in the evaluation.
- Everything is in `docs/technical/` (requirements, 13 UML diagrams, API, database, testing, results).

## Honest weaknesses, if the professor probes

- The UI is plain and busy. A cleaner redesign exists on branch `ux-redesign`, not merged yet.
- All 13 KPI definitions and targets are placeholders until IQAC supplies the official ones (we do not invent NIRF or NAAC definitions).
- Real university data is not loaded yet. Only CO and PO exports may arrive first, and the system handles a partial folder.
- A 4B model on a laptop is slower and its wording varies. Production would use the university GPU.
