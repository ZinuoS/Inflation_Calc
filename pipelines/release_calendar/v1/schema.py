"""SourceRow/TargetRow contract for release_calendar.

Source is the canonical CSV emitted by ../fetch.py (every cell a string, per
naru's CSV reader). TargetRow is the enforced contract: reference_period and
release_date become real dates; release_datetime_et stays an ISO local-ET
string (tz America/New_York is applied downstream in timebase.py, where DST
is handled). reference_period_basis flags PCE rows as provisional_pending_vintage.
"""

import datetime as dt

from pydantic import BaseModel


class SourceRow(BaseModel):
    print: str
    reference_period: str
    reference_period_basis: str
    release_date: str
    release_datetime_et: str
    release_time_basis: str
    source_url: str


class TargetRow(BaseModel):
    print: str
    reference_period: dt.date
    reference_period_basis: str
    release_date: dt.date
    release_datetime_et: str
    release_time_basis: str
    source_url: str
