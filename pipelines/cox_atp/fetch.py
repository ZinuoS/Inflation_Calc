"""Edge parser for cox_atp (Session 2B-final, B2). Deterministic ATP extraction from a
Cox/KBB press release. The extractor is validated (golden); full-series COVERAGE is
blocked on inconsistent report URL slugs -> needs an insights-index crawl (naru#8, see
STATUS.md). No patchy non-consecutive series is shipped (never interpolate)."""
from __future__ import annotations
import re, sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
PIPE = Path(__file__).resolve().parent


def extract_atp(html: str, spec: dict) -> float | None:
    """First $XX,XXX after the ATP anchor phrase -> float. Deterministic. Pure/testable."""
    p = spec["parse"]
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    m = re.search(re.escape(p["anchor"]) + r".{0," + str(p["window_chars"]) + r"}?" + p["value_regex"],
                  text, re.I)
    return float(m.group(1).replace(",", "")) if m else None


if __name__ == "__main__":
    cfg = yaml.safe_load((PIPE / "spec.yaml").read_text())
    print("cox_atp: parser only; coverage blocked on report URL enumeration (see STATUS.md)")
