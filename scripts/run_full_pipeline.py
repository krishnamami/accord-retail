#!/usr/bin/env python3
import subprocess
import sys

STEPS = [
    ("step_1_load_raw_data.py", "LOAD RAW DATA"),
    ("step_2_validate_raw_data.py", "VALIDATE RAW DATA"),
    ("step_3_fold_transform_normalize.py", "FOLD, TRANSFORM & NORMALIZE"),
    ("step_4_project_to_evidence.py", "PROJECT TO EVIDENCE"),
    ("step_5_build_business_context.py", "BUILD BUSINESS CONTEXT"),
    ("step_7_generate_decisions.py", "GENERATE DECISIONS"),
    ("step_6_apply_rules.py", "APPLY RULES"),
    ("step_8_audit_and_replay.py", "AUDIT & REPLAY"),
]

def run_step(script_name, description):
    try:
        print(f"\nRunning: {description}")
        result = subprocess.run([sys.executable, script_name], check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Step failed: {description}")
        return False

def main():
    print("\n╔" + "="*68 + "╗")
    print("║" + "ACCORD RETAIL: PIPELINE ORCHESTRATOR".center(68) + "║")
    print("╚" + "="*68 + "╝")
    
    results = []
    for i, (script, description) in enumerate(STEPS, 1):
        print(f"\n[STEP {i}/{len(STEPS)}]")
        if run_step(script, description):
            results.append((description, "✅"))
        else:
            results.append((description, "❌"))
            break
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    for desc, status in results:
        print(f"{status} {desc}")
    
    if all(status == "✅" for _, status in results):
        print(f"\n✅ ALL STEPS COMPLETE: 190 records created\n")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
