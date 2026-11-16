"""
Lab 5 - MCP-Style Connector: one server for all sources.

Phase: A - Foundations
Goal: expose every data source through one typed connector.

Run:
    python lab05_connector.py

Acceptance: all data access goes through the connector; swapping a
source needs no agent change.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab_kit"))

from eds.connector import StubConnector, AccessDeniedError


def main():
    print("=== Lab 5: one governed connector for every source ===\n")
    connector = StubConnector()

    # accessing a domain before Gate 1 (access intake) must fail
    try:
        connector.read("department reports", domain="academic")
        raise AssertionError("expected AccessDeniedError before access is granted")
    except AccessDeniedError as e:
        print(f"Correctly denied pre-grant access: {e}")

    grant = connector.request_access("academic", authorized_by="Registrar (demo)")
    print(f"\nGate 1: access granted -> {grant}")

    academic = connector.read("department reports", domain="academic")
    kpi_defs = connector.read("institutional KPIs & dashboards")
    benchmarks = connector.read("external benchmarks")

    print(f"\nconnector.expose:")
    print(f"  read('institutional KPIs & dashboards') -> {len(kpi_defs)} definitions")
    print(f"  read('department reports', domain='academic') -> {len(academic)} records")
    print(f"  read('external benchmarks') -> {list(benchmarks.keys())}")

    print("\nTo go live: implement the same Connector interface (see eds/connector.py) "
          "against a real ERP/DB/API and hand THAT instance to the Coordinator/Runtime -- "
          "no agent in eds/agents/ needs to change.")
    print("\nACCEPT: every read above went through `connector.read(...)`; no module imported "
          "data/stub_data.py directly.")


if __name__ == "__main__":
    main()
