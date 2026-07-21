"""SourceRow/TargetRow for bls_seasonal_factors — BLS published PROJECTED CPI-U
seasonal factors, one file per calendar year (Session 3A, Task 3b reroute).

BLS Handbook of Methods, CPI ch. 17 (seasonal adjustment): each January the CPI
program re-estimates seasonal factors and PROJECTS the coming year's factors, which
are then applied mechanically to that year's first releases. This table harvests those
projected factors (the "Seasonal factors table, YYYY" XLSX). `reference_period` is the
month the factor applies to; `factor_year` is its file/calendar year; `published_asof`
is the date the factors were introduced (the January-YYYY CPI release date) — the
vintage key that makes the factor knowable-before-the-month, not a hindsight value.
`projected_factor` is a ratio (published value / 100), so NSA / projected_factor = SA.
"""
from pydantic import BaseModel


class SourceRow(BaseModel):
    series_id: str          # CUSR0000{item_code} (the SA series the factor produces)
    item_code: str          # CPI item code (SETB01, SETA02, ...)
    reference_period: str    # month the factor applies to, YYYY-MM-01
    projected_factor: str    # NSA/SA ratio (published pct / 100)
    factor_year: str         # the factor file's calendar year
    published_asof: str      # Jan-YYYY CPI release date (factor introduction / vintage key)


class TargetRow(BaseModel):
    series_id: str
    item_code: str
    reference_period: str
    projected_factor: float
    factor_year: int
    published_asof: str
