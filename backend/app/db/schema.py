"""The PostgreSQL schema, one table per entry in docs/DATA_CONTRACT.md section 2.

Written as SQLAlchemy Core tables rather than mapped classes: the services already have their own
domain models, so the database layer only needs to say what the tables are, and the queries that
read and write them stay explicit and easy to follow. Alembic's migrations are generated from this
metadata and then read by a person before they are committed.

Where the built system keeps more than the contract lists, the extra is said next to the column.
Every value that is a figure is NUMERIC, never float, so nothing is rounded on its way in or out.
"""

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from app.domain.enums import Domain, FactStatus, KpiFramework, KpiStatus, Role

# Names for constraints, so a migration can refer to one by name and PostgreSQL never invents one
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

# Tables in the database that belong to a library, not to these migrations
FOREIGN_TABLES = ("checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations")


def ours(obj, name, type_, reflected, compare_to) -> bool:
    """For Alembic's comparison: leave LangGraph's checkpoint tables to LangGraph."""
    return not (type_ == "table" and name in FOREIGN_TABLES)


# The dimension of the embeddings for similar-brief search. Provisional: it follows the local
# embedding model chosen in Lab 4, and an empty table can change it in a later migration.
EMBEDDING_DIMENSIONS = 768


def _one_of(values) -> str:
    """The allowed values for a check constraint, taken from the enum, never typed twice."""
    return ", ".join(f"'{v.value}'" for v in values)


DOMAINS = _one_of(Domain)
STATUSES = _one_of(FactStatus)


def _now():
    return DateTime(timezone=True)


department = Table(
    "department",
    metadata,
    Column("code", String(16), primary_key=True),
    Column("name", Text, nullable=False),
    Column("school", Text, nullable=False, server_default=""),
    Column("active", Boolean, nullable=False, server_default="true"),
    # each list's own order, and whether the department is on it: the synthetic sample's list,
    # and the list in the university's own manifest. Once the mode is real, only the second shows
    Column("position", Integer),
    Column("real_position", Integer),
)

source_system = Table(
    "source_system",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("name", Text, nullable=False),
    Column("owner_office", Text, nullable=False),
    Column("kind", String(16), nullable=False),  # csv, sql, api
    UniqueConstraint("name", name="uq_source_system_name"),
)

ingest_batch = Table(
    "ingest_batch",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("source_system_id", ForeignKey("source_system.id"), nullable=False),
    Column("domain", String(16), nullable=False),  # beyond the contract: a batch is one area's file
    Column("data_mode", String(16), nullable=False),
    Column("started_at", _now(), nullable=False),
    Column("finished_at", _now()),
    Column("row_count", Integer, nullable=False, server_default="0"),
    Column("rejected_count", Integer, nullable=False, server_default="0"),
    Column("file_ref", Text, nullable=False),
    Column("checksum", String(64), nullable=False),
    Column("ingested_by", Text, nullable=False),
    CheckConstraint("data_mode in ('synthetic', 'real')", name="data_mode"),
    CheckConstraint(f"domain in ({DOMAINS})", name="domain"),
)

metric_fact = Table(
    "metric_fact",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("batch_id", ForeignKey("ingest_batch.id"), nullable=False),
    Column("domain", String(16), nullable=False),
    Column("metric_key", Text, nullable=False),
    Column("dept_code", ForeignKey("department.code"), nullable=False),
    Column("period_year", String(7), nullable=False),
    Column("period_sub", String(2), nullable=False),
    Column("value", Numeric, nullable=False),
    Column("numerator", Numeric),
    Column("denominator", Numeric),
    Column("unit", Text, nullable=False),
    Column("status", String(24), nullable=False),
    Column("as_of", Date, nullable=False),
    Column("source_system_id", ForeignKey("source_system.id"), nullable=False),
    Column("source_ref", Text, nullable=False),
    Column("recorded_at", _now(), nullable=False),
    UniqueConstraint(
        "batch_id",
        "domain",
        "metric_key",
        "dept_code",
        "period_year",
        "period_sub",
        name="uq_metric_fact_slot",
    ),  # fmt: skip
    CheckConstraint(f"domain in ({DOMAINS})", name="domain"),
    CheckConstraint(f"status in ({STATUSES})", name="status"),
    Index("ix_metric_fact_period_domain", "period_year", "domain"),
)

research_publication = Table(
    "research_publication",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("batch_id", ForeignKey("ingest_batch.id"), nullable=False),
    Column("dedup_key", Text, nullable=False),  # DOI or internal id, counted once (trap T5)
    Column("title", Text, nullable=False),
    Column("venue", Text, nullable=False, server_default=""),
    Column("period_year", String(7), nullable=False),  # the contract calls it year
    Column("indexing", Text, nullable=False, server_default=""),
    Column("status", String(24), nullable=False),
    CheckConstraint(f"status in ({STATUSES})", name="status"),
)

publication_author_dept = Table(
    "publication_author_dept",
    metadata,
    Column("publication_id", ForeignKey("research_publication.id"), nullable=False),
    Column("dept_code", ForeignKey("department.code"), nullable=False),
    Column("position", Integer, nullable=False, server_default="0"),  # credits keep their order
    PrimaryKeyConstraint("publication_id", "dept_code"),
)

kpi_definition = Table(
    "kpi_definition",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("key", String(32), nullable=False),
    Column("name", Text, nullable=False),
    Column("framework", String(16), nullable=False),
    Column("domain", String(16), nullable=False),  # the primary domain, for the dashboard
    Column("domain_tags", ARRAY(String(16)), nullable=False),
    Column("formula", Text, nullable=False),
    Column("unit", Text, nullable=False),
    Column("higher_is_better", Boolean, nullable=False, server_default="true"),
    Column("version", Integer, nullable=False, server_default="1"),
    Column("approved_by", Text),
    Column("approved_on", Date),
    Column("active", Boolean, nullable=False, server_default="true"),
    Column("placeholder", Boolean, nullable=False, server_default="true"),  # rule 12
    Column("display_precision", Integer, nullable=False, server_default="1"),
    Column("at_risk_band_pct", Numeric, nullable=False, server_default="2"),
    Column("note", Text),
    UniqueConstraint("key", "version", name="uq_kpi_definition_key_version"),
    CheckConstraint(f"framework in ({_one_of(KpiFramework)})", name="framework"),
    # a definition that is not a placeholder must say who approved it and when (rule 12)
    CheckConstraint(
        "placeholder or (approved_by is not null and approved_on is not null)", name="approved"
    ),
)

kpi_target = Table(
    "kpi_target",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("kpi_key", String(32), nullable=False),
    Column("period_year", String(7), nullable=False),
    Column("target_value", Numeric, nullable=False),
    Column("framework", String(16), nullable=False),
    Column("source_doc", Text),
    Column("placeholder", Boolean, nullable=False, server_default="true"),
    UniqueConstraint("kpi_key", "period_year", name="uq_kpi_target_kpi_period"),
)

scope_grant = Table(
    "scope_grant",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("domain", String(16), nullable=False),
    Column("dept_code", ForeignKey("department.code")),
    Column("granted_by", Text, nullable=False),
    Column("granted_on", Date, nullable=False),
    Column("expires_on", Date),
    Column("active", Boolean, nullable=False, server_default="true"),
    CheckConstraint(f"domain in ({DOMAINS})", name="domain"),
)

run = Table(
    "run",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("request", Text, nullable=False),
    Column("clarifications", JSONB, nullable=False, server_default="[]"),
    Column("plan", JSONB),
    Column("plan_locked_at", _now()),
    Column("status", String(24), nullable=False),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("created_by", Text, nullable=False),
    Column("created_at", _now(), nullable=False),
    Column("finished_at", _now()),
    # what the run service keeps beyond the contract: questions, plan history, faults, error
    Column("detail", JSONB, nullable=False, server_default="{}"),
)

kpi_result = Table(
    "kpi_result",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("run_id", ForeignKey("run.id"), nullable=False),
    Column("kpi_key", String(32), nullable=False),
    Column("kpi_version", Integer, nullable=False),
    Column("period_year", String(7), nullable=False),
    Column("value", Numeric),  # null when undefined, never zero (trap T9)
    Column("target", Numeric, nullable=False),
    Column("variance_abs", Numeric),
    Column("variance_pct", Numeric),
    Column("status", String(16), nullable=False),
    Column("input_fact_ids", ARRAY(BigInteger), nullable=False),
    Column("flags", JSONB, nullable=False, server_default="{}"),
    CheckConstraint(f"status in ({_one_of(KpiStatus)})", name="status"),
)

evidence = Table(
    "evidence",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("run_id", ForeignKey("run.id"), nullable=False),
    Column("claim_id", Text, nullable=False),
    Column("kpi_result_id", ForeignKey("kpi_result.id")),
    Column("fact_ids", ARRAY(BigInteger), nullable=False),
    Column("source_systems", ARRAY(Text), nullable=False),
    Column("scope", Text),
    Column("tags", ARRAY(Text), nullable=False, server_default="{}"),
)

brief = Table(
    "brief",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("run_id", ForeignKey("run.id"), nullable=False),
    Column("status", String(24), nullable=False),
    Column("content", JSONB, nullable=False),
    Column("rendered_md", Text, nullable=False, server_default=""),
    Column("validation", JSONB, nullable=False),
    Column("created_at", _now(), nullable=False),
    # the governance service also keeps the attempts, diagnosis and the approver's edits
    Column("detail", JSONB, nullable=False, server_default="{}"),
)

brief_version = Table(
    "brief_version",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("brief_id", ForeignKey("brief.id"), nullable=False),
    Column("version", Integer, nullable=False),
    Column("content", JSONB, nullable=False),
    Column("rendered_md", Text, nullable=False, server_default=""),
    Column("approved_by", Text, nullable=False),
    Column("approved_at", _now(), nullable=False),
    Column("edits", JSONB, nullable=False, server_default="[]"),
    Column("reason", Text),
    Column("created_at", _now(), nullable=False),
    # beyond the contract: whether a rollback took it out of service, and the whole record
    Column("rolled_back", Boolean, nullable=False, server_default="false"),
    Column("detail", JSONB, nullable=False, server_default="{}"),
    UniqueConstraint("version", name="uq_brief_version_version"),
)

system_pointer = Table(
    "system_pointer",
    metadata,
    Column("name", String(32), primary_key=True),  # 'current_report'
    Column("brief_version_id", ForeignKey("brief_version.id")),
    Column("updated_by", Text, nullable=False),
    Column("updated_at", _now(), nullable=False),
)

audit_log = Table(
    "audit_log",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("ts", _now(), nullable=False),
    Column("run_id", String(32)),
    Column("actor_type", String(16), nullable=False),
    Column("actor_id", Text, nullable=False),
    Column("action", Text, nullable=False),
    Column("inputs", JSONB, nullable=False),
    Column("outputs", JSONB, nullable=False),
    Column("prev_hash", String(64), nullable=False),
    Column("hash", String(64), nullable=False),
    UniqueConstraint("hash", name="uq_audit_log_hash"),
    CheckConstraint("actor_type in ('user', 'agent', 'system')", name="actor_type"),
)

app_user = Table(
    "app_user",
    metadata,
    Column("id", Integer, Identity(), primary_key=True),
    Column("email", Text, nullable=False),
    Column("name", Text, nullable=False),
    Column("role", String(24), nullable=False),
    Column("dept_code", ForeignKey("department.code")),
    Column("school", Text),  # beyond the contract: a Dean belongs to one school
    Column("active", Boolean, nullable=False, server_default="true"),
    Column("password_hash", Text),
    Column("session_version", Integer, nullable=False, server_default="0"),  # ends old sessions
    UniqueConstraint("email", name="uq_app_user_email"),
    CheckConstraint(f"role in ({_one_of(Role)})", name="role"),
)

system_config = Table(
    "system_config",
    metadata,
    Column("key", String(64), primary_key=True),  # includes data_mode (rule 7)
    Column("value", Text, nullable=False),
)

brief_embedding = Table(
    "brief_embedding",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    # beyond the contract: a prior brief from before the system is not a row in `brief`, so the
    # link is optional and every embedding has its own reference and record
    Column("brief_id", ForeignKey("brief.id")),
    Column("ref", Text, nullable=False),
    Column("kpi_key", String(32)),
    Column("content", Text, nullable=False, server_default=""),  # exactly what was embedded
    Column("record", JSONB, nullable=False, server_default="{}"),
    Column("embedding", VECTOR(EMBEDDING_DIMENSIONS), nullable=False),
    Column("tags", ARRAY(Text), nullable=False, server_default="{}"),
    UniqueConstraint("ref", name="uq_brief_embedding_ref"),
    Index(
        "ix_brief_embedding_embedding",
        "embedding",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    ),
)
