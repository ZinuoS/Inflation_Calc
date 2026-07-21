"""Transform for seasonal_factors_loader (naru.ops only). The edge (fetch.py) already
parses the multi-sheet XLSX, maps item names -> codes, unpivots the 12 month columns to
long form, and joins the introduction date; this only promotes the header and coerces
numerics so the load stays a deterministic, auditable naru step."""
COLUMN_NAMES = ["series_id", "item_code", "reference_period",
                "projected_factor", "factor_year", "published_asof"]


def transform(raw_grid):
    df = ops.promote_header(raw_grid, header_row=1, column_names=COLUMN_NAMES)
    df = ops.drop_empty(df)
    df = ops.coerce_numeric(df, "projected_factor")
    df = ops.coerce_numeric(df, "factor_year")
    return df[[*COLUMN_NAMES, "_src_row"]]
