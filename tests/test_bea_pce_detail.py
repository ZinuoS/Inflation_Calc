"""Parse test for the bea_pce_detail edge (BEA-ingestion session, Task 0)."""
import json

from conftest import load_pipeline

bea = load_pipeline("bea_pce_detail")     # unique-named load; no sys.modules['fetch'] collision

SPEC = {"source": "bea_pce_detail"}
SAMPLE = {"BEAAPI": {"Results": {"Data": [
    {"SeriesCode": "DNMVRC", "LineNumber": "5", "LineDescription": "New motor vehicles",
     "TimePeriod": "2024M06", "DataValue": "437,994"},
    {"SeriesCode": "DHINRG", "LineNumber": "275", "LineDescription": "Net health insurance",
     "TimePeriod": "2024M06", "DataValue": "117.198"},
    {"SeriesCode": "DXXXRC", "LineNumber": "9", "LineDescription": "suppressed",
     "TimePeriod": "2024M06", "DataValue": "(D)"},        # must be skipped
]}}}


def test_parse_strips_commas_maps_period_and_skips_suppressed():
    rows = bea.parse_table(json.dumps(SAMPLE).encode(), "U20405", SPEC)
    assert len(rows) == 2                                  # suppressed (D) dropped
    r = {x["series_id"]: x for x in rows}
    assert r["DNMVRC"]["value"] == "437994" and r["DNMVRC"]["period"] == "2024-06-01"
    assert r["DHINRG"]["value"] == "117.198"
    assert all(x["seasonal"] == "SA" and x["frequency"] == "monthly" for x in rows)


def test_parse_raises_on_api_error():
    import pytest
    err = {"BEAAPI": {"Results": {"Error": {"APIErrorCode": "4", "APIErrorDescription": "inactive"}}}}
    with pytest.raises(SystemExit):
        bea.parse_table(json.dumps(err).encode(), "U20405", SPEC)
