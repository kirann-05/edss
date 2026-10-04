# The EDSS API. Built from the repository root: docker build -f backend/Dockerfile .
# Synthetic data and the canned model by default; the database and the model are configured by
# the environment (compose.yaml). Runs as an unprivileged user.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PYTHONUNBUFFERED=1
WORKDIR /edss/backend

# dependencies first, so a code change does not reinstall them
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
COPY scripts/seed.py scripts/db_roles.py /edss/scripts/
RUN uv sync --frozen --no-dev && useradd --system --uid 10001 edss && chown -R edss /edss
USER edss
ENV PATH=/opt/venv/bin:$PATH

EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=20s --retries=10 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
