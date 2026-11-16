# Assignment 4: Memory and Retrieval (state vs stored)

Course: Agentic AI (26ECAC401), KLE Technological University
Worklet 15: Executive Decision Support System (EDSS)
Book phase: A, Foundations

## Objective

Separate short-term run state from long-term stored knowledge. The session state holds the current draft, while the stored reference (KPIs and the history of past decisions) is retrieved by tags and by similarity. The book's pitfall: do not conflate run state with the archive; mixing them corrupts the baseline.

## Concept applied in EDSS

While a brief is being prepared, its draft figures (for example a draft placement percentage) belong to that run only. Separately, EDSS keeps a history of prior published executive reports. When leadership looks at this quarter's placement figure, the system can pull up last quarter's report on the same topic. The two stores are kept apart so a draft never leaks into the history.

## Technical stack

- Python 3, standard library only (`re` for tokenising)
- [`eds/memory.py`](../lab_kit/eds/memory.py)
- Similarity is a dependency-free stand-in for embeddings: Jaccard overlap of word tokens

## Implementation

Script: [`lab04_memory.py`](lab04_memory.py)

1. Creates a `RunState` for the request and sets `state.draft` to `{"institution_placement_percentage": 76.3, "status": "draft"}`. This is short-term and never persisted.
2. Creates a `LongTermStore` and adds three prior reports: `2025-Q4` (tags placement, quarterly), `2025-Q3` (finance, quarterly) and `2025-NAAC` (academic, accreditation), each with text and a payload.
3. `retrieve_by_tags(["quarterly"])` returns items sharing any requested tag. Asserts it returns exactly `2025-Q4` and `2025-Q3`.
4. `retrieve_by_similarity("placement percentage executive report this quarter", k=2)` scores each item by token overlap and returns the top two with a non-zero score. Asserts that the placement report `2025-Q4` ranks first.

Key pieces:

| Name | File | Role |
| --- | --- | --- |
| `RunState` | [`memory.py`](../lab_kit/eds/memory.py) | Request, draft and scratch for the current run |
| `LongTermStore.add` | [`memory.py`](../lab_kit/eds/memory.py) | Stores an item with id, tags, text, payload |
| `LongTermStore.retrieve_by_tags` | [`memory.py`](../lab_kit/eds/memory.py) | Tag filter |
| `LongTermStore.retrieve_by_similarity` | [`memory.py`](../lab_kit/eds/memory.py) | Jaccard similarity, top k |

## How to run

```bash
cd Assignments/Assignment-04_Memory_and_Retrieval
python lab04_memory.py
```

On Windows, if the console shows encoding errors, run `set PYTHONIOENCODING=utf-8` first.

## Result / evidence

Acceptance (book): for a given task, retrieval returns correctly-tagged candidates and similar prior items.

From [`output/run_log.txt`](output/run_log.txt):

```
state.draft (short-term, this run only): {'institution_placement_percentage': 76.3, 'status': 'draft'}

retrieve(store, tags=['quarterly']) -> ['2025-Q4', '2025-Q3']
retrieve(history, embed(candidate), k=2) -> ['2025-Q4', '2025-Q3']

ACCEPT: tag filter and similarity search both returned correctly-matched prior items; state.draft never touched the long-term store.
```

The placement-themed Q4 report ranks first by similarity, as the assertion requires.

## In the full system

| | |
| --- | --- |
| Production code | Run state lives in the graph's checkpoints; the archive of prior briefs is [`app/services/archive.py`](../../Course_Project/backend/app/services/archive.py), and with pgvector [`app/db/archive_store.py`](../../Course_Project/backend/app/db/archive_store.py) |
| What it does there | In the review queue, a draft's "Prior briefs" tab lists earlier reports with what was decided and why they match |
| Proved by | [`tests/api/test_archive_publish.py`](../../Course_Project/backend/tests/api/test_archive_publish.py), [`tests/db/test_archive_store.py`](../../Course_Project/backend/tests/db/test_archive_store.py) |
