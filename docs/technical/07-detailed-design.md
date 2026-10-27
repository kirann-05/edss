# 7. Detailed design

For each module: its job, the candidate algorithms considered, the one chosen and why, and pseudocode with inputs and outputs. Names in `code` are the real functions. Decisions referred to as D-numbers are in `docs/DECISIONS.md`.

## M1. Ingestion and reconciliation (`app/ingestion/`)

**Job.** Turn a folder of department exports into immutable, validated records, and say plainly what was refused and what is missing.

| Candidate | Verdict |
| --- | --- |
| Load everything, fix later | Rejected: bad rows would reach figures |
| Reject the whole file on one bad row | Rejected: one typo would block a department |
| **Validate row by row, keep the good rows, report each refused row with its reason, never change an earlier record** | Chosen |

```text
ingest_folder(folder, today, data_mode) -> FolderResult
  input : manifest.yml naming each source and file; departments.csv
  output: accepted records (immutable), refused rows with reasons, files that could not be read
  read departments from the manifest
  for each source in the manifest:
      adapter = CsvAdapter or SqlAdapter (column map from the manifest)
      if the file's checksum was loaded before: skip (adds nothing)
      for each row:
          reasons = validate(row)   # department known, metric in catalogue, period valid,
                                    # status and as_of present, numerator <= denominator ...
          if reasons: refuse(row, reasons)
          else: add MetricFact(batch, source_ref = file:row)
  current figures = newest batch per (department, metric, period, sub-period)
```

## M2. KPI engine (`app/kpi/engine.py`, `formulas.py`)

**Job.** Compute every KPI exactly, from approved definitions, with target, variance and status. No model involved.

| Candidate | Verdict |
| --- | --- |
| Hard-code each KPI in Python | Rejected: a new IQAC definition would need a code change |
| Let the model compute | Rejected by rule 1 |
| `eval` a formula string | Rejected: unsafe |
| **A small whitelisted formula grammar (`sum`, `mean`, `weighted_mean`, `unique_publications`, + - * /), parsed with Python's `ast` and evaluated on `Decimal`** | Chosen: definitions are data, evaluation is exact and safe |

```text
compute(definition, period) -> KpiResult
  input : formula e.g. 100 * sum("plc.placed_confirmed") / sum("plc.registered"); facts for the period
  output: value, target, variance, status, per-department values, input fact ids, flags
  parsed = parse_formula(formula)          # refuses anything outside the grammar
  for each department:
      facts = final or audited facts only  # provisional, forecast, unreconciled kept out (rule 4)
      if none: mark missing (never zero)
      value_d = evaluate(parsed, [d])      # division by zero gives UNDEFINED, not 0 or 100
  value = evaluate(parsed, eligible departments)   # from totals, never an average of percentages (rule 11)
  status = judge(value, target, higher_is_better, band_pct)

judge(value, target, higher_is_better, band_pct) -> (status, variance)
  favourable = (value - target) if higher_is_better else (target - value)
  if favourable < 0:                         missed      # on the unrounded value (rule 5)
  elif favourable < |target| * band_pct/100: at risk
  else:                                      met
```

Worked example (trap T6): 937 placed of 1,250 registered gives 74.96 against a target of 75. Favourable = -0.04, so **missed**, although it displays as 75.0.

## M3. Planner (`app/agents/skills/plan_skill.py`)

**Job.** Turn a vague request into a plan a person can edit and lock.

| Candidate | Verdict |
| --- | --- |
| Rules only | Fast and predictable, but misses unusual wording |
| Model only | Measured: right questions 4 of 10, plans fully right 4 of 6 |
| **Hybrid: rules read the request first, the model only fills what the rules could not read, a person edits and locks** | Chosen (D30): 9 of 10 and 6 of 6, with 6 model calls instead of 16 |

```text
clarify(request, answers) -> questions
  slots = rules_read(request)            # period ("last year" -> previous period), areas, audience
  missing = slots not read
  if missing and a model is configured: ask the model only about the missing slots
  return a question for each slot still unknown (with the real choices)

propose_plan(request, answers) -> Plan(revision 1)
lock_plan(plan) -> locked plan               # refused if no area or no KPI
```

## M4. Domain fan-out and scoped reading (`app/agents/graph.py`, `app/mcp_connector/`)

**Job.** Read each planned area in parallel, only through the connector, only within the plan's areas.

```text
access_check(state) -> scope
  for each planned area: require an active, unexpired Registrar grant, else stop the run
fan_out_domains(state) -> [Send("domain_agent", area) for each planned area]
domain_agent(area) -> DomainView
  facts = connector.get_domain_metrics(area, period)   # MCP call with the run's token
  # outside the token's areas: refused and audited (connector.refused)
kpi_synthesis(all DomainViews) -> figures              # the join waits for every agent
```

## M5. Option drafting with reference tokens (`app/agents/skills/options_skill.py`, `tokens.py`)

**Job.** Draft two or three options per off-target KPI, in words, without the model ever writing a number.

| Candidate | Verdict |
| --- | --- |
| Give the model the numbers and trust it | Rejected: models round, invent and miscopy |
| Strip numbers after generation | Rejected: loses meaning, cannot tell a real figure from an invented one |
| **The model writes `{{kpi:KEY}}` and `{{fact:ID}}` tokens; code fills each from the engine; any bare number is a violation** | Chosen |

```text
draft_option_set(model, figure, pack) -> OptionSet
  input : KPI name, status, the tokens it may use, the framework pack's guidance
  output: 2 or 3 options, each with title, description, assumptions, risks, trade-offs
  draft = model.generate("draft_options", payload, schema=OptionSet, check=code_side_check)
  # code_side_check: token keys exist, 2 to 3 options, risks and trade-offs present
render(text, context) -> text with figures   # done at display time from engine values
```

## M6. Validation gate and targeted repair (`app/agents/validation/`, `app/agents/repair.py`)

**Job.** No draft reaches a person unless all nine checks pass, or it is escalated with a diagnosis.

| Candidate | Verdict |
| --- | --- |
| Ask a model to review the draft | Rejected: not deterministic, cannot be proved |
| Regenerate the whole brief on any failure | Rejected: slow, and can break parts that were fine |
| **Nine deterministic checks returning violations with a locator (KPI, option, field, section); repair only what failed; at most 3 attempts** | Chosen |

```text
validate(brief, context) -> ValidationReport
  for check in [V1 .. V9]:
      violations += check(brief, context)      # each with locator and the fix kind
  passed = no violations

loop (graph edge validate -> regenerate -> validate):
  report = validate(brief)
  if report.passed: draft (green) -> human gate
  attempts += 1
  if attempts >= MAX_ATTEMPTS (3): escalate with the diagnosis -> human gate
  for each violation, by fix kind:
      regenerate_options -> redraft only that KPI's options
      rebuild_figure     -> recompute only that figure from the engine
      rebuild_sections   -> rebuild assumptions or data health from the facts
      reset_status       -> recompute the status from unrounded values
```

## M7. Governance (`app/governance/service.py`)

**Job.** Let only an authorised, named person publish, and keep every version.

```text
approval_state(brief) -> can_approve, needs_acknowledgement, reason
  if decided: no
  if validation passed: yes
  if escalated and any integrity check failed (V1 V4 V5 V6 V7 V9): no, send back or override only
  if escalated and only completeness failed (V2 V3 V8): yes, with a recorded acknowledgement

decide(brief, person, decision) -> result
  require permission "approve"; require a reason for override and send back
  if edit: apply edits, re-validate (same nine checks), refuse if any fails
  publish: new immutable version N, pointer -> N, add to the archive, audit
rollback(person, to_version, reason) -> pointer -> to_version; nothing deleted; audit
diff(a, b) -> changed figures (never shown as two identical texts), options, assumptions
```

## M8. Audit hash chain (`app/governance/audit.py`, `app/db/audit_store.py`)

| Candidate | Verdict |
| --- | --- |
| Ordinary log table | Rejected: rows can be edited silently |
| External ledger or blockchain | Rejected: real data may not leave the machine, and it is far heavier than needed |
| **SHA-256 hash chain over canonical JSON, one writer at a time, plus database permissions and a trigger** | Chosen |

```text
append(actor, action, inputs, outputs) -> AuditRow
  lock (advisory lock in PostgreSQL)
  previous = last row's hash, or the genesis hash
  hash = SHA256(previous + time + run + actor + action + canonical(inputs) + canonical(outputs))
  insert row; unlock
verify(rows) -> ok, or the first row whose hash does not match
```

## M9. Data health (`app/services/store.py`, `app/kpi/engine.py`)

```text
health(department, area, period) -> state
  facts = records for that cell
  if none: missing
  elif period is closed: closed year
  elif today - oldest as_of > stale_after_days (90): stale, with its age
  else: fresh
  also counts provisional, forecast and pending-reconciliation records
```

## M10. Similar prior briefs (`app/services/archive.py`, `app/db/archive_store.py`)

| Candidate | Verdict |
| --- | --- |
| Keyword search | Weak on paraphrase |
| **In memory: Jaccard overlap of off-target KPI keys. In PostgreSQL: cosine distance on pgvector embeddings of the brief's words (never its figures), with a hashing embedder fallback when no model is running** | Chosen |

```text
similar(draft, limit 3) -> prior briefs with the shared KPIs and a reason
  memory   : score = |off_target_now ∩ off_target_before| / |union|; best first, then most recent
  database : order by embedding <=> embed(words of the draft) limit 3
```
