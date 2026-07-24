"""Shared test helpers.

`load_pipeline` loads a pipeline's `fetch.py` under a UNIQUE module name. Every pipeline's file is
literally named `fetch.py`, so the old `sys.path.insert(...); import fetch` pattern cached the FIRST
one imported into `sys.modules['fetch']` and handed it to every later test — a real bug that a
root-level `fetch.py` (from a flattened web upload) made worse by shadowing all of them. Loading by
path under `<name>_fetch` removes the shared-name hazard entirely.
"""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "pipelines"))          # for the shared `_ingest` import


def load_pipeline(name: str):
    spec = importlib.util.spec_from_file_location(f"{name}_fetch",
                                                  REPO / "pipelines" / name / "fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
