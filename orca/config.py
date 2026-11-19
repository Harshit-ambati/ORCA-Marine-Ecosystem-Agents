"""Read local development settings, preferring a pasted key over a stale shell key."""

import os
from pathlib import Path


def load_local_env():
    path = Path(__file__).resolve().parent.parent / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in {"GEMINI_API_KEY", "OPENAI_API_KEY", "ORCA_PROVIDER", "ORCA_MODEL"}:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if value:
            if key.endswith("_API_KEY"):
                os.environ[key] = value
            else:
                os.environ.setdefault(key, value)
