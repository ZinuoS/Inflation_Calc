"""SourceRow/TargetRow contract for alfred_vintages.

Bitemporal observations: (series_id, reference_period, observed_asof_vintage) is
the natural key -- a distinct value per vintage, so no vintage ever supersedes
another (they coexist as active rows). vintage_end stays a STRING because open
vintages carry 9999-12-31, which overflows pandas Timestamp. mapping_series_id is
the join back to mapping.yaml (null for PCE headline/core, which have no CPI item).
"""

import datetime as dt

from pydantic import BaseModel


class SourceRow(BaseModel):
    series_id: str
    mapping_series_id: str
    reference_period: str
    observed_asof_vintage: str
    vintage_end: str
    value: str


class TargetRow(BaseModel):
    series_id: str
    mapping_series_id: str
    reference_period: dt.date
    observed_asof_vintage: dt.date
    vintage_end: str
    value: float
