# Chapter 15: Executive Decision Support System (verbatim text of the professor's PDF)

Plain text extraction of the supplied PDF. Tables are flattened and page footers remain. The original PDF sits beside this file. If the two disagree, the PDF wins.

```text
CHAPTER 15

Executive Decision Support System
One real-time, drill-down view of institution-wide KPIs against NIRF/NAAC and strategic-plan targets.

Human authority: the executive / leadership. Primary output: decision brief with options and risks.

The 14-Lab Method (Recap)
Every worklet in this book is built the same way: as a coordinator-plus-workers agentic system that is grown, one
capability at a time, through 14 hands-on labs. This chapter is self-contained — it restates the method, the node-
graph legend and the pseudocode conventions before applying them to this worklet — so it can be handed to a
team on its own.
The guiding design principle is constant across all worklets: agents draft and flag; a named human approves. No
worklet takes a consequential action autonomously — the human authority named in this chapter signs off
before anything is published or sent.
The four phases
 Phase                                                             What it establishes
 Phase A — Foundations (Labs 1–6)                                  Turn a single agent loop into a tool-using, skill-driven,
                                                                   memory-backed agent that reaches all data through one
                                                                   connector and runs inside a governed runtime with an
                                                                   audit log.
 Phase B — Orchestration (Labs 7–8)                                Wire the specialist agents into an explicit node graph, then
                                                                   parallelise the per-unit work and merge the best results.
 Phase C — Applied reliability (Labs 9–11)                         Ground every output in evidence, make the pipeline self-
                                                                   healing on validation failure, and treat the spec as a tested
                                                                   build.
 Phase D — Governance & capstone (Labs 12–14)                      Add safety, approval, evaluation and rollback; plug in
                                                                   domain specialists; integrate everything into a deployed,
                                                                   team-owned system.

Reading the node graph
 Navy — the apniLeap AURA Coordinator: owns the run-state, plan, budgets and audit log.
 Light blue — specialist agents, each with one responsibility and a typed message contract.
 Amber — the human review gate: a hard stop; the named human is the final authority.
 Green — governed publish/act: versioned, auditable, reversible.
 Dashed grey — coordinator oversight of every agent; a red back-edge is validation → regenerate.
Pseudocode conventions
 Pseudocode is language-neutral: Coordinator orchestrates; Agent.step(ctx) is one specialist doing its job on
    the shared run-context; a human gate returns approve / edit / override.
 The blueprint/plan is locked before work begins; validation is a hard gate; the human approves before
    publish.

15.1 Worklet Overview



                                      Agentic AI Worklets — 14-Lab Build Book   |   Page 226
Leadership reviews academic, research, placement, and finance performance from separate departmental
reports that arrive on different schedules and formats, with no single real-time view of institution-wide KPIs and
no drill-down from a KPI back to its source.
This worklet proposes an Executive Decision Support System that aggregates the four domains in parallel,
synthesizes institution-wide KPIs aligned to NIRF/NAAC and strategic-plan targets, and generates a leadership-
ready report with drill-down evidence back to the source department — turning scattered, lagging reports into
one auditable, real-time executive view.
Stakeholders: Principal/Director, Registrar, Deans, Governing Council
Problems heard
 Leadership reviews performance from separate departmental reports on different schedules and formats.
 There is no single, real-time view of institution-wide KPIs against NIRF/NAAC or strategic-plan targets.
 By the time a consolidated report reaches the Governing Council, the numbers are already weeks old.
 Drilling down from a KPI to the department or root cause requires going back to each department
    separately.
 Provisional, forecast, or unreconciled figures can be mistaken for final.

15.2 Target Final Solution (Definition of Done)
The capstone (Lab 14) is complete when, for a real case, the worklet turns a request into a validated, evidence-
grounded decision brief with options and risks that passes every check, is reviewed and approved by the
executive / leadership, and is published with a full audit trail — with light human edits, not a rewrite.
Capabilities
 Capability                                                     What it means
 Each                                                           Each department's academic, research, placement, and
                                                                finance systems are linked with institution-level read access
                                                                authorized by the Registrar.
 The                                                            The Academic, Research, Placement, and Finance agents each
                                                                aggregate their domain's metrics across departments, in
                                                                parallel.
 The                                                            The KPI Agent synthesizes the four domain views into
                                                                institution-wide KPIs aligned to NIRF/NAAC and strategic-plan
                                                                targets.
 The                                                            The Report Generation Agent compiles a leadership-ready
                                                                report with drill-down evidence back to the source
                                                                department and metric.
 Principal/Director/Registrar                                   Principal/Director/Registrar reviews the report, flags any KPI
                                                                needing clarification, and approves it for circulation.
 The                                                            The Governing Council receives the approved report at its
                                                                scheduled review cycle.

Success metrics (KPIs)
 100% of validation checks pass before the executive / leadership review (e.g. every figure cites its source).
 Every decision brief with options and risks is grounded in verified institutional data, with an evidence record.
 Zero consequential actions without the executive / leadership's approval; a complete audit trail and one-
    click rollback.

15.3 System at a Glance — the Node Graph

                                   Agentic AI Worklets — 14-Lab Build Book   |   Page 227
A coordinator-plus-workers system: the apniLeap AURA Coordinator holds the plan, run-state and audit log and
drives the pipeline; validation is a hard gate; the human review is a hard stop before publish.




   Figure 15 — the Executive Decision Support System agent graph. Amber = human gate; green = governed publish; dashed =
                                                    coordinator oversight.

End-to-end flow
 Each department's academic, research, placement, and finance systems are linked with institution-level read
    access authorized by the Registrar.
 The Academic, Research, Placement, and Finance agents each aggregate their domain's metrics across
    departments, in parallel.
 The KPI Agent synthesizes the four domain views into institution-wide KPIs aligned to NIRF/NAAC and
    strategic-plan targets.

                                    Agentic AI Worklets — 14-Lab Build Book   |   Page 228
    The Report Generation Agent compiles a leadership-ready report with drill-down evidence back to the
     source department and metric.
    Principal/Director/Registrar reviews the report, flags any KPI needing clarification, and approves it for
     circulation.
    The Governing Council receives the approved report at its scheduled review cycle.

15.4 Agent Roster — Roles, Communication & Guardrails
 #                             Agent                             Role & communication                  Guardrails
 0                             apniLeap AURA Coordinator         Receives the                          Never bypass human approval;
                                                                 leadership/Registrar prompt           enforce data scope, audit
                                                                 command, checks permissions,          logging, source citation, and
                                                                 creates the run plan, initializes     exception routing.
                                                                 agents, monitors state.
 1                             Academic Agent                    Aggregates pass percentage,           Pull only from approved
                                                                 CO/PO attainment, and                 records; show the underlying
                                                                 curriculum compliance across          spread; flag departments with
                                                                 departments, in parallel with B,      stale or missing data.
                                                                 C, D.
 2                             Research Agent                    Aggregates publications,              Pull only from validated
                                                                 citations, and grants across          records; never double-count a
                                                                 departments, in parallel with A,      cross-department
                                                                 C, D.                                 collaboration; cite the source
                                                                                                       system.
 3                             Placement Agent                   Aggregates placement                  Pull only from Placement-Cell-
                                                                 percentage, average package,          verified records; never present
                                                                 and internship completion, in         a provisional offer as a
                                                                 parallel with A, B, D.                confirmed placement; flag
                                                                                                       gaps.
 4                             Finance Agent                     Aggregates budget utilization,        Pull only from
                                                                 revenue, and grant funds at           audited/approved figures;
                                                                 institution level, in parallel with   never project a forecast as an
                                                                 A, B, C.                              actual; flag figures pending
                                                                                                       reconciliation.
 5                             KPI Agent                         Synthesizes the four domains          Use only approved KPI
                                                                 into institution-wide KPIs            definitions and targets; show
                                                                 aligned to NIRF/NAAC and              formula and source; never
                                                                 strategic-plan targets.               mask a missed target in a
                                                                                                       rounded figure.
 6                             Report Generation Agent           Compiles the executive report         Publish only approved figures;
                                                                 and dashboard with drill-down         keep drill-down traceable;
                                                                 evidence.                             version every executive report.
 7                             Principal / Registrar /           Reviews the report and KPIs,          Principal/Registrar/Council
                               Governing Council Review          flags items, approves for             decision is the final authority
                                                                 circulation; Council receives it      for circulating an executive
                                                                 on schedule.                          report.

15.5 Agent Interconnections (Message Map)
How the agents are wired — the payloads that flow between them and when. The last rows show the human
gate and governed publish.
 From                          To                                Message / payload                     When
 Coordinator                   Academic Agent                    run-context + task                    run start
 Academic Agent                Research Agent                    state / partial result                in pipeline

                                    Agentic AI Worklets — 14-Lab Build Book   |   Page 229
Research Agent                    Placement Agent                    state / partial result              in pipeline
Placement Agent                   Finance Agent                      state / partial result              in pipeline
Finance Agent                     KPI Agent                          state / partial result              in pipeline
KPI Agent                         Report Generation Agent            state / partial result              in pipeline
Report Generation Agent           Principal / Registrar /            state / partial result              in pipeline
                                  Governing Council Review
Principal / Registrar /           The Executive / Leadership gate    draft decision brief with           for review
Governing Council Review                                             options and risks + evidence
The Executive / Leadership        Coordinator                        approve | edit | override           human decision
gate
Coordinator                       Governance / Publish               final decision brief with options   on approval
                                                                     and risks (versioned)

15.6 Data Model
Entity                                                               Key fields
Domain metrics                                                       Academic, research, placement, and finance metrics
                                                                     aggregated across departments.
KPI definition                                                       Approved institution-wide KPI formulas and target values.
Target & variance                                                    NIRF/NAAC and strategic-plan targets with computed variance.
Drill-down evidence                                                  Traceable links from each KPI to its source department and
                                                                     metric.
Executive report                                                     Leadership-ready report and dashboard, pending approval.

15.7 Solution Paradigm — Pseudocode
Orchestrator (the whole run)
function run_executive_decision_support_system(request):
  ctx = Coordinator.new_run(request)          # isolated, checkpointed
  plan = Coordinator.build_plan(request) # locked before work begins
  ctx = AcademicAgent.step(ctx, plan)
  ctx = ResearchAgent.step(ctx, plan)
  ctx = PlacementAgent.step(ctx, plan)
  ctx = FinanceAgent.step(ctx, plan)
  ctx = KPIAgent.step(ctx, plan)
  ctx = ReportGenerationAgent.step(ctx, plan)
  ctx = PrincipalRegistrarGoverningCouncilReview.step(ctx, plan)
  report = ValidationAgent.validate(ctx, plan) # hard gate
  while not report.passed and attempts < MAX: # self-healing (Lab 10)
     Coordinator.regenerate(report.failing); report = validate(ctx, plan)
  draft = assemble(ctx)                   # the decision brief with options and risks
  decision = TheGate.review(draft) # HUMAN — final authority
  if decision.approved:
     final = apply(decision.edits, draft)
     Governance.publish(final, version=next()); Audit.log_all()
  return final



Validation (the acceptance gate)
function ValidationAgent.validate(ctx, plan):
  checks = [
   ('every figure cites its source', test_0(ctx, plan)),
   ('assumptions are stated explicitly', test_1(ctx, plan)),
   ('each option lists its risks and trade-offs', test_2(ctx, plan)),
   ('no action is taken without leadership approval', test_3(ctx, plan)),


                                        Agentic AI Worklets — 14-Lab Build Book   |   Page 230
   ]
   failing = [n for n,ok in checks if not ok]
   return Report(passed = not failing, failing = failing,
            diagnosis = explain(failing))



Connector (one governed surface for all sources)
 connector.expose:
   read('institutional KPIs & dashboards')
   read('department reports')
   read('external benchmarks')
 agents.use(connector) # no agent touches a source directly



Worked example — one decision / KPI, end to end
How a single decision / KPI travels through the pipeline, from plan to a validated, approved and published
decision brief with options and risks. This is the level of traceability every decision / KPI should have.
 Stage                                                                What happens
 Plan / slot                                                          The coordinator locks the plan and picks one decision / KPI to
                                                                      work — its constraints fixed before any content is chosen.
 Source candidate                                                     A retrieval agent proposes a candidate for this decision / KPI
                                                                      from institutional KPIs & dashboards, with provenance.
 Grounded candidate                                                   A generation agent produces a fresh candidate grounded in
                                                                      verified institutional data, attaching an evidence record
                                                                      (source, scope, tags).
 Screen & select                                                      Candidates are calibrated and screened; the best-aligned one
                                                                      that satisfies the plan is selected, the rest logged.
 Validation                                                           The result is checked (every figure cites its source; each option
                                                                      lists its risks and trade-offs); on failure only this decision / KPI
                                                                      is regenerated.
 Human review                                                         The Executive / Leadership sees the draft decision brief with
                                                                      options and risks with its evidence and validation report, and
                                                                      approves, edits or overrides.
 Publish & audit                                                      On approval the governed publish versions the decision brief
                                                                      with options and risks, records the audit trail, and updates
                                                                      history for future runs.

15.8 Hybrid Execution Methodology
How the coordinator runs each stage — what is human-gated, what runs in parallel, what is sequential.
 Stage                                                                Execution mode & coordinator behavior
 Gate 1: access intake                                                Sequential — start only after each domain grants institution-
                                                                      level read access authorized by the Registrar.
 Parallel domain aggregation                                          Parallel — Academic, Research, Placement, and Finance agents
                                                                      each aggregate at the same time.
 KPI synthesis                                                        Sequential — KPIs are computed only after all four domain
                                                                      agents return data.
 Report generation                                                    Sequential — the report is compiled after the KPI set is
                                                                      finalized.
 Stakeholder approval                                                 Sequential — Principal/Registrar approves before the
                                                                      Governing Council; corrections route back.


                                         Agentic AI Worklets — 14-Lab Build Book   |   Page 231
 Dashboard update                                              Parallel after approval — executive dashboard (KPIs, domain
                                                               metrics, report) publishes together.

15.9 Dashboard Template
What the executive / leadership sees to review, approve and monitor.
 Panel                                                         Shows
 Institution KPIs                                              KPIs against NIRF/NAAC and strategic-plan targets with
                                                               variance.
 Domain metrics                                                Academic, research, placement, and finance breakdowns.
 Drill-down evidence                                           Traceable path from each KPI to its source department and
                                                               metric.
 Executive report                                              Approved, versioned leadership report for the Governing
                                                               Council.

15.10 The 14-Lab Evolution
Each lab is a working increment that adds one capability to this worklet and activates specific nodes. Ship the
deliverable and pass acceptance before advancing — by Lab 14 they compose into the deployed decision brief
with options and risks system.




                                  Agentic AI Worklets — 14-Lab Build Book   |   Page 232
Lab 1 — Agent vs Chatbot — the decision brief with options and risks planner loop
Phase: A · Foundations     Goal: Establish the agent loop (clarify → plan → revise) instead of a one-shot chatbot
answer.

What it adds to this worklet. A minimal planner that clarifies the request, proposes a plan for producing the
decision brief with options and risks, and revises on feedback — the seed this worklet grows from.
 Inputs                         Outputs                             Agents / nodes             Deliverable & acceptance
 Free-text request; core        A clarified request + an editable   Coordinator (loop only).   A notebook agent that clarifies,
 parameters.                    outline plan for the decision                                  plans and revises a decision
                                brief with options and risks.                                  brief with options and risks


                                      Agentic AI Worklets — 14-Lab Build Book   |   Page 233
                                                                                                      outline. Accept: Given a vague
                                                                                                      request it asks at least two
                                                                                                      clarifying questions and yields
                                                                                                      a coherent, editable plan.
Nodes activated. Coordinator loop (no specialist nodes yet).
Pitfall to avoid. Don't answer in one shot — without clarify/revise it's a chatbot, not an agent.
Lab 1 — plan & revise
 req = clarify(user_request)     # ask until inputs complete
 plan = propose_plan(req)         # outline for the decision brief with options and risks
 while user.wants_changes(plan): plan = revise(plan, user.feedback)
 return plan              # not final — a structured plan



Lab 2 — Tool-Using Agent — call data & compute
Phase: A · Foundations       Goal: Give the agent tools it must call to act, rather than answering from memory.

What it adds to this worklet. Readers for institutional KPIs & dashboards and department reports, plus a
domain calculator/checker, so the planner acts on real data.
 Inputs                             Outputs                            Agents / nodes                 Deliverable & acceptance
 institutional KPIs & dashboards;   Verified computed values and       Coordinator + tool layer.      An agent that reads
 department reports;                parsed inputs.                                                    institutional KPIs & dashboards
 parameters.                                                                                          and computes/validates
                                                                                                      through typed tools. Accept:
                                                                                                      Key numbers and lookups
                                                                                                      always go through tools, never
                                                                                                      hand-done in the prompt.
Nodes activated. Tool layer feeding the early data agents.
Pitfall to avoid. Never assert a fact in the prompt that a tool should verify.
Lab 2 — typed tools
 a = tool.read('institutional KPIs & dashboards')
 b = tool.read('department reports')
 v = tool.compute(a, b)
 assert v.valid



Lab 3 — Skill Creation — reusable plan & format skills
Phase: A · Foundations       Goal: Package repeatable capability as reusable, schema-typed skills.

What it adds to this worklet. A plan/blueprint skill and a formatting skill that renders the decision brief with
options and risks — both reusable across cases.
 Inputs                             Outputs                            Agents / nodes                 Deliverable & acceptance
 Parsed inputs; template spec.      A locked plan object; a            Planning and assembly emerge   Two callable skills with
                                    formatted decision brief with      as skills.                     schemas, invoked by the agent.
                                    options and risks shell.                                          Accept: The same skill works
                                                                                                      for two different cases without
                                                                                                      code changes.
Nodes activated. Plan node + Assembly node (as skills).
Pitfall to avoid. Keep skills case-agnostic and typed; hard-coding one case breaks reuse.
Lab 3 — skill interface
 skill plan(inputs) -> Plan: return expand(inputs).lock()
 skill format_decision(result, template) -> Document



                                          Agentic AI Worklets — 14-Lab Build Book   |   Page 234
Lab 4 — Memory & Retrieval — state vs stored
Phase: A · Foundations         Goal: Separate short-term run state from long-term stored knowledge.

What it adds to this worklet. Session state (the current draft) vs stored reference — institutional KPIs &
dashboards and the history of past decision / KPIs — retrieved by tags and by similarity.
 Inputs                               Outputs                            Agents / nodes                    Deliverable & acceptance
 institutional KPIs & dashboards;     Tag- and similarity-based          Retrieval agent; foundations of   Retrieval over the store +
 history of prior decision / KPIs;    retrieval.                         later screening.                  history with tag filters and
 current draft.                                                                                            embedding similarity. Accept:
                                                                                                           For a given task, retrieval
                                                                                                           returns correctly-tagged
                                                                                                           candidates and similar prior
                                                                                                           items.
Nodes activated. Retrieval node; seeds validation/no-repeat.
Pitfall to avoid. Don't conflate run state with the archive — mixing them corrupts the baseline.
Lab 4 — memory split
 state.draft = candidate             # short-term
 hits = retrieve(store, tags)        # long-term
 prior = retrieve(history, embed(candidate), k=5) # similarity



Lab 5 — MCP-Style Connector — one server for all sources
Phase: A · Foundations         Goal: Expose every data source through one typed connector.

What it adds to this worklet. A single connector fronting institutional KPIs & dashboards, department reports
and external benchmarks so every agent reaches data the same governed way.
 Inputs                               Outputs                            Agents / nodes                    Deliverable & acceptance
 The worklet's data sources.          A uniform, typed tool surface.     Connector used by all data-       A connector server with typed
                                                                         facing agents.                    endpoints and auth; agents call
                                                                                                           only through it. Accept: All
                                                                                                           data access goes through the
                                                                                                           connector; swapping a source
                                                                                                           needs no agent change.
Nodes activated. Connector under the data agents.
Pitfall to avoid. No agent should touch a source directly; a bypass defeats governance later.
Lab 5 — connector
 connector.expose:
   read('institutional KPIs & dashboards')
   read('department reports')
   read('external benchmarks')
 agents.use(connector) # no agent touches a source directly



Lab 6 — Runtime — skills, tools, memory, audit
Phase: A · Foundations         Goal: Run the agent inside a controlled runtime with a full audit log.

What it adds to this worklet. A runtime binding skills + tools + memory behind the loop, enforcing budgets and
approval gates and logging every step — the backbone later labs plug into.
 Inputs                               Outputs                            Agents / nodes                    Deliverable & acceptance
 Skills (Lab 3), connector (Lab 5),   A governed run with audit +        Coordinator hardened into the     Runtime wrapping the agent:
 memory (Lab 4).                      checkpoints.                       runtime controller.               budgets, gates,


                                            Agentic AI Worklets — 14-Lab Build Book   |   Page 235
                                                                                                        checkpoint/resume, audit log.
                                                                                                        Accept: Every action is logged
                                                                                                        with inputs/outputs; a crashed
                                                                                                        run resumes from its last
                                                                                                        checkpoint.
Nodes activated. Coordinator runtime around all nodes.
Pitfall to avoid. Log inputs and outputs, not just messages; checkpoint before risky steps or resume loses state.
Lab 6 — controlled loop
 run = Runtime(budget=B, gates=[publish])
 for step in agent.loop():
   audit.log(step.intent, step.action, step.result)
   if step.risky: wait_for_approval(step)
   checkpoint(run.state)



Lab 7 — Agentic Node Graph — the full pipeline
Phase: B · Orchestration      Goal: Wire the specialist agents into one explicit graph with state and branching.

What it adds to this worklet. The complete pipeline as a node graph: Academic Agent, Research Agent,
Placement Agent → … → the executive / leadership gate → publish, with a validation → regenerate back-edge.
 Inputs                            Outputs                            Agents / nodes                    Deliverable & acceptance
 All Phase-A skills/agents.        An executable graph producing      All core agents connected (see    A graph runner that produces a
                                   a first end-to-end draft.          this chapter's node graph).       full decision brief with options
                                                                                                        and risks draft end to end.
                                                                                                        Accept: One command yields a
                                                                                                        validated decision brief with
                                                                                                        options and risks draft end to
                                                                                                        end.
Nodes activated. All core nodes + the back-edge.
Pitfall to avoid. Bound the retry edge — an unbounded regenerate loop can spin forever.
Lab 7 — graph
 graph.chain(ingest -> plan -> workers -> validate)
 graph.edge(validate --fail--> workers) # bounded retry
 graph.edge(validate --pass--> assemble -> gate -> publish)



Lab 8 — Parallel Swarm — many decision / KPIs, then merge
Phase: B · Orchestration      Goal: Parallelise the per-unit work and select the best.

What it adds to this worklet. Several worker agents process decision / KPIs in parallel; a merge/selector picks
the best per the plan — cutting latency and improving quality.
 Inputs                            Outputs                            Agents / nodes                    Deliverable & acceptance
 Locked plan; per-unit work        Best-of-N results merged into      Parallel workers + a Merge        A fan-out/fan-in that processes
 items.                            one compliant output.              selector under the Coordinator.   all units and merges by
                                                                                                        alignment to the plan. Accept:
                                                                                                        Parallel run matches or beats
                                                                                                        sequential quality at lower
                                                                                                        wall-clock time.
Nodes activated. Parallel worker fan-out + merge.
Pitfall to avoid. Merge strictly by plan alignment; picking the 'nicest' output quietly breaks coverage.
Lab 8 — fan-out/in
 results = parallel_map(process_decision, plan.units)

                                         Agentic AI Worklets — 14-Lab Build Book   |   Page 236
 output = merge(results, key=alignment_to(plan))



Lab 9 — Deep Research — ground & evidence
Phase: C · Applied reliability    Goal: Ground every output in cited, in-scope evidence.

What it adds to this worklet. For each decision / KPI the agent builds an evidence record grounded in verified
institutional data, so validity is auditable and out-of-scope content can't slip through.
 Inputs                            Outputs                            Agents / nodes                   Deliverable & acceptance
 verified institutional data;      An evidence record per unit; a     Generation + grounding step      Each candidate carries an
 candidate outputs.                paper-level evidence table.        feeding Validation.              evidence record; an evidence
                                                                                                       table is produced. Accept:
                                                                                                       Every output maps to an in-
                                                                                                       scope source; ungrounded
                                                                                                       candidates are rejected.
Nodes activated. Grounding step into the validation check.
Pitfall to avoid. Require a real source; a plausible-sounding but ungrounded item must be rejected, not kept.
Lab 9 — grounding
 for c in candidates:
   ev = research(c, source='verified institutional data')
   if not ev.in_scope: reject(c)
   c.evidence = ev



Lab 10 — Ops Resilience — validate, diagnose, fix
Phase: C · Applied reliability    Goal: Make the pipeline self-healing when validation fails.

What it adds to this worklet. When a check fails (every figure cites its source; assumptions are stated explicitly),
the agent diagnoses the exact failing constraint and regenerates only the offending part.
 Inputs                            Outputs                            Agents / nodes                   Deliverable & acceptance
 Validation report; current        A repaired, passing output with    Validation agent +               Failure-injection tests showing
 output.                           a diagnosis log.                   Coordinator's regenerate loop.   automatic diagnosis and
                                                                                                       targeted repair. Accept:
                                                                                                       Injected faults are detected
                                                                                                       and fixed within the retry
                                                                                                       budget.
Nodes activated. Validation node + self-healing loop.
Pitfall to avoid. Regenerate only the failing part — rebuilding everything wastes budget and churns good work.
Lab 10 — diagnose & fix
 report = validate(output, plan)
 while not report.passed and attempts < BUDGET:
    regenerate(report.failing); report = validate(output, plan)
 if not report.passed: escalate(report) # to the human



Lab 11 — SDLC Factory — spec → tested output
Phase: C · Applied reliability    Goal: Treat the plan as a spec and the output as a tested implementation.

What it adds to this worklet. The worklet becomes a factory: plan in, a decision brief with options and risks out
that provably passes an automated acceptance suite before the executive / leadership sees it.
 Inputs                            Outputs                            Agents / nodes                   Deliverable & acceptance


                                         Agentic AI Worklets — 14-Lab Build Book   |   Page 237
 The locked plan (spec); the      A result plus a green test         Validation as the test harness;   A 'build' command: plan →
 acceptance suite.                report.                            Coordinator as the build.         decision brief with options and
                                                                                                       risks + passing acceptance
                                                                                                       report. Accept: No decision
                                                                                                       brief with options and risks
                                                                                                       advances to the executive /
                                                                                                       leadership without a fully
                                                                                                       passing acceptance report.
Nodes activated. Validation gates the whole graph.
Pitfall to avoid. The acceptance suite is the gate; never let a result skip to the human without a green report.
Lab 11 — spec→artifact
 artifact = build(plan)      # graph run (Lab 7/8/10)
 report = acceptance_suite(artifact, plan)
 require report.all_pass       # gate before human review



Lab 12 — Safety & Governance — approval, eval, rollback
Phase: D · Governance & capstone         Goal: Add confidentiality, approval, evaluation and rollback.

What it adds to this worklet. Access control and confidentiality, the the executive / leadership approval gate as
a hard stop, evaluation metrics, versioning and one-click rollback.
 Inputs                           Outputs                            Agents / nodes                    Deliverable & acceptance
 Draft-vs-approved states; role   A governed, reversible release.    Governance & Audit agent; the     Approval workflow + metrics +
 permissions; metrics.                                               human gate formalised.            rollback, with confidentiality
                                                                                                       controls. Accept: Only the
                                                                                                       executive / leadership-
                                                                                                       approved results publish; any
                                                                                                       release rolls back cleanly.
Nodes activated. Human gate + governance node.
Pitfall to avoid. Confidentiality and rollback are requirements, not extras.
Lab 12 — governed release
 require actor.can_approve and out.status=='draft'
 final = apply(human.edits, out); final.status='approved'
 governance.publish(final, version=v+1); metrics.record(...)
 on rollback(v): restore(version=v)



Lab 13 — Discipline-Specific Agents — domain specialisation
Phase: D · Governance & capstone         Goal: Specialise the worklet to its domain variants.

What it adds to this worklet. Pluggable specialists — domain packs (academics, finance, operations) — so
outputs match the specific style and constraints of each case.
 Inputs                           Outputs                            Agents / nodes                    Deliverable & acceptance
 Domain profile; the work item.   Domain-appropriate outputs         Specialist plugged into the       A specialist producing domain-
                                  with correct schemes.              generation node.                  correct decision brief with
                                                                                                       options and riskss. Accept:
                                                                                                       Specialist outputs use valid
                                                                                                       domain patterns and produce
                                                                                                       checkable results.
Nodes activated. Specialist into the generation node.
Pitfall to avoid. Every specialist output needs a checkable scheme; clever but vague outputs are unusable.
Lab 13 — specialist plug-in

                                        Agentic AI Worklets — 14-Lab Build Book   |   Page 238
 specialist = registry.get(domain)
 out = specialist.generate(item)
 GenerationAgent.use(specialist)



Lab 14 — Capstone — team-owned system
Phase: D · Governance & capstone         Goal: Integrate everything into a deployed, team-owned system.

What it adds to this worklet. The full worklet: connector + runtime + node graph + parallel work + grounding +
self-healing + governance + specialists, with a the executive / leadership dashboard — delivered and demoed
end to end.
 Inputs                           Outputs                           Agents / nodes                 Deliverable & acceptance
 All prior lab deliverables.      A deployed worklet: request →     All agents under the           Deployed system + the
                                  approved, published decision      Coordinator (this chapter's    executive / leadership
                                  brief with options and risks.     node graph).                   dashboard + audit trail + a
                                                                                                   demo on a real case. Accept:
                                                                                                   The Executive / Leadership
                                                                                                   produces an approved,
                                                                                                   validated decision brief with
                                                                                                   options and risks in one
                                                                                                   session.
Nodes activated. Every node, deployed.
Pitfall to avoid. Integrate, don't rewrite — if the labs kept the contracts, the capstone is wiring.
Lab 14 — end-to-end
 system = deploy(connector, runtime, graph, governance)
 artifact = system.run(request)    # the decision brief with options and risks
 dashboard.show(artifact, metrics, audit)



15.11 Reference Architecture, Pilot & MVP
Reference architecture
 Data capture: department academic, research, placement, and finance systems (read access).
 Data layer: institution-wide schema for domain metrics, KPI definitions, targets, and evidence.
 AI layer: cross-department aggregation, KPI synthesis, variance analysis, report generation.
 Workflow layer: Registrar-authorized access, Principal/Registrar review queue, dashboard, Council
    distribution.
 Governance layer: read-access control, no-forecast-as-final rule, drill-down traceability, audit log.
Pilot artifacts
 An institution-level read-access connector to each domain system for one review cycle.
 A KPI synthesis engine with approved NIRF/NAAC target definitions.
 A report-generation pipeline with drill-down links.
 An executive dashboard with an exportable leadership report.
Suggested MVP roadmap
 Order                            Capability                        What it delivers               Agents involved
 1                                Domain aggregation                Academic, research,            Coordinator, Domain Agents.
                                                                    placement, and finance
                                                                    metrics.
 2                                KPI synthesis                     Institution-wide KPIs with     KPI Agent.
                                                                    targets and variance.


                                       Agentic AI Worklets — 14-Lab Build Book   |   Page 239
 3                            Report generation                     Leadership report with drill-         Report Generation Agent.
                                                                    down evidence.
 4                            Approval workflow                     Principal/Registrar review and        Principal/Registrar Review.
                                                                    circulation.
 5                            Drill-down                            Trace any KPI to its source           Report Generation Agent.
                                                                    department.
 6                            Executive dashboard                   KPIs, domain metrics, and             Coordinator.
                                                                    report in one view.

Risks & mitigations
 Risk                                      Why it matters                                     Mitigation (where handled)
 Plan drift                                individual results deviate from the locked         Lock the plan (Lab 3/7); validation rejects
                                           plan                                               any deviation before the human sees it.
 Ungrounded output                         content not backed by verified institutional       Grounded generation with an evidence
                                           data                                               record per unit (Lab 9); ungrounded items
                                                                                              are rejected.
 Failed checks slip through                a result violates a rule (every figure cites its   Validation is a hard gate (Lab 10/11); failing
                                           source)                                            results are diagnosed and regenerated,
                                                                                              never advanced.
 Runaway loops                             the regenerate loop never converges                Bound MAX_ATTEMPTS (Lab 7/10); on
                                                                                              exhaustion, escalate to the executive /
                                                                                              leadership with a diagnosis.
 Over-automation                           the system acts without the executive /            The human gate is a hard stop; all outputs
                                           leadership                                         are drafts; edits and overrides are
                                                                                              effortless and logged (Lab 12).

15.12 Guardrails, Metrics, Milestones & Glossary
Guardrails
 Do not circulate an institution-wide KPI or executive report without Principal/Director/Registrar approval.
 Keep department-level detail traceable but access-controlled.
 Never present a forecast, provisional figure, or unreconciled number as final.
 Use only approved KPI definitions and targets; show the formula and source behind every KPI.
 Version every executive report and keep an audit log of circulation.
Delivery milestones
 Week                         Labs                                  Focus                                 Exit deliverable
 Week 1                       Labs 1–3                              Planner loop, tools, reusable         Runnable planner + core skill
                                                                    skills
 Week 2                       Labs 4–6                              Memory/retrieval, connector,          Data via connector; audited
                                                                    governed runtime                      runs
 Week 3                       Labs 7–8                              Full node graph + parallel            End-to-end draft — shared
                                                                    processing                            with faculty
 Week 4                       Labs 9–10                             Grounding + self-healing              Grounded output; auto-
                                                                    validation                            repair on faults
 Week 5                       Labs 11–12                            Tested build +                        Tested artifact; approval,
                                                                    safety/governance                     metrics, rollback
 Week 6                       Labs 13–14                            Domain specialisation +               Deployed system + demo on
                                                                    capstone                              a real case
 Checkpoint: from the 3rd week, worklets are shared with all faculty for feedback — plan the Week-3 end-to-end
 draft (Labs 7–8) to be demo-ready.


                                     Agentic AI Worklets — 14-Lab Build Book      |   Page 240
Glossary
 Term                                            Meaning
 Coordinator                                     The orchestrator agent that owns run-state, plan, budgets and
                                                 the audit log.
 Node graph                                      The explicit wiring of agents, gates and back-edges for one
                                                 worklet.
 Human gate                                      The approval step; the named human is the final authority.
 Grounding                                       Linking an output to a real in-scope source (evidence).
 Validation                                      The automated acceptance gate a result must pass before
                                                 human review.
 Blueprint / plan                                The locked specification the pipeline obeys.




                    Agentic AI Worklets — 14-Lab Build Book   |   Page 241
```
