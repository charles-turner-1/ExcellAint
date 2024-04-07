import pytest


def test_import():
    import excellaint

def test_parse_pl_df():
    import numpy as np
    import polars as pl

    import excellaint as ea

    arr = np.array(["2021-01-01","2021-01-02","2021-01-03"],dtype="datetime64")
    df = pl.DataFrame({"date":pl.Series(arr)})
    df = ea.parse_datetime_column(df,"date")
    assert df.column("date").dtype == pl.Date32