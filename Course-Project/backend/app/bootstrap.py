"""Assembles the services into one application state.

Everything is built here, in one place, from settings: the data store, the connector agents read
through, the model behind its data-mode guard, the graph, the audit log, the governance service
and the run service. Tests build the same state with other settings, or with runs executed inline.
"""

import secrets
from collections.abc import Callable
from datetime import date, timedelta

from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import Engine, create_engine

from app.agents.connector import Connector
from app.agents.fake_llm import FakeLLM
from app.agents.graph import GraphDeps, build_graph
from app.agents.llm import LlmSettings, get_chat_model
from app.agents.runtime import RunEvents, Runtime
from app.agents.validation.suite import validate
from app.api.deps import AppState, demo_login_enabled
from app.core.config import Settings
from app.core.throttle import LoginThrottle
from app.db.archive_store import DbArchive
from app.db.audit_store import DbAuditLog
from app.db.checkpoints import checkpointer
from app.db.dataset_store import load_dataset
from app.db.embeddings import HashingEmbedder, OllamaEmbedder
from app.db.state_store import DbSystemConfig, ScopeRows, UserRows
from app.db.urls import app_url
from app.db.work_store import GovernanceRows, RunRows
from app.domain.enums import Role
from app.governance.audit import AuditLog
from app.governance.service import GovernanceService
from app.mcp_connector.context import RunConnector, mcp_session
from app.mcp_connector.tokens import RunTokens
from app.services.archive import Archive, prior_from_version, seed_archive
from app.services.connector import InMemoryConnector, ScopeRegistry
from app.services.demo_state import ModelSwitch
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
        if settings.data_mode == "real":
            raise RuntimeError("DATA_MODE=real needs JWT_SECRET, a long random value in .env")
        # Synthetic mode only: a throwaway secret, so sessions end when the server restarts
        jwt_secret = secrets.token_urlsafe(32)
    seed_password = (
        settings.edss_seed_password.get_secret_value() if settings.edss_seed_password else None
    )

    data_source = DataSource(settings)
    audit, events = AuditLog(), RunEvents()
    engine = None
    if settings.edss_database:
        store, scopes, system_config, users, audit, engine = _from_database(
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
    switches: list[ModelSwitch] = []
    if llm.provider != "fake" and demo_login_enabled(settings) and settings.edss_demo_state:
        # the seeded starting state is canned; live runs use the real model (main.fresh_state)
        drafter = ModelSwitch(drafter, FakeLLM("drafter"))
        clarifier = ModelSwitch(clarifier, FakeLLM("clarifier"))
        switches = [drafter, clarifier]

    archive = _archive(settings, store, engine)

    def remember(version) -> None:
        """A published report becomes a prior for the briefs after it. If that fails, say so: the
        approval itself stands, and it is already audited."""
        try:
            archive.add(prior_from_version(version))
        except Exception as error:  # noqa: BLE001  never undo an approval over the archive
            audit.append(
                actor_type="system", actor_id="archive", action="archive.add_failed",
                inputs={"version": version.version}, outputs={"error": str(error)[:300]},
            )  # fmt: skip

    governance = GovernanceService(
        audit,
        validator=lambda doc: validate(doc, context_for_document(doc, connector)),
        store=GovernanceRows(engine) if engine else None,
        on_publish=remember,
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
    saver = checkpointer(app_url(), max_size=8) if engine else InMemorySaver()
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
        saver,
    )
    runs = RunService(
        store=RunRows(engine) if engine else None,
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
    state = AppState(
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
        archive=archive,
        data_source=data_source,
        clock=clock or date.today,
        drafter=drafter,
        clarifier=clarifier,
        switches=switches,
        throttle=LoginThrottle(
            max_failures=settings.login_max_failures,
            window=timedelta(minutes=settings.login_lockout_minutes),
            lockout=timedelta(minutes=settings.login_lockout_minutes),
        ),
    )
    if engine is not None:
        state.on_shutdown += [saver.conn.close, engine.dispose]
    return state


def _from_database(
    settings: Settings, today: date, store: DataStore | None, seed_password: str | None
) -> tuple[DataStore, ScopeRegistry, DbSystemConfig, UserStore, DbAuditLog, Engine]:
    """The data, the grants, the data mode and the people, from PostgreSQL (CHECKLIST L5d).
    A first start writes the seed people and the default grants there once. It connects as the
    app role, which cannot change or delete the audit log (migration 0004)."""
    engine = create_engine(app_url(), pool_pre_ping=True)
    config = DbSystemConfig(engine)
    mode = config.data_mode()
    if mode != settings.data_mode:
        # the stored mode and the environment must agree, so every check keyed on either is right
        if mode == "real":
            raise RuntimeError(
                f"the database is in real mode (real data has been loaded) but DATA_MODE="
                f"{settings.data_mode}. Set DATA_MODE=real"
            )
        raise RuntimeError(
            "DATA_MODE=real but the database holds no real data. Load it first with "
            "make ingest DIR=data/real/<folder> ARGS=--db, which switches the database to real mode"
        )
    if store is None:
        with engine.connect() as conn:
            try:
                dataset, definitions, targets = load_dataset(conn, mode)
            except LookupError:
                raise RuntimeError(
                    "the database holds no data yet: make db-migrate, then make seed-db for the "
                    "synthetic sample or make ingest DIR=... MODE=real ARGS=--db for real data"
                ) from None
        store = DataStore(dataset, definitions, targets, today, settings.stale_after_days)

    grants = ScopeRows(engine)
    held = grants.load()
    scopes = ScopeRegistry(today, grants=held or None, on_change=grants.replace)
    if not held:
        grants.replace(scopes.all())

    rows = UserRows(engine)
    people, hashes, versions = rows.load()
    # real data opens only to real people: the synthetic personas were switched off at the first
    # real load, and nobody is seeded here
    admins = [
        p
        for p in people
        if p.role is Role.ADMIN and p.active and not p.email.endswith("@edss.test")
    ]
    if mode == "real" and not admins:
        raise RuntimeError(
            "real mode needs an administrator: make create-user ARGS='--role admin ...'"
        )
    if people:
        users = UserStore(people, "", stored_hashes=hashes, versions=versions, on_change=rows.save)
    else:
        users = build_seed_users(seed_password, on_change=rows.save)
        users.save_all()
    audit = DbAuditLog(engine)
    return store, scopes, config, users, audit, engine


def _archive(settings: Settings, store: DataStore, engine: Engine | None):
    """Prior briefs: fixture history built by the canned model, never a live model call. In
    database mode they are embedded and searched by meaning with pgvector (Lab 4, L5h)."""
    if settings.data_mode == "real":
        # the seeded priors are invented history built from the data by the canned model. Beside
        # real figures they would read as real decisions, so with real data the archive starts empty
        return Archive([])
    priors = seed_archive(store, FakeLLM("drafter"))
    if engine is None:
        return priors
    embedder = (
        OllamaEmbedder(settings.llm_base_url, settings.llm_embed_model)
        if settings.llm_embed_model
        else HashingEmbedder()
    )
    archive = DbArchive(engine, embedder, {d.key: d.name for d in store.definitions})
    archive.index(priors.all())
    return archive
