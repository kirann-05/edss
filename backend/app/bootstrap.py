"""Assembles the services into one application state.

Everything is built here, in one place, from settings: the data store, the connector agents read
through, the model behind its data-mode guard, the graph, the audit log, the governance service
and the run service. Tests build the same state with other settings, or with runs executed inline.
"""

import secrets
from datetime import date

from langgraph.checkpoint.memory import InMemorySaver

from app.agents.graph import GraphDeps, build_graph
from app.agents.llm import LlmSettings, get_chat_model
from app.agents.runtime import RunEvents, Runtime
from app.agents.validation.suite import validate
from app.api.deps import AppState
from app.core.config import Settings
from app.governance.audit import AuditLog
from app.governance.service import GovernanceService
from app.services.archive import seed_archive
from app.services.connector import InMemoryConnector, ScopeRegistry
from app.services.runs import RunService, plan_catalogue_from
from app.services.store import DataStore
from app.services.system_config import SystemConfig
from app.services.users import build_seed_users
from app.services.validation_context import context_for_document


def build_state(settings: Settings, today: date, *, synchronous_runs: bool = False) -> AppState:
    jwt_secret = settings.jwt_secret.get_secret_value() if settings.jwt_secret else None
    if jwt_secret is None:
        # Synthetic mode only: a throwaway secret, so sessions end when the server restarts
        jwt_secret = secrets.token_urlsafe(32)
    seed_password = (
        settings.edss_seed_password.get_secret_value() if settings.edss_seed_password else None
    )

    store = DataStore.build(today, settings.stale_after_days)
    audit, events = AuditLog(), RunEvents()
    scopes = ScopeRegistry(today)
    connector = InMemoryConnector(store, scopes)
    system_config = SystemConfig(settings.data_mode)

    llm = LlmSettings.from_settings(settings)
    drafter = get_chat_model("drafter", llm, system_config)
    clarifier = get_chat_model("clarifier", llm, system_config)

    governance = GovernanceService(
        audit, validator=lambda doc: validate(doc, context_for_document(doc, connector))
    )
    runtime = Runtime(audit, events, budget_seconds=settings.run_budget_seconds)
    graph = build_graph(
        GraphDeps(
            connector=connector,
            model=drafter,
            runtime=runtime,
            create_draft=lambda **kw: governance.create_draft(**kw).id,
            max_attempts=settings.max_attempts,
            source_latency=settings.source_latency_ms / 1000,
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
    )
    return AppState(
        settings=settings,
        store=store,
        users=build_seed_users(seed_password),
        jwt_secret=jwt_secret,
        audit=audit,
        events=events,
        scopes=scopes,
        connector=connector,
        system_config=system_config,
        governance=governance,
        runs=runs,
        archive=seed_archive(store, drafter),
    )
