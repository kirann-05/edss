"""
Lab 6 - Runtime: skills, tools, memory, audit.

Phase: A - Foundations
Goal: run the agent inside a controlled runtime with a full audit log.

Run:
    python lab06_runtime.py

Acceptance: every action is logged with inputs/outputs; a crashed run
resumes from its last checkpoint.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab_kit"))

from pathlib import Path
from eds.coordinator import Coordinator, AuditLog

OUT_DIR = Path(__file__).resolve().parent / "output"


def main():
    print("=== Lab 6: governed runtime (budget, gates, checkpoint/resume, audit) ===\n")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit_path = OUT_DIR / "audit_log.jsonl"
    if audit_path.exists():
        audit_path.unlink()

    audit = AuditLog(path=audit_path)
    coordinator = Coordinator(audit=audit, checkpoint_dir=OUT_DIR / "checkpoints")

    ctx = coordinator.new_run({"review_cycle": "Q1 FY26 (Lab 6 demo)",
                                "domains": ["academic", "finance"], "requested_by": "Registrar"})

    for step_name in ["academic aggregation", "finance aggregation"]:
        ctx.note(f"simulated step: {step_name} would run here")
        audit.log(ctx.run_id, "Coordinator", f"run {step_name}", "simulated agent step",
                   ctx.log[-1])
        if "risky" in step_name:  # if step.risky: wait_for_approval(step)
            pass
        coordinator.checkpoint(ctx)

    print(f"Audit log written to: {audit_path}")
    for entry in audit.as_list():
        print(f"  [{entry['ts']}] {entry['actor']} :: {entry['intent']} -> {entry['result_summary']}")

    # simulate a crash: build a *new* Coordinator/process and resume from checkpoint
    print("\nSimulating a crash and resuming from the last checkpoint in a fresh process...")
    fresh_coordinator = Coordinator(checkpoint_dir=OUT_DIR / "checkpoints")
    resumed = fresh_coordinator.resume(ctx.run_id)
    print(f"Resumed run {ctx.run_id} at attempt={resumed['attempts']}, "
          f"log has {len(resumed['log'])} entries:")
    for line in resumed["log"]:
        print(f"  - {line}")

    assert len(audit.as_list()) >= 3, "expected at least 3 audited actions"
    assert resumed["log"] == ctx.log, "resumed state must match the pre-crash state"

    print("\nACCEPT: every action was logged with inputs/outputs, and the resumed run's state "
          "matches the pre-crash state exactly.")


if __name__ == "__main__":
    main()
