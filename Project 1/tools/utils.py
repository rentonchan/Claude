"""
utils.py — Shared Utilities
Layer 3: Tools | B.L.A.S.T. Framework

Shared helper functions available to all tools in this project.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Union
from dotenv import load_dotenv

# Load secrets from .env
load_dotenv()

# ──────────────────────────────────────────────
# Logging Setup
# ──────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("blast")


# ──────────────────────────────────────────────
# Path Helpers
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"
TMP_DIR.mkdir(exist_ok=True)


def tmp_path(filename: str) -> Path:
    """Return a path inside .tmp/ for intermediate file operations."""
    return TMP_DIR / filename


# ──────────────────────────────────────────────
# Env Helpers
# ──────────────────────────────────────────────
def require_env(key: str) -> str:
    """
    Retrieve a required environment variable.
    Raises a clear error if the key is missing — never silently fails.
    """
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Missing required environment variable: '{key}'. "
            f"Check your .env file."
        )
    return value


# ──────────────────────────────────────────────
# JSON Helpers
# ──────────────────────────────────────────────
def save_json(data: Union[dict, list], filename: str) -> Path:
    """Save data as JSON to .tmp/ and return the file path."""
    path = tmp_path(filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved JSON → {path}")
    return path


def load_json(filename: str) -> Union[dict, list]:
    """Load JSON from .tmp/."""
    path = tmp_path(filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────────
# Timestamp Helper
# ──────────────────────────────────────────────
def now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ──────────────────────────────────────────────
# Self-Test
# ──────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("utils.py self-test starting...")
    test_data = {"status": "ok", "timestamp": now_iso(), "source": "utils.py"}
    path = save_json(test_data, "utils_self_test.json")
    loaded = load_json("utils_self_test.json")
    assert loaded["status"] == "ok", "JSON round-trip failed"
    logger.info(f"✅ utils.py self-test passed. Wrote and read: {loaded}")
