"""Minimal, dependency-free .env loader.

So that `python pipeline/<script>.py` runs without external env sourcing (e.g. `set -a; source
.env`). Loads KEY=VALUE lines from the repo-root .env into os.environ but NEVER overrides a value
already set, so explicit exports (run_coverage.sh, launchd, CI) still win. Secrets stay in .env;
no values are printed. Call load_env() once, before any os.environ.get of a secret.
"""
import os


def load_env(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    try:
        with open(path) as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, val)
    except FileNotFoundError:
        pass
