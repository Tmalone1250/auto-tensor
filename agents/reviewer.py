"""
agents/reviewer.py — Reviewer Agent v1.0
Auditor + Verification Engine for Auto-Tensor.
Governed by core/health_check.py. Routes execution via core/executor.py.
"""
import os
import sys
import logging
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.health_check import governor_gate
from core.executor import run_wsl_in_workspace

LOG_PATH = "logs/reviewer.log"
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

DIFF_PATHS = [
    "workspace/optimism/rust/kona/justfile",
    "workspace/optimism/rust/kona/docker/fpvm-prestates/cannon-repro.dockerfile",
]


def audit_side_effects() -> dict:
    """Check scope: does this fix touch more than the two expected files?"""
    result = run_wsl_in_workspace(
        "optimism/rust/kona",
        "git diff --name-only",
        timeout=30,
    )
    changed = [l.strip() for l in result.stdout.splitlines() if l.strip()]
    expected = {"justfile", "docker/fpvm-prestates/cannon-repro.dockerfile"}
    touched  = {os.path.basename(p) for p in changed}

    side_effects = touched - expected
    ok = len(side_effects) == 0
    logging.info(f"Reviewer: Side-effect check — changed={changed}, side_effects={side_effects}, clean={ok}")
    return {"changed_files": changed, "side_effects": list(side_effects), "clean": ok}


def audit_surgical_density() -> dict:
    """Count lines changed — enforce < 20 line delta."""
    result = run_wsl_in_workspace(
        "optimism/rust/kona",
        "git diff --shortstat",
        timeout=30,
    )
    stat = result.stdout.strip()

    # Parse "+ X insertions, - Y deletions"
    lines_changed = 0
    for token in stat.split(","):
        token = token.strip()
        if "insertion" in token or "deletion" in token:
            try:
                lines_changed += int(token.split()[0])
            except ValueError:
                pass

    surgical = lines_changed <= 20
    logging.info(f"Reviewer: Line delta = {lines_changed} — surgical={surgical}")
    return {"stat": stat, "lines_changed": lines_changed, "surgical": surgical}


def verify_after_state() -> dict:
    """Re-run the corrected build to confirm PASS state."""
    IMAGE       = "us-docker.pkg.dev/oplabs-tools-artifacts/images/cannon-builder:v1.0.0"
    TARGET_SPEC = "kona/docker/cannon/mips64-unknown-none.json"

    result = run_wsl_in_workspace(
        "optimism/rust/kona",
        f"docker.exe run --rm "
        f"-v \"$(wslpath -w $(pwd)):/workdir\" "
        f"-w=/workdir {IMAGE} "
        f"cargo build -Zbuild-std=core,alloc -Zjson-target-spec "
        f"--target {TARGET_SPEC} "
        f"-p kona-client --bin kona-client --profile release-client-lto",
        timeout=600,
    )
    passed = result.returncode == 0
    log = (result.stdout + result.stderr)[:1000]
    logging.info(f"Reviewer: Verification build {'PASSED' if passed else 'FAILED'}.")
    return {"passed": passed, "log": log}


def run() -> dict:
    print("[REVIEWER] Checking Governor clearance...")
    if not governor_gate():
        print("[REVIEWER] Governor BLOCKED — Halting review.")
        return {}

    print("[REVIEWER] Governor cleared. Beginning audit.")

    side_fx   = audit_side_effects()
    density   = audit_surgical_density()
    after     = verify_after_state()

    report = {
        "side_effects":    side_fx,
        "surgical_density": density,
        "verification":    after,
        "overall_pass":    side_fx["clean"] and density["surgical"] and after["passed"],
    }

    import json
    print(f"\n[REVIEWER] Audit Complete:\n{json.dumps(report, indent=2)}")
    logging.info(f"Reviewer: Final report: {json.dumps(report)}")
    return report


if __name__ == "__main__":
    run()
