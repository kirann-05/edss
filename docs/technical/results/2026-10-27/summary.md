# Test run, 2026-10-27

Every suite, one after another, on commit `8fffaea` (`main`). Raw output of each is in `logs/`.

| Command | Result | Time |
| --- | --- | --- |
| `make db-up` | passed | 3s |
| `make check` | passed | 58s |
| `make test-db` | passed | 14s |
| `make test-api-db` | passed | 22s |
| `make e2e` | passed | 46s |
| `make rehearse` | passed | 18s |
| `make acceptance` | passed | 2s |
| `make benchmark` | passed | 30s |
| `make coverage` | passed | 91s |
| `make smoke` | passed | 103s |

| Measure | Value |
| --- | --- |
| Backend tests | 1136 passed, 2 skipped by design |
| Web unit and component tests | 238 passed in 17 files |
| Database tests | 68 passed, 1 skipped (needs a running local model) |
| API tests in database mode | 242 passed |
| Browser tests | 18 passed |
| Demo rehearsal | 2 passed (the nine steps, and DEMO.md agreeing with the test) |
| Fault trials | 94, 0 problems |
| Backend line coverage | 98 percent |
| Fresh clone in containers | passed |

Also here: `acceptance-report.md`, `benchmark.md`, `coverage.txt`, and `metrics.json` with the same figures for scripts.
