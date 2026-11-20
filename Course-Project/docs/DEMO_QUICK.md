# Demo, quick version (12 minutes, real model)

Read this in the car. The full detail is in `docs/DEMO.md`; this is only what to click and say.
The screens are busy, so each step says what to look at and what to ignore.

## Terminal setup: tabs and folders

Open Terminal (Cmd+Space, type `Terminal`, Enter). You need **4 tabs**. Cmd+T opens a new tab, Cmd+1 to Cmd+4 switches between them.

| Tab | Folder | Purpose | You type | Leave it |
| --- | --- | --- | --- | --- |
| 1 | any, no need to change | The language model | `OLLAMA_KEEP_ALIVE=30m OLLAMA_NUM_PARALLEL=4 ollama serve` | Running. Never type in it again. |
| 2 | any | Warm-up, once | `ollama run qwen3.5:4b "hi"`, wait for a reply, then `/bye` | Free after that, close it or reuse it |
| 3 | **the project** | The demo itself | `cd ~/Claude/edss` then `LLM_PROVIDER=ollama LLM_MODEL=qwen3.5:4b make demo` | Running. Never type in it again. |
| 4 | **the project** | Spare, for reset and test commands | `cd ~/Claude/edss` | Free for commands |

Rules:
- Only tabs 3 and 4 need the folder change. Do `cd ~/Claude/edss` first in each of them. If a `make` command says "No rule to make target", you are in the wrong folder: run `cd ~/Claude/edss`.
- Tabs 1 and 3 look stuck while running. That is normal. Do not type in them. Ctrl+C in a tab stops what it is running.
- Skip tab 1 if Ollama is already running (check: `curl -s http://127.0.0.1:11434/api/version` prints a version).
- Start order: 1, then 2, then 3, then open Chrome. Tab 4 any time.
- All the later commands in "Terminal commands, in order" (reset, acceptance, benchmark, check, rehearse, open diagrams) go in **tab 4**.

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

## Terminal commands, in order

Run all of these from the repo folder: `cd ~/Claude/edss`. Each one is what you type, then what to say about it.

**A. Start (before the professor looks)**

```bash
OLLAMA_NUM_PARALLEL=4 ollama serve
```
Tab 1, leave it running. Skip if it already is.

```bash
ollama list
```
Shows `qwen3.5:4b` and `nomic-embed-text`. Say: "The model is local, 3.4 GB, no network."

```bash
ollama run qwen3.5:4b "hi"
```
Wait for a reply, then type `/bye`. This loads the model so the live run is not slow.

```bash
LLM_PROVIDER=ollama LLM_MODEL=qwen3.5:4b make demo
```
Tab 2. Wait for "EDSS is ready" and "Drafts: ollama". Now do the browser walk above (steps 1 to 7).

**B. During the walk, only if asked or if it breaks**

```bash
make demo-reset
```
Tab 3. Back to the starting state in 2 seconds. Sign in again.

```bash
tail -f .demo/api.log
```
Optional, to show the agents reading through the connector while the live run is going. Ctrl-C to stop.

**C. After the walk: "show me it is tested" (pick two, they take time)**

```bash
make acceptance
```
2 seconds. Injects every fault into every plan. Say: "94 of 94 caught and repaired, 0 escaped."

```bash
make benchmark
```
30 seconds. Say: "Four agents in parallel are 4.0 times faster than one at a time."

```bash
make check
```
About 1 minute. Lint, types, 1,136 backend and 238 web tests. Say: "Nothing is committed unless this is green."

```bash
make rehearse
```
About 20 seconds. A browser walks the demo script by itself and checks the steps. Needs `make demo` stopped (it uses other ports, so it also works with the demo running).

Do not run `make coverage`, `make smoke` or `make test-db` live: they take 1.5 minutes or more, and the database ones need Docker running. Show their saved output instead:

```bash
cat docs/technical/results/2026-10-27/summary.md
```
All suites with today's numbers in one table.

**D. After that: "show me the design"**

```bash
ls docs/technical
```
12 numbered documents plus uml and results.

```bash
open docs/technical/uml/png/02_architecture.png
open docs/technical/uml/png/06_sequence_brief.png
open docs/technical/uml/png/11_activity_validate.png
```
Architecture, one brief from request to human gate, and the validation and repair loop. Say what each shows in one sentence.

```bash
open docs/technical/results/2026-10-27/acceptance-report.md
```
The fault table, if they want proof of the 94.

**E. Stop**

Ctrl-C in the `make demo` tab (it stops both servers), then Ctrl-C in the `ollama serve` tab.

If any command fails, the answer is the same: Ctrl-C, run `make demo` (canned), and carry on.

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
