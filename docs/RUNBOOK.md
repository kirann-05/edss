# EDSS runbook

For the university IT cell. How to install, run, back up, restore and upgrade EDSS on one server. Every step here is exercised by `make smoke`, which starts from a fresh clone and runs steps 1 to 6.

## What runs

Four containers from `compose.yaml`:

| Service | What it is | Reachable from |
| --- | --- | --- |
| `db` | PostgreSQL 16 with pgvector. The data lives in the Docker volume `edss-db` | 127.0.0.1:5432 only |
| `migrate` | Runs once at each start: schema migrations, the app role's password, the graph's checkpoint tables, the synthetic data | Nothing, it exits |
| `backend` | The API (FastAPI), connecting as the role `edss_app`, which cannot change or delete the audit log | Only the web app, inside Docker |
| `frontend` | The web app (Next.js). The only way in | 127.0.0.1:3000 by default |

Nothing is published beyond this machine unless you change `EDSS_BIND`. Nothing is sent outside it: no telemetry, no external tracing, and the language model must be on this machine or a university server.

## 1. What the server needs

- Linux (x86_64 or arm64), 4 GB of memory, 10 GB of disk
- Docker Engine with the compose plugin (`docker compose version` works)
- git, `make`, and Python 3.12 with [uv](https://docs.astral.sh/uv/) for the backup command

## 2. Get the code

```bash
git clone <the repository> edss
```

## 3. Configure `.env`

Copy `.env.example` to `.env` in the repository folder, then `chmod 600 .env`. It is never committed. Set at least these, each a long random string (`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`):

| Variable | What it is |
| --- | --- |
| `EDSS_DB_PASSWORD` | The database owner, used only by migrations and backups |
| `EDSS_DB_APP_PASSWORD` | The app's own database role |
| `JWT_SECRET` | Signs session cookies |
| `EDSS_SEED_PASSWORD` | The shared password of the synthetic users, until real accounts exist |

Optional: `EDSS_WEB_PORT` (default 3000), `EDSS_BIND` (default 127.0.0.1), `EDSS_DEMO_LOGIN=true` for the one-click role buttons (synthetic data only), `COOKIE_SECURE=true` once it is served over HTTPS.

## 4. Start, stop, look

```bash
make up
```

Builds the images the first time (a few minutes), then starts everything and waits until each container is healthy, about 30 seconds after that. Open http://127.0.0.1:3000.

```bash
make down
```

Stops everything. The data stays in the `edss-db` volume. `make up` again picks it up.

```bash
docker compose --profile app ps
docker compose --profile app logs -f backend
```

Status and logs. The backend's health is `/api/health`; the signed-in status page shows the data mode as the database holds it.

## 5. Day-to-day facts worth knowing

- **Every `make up` reloads the synthetic data.** Runs, briefs, versions, people and the audit log are kept. The synthetic figures are regenerated the same way each time, so their record ids do not change.
- **The audit log cannot be edited.** The app's role is refused update, delete and truncate on it, and a trigger refuses them to the owner too. Its hash chain can be checked from the Audit page at any time.
- **A restart does not lose work.** A draft waiting for a person stays waiting. A run that was working is shown as stopped and can be resumed from its last step.

## 6. Backups

```bash
make db-backup
```

Writes `backups/edss-<date>-<time>.dump`, readable by the user who ran it only, then restores it at once into a throwaway database, compares every table with the live one and verifies the audit chain. It ends with "Backup is good." or says what is wrong. `backups/` is never committed. Keep copies on university storage only.

Daily at 02:00, from cron, as the user who owns the repository folder:

```
0 2 * * * cd /path/to/edss && make db-backup >> backups/backup.log 2>&1
```

To check an older backup: `cd backend && uv run python ../scripts/db_backup.py --check ../backups/<file>.dump`.

## 7. Restore

Check the backup first (step 6). Then, with the app stopped:

```bash
docker compose --profile app stop backend frontend
docker compose exec -T db dropdb -U edss_owner edss
docker compose exec -T db createdb -U edss_owner edss
docker compose exec -T db pg_restore -U edss_owner -d edss --exit-on-error < backups/<file>.dump
make up
```

Then open the Audit page and press "Check again": the chain must verify.

Without Docker, against a PostgreSQL installed directly, the same commands work with `pg_dump`, `dropdb`, `createdb` and `pg_restore` and `-h 127.0.0.1`.

## 8. Upgrade

```bash
make db-backup
git pull
make up
```

`make up` rebuilds the images and the `migrate` container brings the schema up to date before the API starts.

## 9. Not ready yet

Said plainly, so nobody finds out the hard way:

- **Real data.** `DATA_MODE=real` refuses to start. Loading the university's exports into the database is the next piece of work, after the data specification is signed (docs/PENDING.md).
- **Single sign-on.** People sign in with a password, or the demo buttons with synthetic data. University SSO is not built.
- **HTTPS.** The web app speaks plain HTTP on 127.0.0.1. Serving it to others needs a reverse proxy with the university's certificate in front of it, and `COOKIE_SECURE=true`.
- **One API process.** The backend is not built to run as several copies behind a load balancer (decision D31).

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `set EDSS_DB_PASSWORD in .env` or `run make db-migrate once` when starting | A required variable is missing from `.env`, see step 3 |
| `Port 3000 is in use` or `address already in use` | Set `EDSS_WEB_PORT` to a free port in `.env` |
| The `migrate` container exits with an error | `docker compose --profile app logs migrate`. A seed that reports a lost trap means the data changed, which must be looked into before use |
| Backend unhealthy | `docker compose --profile app logs backend`. A database it cannot reach usually means a wrong `EDSS_DB_APP_PASSWORD` |
| "Backup FAILED ITS CHECK" | Do not rely on that file. Keep the previous good backup and report the message |
