# The live demo, step by step

About 12 minutes. Read this once before the first rehearsal. Every label in quotes below is the exact text on screen, checked on 2026-10-04 against the running demo. If one changes, `make rehearse` fails and names the step.

| Step | Who | What it proves | Time |
| --- | --- | --- | --- |
| 1 | Registrar | The system tells you what the data cannot support before anyone reads a figure | 1 min |
| 2 | Registrar | The agent asks before it plans, and a person edits the plan | 1.5 min |
| 3 | Registrar | Four domain agents work at the same time | 1 min |
| 4 | Registrar | A missed target is never hidden by rounding, and every figure opens to its source | 1.5 min |
| 5 | Registrar | The brief: options, risks, trade-offs, assumptions, badges | 1.5 min |
| 6 | Registrar | Break it on purpose: validation catches it and repairs only the failing part | 1.5 min |
| 7 | Principal | A named person edits and approves. Version 2 publishes | 1.5 min |
| 8 | Principal | Roll back, and the audit chain still verifies | 1 min |
| 9 | HOD (CSE) | A HOD sees only their own department's detail | 1 min |
| Close | You | What changes when real data arrives | 0.5 min |

## Pre-flight checklist

**The night before**

- [ ] `git pull`, then `make check` and `make rehearse`. Both must be green. The rehearsal walks steps 1 to 9 in a browser in about 20 seconds.
- [ ] `make demo`, walk all nine steps once, then `make demo-reset`.
- [ ] Laptop charged. Charger, and the HDMI or USB-C adapter for the projector, in the bag.
- [ ] A screen recording of one full rehearsal on the laptop and on a USB stick (the last-resort backup below). `make demo-video` makes it: `demo-video/edss-demo.webm`, about 75 seconds, with a pause on each step to say its line. It plays in Chrome, Firefox and VLC; QuickTime does not play webm.

**Fifteen minutes before**

- [ ] Plugged into power.
- [ ] Do Not Disturb on. Mail, chat and anything that pops up closed.
- [ ] One terminal tab: `make demo`. Wait for "EDSS is ready". The banner must say "Synthetic data only", "Drafts: fake" and "Ready-made: one approved report (version 1) and one draft waiting for review".
- [ ] Now Wi-Fi off. Nothing needs the network once it is running, and it is worth saying so in step 1.
- [ ] A second terminal tab in the repo folder, for `make demo-reset` if you need it.
- [ ] Chrome, one window, one tab, at http://127.0.0.1:3000. Zoom 125 percent (Cmd and +). Mirror the display to the projector. Every screen is checked to fit a 1280 by 720 projector at this zoom.
- [ ] The sign-in page is showing.

**Model off, and why.** The demo drafts with the canned FakeLLM, so every run takes about a second and says the same thing every time. The local model works (`LLM_PROVIDER=ollama LLM_MODEL=qwen3.5:4b make demo`), but on this MacBook Air a full brief takes about a minute instead of a second, and its wording changes from run to run. If asked, say so plainly and point to the measured results in `docs/evals`: option drafts pass all nine checks, and the planner reads requests with rules first because the model alone asked the right questions only 4 times in 10 (with the rules first, 9 in 10). Production runs the model on the university GPU.

## Switching person

Top right, click your name (the account menu), then "Sign out", then the role button. Going to the sign-in page while signed in only sends you back to the dashboard.

## The steps

### Step 1. Data health first (Registrar)

**Click** "Registrar" (Anand Deshpande) on the sign-in page.

**Screen shows** the dashboard for "2025-26 (current)": "Current approved report, Decision brief, 2025-26, version 1", the note "13 of 13 KPI definitions and targets are placeholders pending IQAC approval", and "Some figures rest on incomplete data: No record: MECH, Excluded: BIOTECH, Stale: CIVIL, Undefined: AIML". Counts: 2 Missed, 1 At risk, 10 Met.

**Click** "Open data health".

**Screen shows** the grid of departments by area. Scroll down a little: CIVIL placement says "Stale, 150 days". MECH research says "No record". BIOTECH finance carries "1 pending reconciliation".

**Say** "Before anyone looks at a KPI, the system says what the data cannot support. Civil's placement data is five months old, so it is used but flagged everywhere. Mechanical has no research record this year, so it is left out of research figures, never counted as zero. All of this is synthetic data, generated with these problems planted on purpose, and everything runs on this laptop with the Wi-Fi off."

**If it goes wrong.** No role buttons on the sign-in page means demo mode is off: you started `make dev`, not `make demo`. Ctrl-C and run `make demo`.

### Step 2. A vague request, questions, and an edited plan (Registrar)

**Click** "New brief" in the menu, then the example "Prepare the leadership brief", then "Start".

**Screen shows** "Questions from the planner": "Which period should the brief cover?", "Which areas should it cover?", "Who will read it?", each with a "Why I ask" line.

**Click** "2025-26", "All four areas", "Governing Council review", then "Continue".

**Screen shows** the plan, "Revision 1", with 13 of 13 KPIs ticked.

**Click** untick "Curriculum compliance" (under Academic), then "Save changes". The plan says "Revision 2" and "12 of 13 chosen".

**Say** "The request was too vague to plan, so the agent asked for exactly the three things it needed, and said why. Its plan is a proposal. I removed curriculum compliance because the Council reviewed it last month. Every revision is kept, and nothing runs until I lock it."

**If it goes wrong.** If no questions appear, the request was specific enough to plan straight away: carry on from the plan. "Save changes" only appears once something is changed.

### Step 3. Four agents at the same time (Registrar)

**Click** "Lock plan and start".

**Screen shows** the timeline filling in: "Academic agent", "Research agent", "Placement agent", "Finance agent", each about 700 ms, then "KPI synthesis", "Options for ..." for the three off-target KPIs, "Brief composed", "Validation, attempt 1, All nine checks passed", and at the top "The draft passed all nine checks and is waiting for a person". Under Progress: "Elapsed" about one second and "4 domain agents worked at the same time (measured from the events)".

**Say** "Each domain agent pauses 700 milliseconds to stand in for a slow university system. Four of those one after another would be almost three seconds; the whole run took about one, so they ran at the same time, and that is measured from the events, not claimed. No agent touches a data source directly: every read goes through an MCP server, with a token that opens only this plan's areas, and every read is a row in the audit log."

**If it goes wrong.** It finishes in about a second, so it can be over before you turn round: point at the timings instead. To make it visible, start the demo with `SOURCE_LATENCY_MS=2500 make demo`. If the page stays on "Running" for more than 30 seconds, reload it: the run carries on in the server.

### Step 4. The miss that rounds to the target (Registrar)

**Click** "Dashboard" in the menu, then the "Placement percentage" card.

**Screen shows** 75.0 percent against a target of 75.0 percent, marked "Missed", with "Reads as 75.0 but the target is missed." The drill-down opens: "Shown to 1 place this reads as 75.0, the same as the target. It is missed: the exact figure is 74.96". Under "How it is calculated": 937 placed over 1,250 registered. Under "By department", the note that the institution figure of 75.0% is built from totals, while a simple average of departments would give 75.7%. AIML shows as undefined and CIVIL as stale. Under "Source records": "16 records behind this figure", each with its source system, source reference and as-of date.

**Say** "A miss is never hidden by rounding: the status is decided on the exact figure. The institution figure comes from totals, not by averaging department percentages, which would wrongly say 75.7. AIML has nothing to divide by, so it has no value, which is not zero. And every number opens down to the record it came from."

**If it goes wrong.** If the card does not open, go to http://127.0.0.1:3000/?kpi=PL_PCT.

### Step 5. The brief (Registrar)

**Click** "Review queue" in the menu, then "Prepare the leadership brief".

**Screen shows** "Decision brief, 2025-26", "Draft", "Validation passed". "KPIs at a glance" with each status. "Options for decision" for Overall pass percentage, Publications per faculty and Placement percentage: two or three options each with assumptions, risks and trade-offs, and a note that the "Strategic plan pack" guided them. Placement percentage has the option "Confirm provisional offers quickly". At the bottom, "Assumptions and caveats" lists Stale, No record, Excluded, Undefined, Provisional and Forecast, then the "Validation" tab with V1 to V9 passed.

**Say** "The model drafts the words. It never writes a number: every figure in the text is filled in afterwards from the KPI engine, so it cannot be wrong or rounded differently. Provisional offers and forecast revenue are shown apart and never counted as final. Nine checks run before any person sees this, and the result is here."

**If it goes wrong.** Nothing here is live, so it does not.

### Step 6. Break it on purpose (Registrar)

**Click** "New brief", the example "Placement and research brief for the Governing Council for 2025-26", "Start". Then "Demo: inject a failure", tick "A figure written by hand", and "Lock plan and start".

**Screen shows** "Failing: V1 Every figure cites its source", then "Repair, attempt 2", then "All nine checks passed". **Click** "Open the draft" and scroll to "Every attempt" at the bottom: the validation report says "Attempt 1: failing V1" and "Attempt 2: all nine checks passed".

**Say** "That made the model write a made-up percentage into an option, the commonest way a language model gets a report wrong. The first check caught it, the system repaired only the option that failed and checked everything again. The retry budget is three attempts. If it still fails, it stops and hands the draft to a person with the diagnosis, it never loops."

**If it goes wrong.** If "Demo: inject a failure" is missing, you are past the plan: start another run. Any of the eight faults works, each is caught by a different check.

### Step 7. The Principal edits and approves

**Click** your name, "Sign out", then "Principal / Director" (Dr. Kavita Rao). Then "Review queue" in the menu. It lists the drafts waiting. **Click** "Prepare the leadership brief".

**Click** "Edit options". Change the first option's Title to "Targeted academic support, reviewed by the Dean each semester". **Click** "Check my edits": "Your edits pass all nine checks. Nothing is saved until you approve." **Click** "Approve with edits".

**Screen shows** "Approve with your edits?" with the change shown as After. **Click** "Approve with edits" in the dialog.

**Screen shows** "Published as version 2", "Approved by Dr. Kavita Rao (Principal / Director)" and "1 edit made on approval".

**Say** "Agents draft and flag, a named person decides. My edit went through the same nine checks, and the draft's original text is kept beside it so anyone can see what I changed."

**If it goes wrong.** Do not type digits into an edit: a figure written by hand fails check V1 for a person too, and the message says so. Plain "Approve", then "Approve and publish", is the shorter path if time is short.

### Step 8. Roll back, and the audit chain (Principal)

**Click** "Reports". **Screen shows** version 2 as current and version 1 as previous. Under "Compare versions", Curriculum compliance is removed and the edited title is shown before and after.

**Click** "Make current" on the v1 row. Type a reason, for example "Restoring the version the Council already saw". **Click** "Roll back to version 1". **Screen shows** "Version 1 is current again", and v2 says "Rolled back".

**Click** "Audit". **Screen shows** "The audit chain verifies", with every step listed, including the rollback and each "Read through the connector" the agents made.

**Say** "Every approved brief is kept and nothing is deleted: a rollback moves the pointer back and needs a reason. Every step, by the agents and by people, is in an append-only log where each entry carries the hash of the one before, so changing any past entry breaks the chain."

**If it goes wrong.** "Roll back to version 1" stays grey until a reason is typed.

### Step 9. What a HOD can see (HOD, CSE)

**Click** your name, "Sign out", then "Head of Department (CSE)" (Dr. Priya Joshi).

**Screen shows** a menu of only "Dashboard", "Reports" and "Data health". **Click** the "Placement percentage" card: CSE shows its figure and records, and every other department says "restricted". In "Data health", only the CSE row shows any detail.

**Say** "The HOD sees the institution's KPIs but only their own department's detail. That is enforced on the server, not by hiding things on the page: asking for another department's record gets the same answer as a record that does not exist."

**If it goes wrong.** If you want to show the refusal, type http://127.0.0.1:3000/review into the address bar: "Your role does not include this."

### Close. Real data

**Say** "Real data is waiting on the university, and the list of what we need is in `docs/PENDING.md`. When it arrives, nothing in the agents, the KPI engine or the screens changes: the university's exports go in a folder with a manifest, and the same path that read this synthetic set reads them."

Optional, in the second terminal tab: `MODE=synthetic make ingest DIR=data/sample` prints the reconciliation report that a real folder gets: coverage by department and area, records that are not final, and every rejected row with its reason.

## Between rehearsals

`make demo-reset` puts the demo back to its start (one approved report, one draft waiting) in about 2 seconds without stopping it. Everyone has to sign in again afterwards. `DEMO_STATE=0 make demo` starts with nothing ready made.

## If all else fails

Try these in order. Keep talking while you do it: what the step was going to show is in the Say lines above.

1. **Something is stuck or in a strange state.** `make demo-reset` in the second tab, sign in again, and carry on from the step you were on. 2 seconds.
2. **A server crashed.** Ctrl-C in the first tab, then `DEMO_SKIP_BUILD=1 make demo`. About 5 seconds. The logs are in `.demo/`.
3. **"Port 8000 (or 3000) is in use".** `DEMO_API_PORT=8100 DEMO_WEB_PORT=3100 make demo`, and open http://127.0.0.1:3100.
4. **The laptop itself fails.** Play the recorded rehearsal (`make demo-video`) from the USB stick and narrate over it with the Say lines. One screenshot per step, at projector size, is in `docs/demo-screens` (`REHEARSE_SCREENS=1 make rehearse` makes them again).

## Things not to do live

- Do not switch to the real model live. It works, but a brief takes about a minute and the wording is different each time.
- Do not press "Refresh data" while a run is going: it is refused until the run finishes.
- Do not open Admin unless asked. It works, it just is not the story.
