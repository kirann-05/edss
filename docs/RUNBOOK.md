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

## 9. Real data

Only after the data specification is signed and the exports have been checked with their data owners. Keep the folder under `data/real/`, which git never sees. Start from a copy of `data/sample/templates`: one file per area, a worked example row, and a `manifest.yml` whose source names say `CHANGE ME` until you write in where each file really comes from. Delete the example rows.

1. **Check the folder** (nothing is written): `make ingest DIR=data/real/2026-10`. It reads `manifest.yml` and every file it names, and prints the reconciliation report: what was accepted, every refused row with its reason, and where there is no record at all. Fix refused rows at the source.
2. **Back up, and stop the app**: `make db-backup`, then `docker compose --profile app stop backend frontend`. The app keeps people and data in memory while it runs, so it must not be running while a load changes the database underneath it (decision D31). If it is, it stops answering, with a 503 asking for a restart in real mode, within a second of the switch. The database itself stays up.
3. **Load it**: `make ingest DIR=data/real/2026-10 ARGS=--db`. What was accepted is added to the database; a file that has not changed adds nothing, a changed file becomes a new batch, and earlier records are never changed, so a record an approved brief cites stays as it was. A newer file wins slot by slot (department, measure, period). So deleting a wrong row from a file does not withdraw its figure: the earlier value stays current. Send the row again with the corrected value. The departments in the manifest become the list the app shows.
4. **The first real load switches the database to real mode**, once. From then the synthetic records are kept but never read, and the synthetic personas are switched off. It is a row in the audit log.
5. **Create the first administrator**: `make create-user ARGS="--email it.admin@<university> --name 'IT Administrator' --role admin"`. It asks for the password twice and never shows it.
6. **Start in real mode**: set `DATA_MODE=real` in `.env` (with `JWT_SECRET` and `EDSS_DEMO_LOGIN=false`), then `make up`. The app refuses to start if `DATA_MODE` and the database disagree, if `JWT_SECRET` is missing, or if there is no real administrator. In real mode the language model must be on this machine or a university server; a hosted model is refused.

Inside the containers, steps 3 and 5 are the same scripts, and both have been run this way on a throwaway stack: `docker compose run --rm -v "$PWD/data/real:/data/real:ro" migrate python /edss/scripts/ingest.py /data/real/2026-10 --mode real --db`, and `docker compose run --rm migrate python /edss/scripts/create_user.py --email ... --name ... --role admin`.

## 10. Not ready yet

Said plainly, so nobody finds out the hard way:

- **Official KPI definitions.** Every KPI is a placeholder until IQAC supplies the approved list, so statuses are not official, even on real data.
- **Single sign-on.** People sign in with a password, or the demo buttons with synthetic data. University SSO is not built.
- **HTTPS.** The web app speaks plain HTTP on 127.0.0.1. Serving it to others needs a reverse proxy with the university's certificate in front of it, sending `Strict-Transport-Security`, and `COOKIE_SECURE=true`. The app itself already refuses to be framed by another site and sends the other protective headers.
- **One API process.** The backend is not built to run as several copies behind a load balancer (decision D31).

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `set EDSS_DB_PASSWORD in .env` or `run make db-migrate once` when starting | A required variable is missing from `.env`, see step 3 |
| `Port 3000 is in use` or `address already in use` | Set `EDSS_WEB_PORT` to a free port in `.env` |
| The `migrate` container exits with an error | `docker compose --profile app logs migrate`. A seed that reports a lost trap means the data changed, which must be looked into before use |
| Backend unhealthy | `docker compose --profile app logs backend`. A database it cannot reach usually means a wrong `EDSS_DB_APP_PASSWORD` |
| `the database is in real mode but DATA_MODE=synthetic` | Real data has been loaded: set `DATA_MODE=real` in `.env` |
| `real mode needs an administrator` | Step 5 of Real data |
| "Backup FAILED ITS CHECK" | Do not rely on that file. Keep the previous good backup and report the message |
