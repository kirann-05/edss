"""Rule 6: no agent touches a data source directly.

Agents get data through the connector protocol and nothing else. This test reads the source of
every module under app/agents and fails the build if one imports a reader, so the rule cannot be
broken by accident, in a hurry, or by a library that looks harmless.
"""

import ast
from pathlib import Path

import pytest

AGENTS = Path(__file__).parents[2] / "app" / "agents"

# Inside the app, agents may use these and nothing else. The KPI engine and formulas are pure
# functions. The loader reads YAML files and the store reads data, so both are out.
ALLOWED_APP_PREFIXES = (
    "app.agents",
    "app.domain",
    "app.kpi.catalogue",
    "app.kpi.engine",
    "app.kpi.formulas",
    "app.kpi.results",
    "app.kpi.describe",
    "app.core.canonical",
    "app.core.config",
    "app.services.system_config",
)

# Libraries whose job is to read data. Reaching for one inside an agent is a bypass.
READER_LIBRARIES = {
    "csv",
    "sqlite3",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "pandas",
    "openpyxl",
    "yaml",
}


def modules():
    return sorted(AGENTS.rglob("*.py"))


def imports_of(path: Path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_there_are_agent_modules_to_check():
    assert len(modules()) >= 5


@pytest.mark.parametrize("path", modules(), ids=lambda p: str(p.relative_to(AGENTS)))
def test_an_agent_module_imports_no_data_reader(path):
    for name in imports_of(path):
        root = name.split(".")[0]
        assert root not in READER_LIBRARIES, f"{path.name} imports {name}, a data reader"
        if root == "app":
            assert name.startswith(ALLOWED_APP_PREFIXES), (
                f"{path.name} imports {name}. Agents read data only through the connector protocol"
            )


@pytest.mark.parametrize("path", modules(), ids=lambda p: str(p.relative_to(AGENTS)))
def test_an_agent_module_opens_no_file_itself(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "open", f"{path.name} calls open() directly"


def test_the_check_itself_can_fail(tmp_path):
    """A control: prove the scan would catch a bypass, so a green run means something."""
    bad = tmp_path / "bypass.py"
    bad.write_text("import csv\nfrom app.services.store import DataStore\n")
    found = list(imports_of(bad))
    assert "csv" in found and "app.services.store" in found
    assert found[1].startswith(ALLOWED_APP_PREFIXES) is False
