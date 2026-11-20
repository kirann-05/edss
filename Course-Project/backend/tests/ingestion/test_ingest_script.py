"""make ingest: what the command says, and its exit code, for each kind of folder it can be given."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "ingest.py"


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("ingest_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def folder(tmp_path, exported) -> Path:
    target = tmp_path / "drop"
    shutil.copytree(exported, target)
    return target


@pytest.fixture
def run(script, monkeypatch, capsys):
    def go(*args):
        monkeypatch.setattr(sys, "argv", ["ingest.py", *map(str, args)])
        code = script.main()
        out = capsys.readouterr()
        return code, out.out, out.err

    return go


def test_a_clean_folder_exits_0_with_the_report(run, folder):
    code, report, _ = run(folder, "--mode", "synthetic")
    assert code == 0 and "rejected" in report.lower()


def test_a_refused_row_exits_1_and_the_report_gives_its_reason(run, folder):
    path = folder / "placement.csv"
    header, first, *rest = path.read_text().splitlines()
    columns = header.split(",")
    cells = first.split(",")
    cells[columns.index("status")] = ""  # a row without a status is refused (DATA_CONTRACT 7)
    path.write_text("\n".join([header, ",".join(cells), *rest]) + "\n")
    code, report, _ = run(folder, "--mode", "synthetic")
    assert code == 1 and "status" in report


def test_a_folder_without_a_manifest_exits_2(run, tmp_path):
    code, _, err = run(tmp_path, "--mode", "synthetic")
    assert code == 2 and "has no manifest.yml" in err


def test_a_file_that_cannot_be_read_exits_2(run, folder):
    (folder / "finance.csv").unlink()
    code, report, _ = run(folder, "--mode", "synthetic")
    assert code == 2 and "could not be read" in report


def test_the_report_can_be_written_to_a_file_too(run, folder, tmp_path):
    out = tmp_path / "REPORT.md"
    code, report, _ = run(folder, "--mode", "synthetic", "--report", out)
    assert code == 0 and out.read_text() + "\n" == report  # the same words, on screen and on file


def test_the_database_load_is_for_real_data_only(run, folder):
    code, _, err = run(folder, "--mode", "synthetic", "--db")
    assert code == 2 and "--db is for real data" in err


def test_real_data_outside_the_ignored_folder_is_warned_about(run, folder):
    _, _, err = run(folder, "--mode", "real")
    assert "is not ignored by git" in err
