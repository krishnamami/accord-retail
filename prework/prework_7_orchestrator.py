#!/usr/bin/env python3
"""
ORCHESTRATOR: PREWORK FOR STEP 7
Runs all validation scripts before building agents.
"""

import subprocess
import sys

PREWORK_STEPS = [
    ("prework_7a_validate_decisions.py", "VALIDATE DECISIONS"),
    ("prework_7b_rule_activation_model.py", "BUILD RULE ACTIVATION MODEL"),
    ("prework_7c_verify_chain.py", "VERIFY COMPLETE CHAIN"),
    ("prework_7d_detailed_decision_report.py", "DETAILED DECISION REPORT"),
]

def run_script(script_name, description):
    try:
        print(f"\n{'='*80}")
        print(f"Running: {description}")
        print(f"{'='*80}")
        result = subprocess.run([sys.executable, script_name], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed: {e}")
        return False

def main():
    print("\n╔" + "="*78 + "╗")
    print("║" + "PREWORK FOR STEP 7: AGENTS".center(78) + "║")
    print("║" + "Complete validation of decisions".center(78) + "║")
    print("╚" + "="*78 + "╝")
    
    results = []
    
    for script, description in PREWORK_STEPS:
        if run_script(script, description):
            results.append((description, "✅"))
        else:
            results.append((description, "❌"))
            break
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")
    
    for description, status in results:
        print(f"{status} {description}")
    
    if all(status == "✅" for _, status in results):
        print(f"\n✅ ALL PREWORK COMPLETE - READY FOR STEP 7: AGENTS\n")
    else:
        print("\n❌ Prework incomplete")
        sys.exit(1)

if __name__ == "__main__":
    main()
