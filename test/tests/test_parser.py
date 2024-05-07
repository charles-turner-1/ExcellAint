import numpy as np
import polars as pl
import pytest
from pytest import fixture

import excellaint as ea


@fixture
def setup():
    """
    Just a simple setup function to create a parser and a DataFrame that we can
    use in some of our tests.
    """

    import excellaint as ea

    ea_parser = ea.Parser()

    arr = np.array(["2021-01-01","2021-01-02","2021-01-03"],dtype="datetime64")
    df = pl.DataFrame({"date":pl.Series(arr)})

    return ea_parser,df



def test_fail_dt_col_not_str(setup):
    """ 
    Check that we have a string datetime column. This test should fail currently
    but obviously for ease of use we should be able to handle this down the 
    track.
    """
    ea_parser,df = setup

    with pytest.raises(NotImplementedError):
        df = ea_parser(df,"date",check_sorted=False)

def test_fail_dt_col_sorting(setup):
    """
    Check that we aren't trying to sort our datetime column. Right now, `ea_parser`
    should raise a `NotImplementedError` if we try to sort our datetime column.
    """

    ea_parser,df = setup
    df = df.with_columns(pl.col("date").dt.strftime("%Y-%m-%d").alias("date"))

    df = ea_parser(df,"date",check_sorted=False)

    df = ea_parser(df,"date",check_sorted=True)

    assert True


def test_autoindex_col():
    """
    Check that we can add an index column to our DataFrame.
    """

    eap = ea.Parser()

    date_arr = np.array(["2021-01-01","2021-01-02","2021-01-03"],dtype="datetime64")
    id_arr = np.array([101,102,103])

    df = pl.DataFrame(
        {
            "date" : pl.Series(date_arr),
            "runtime_id" : pl.Series(id_arr),
        }
    )

    df = eap._add_index(df)
    assert set(df.columns) == set(["excellaint_index","date","runtime_id"])
    
    df = eap._clean_index(df)
    assert set(df.columns) == set(["date","runtime_id"])


