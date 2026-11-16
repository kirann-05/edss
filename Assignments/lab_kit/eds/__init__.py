"""
Executive Decision Support System (EDS)
========================================

A coordinator-plus-workers agentic system, built lab by lab per the
"14-Lab Worklet Build Book" (Chapter 15 - Executive Decision Support
System) and scoped by the "Executive Decision Support System" problem
brief.

Package map (which lab introduced each module):

    connector.py    - Lab 5  (one governed surface for all data sources)
    memory.py       - Lab 4  (short-term run state vs long-term store)
    skills.py        - Lab 3  (reusable, schema-typed plan/format skills)
    tools.py         - Lab 2  (typed tools the agents must call to act)
    coordinator.py  - Lab 1, 6, 10, 11 (planner loop -> governed runtime
                       -> self-healing -> tested-build gate)
    graph.py         - Lab 7, 8 (explicit node graph + parallel swarm)
    validation.py    - Lab 9, 10, 11 (grounding, hard gate, acceptance suite)
    governance.py    - Lab 12 (approval, versioning, rollback, audit)
    specialists.py   - Lab 13 (pluggable domain specialist packs)
    agents/          - Lab 7  (the specialist agents themselves)

`labs/lab14_capstone.py` wires all of the above together into the one
deployed, team-owned agentic workflow.
"""

__version__ = "1.0.0"
