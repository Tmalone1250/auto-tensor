"""
core/health_check.py — The Governor
Auto-Tensor Rate-Limit Protection & Miner Priority Enforcement
"""
import os
import time
import logging
import requests
from datetime import datetime

# --- Configuration ---
GITHUB_PAT = os.getenv("GITHUB_PAT")
QUOTA_THRESHOLD = 750       # 15% of 5,000
HEARTBEAT_LOW = "HEARTBEAT_LOW"
HEARTBEAT_OK  = "HEARTBEAT_OK"
LOG_PATH = "logs/governor.log"

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def _headers() -> dict:
    h = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_PAT:
        h["Authorization"] = f"token {GITHUB_PAT}"
    return h


def check_rate_limit() -> dict:
    """Query /rate_limit and return the core quota dict."""
    try:
        resp = requests.get("https://api.github.com/rate_limit", headers=_headers(), timeout=10)
        resp.raise_for_status()
        return resp.json().get("resources", {}).get("core", {})
    except Exception as e:
        logging.error(f"Health check request failed: {e}")
        return {}


def governor_gate() -> bool:
    """
    The Governor.

    Returns True if agents may proceed.
    Returns False (and blocks) if quota is critically low.

    Miner Priority Rule:
        Any failure here results in an immediate halt of all Scout/Coder activity.
    """
    core = check_rate_limit()

    if not core:
        # Network failure — assume miner has priority, halt agents.
        logging.critical("Governor: Health check returned empty — HALTING all agent activity (Miner Priority).")
        return False

    remaining = core.get("remaining", 0)
    reset_ts   = core.get("reset", 0)
    limit      = core.get("limit", 5000)

    pct = (remaining / limit * 100) if limit else 0
    status = HEARTBEAT_OK if remaining >= QUOTA_THRESHOLD else HEARTBEAT_LOW

    logging.info(
        f"Governor: {status} | remaining={remaining}/{limit} ({pct:.1f}%) | "
        f"reset={datetime.utcfromtimestamp(reset_ts).strftime('%H:%M:%S UTC')}"
    )

    if status == HEARTBEAT_LOW:
        sleep_seconds = max(0, reset_ts - int(time.time())) + 60  # +60s buffer
        logging.warning(
            f"Governor: {HEARTBEAT_LOW} — quota below 15%. "
            f"Entering mandatory sleep for {sleep_seconds}s. "
            f"Miner has priority. All Scout/Coder activity HALTED."
        )
        print(f"[GOVERNOR] {HEARTBEAT_LOW} — sleeping {sleep_seconds}s until quota resets.")
        time.sleep(sleep_seconds)
        # Re-check after sleep
        return governor_gate()

    return True


if __name__ == "__main__":
    can_proceed = governor_gate()
    print(f"[GOVERNOR] Agents cleared to proceed: {can_proceed}")
