# DATA CONTRACT

This mirrors sections 4 to 9 of the Data Requirements Specification sent to the HOD. When real extracts arrive, adapters map them into these tables. If the university's columns differ, change the adapter, never the agents.

## 1. Enums

- `domain`: academic, research, placement, finance, reference
- `status`: final, audited, provisional, forecast, pending_reconciliation
- `kpi_framework`: NIRF, NAAC, STRATEGIC
- `kpi_status`: met, at_risk, missed, undefined
- `data_mode`: synthetic, real
- `brief_status`: draft, escalated, approved, published, rolled_back, overridden

## 2. Tables

```
department(code PK, name, school, active)

source_system(id PK, name, owner_office, kind)         -- csv, sql, api

ingest_batch(id PK, source_system_id, data_mode, started_at, finished_at,
             row_count, rejected_count, file_ref, checksum, ingested_by)

metric_fact(id PK, batch_id FK, domain, metric_key, dept_code FK,
            period_year, period_sub,                   -- e.g. 2025-26, S1 or Q3
            value NUMERIC, numerator NUMERIC NULL, denominator NUMERIC NULL, unit,
            status, as_of DATE, source_system_id FK, source_ref TEXT,
            recorded_at, UNIQUE(batch_id, domain, metric_key, dept_code, period_year, period_sub))

research_publication(id PK, batch_id FK, dedup_key,    -- DOI or internal id
                     title, venue, year, indexing, status)
publication_author_dept(publication_id FK, dept_code FK)

kpi_definition(id PK, key, name, framework, domain_tags, formula, unit,
               higher_is_better BOOL, version INT, approved_by, approved_on,
               active BOOL, placeholder BOOL)          -- placeholder true until IQAC supplies it

kpi_target(id PK, kpi_key, period_year, target_value, framework, source_doc, placeholder BOOL)

scope_grant(id PK, domain, dept_code NULL, granted_by, granted_on, expires_on, active)

run(id PK, request, clarifications JSONB, plan JSONB, plan_locked_at,
    status, attempts, created_by, created_at, finished_at)

kpi_result(id PK, run_id FK, kpi_key, kpi_version, period_year, value NUMERIC NULL,
           target NUMERIC, variance_abs, variance_pct, status,
           input_fact_ids BIGINT[], flags JSONB)       -- stale, provisional_inputs, undefined

evidence(id PK, run_id FK, claim_id, kpi_result_id FK, fact_ids BIGINT[],
         source_systems TEXT[], scope TEXT, tags TEXT[])

brief(id PK, run_id FK, status, content JSONB, rendered_md TEXT,
      validation JSONB, created_at)

brief_version(id PK, brief_id FK, version INT, content JSONB, rendered_md TEXT,
              approved_by, approved_at, edits JSONB, reason, created_at)

system_pointer(name PK, brief_version_id FK, updated_by, updated_at)   -- 'current_report'

audit_log(id PK, ts, run_id NULL, actor_type, actor_id, action,
          inputs JSONB, outputs JSONB, prev_hash, hash)

app_user(id PK, email UNIQUE, name, role, dept_code NULL, active, password_hash)

system_config(key PK, value)                           -- includes data_mode

brief_embedding(brief_id FK, kpi_key NULL, embedding VECTOR, tags TEXT[])
```

## 3. Metric catalogue

Keys are stable. Adapters map source columns onto them.

| Domain | metric_key | Meaning |
| --- | --- | --- |
| academic | acad.students_appeared | Students who appeared in exams |
| academic | acad.students_passed | Students who passed |
| academic | acad.co_attainment | CO attainment level (value) with target level in numerator-free form |
| academic | acad.po_attainment | PO attainment level |
| academic | acad.courses_total | Courses offered |
| academic | acad.courses_approved_syllabus | Courses with approved syllabus |
| academic | acad.courses_current_revision | Courses on the current revision |
| academic | acad.courses_outcome_mapped | Courses with outcome mapping |
| research | res.publications_count | Publications (department credit) |
| research | res.citations_count | Citations with source and as-of |
| research | res.grant_sanctioned | Sanctioned grant amount (INR lakh) |
| research | res.grant_count | Grants sanctioned |
| placement | plc.eligible | Students eligible |
| placement | plc.registered | Students registered |
| placement | plc.placed_confirmed | Offers verified by the Placement Cell |
| placement | plc.offers_provisional | Offers not yet confirmed (always separate) |
| placement | plc.package_avg_lpa / plc.package_median_lpa / plc.package_max_lpa | Package statistics |
| placement | plc.intern_required / plc.intern_completed | Internship counts |
| finance | fin.budget_sanctioned | Sanctioned budget (INR lakh) |
| finance | fin.expenditure_actual | Expenditure (audited or approved only as actual) |
| finance | fin.revenue_actual / fin.revenue_forecast | Revenue, forecast kept separate and status forecast |
| finance | fin.grant_received / fin.grant_utilized | Grant funds |
| reference | ref.faculty_count / ref.enrolled_students / ref.sanctioned_intake | Denominators |

Institution-level publications come from `research_publication` deduplicated on `dedup_key`, not from summing department counts.

## 4. Placeholder KPI seed (not real definitions)

All rows carry `placeholder = true` and the marker `PLACEHOLDER_PENDING_IQAC`. Targets here exist so the synthetic demo has misses to talk about. Replace with the university's approved list. Do not map these to NIRF or NAAC parameter codes until IQAC and the official framework documents say how.

| Key | Name | Formula (over metric keys) |
| --- | --- | --- |
| AC_PASS_PCT | Overall pass percentage | 100 * sum(acad.students_passed) / sum(acad.students_appeared) |
| AC_CO | Average CO attainment | course-weighted mean of acad.co_attainment |
| AC_PO | Average PO attainment | programme-weighted mean of acad.po_attainment |
| AC_CURR | Curriculum compliance percentage | 100 * sum(acad.courses_current_revision) / sum(acad.courses_total) |
| RS_PUB_PF | Publications per faculty | unique publications / sum(ref.faculty_count) |
| RS_CIT_PP | Citations per publication | sum(res.citations_count) / unique publications |
| RS_GRANT_PF | Grant funding per faculty | sum(res.grant_sanctioned) / sum(ref.faculty_count) |
| PL_PCT | Placement percentage | 100 * sum(plc.placed_confirmed) / sum(plc.registered) |
| PL_AVG | Average package | weighted by confirmed placements |
| PL_INT | Internship completion percentage | 100 * sum(plc.intern_completed) / sum(plc.intern_required) |
| FN_UTIL | Budget utilisation percentage | 100 * sum(fin.expenditure_actual) / sum(fin.budget_sanctioned) |
| FN_GRANT_UTIL | Grant utilisation percentage | 100 * sum(fin.grant_utilized) / sum(fin.grant_received) |
| FN_REV | Revenue (actual) | sum(fin.revenue_actual), forecast shown separately |

Whether placement percentage uses eligible or registered as denominator is a university decision. Make it a one-line change in the definition row.

## 5. Open data rules to confirm with IQAC

- Cross-department publication credit: institution counts once, each participating department is credited. Needs confirmation.
- Whether provisional offers count anywhere. Default: never in placement percentage.
- How stale is stale. Default: `STALE_AFTER_DAYS=90` from as_of.
- Rounding and display precision per KPI.

## 6. Synthetic dataset

`backend/app/synthetic/generator.py`, deterministic with seed 42. 8 departments, 3 academic years (2023-24 to 2025-26), semester or quarter granularity as appropriate, realistic volumes. It must be good enough to demo and to test. It plants these traps on purpose, each with a test that asserts the system handles it:

| Trap | What is planted | Expected handling |
| --- | --- | --- |
| T1 | One department's placement data has as_of more than 120 days old | Flagged stale, shown in data health and in the brief assumptions |
| T2 | One department has no research data for the latest year | Flagged missing, not treated as zero |
| T3 | About 12% of offers are provisional | Excluded from placement percentage, shown separately with badge |
| T4 | Final finance quarter has revenue_forecast rows | Never summed into actuals |
| T5 | Two departments share one DOI | Counted once at institution level, credited to both departments |
| T6 | A KPI computes to 74.96 against a target of 75 | Displays as 75.0 but status is missed |
| T7 | Department pass percentages whose simple mean differs from the weighted institution value | Institution value uses numerators and denominators |
| T8 | One finance figure with status pending_reconciliation | Badged, excluded from actuals, listed in assumptions |
| T9 | One department with a zero denominator for a KPI | KPI undefined for that department, not 0 or 100 |
| T10 | Two KPIs that miss, one that is at risk, the rest met | The demo story has something to decide |

Real data replaces this by switching `data_mode` to real after ingesting a batch tagged real. Switching modes must wipe nothing silently: the synthetic batch is archived and excluded from runs once data_mode is real.

## 7. Ingestion rules

- Reject rows without status or as_of. Count and report rejects, never swallow them.
- Every row keeps its source reference (file name and row, or query id and key).
- Re-ingesting the same checksum is a no-op.
- Percent-like values arrive as numerator and denominator whenever the source has them.
- CSV templates for each domain live in `data/sample/templates/` (create from this contract on Day 1).
