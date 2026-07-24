"""Guards for the Session-8 benchmark layer: parse correctness, no-fabrication in the consensus
curation artifact, the leakage-safe SA conversion, and the pre-registered evaluation machinery."""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "pipelines"))          # for the shared _ingest import


def _load_pipeline(name: str):
    """Load pipelines/<name>/fetch.py under a UNIQUE module name — every pipeline's file is
    literally `fetch.py`, so a plain `import fetch` would collide/cache the wrong one."""
    spec = importlib.util.spec_from_file_location(f"{name}_fetch",
                                                  REPO / "pipelines" / name / "fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cleveland_parse_is_prerelease_and_sane():
    CF = _load_pipeline("cleveland_nowcast")
    raw = (REPO / "data" / "raw" / "cleveland_nowcast").glob("*/nowcast_month.json")
    raw = sorted(raw)[-1].read_bytes()
    rows = CF.parse(raw)
    assert len(rows) > 400
    import datetime as dt
    for r in rows:
        # every row's as-of must sit in the plausible release window after its ref month (no leak)
        gap = dt.date.fromisoformat(r["observed_asof"]) - dt.date.fromisoformat(r["reference_month"])
        assert dt.timedelta(days=10) <= gap <= dt.timedelta(days=80), r
        assert r["vintage_status"] == "point_in_time"


def test_consensus_ships_gap_first_and_rejects_uncited_facts():
    CH = _load_pipeline("consensus_history")
    rows = CH.read_rows()
    assert rows, "gap grid should be seeded"
    # a curated row without a source_url/article_date is an uncited fact -> must be rejected
    bad = dict(rows[0]); bad.update(article_type="preview", consensus_pct="0.3",
                                    source_url="", article_date="")
    assert any("uncited" in p or "source_url" in p for p in CH.validate([bad]))
    # a gap row carrying a value (interpolation smell) -> rejected
    smell = dict(rows[0]); smell.update(article_type="gap", consensus_pct="0.3")
    assert any("interpolation" in p for p in CH.validate([smell]))
    # the shipped grid itself must be clean
    assert CH.validate(rows) == []


def test_sa_conversion_is_leakage_safe_and_accurate():
    """SA-from-projected-factor must use only prior-year factors and reconstruct SA MoM well."""
    from nowcast import benchmarks as B, db
    import datetime as dt
    import numpy as np
    with db.connect(B.DB) as conn:
        errs = []
        for inst in ("cpi_headline", "cpi_core"):
            sa = B._levels(conn, B.SA_ID[inst])
            for ref in sa:
                if not ("2023-01-01" <= ref <= "2026-06-01"):
                    continue
                a = B.actual_sa_mom_pct(conn, inst, ref)
                r = B._proj_factor_ratio(conn, inst, ref)
                nsa = B._levels(conn, B.NSA_ID[inst]); pm = B._add(ref, -1)
                if a is None or r is None or ref not in nsa or pm not in nsa or not nsa[pm]:
                    continue
                nsa_mom_bp = (nsa[ref] / nsa[pm] - 1) * 10000       # feed ACTUAL nsa -> should recover SA
                sa_hat = B.our_call_sa_pct(conn, inst, ref, nsa_mom_bp)
                errs.append(abs(sa_hat - a) * 100)
        assert np.mean(errs) < 4.0, f"SA conversion MAE too high: {np.mean(errs):.2f}bp"


def test_binom_p_symmetric():
    from nowcast import benchmarks as B
    assert B._binom_p(5, 10) == 1.0
    assert B._binom_p(10, 10) == pytest.approx(round(2 / 1024, 4))    # reported rounded to 4dp
    assert 0.0 <= B._binom_p(8, 10) <= 1.0


def test_no_curated_consensus_row_is_uncited():
    """Every curated consensus row must carry a source_url AND article_date — no fabrication.
    (Figures were sourced via web search of the cited dated articles; each remains spot-checkable.)"""
    CH = _load_pipeline("consensus_history")
    rows = CH.read_rows()
    assert CH.validate(rows) == []
    curated = [r for r in rows if r["article_type"] in ("preview", "recap")]
    assert curated, "expected some curated consensus rows"
    for r in curated:
        assert r["consensus_pct"] and r["source_url"] and r["article_date"], r
        # consensus is the rounded market variable -> must be a multiple of 0.1
        assert abs(round(float(r["consensus_pct"]) / 0.1) * 0.1 - float(r["consensus_pct"])) < 1e-9, r
