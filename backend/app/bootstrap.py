"""Assembles the services into one application state.

Everything is built here, in one place, from settings: the data store, the connector agents read
through, the model behind its data-mode guard, the graph, the audit log, the governance service
and the run service. Tests build the same state with other settings, or with runs executed inline.
"""

import secrets
from collections.abc import Callable
from datetime import date, timedelta

from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import create_engine

from app.agents.connector import Connector
from app.agents.fake_llm import FakeLLM
from app.agents.graph import GraphDeps, build_graph
from app.agents.llm import LlmSettings, get_chat_model
from app.agents.runtime import RunEvents, Runtime
from app.agents.validation.suite import validate
from app.api.deps import AppState
from app.core.config import Settings
from app.core.throttle import LoginThrottle
from app.db.audit_store import DbAuditLog
from app.db.dataset_store import load_dataset
from app.db.state_store import DbSystemConfig, ScopeRows, UserRows
from app.db.urls import app_url
from app.governance.audit import AuditLog
from app.governance.service import GovernanceService
from app.mcp_connector.context import RunConnector, mcp_session
from app.mcp_connector.tokens import RunTokens
from app.services.archive import seed_archive
from app.services.connector import InMemoryConnector, ScopeRegistry
from app.services.refresh import DataSource
from app.services.runs import RunRecord, RunService, plan_catalogue_from
from app.services.store import DataStore
from app.services.system_config import SystemConfig
from app.services.users import UserStore, build_seed_users
from app.services.validation_context import context_for_document
from app.specialists import SPECIALISTS


def build_state(
    settings: Settings,
    today: date,
    *,
    synchronous_runs: bool = False,
    store: DataStore | None = None,
    clock: Callable[[], date] | None = None,
    run_tokens: RunTokens | None = None,
) -> AppState:
    """`store` lets the same services run over data that came from files or a database.
    `run_tokens` is the MCP server's token store, needed when runs read over MCP."""
    jwt_secret = settings.jwt_secret.get_secret_value() if settings.jwt_secret else None
    if jwt_secret is None:
        # Synthetic mode only: a throwaway secret, so sessions end when the server restarts
        jwt_secret = secrets.token_urlsafe(32)
    seed_password = (
        settings.edss_seed_password.get_secret_value() if settings.edss_seed_password else None
    )

    data_source = DataSource(settings)
    audit, events = AuditLog(), RunEvents()
    if settings.edss_database:
        store, scopes, system_config, users, audit = _from_database(
            settings, today, store, seed_password
        )
    else:
        store = store or data_source.load(today)
        scopes = ScopeRegistry(today)
        system_config = SystemConfig(settings.data_mode)
        users = build_seed_users(seed_password)
    connector = InMemoryConnector(store, scopes)

    llm = LlmSettings.from_settings(settings)
    drafter = get_chat_model("drafter", llm, system_config)
    clarifier = get_chat_model("clarifier", llm, system_config)

    governance = GovernanceService(
        audit, validator=lambda doc: validate(doc, context_for_document(doc, connector))
    )
    runtime = Runtime(audit, events, budget_seconds=settings.run_budget_seconds)
    graph_connector: Connector = connector
    open_reads = None
    if settings.connector_url:
        # rule 6 over the wire: each run reads through the MCP endpoint with its own token
        if run_tokens is None:
            raise ValueError("CONNECTOR_URL is set, so the app must pass its run tokens")
        tokens, url = run_tokens, settings.connector_url
        graph_connector = RunConnector()

        def open_reads(record: RunRecord):
            assert record.plan is not None
            return mcp_session(url, tokens, record.id, record.created_by, record.plan.domains)

    # Lab 13: a KPI tagged with a framework that waits for IQAC stops the app (rule 12)
    SPECIALISTS.check_definitions(d.framework for d in store.definitions)
    graph = build_graph(
        GraphDeps(
            connector=graph_connector,
            model=drafter,
            runtime=runtime,
            create_draft=lambda **kw: governance.create_draft(**kw).id,
            max_attempts=settings.max_attempts,
            source_latency=settings.source_latency_ms / 1000,
            frameworks=SPECIALISTS,
        ),
        InMemorySaver(),
    )
    runs = RunService(
        model=clarifier,
        graph=graph,
        catalogue=lambda: plan_catalogue_from(connector),
        audit=audit,
        events=events,
        system_config=system_config,
        synchronous=synchronous_runs,
        open_reads=open_reads,
        direct=connector,
    )
    return AppState(
        settings=settings,
        store=store,
        users=users,
        jwt_secret=jwt_secret,
        audit=audit,
        events=events,
        scopes=scopes,
        connector=connector,
        system_config=system_config,
        governance=governance,
        runs=runs,
        archive=seed_archive(store, FakeLLM("drafter")),  # fixture history, never a live model call
        data_source=data_source,
        clock=clock or date.today,
        drafter=drafter,
        clarifier=clarifier,
        throttle=LoginThrottle(
            max_failures=settings.login_max_failures,
            window=timedelta(minutes=settings.login_lockout_minutes),
            lockout=timedelta(minutes=settings.login_lockout_minutes),
        ),
    )


def _from_database(
    settings: Settings, today: date, store: DataStore | None, seed_password: str | None
) -> tuple[DataStore, ScopeRegistry, DbSystemConfig, UserStore, DbAuditLog]:
    """The data, the grants, the data mode and the people, from PostgreSQL (CHECKLIST L5d).
    A first start writes the seed people and the default grants there once. It connects as the
    app role, which cannot change or delete the audit log (migration 0004)."""
    engine = create_engine(app_url(), pool_pre_ping=True)
    if store is None:
        with engine.connect() as conn:
            try:
                dataset, definitions, targets = load_dataset(conn)
            except KeyError:
                raise RuntimeError(
                    "the database holds no data yet: run make db-migrate and make seed-db"
                ) from None
        store = DataStore(dataset, definitions, targets, today, settings.stale_after_days)

    grants = ScopeRows(engine)
    held = grants.load()
    scopes = ScopeRegistry(today, grants=held or None, on_change=grants.replace)
    if not held:
        grants.replace(scopes.all())

    rows = UserRows(engine)
    people, hashes, versions = rows.load()
    if people:
        users = UserStore(people, "", stored_hashes=hashes, versions=versions, on_change=rows.save)
    else:
        users = build_seed_users(seed_password, on_change=rows.save)
        users.save_all()
    return store, scopes, DbSystemConfig(engine, settings.data_mode), users, DbAuditLog(engine)
