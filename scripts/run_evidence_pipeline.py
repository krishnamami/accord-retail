#!/usr/bin/env python3
"""
Runs the data pipeline RAW -> VALIDATE -> TRANSFORM -> EVIDENCE -> BUSINESS_CONTEXT (steps 1-5)
and stops. Decisions (steps 6-9) are deliberately NOT run: they must be repaired separately
before they consume the corrected evidence.

Usage:
    python scripts/run_evidence_pipeline.py                      # all businesses
    python scripts/run_evidence_pipeline.py --business-id <uuid> # one business (repeatable)
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("step_1_load_raw_data.py", "LOAD RAW DATA"),
    ("step_2_validate_raw_data.py", "VALIDATE RAW DATA"),
    ("step_3_fold_transform_normalize.py", "FOLD, TRANSFORM & NORMALIZE"),
    ("step_4_project_to_evidence.py", "PROJECT TO EVIDENCE"),
    ("step_5_build_business_context.py", "BUILD BUSINESS CONTEXT"),
]


def main():
    passthrough = sys.argv[1:]
    print("\n╔" + "=" * 68 + "╗\n║" + "ACCORD RETAIL: EVIDENCE PIPELINE (steps 1-5, no decisions)".center(68) + "║\n╚" + "=" * 68 + "╝")
    results = []
    for i, (script, description) in enumerate(STEPS, 1):
        print(f"\n[STEP {i}/{len(STEPS)}] {description}")
        rc = subprocess.run([sys.executable, os.path.join(HERE, script), *passthrough]).returncode
        results.append((description, rc == 0))
        if rc != 0:
            break
    print("\n" + "=" * 70 + "\nSUMMARY\n" + "=" * 70)
    for desc, ok in results:
        print(f"{'✅' if ok else '❌'} {desc}")
    if not all(ok for _, ok in results) or len(results) < len(STEPS):
        sys.exit(1)
    print("\nStopped after BUSINESS_CONTEXT. Run scripts/verify_pipeline.py to reconcile against raw data.")


if __name__ == "__main__":
    main()
