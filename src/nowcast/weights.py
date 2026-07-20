"""BLS CPI relative-importance weights, served AS OF a date (Session 3A, Task 2).

BLS Handbook of Methods, CPI ch. 17 (weights): relative importances are updated
annually; the weights in effect during calendar year Y are the year-Y relative
importances. A backtest for 2021 must aggregate with 2021 weights, never today's —
so this module keys weights by the year in effect and REFUSES dates outside the
ingested coverage rather than silently substituting the nearest year.

Coverage is exactly the weight_year values present in cpi_weights (currently 2020-2025;
earlier RI tables 404 at the BLS URL, later years not yet published). Deterministic,
offline (rule 4), via db.connect.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from nowcast import db

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "db" / "nowcast.sqlite"


class OutOfWeightCoverage(Exception):
    """The requested date's year has no ingested relative-importance vintage."""


def coverage_years(db_path=DEFAULT_DB) -> set[int]:
    with db.connect(db_path) as conn:
        return {r[0] for r in conn.execute(
            "SELECT DISTINCT weight_year FROM cpi_weights WHERE _superseded_by_run_id IS NULL")}


def _normalize_year(date: str | dt.date) -> int:
    if isinstance(date, dt.date):
        return date.year
    return dt.date.fromisoformat(date).year


def weights_as_of(date: str | dt.date, basis: str = "cpi_u", db_path=DEFAULT_DB) -> dict[str, float]:
    """{item_code: weight} for the relative-importance vintage in effect on `date`.

    `basis` is "cpi_u" or "cpi_w". Raises OutOfWeightCoverage if the date's year is not
    among the ingested vintages — never falls back to a different year (that would be a
    vintage leak on the weights side, the mirror of the timebase firewall)."""
    col = {"cpi_u": "weight_cpi_u", "cpi_w": "weight_cpi_w"}[basis]
    year = _normalize_year(date)
    if year not in coverage_years(db_path):
        raise OutOfWeightCoverage(
            f"no CPI relative-importance vintage for {year}; coverage = {sorted(coverage_years(db_path))}"
        )
    with db.connect(db_path) as conn:
        return {
            code: w
            for code, w in conn.execute(
                f"SELECT item_code, {col} FROM cpi_weights "
                "WHERE weight_year = ? AND _superseded_by_run_id IS NULL",
                (year,),
            )
        }
