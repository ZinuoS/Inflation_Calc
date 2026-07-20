"""Transform for cpi_weights_loader (naru.ops only)."""
COLUMN_NAMES = ["weight_year","item_code","weight_cpi_u","weight_cpi_w"]
def transform(raw_grid):
    df = ops.promote_header(raw_grid, header_row=1, column_names=COLUMN_NAMES)
    df = ops.drop_empty(df)
    df = ops.coerce_numeric(df, "weight_year")
    df = ops.coerce_numeric(df, "weight_cpi_u")
    df = ops.coerce_numeric(df, "weight_cpi_w")
    return df[[*COLUMN_NAMES, "_src_row"]]
