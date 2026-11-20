from pathlib import Path

import pytest

from app.domain.enums import Domain, KpiFramework
from app.kpi.catalogue import CATALOGUE
from app.kpi.formulas import parse_formula
from app.kpi.loader import (
    PLACEHOLDER_MARKER,
    DefinitionError,
    load_definitions,
    load_seed_definitions,
    load_seed_targets,
    load_targets,
)

PERIODS = {"2023-24", "2024-25", "2025-26"}


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "defs.yaml"
    path.write_text(text)
    return path


def test_the_seed_has_the_thirteen_placeholder_kpis_from_the_data_contract():
    definitions = load_seed_definitions()
    assert [d.key for d in definitions] == [
        "AC_PASS_PCT", "AC_CO", "AC_PO", "AC_CURR",
        "RS_PUB_PF", "RS_CIT_PP", "RS_GRANT_PF",
        "PL_PCT", "PL_AVG", "PL_INT",
        "FN_UTIL", "FN_GRANT_UTIL", "FN_REV",
    ]  # fmt: skip


def test_every_seed_row_is_marked_placeholder_and_aligned_to_no_official_framework():
    # rule 12: we do not claim NIRF or NAAC alignment we cannot source
    for definition in load_seed_definitions():
        assert definition.placeholder is True
        assert definition.approved_by is None
        assert definition.framework is KpiFramework.STRATEGIC


def test_every_seed_formula_parses_against_the_catalogue():
    for definition in load_seed_definitions():
        parse_formula(definition.formula, CATALOGUE)


def test_domain_tags_default_to_the_primary_domain():
    by_key = {d.key: d for d in load_seed_definitions()}
    assert by_key["AC_PASS_PCT"].domain_tags == (Domain.ACADEMIC,)
    assert by_key["RS_PUB_PF"].domain_tags == (Domain.RESEARCH, Domain.REFERENCE)


def test_every_kpi_has_a_target_for_every_period():
    targets = load_seed_targets()
    keys = {d.key for d in load_seed_definitions()}
    assert {(t.kpi_key, t.period_year) for t in targets} == {(k, p) for k in keys for p in PERIODS}
    assert all(t.placeholder for t in targets)
    assert all(t.source_doc == PLACEHOLDER_MARKER for t in targets)


def test_a_placeholder_without_the_marker_is_refused(tmp_path):
    path = write(
        tmp_path,
        """
- key: X
  name: X
  domain: academic
  formula: 'sum("acad.students_passed")'
  unit: students
  placeholder: true
""",
    )
    with pytest.raises(DefinitionError, match="PLACEHOLDER_PENDING_IQAC"):
        load_definitions(path)


def test_an_unparseable_formula_is_refused_with_the_kpi_named(tmp_path):
    path = write(
        tmp_path,
        """
- key: BAD
  name: Bad
  domain: academic
  formula: 'sum("acad.nope")'
  unit: x
  note: PLACEHOLDER_PENDING_IQAC
""",
    )
    with pytest.raises(DefinitionError, match="BAD"):
        load_definitions(path)


def test_duplicate_keys_are_refused(tmp_path):
    row = """
- key: DUP
  name: Dup
  domain: academic
  formula: 'sum("acad.students_passed")'
  unit: x
  note: PLACEHOLDER_PENDING_IQAC
"""
    with pytest.raises(DefinitionError, match="duplicate"):
        load_definitions(write(tmp_path, row + row))


def test_a_target_for_an_unknown_kpi_is_refused(tmp_path):
    path = tmp_path / "targets.yaml"
    path.write_text("source_doc: PLACEHOLDER_PENDING_IQAC\ntargets:\n  NOPE: {2025-26: 1}\n")
    with pytest.raises(DefinitionError, match="NOPE"):
        load_targets(path, known_keys={"AC_PASS_PCT"})
