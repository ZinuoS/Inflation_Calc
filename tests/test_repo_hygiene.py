"""Repo hygiene guard — fails on the root-level module shadowing that a flattened web upload once
introduced (a repo-root `fetch.py` shadowed every `pipelines/*/fetch.py` on sys.path, plus stray
`test_*.py` duplicates of `tests/` files). Keeps the repo root free of importable modules and of
any basename that duplicates a file living under pipelines/, src/, or tests/.
"""
import subprocess
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# The only files that legitimately live at the repo root.
ALLOWED_ROOT = {".gitignore", "CLAUDE.md", "LICENSE", "README.md", "pyproject.toml", "uv.lock"}
# Extensions that become importable / collectible on sys.path and so must never sit at the root.
SHADOWING_EXT = {".py", ".yaml", ".yml"}


def _tracked_files() -> list[str]:
    out = subprocess.run(["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True, check=True)
    return [ln for ln in out.stdout.splitlines() if ln]


def test_repo_root_has_no_importable_modules():
    """No .py/.yaml at the repo root — those shadow package and pipeline modules on sys.path."""
    files = _tracked_files()
    offenders = [f for f in files if "/" not in f and Path(f).suffix in SHADOWING_EXT]
    assert not offenders, f"root-level importable files shadow real modules: {offenders}"


def test_root_files_are_the_known_allowlist():
    """Any new bare file at the repo root is a review trip-wire (catches stray .md/.txt/.bundle)."""
    root = {f for f in _tracked_files() if "/" not in f}
    unexpected = root - ALLOWED_ROOT
    assert not unexpected, (f"unexpected repo-root files {sorted(unexpected)}; put them under "
                            f"docs/ pipelines/ src/ tests/, or add to ALLOWED_ROOT if truly root-level")


def test_no_root_file_duplicates_a_packaged_file():
    """A root file whose basename also exists under pipelines/ src/ tests/ is a shadow/duplicate."""
    files = _tracked_files()
    packaged = defaultdict(list)
    for f in files:
        if f.startswith(("pipelines/", "src/", "tests/")):
            packaged[Path(f).name].append(f)
    clashes = {f: packaged[Path(f).name] for f in files
               if "/" not in f and Path(f).name in packaged}
    assert not clashes, f"root files duplicate packaged modules: {clashes}"
