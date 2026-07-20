"""timebase — the ONLY sanctioned read path for historical data (rule 6).

Every model-facing read of a first-release value or MoM goes through this module.
It joins release_calendar (release time) with the ALFRED vintages (release date +
value + reference period) and returns only what was observable strictly before a
given forecast_time. If this module ever leaks a value that was not yet public at
forecast_time, every backtest built on it is invalid.

Design decisions (all firewall-critical):

* Observable datetime of (series, reference month) = that reference period's
  FIRST-RELEASE VINTAGE DATE (from ALFRED -- the authoritative, series-specific
  date the value first appeared) at the release clock time. The clock time is
  looked up from release_calendar for that print+date; when the calendar has no
  matching row (pre-1990 history, annual-revision vintages) it falls back to the
  BLS/BEA 08:30 ET convention. Because the calendar's times are all 08:30 ET
  (override table empty), join and fallback are numerically identical today -- the
  join exists to pick up any future documented time override.
* This means PCE's reference_period never depends on release_calendar's provisional
  (month-1) assignment: timebase reads PCE reference periods from the vintages
  themselves, where they are definitionally correct (research plan D3).
* strictly-before: observable_datetime < forecast_time. At the exact release
  instant the value is NOT yet observable -- the prior print stands.

MoM uses first_release_mom (the within-vintage rule; see views.py). Series-start
and data-gap boundaries have no MoM row by construction; asof_mom skips them,
asof_mom_for_ref raises NoMomExists so a backtest join can never silently fall
back to a different reference month.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from zoneinfo import ZoneInfo

from nowcast import db

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "db" / "nowcast.sqlite"

ET = ZoneInfo("America/New_York")
RELEASE_TIME_ET = dt.time(8, 30)  # BLS/BEA convention (spot-checked, Task 1)


class TimebaseError(Exception):
    """Base for timebase read errors."""


class UnknownSeries(TimebaseError):
    """series_id is neither an ALFRED series id nor a mapping.yaml crosswalk id."""


class NotYetReleased(TimebaseError):
    """The requested reference period had not been released by forecast_time."""


class NoMomExists(TimebaseError):
    """No within-vintage MoM exists for this reference period (series-start, or a
    data gap where the prior month was never released). NOT a leakage condition --
    a structural absence the caller must handle, never silently substitute."""


class PreVintageFloor(TimebaseError):
    """The reference period is below the series' vintage_floor -- ALFRED bulk-archived
    it, so its 'first release' is actually a restated value, not what was published in
    real time. Sibling of NoMomExists: a structural absence, never a usable first
    release. Using it as first-release would be exactly the restated-history leak the
    floor exists to make impossible."""


def _series_print(series_id: str) -> str:
    """Which release prints this series: CPI, PPI, or PCE."""
    if series_id == "PPIFIS":
        return "PPI"
    if series_id in ("PCEPI", "PCEPILFE"):
        return "PCE"
    return "CPI"  # CPIAUCSL, CPILFESL, CPI*SL aliases, CUSR0000* components


def _normalize_forecast_time(forecast_time: dt.datetime) -> dt.datetime:
    """Naive forecast_time is interpreted as ET (the release timezone)."""
    if forecast_time.tzinfo is None:
        return forecast_time.replace(tzinfo=ET)
    return forecast_time


def _normalize_ref(ref_period: str | dt.date) -> str:
    if isinstance(ref_period, dt.date):
        return ref_period.replace(day=1).isoformat()
    return dt.date.fromisoformat(ref_period).replace(day=1).isoformat()


class Timebase:
    """Vintage-safe reader bound to one open connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        # crosswalk: accept mapping.yaml ids or ALFRED ids, resolve to ALFRED id
        self._to_series: dict[str, str] = {}
        for series_id, mapping_id in conn.execute(
            "SELECT DISTINCT series_id, mapping_series_id FROM observations"
        ):
            self._to_series[series_id] = series_id
            if mapping_id:
                self._to_series.setdefault(mapping_id, series_id)
        # release-time overrides keyed by (print, release_date); today all 08:30 ET
        self._release_dt_et: dict[tuple[str, str], str] = {
            (p, d): iso
            for p, d, iso in conn.execute(
                "SELECT print, release_date, release_datetime_et FROM release_calendar"
            )
        }
        # per-series vintage floor: earliest ref with a genuine (non-bulk-archived)
        # first release. MoM below the floor is restated-as-first -> refused.
        self._vintage_floor: dict[str, str] = dict(
            conn.execute("SELECT series_id, vintage_floor FROM series_vintage_floor")
        )

    # -- resolution ------------------------------------------------------------

    def resolve(self, series_id: str) -> str:
        try:
            return self._to_series[series_id]
        except KeyError:
            raise UnknownSeries(
                f"{series_id!r} is not an ALFRED series id or a mapping.yaml crosswalk id"
            ) from None

    def _observable_dt(self, series_id: str, vintage: str) -> dt.datetime:
        """When (series, whose first-release vintage is `vintage`) became public."""
        key = (_series_print(series_id), vintage)
        iso = self._release_dt_et.get(key)
        if iso is not None:
            return dt.datetime.fromisoformat(iso).replace(tzinfo=ET)
        return dt.datetime.combine(dt.date.fromisoformat(vintage), RELEASE_TIME_ET, tzinfo=ET)

    # -- level asof ------------------------------------------------------------

    def asof(self, series_id: str, forecast_time: dt.datetime) -> float:
        """Last first-release LEVEL observable strictly before forecast_time."""
        sid = self.resolve(series_id)
        ft = _normalize_forecast_time(forecast_time)
        best: tuple[str, float] | None = None
        for ref, value, vintage in self.conn.execute(
            "SELECT reference_period, first_release_value, first_release_vintage "
            "FROM first_release WHERE series_id = ?",
            (sid,),
        ):
            if self._observable_dt(sid, vintage) < ft and (best is None or ref > best[0]):
                best = (ref, value)
        if best is None:
            raise NotYetReleased(f"{sid}: nothing released before {ft.isoformat()}")
        return best[1]

    # -- MoM asof --------------------------------------------------------------

    def asof_mom(self, series_id: str, forecast_time: dt.datetime) -> float:
        """Latest within-vintage MoM observable strictly before forecast_time.
        Omitted-boundary reference months are naturally skipped."""
        sid = self.resolve(series_id)
        ft = _normalize_forecast_time(forecast_time)
        floor = self._vintage_floor.get(sid)
        best: tuple[str, float] | None = None
        for ref, mom, vintage in self.conn.execute(
            "SELECT reference_period, mom, vintage FROM first_release_mom WHERE series_id = ?",
            (sid,),
        ):
            if floor is not None and ref < floor:
                continue  # below vintage floor: restated-as-first, skipped
            if self._observable_dt(sid, vintage) < ft and (best is None or ref > best[0]):
                best = (ref, mom)
        if best is None:
            raise NotYetReleased(f"{sid}: no MoM released before {ft.isoformat()}")
        return best[1]

    def asof_mom_for_ref(
        self, series_id: str, ref_period: str | dt.date, forecast_time: dt.datetime
    ) -> float:
        """The specific reference month's first-release MoM, ONLY if observable.

        Raises NoMomExists if that month has no within-vintage MoM (series-start or
        gap), and NotYetReleased if its print had not occurred by forecast_time.
        Backtest joins use this form: a silent fall-back to a different reference
        month is impossible by construction.
        """
        sid = self.resolve(series_id)
        ref = _normalize_ref(ref_period)
        ft = _normalize_forecast_time(forecast_time)
        floor = self._vintage_floor.get(sid)
        if floor is not None and ref < floor:
            raise PreVintageFloor(
                f"{sid} {ref}: below vintage_floor {floor} -- ALFRED bulk-archived, "
                "first release is restated not real-time"
            )
        row = self.conn.execute(
            "SELECT mom, vintage FROM first_release_mom WHERE series_id = ? AND reference_period = ?",
            (sid, ref),
        ).fetchone()
        if row is None:
            raise NoMomExists(f"{sid}: no within-vintage MoM for reference {ref}")
        mom, vintage = row
        if self._observable_dt(sid, vintage) >= ft:
            raise NotYetReleased(
                f"{sid} {ref}: released {vintage} 08:30 ET, not observable at {ft.isoformat()}"
            )
        return mom


@contextmanager
def open_timebase(db_path: str | Path = DEFAULT_DB) -> Iterator[Timebase]:
    """Open a Timebase over a WAL/busy-timeout connection, guaranteed to close."""
    with db.connect(db_path) as conn:
        yield Timebase(conn)
