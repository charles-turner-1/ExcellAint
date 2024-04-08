import os
import warnings

import pandas as pd
import polars as pl
import polars.selectors as cs

import excellaint as ea

ea.config.date_sep = "/"
ea.config.datetime_sep = " "
DATETIME_COL = "DATE_STR"

test_file = "/Users/ct6g18/Python/ExcellAint/test/test_data/2_digit_yr.xlsx"
df = pd.read_excel(test_file).rename(columns={"mangled_dates" : DATETIME_COL})

colnames_init = df.columns.tolist()[:2]

# SPlit datetimes and split dates are very similar but the order we need to drop
# columns in is different, so we can't combine them for the time being - will 
# a bit of a refactor first

def split_datetimes(df : pl.DataFrame | pd.DataFrame
                   ,datetime_col : str = "mangled_dates"
                   ,datetime_sep : str = ea.config.datetime_sep
                   ) -> pl.DataFrame:
    """
    Type union between pl.Dataframe and pd.DataFrame should be removed.

    To be honest, I haven't got a particularly good idea as to how this works. I
    copied it from stackoverflow 
    (https://stackoverflow.com/questions/73699500/python-polars-split-string-column-into-many-columns-by-delimiter)
    and it seems to do what I wanted.

    """

    if isinstance(df, pl.DataFrame):
        pass
    elif isinstance(df, pd.DataFrame):
        df = pl.from_pandas(df)
    else:
        raise ValueError("df must be a pandas or polars DataFrame")

    return (
        df
        .with_columns(
            pl.col(datetime_col).str.split(datetime_sep)
                                    .alias("[date,time]"))
        .explode("[date,time]")
        .with_columns(
            ("string_" + pl.arange(0, pl.len()).cast(pl.Utf8).str.zfill(2))
            .over("row_id")
            .alias("col_nm")
        )
        .pivot(
            index=['row_id',datetime_col],
            values='[date,time]',
            columns='col_nm',
        )
        .drop(DATETIME_COL)
        .rename(
            {
                "string_00": datetime_col,
                "string_01": "time_str"
            }
        )
    )

def split_dates(df : pl.DataFrame | pd.DataFrame
               ,datetime_col : str = "mangled_dates"
               ,date_sep : str = ea.config.date_sep
               ) -> pl.DataFrame:
    """
    Type union between pl.Dataframe and pd.DataFrame should be removed.

    To be honest, I haven't got a particularly good idea as to how this works. I
    copied it from stackoverflow 
    (https://stackoverflow.com/questions/73699500/python-polars-split-string-column-into-many-columns-by-delimiter)
    and it seems to do what I wanted.

    """

    if isinstance(df, pl.DataFrame):
        pass
    elif isinstance(df, pd.DataFrame):
        df = pl.from_pandas(df)
    else:
        raise ValueError("df must be a pandas or polars DataFrame")

    return (
        df
        .with_columns(
            pl.col(datetime_col).str.split(date_sep)
                                    .alias("[date]"))
        .explode("[date]")
        .with_columns(
            (pl.arange(0, pl.len()))
            .over("row_id")
            .alias("col_nm")
        )
        .pivot(
            index=['row_id',datetime_col,'Time'],
# We can make this more robust in the future by working out all the columns other 
# than the column we want to split
            values='[date]',
            columns='col_nm',
        )
        .drop(datetime_col)
    )   

def convert_time(df : pl.DataFrame) -> pl.DataFrame:
    """
    Takes the time column and converts it to a time object.

    This is somewhat less ambiguous than splitting dates up, so I'm going to 
    keep it simple for now so we can resolve the main issue
    """
    return (
        df.with_columns(
            pl.col("time_str")
            .str
            .to_time(f"%H{ea.config.time_sep}%M")
            .alias("Time")
        )
    )

def assign_datetype(cols_to_process : list[str]
                   ,max_chars_dict : dict[str,int]
                   ,max_val_dict : dict[str,int]
                   ) -> dict[str,str]:
    """
    This function takes the columns to process, the maximum number of characters
    in each column and the maximum value in each column and returns a dictionary
    of the `date data` types of each column:
        - Year 
        - Month
        - Day
    """
    available_date_data_types = { 
        "Year",
        "Month",
        "Day",
    }

    mappings = {
        "Year" : None,
        "Month" : None,
        "Day" : None,
    }

    for key, val in max_chars_dict.items():
        if val == 4:
            mappings["Year"] = int(key)
            available_date_data_types.remove("Year")

            if not ea.config.allow_monthfirst:
                mappings["Day"] = 2 - mappings["Year"]
                mappings["Month"] = 1

                available_date_data_types.remove("Day")
                available_date_data_types.remove("Month")
                break
            
            else:
                raise NotImplementedError("Only an instance with a four digit year is supported at the moment.")


    if len(available_date_data_types) > 0:
        raise AssertionError(f"Could not assign all date data types. Remaining: {available_date_data_types}. Please check the data.")

    mappings = {str(val) : key for key, val in mappings.items()}

    warnings.warn("Did not use the following arguments: {max_val_dict}, {cols_to_process}."
                  " We probably need to make this function a bit smarter."
                  ,stacklevel=2)

    return mappings
        
def year_to_int(df : pl.DataFrame
                ,year_col : str = "Year"
                ) -> pl.DataFrame:
    """
    This gets a bit stupid, because we need to generate a new column which is a
    boolean: is the year column four characters. If so, we can cast it to an int.
    If not, we want to check if the two characters we have are less than or equal 
    to the current year. If so, we prepend "20". If not, we prepend "19".
    """

    # Spoof the current year

    CURRENT_YEAR = 24

    df = df.with_columns(
        pl.col("Year").str.len_chars().alias("year_len")
    )

    df = df.with_columns(
        pl.when(pl.col("year_len") == 4)
          .then(pl.col("Year").cast(pl.Int32))
          .otherwise(
            pl.col("Year")
          ).alias("Year")
    )

    df = df.with_columns(
        pl.when(pl.col("year_len") == 2)
        .then(
            pl.when(pl.col("Year").cast(pl.Int32) <= CURRENT_YEAR)
            .then(pl.lit("20"))
            .otherwise(pl.lit("19"))
           )
        .otherwise(pl.lit(""))
        .alias("prepend_col")
    )

    df = df.with_columns(
        (pl.col("prepend_col") + pl.col("Year").alias("Year"))
        .cast(pl.Int32)
        .alias("Year")
    )

    df = df.drop("year_len","prepend_col")

    return df.with_columns(
        pl.col(year_col).cast(pl.Int32)
    )

def combine_date_cols(df : pl.DataFrame) -> pl.DataFrame:
    """
    This function takes a dataframe with date columns and a time column and 
    combines them into a datetime column. Since the names are all set by the 
    previous functions we can keep things really constrained

    """

    df = df.with_columns(
        pl.date(
            pl.col("Year"),
            pl.col("Month"),
            pl.col("Day"),
        ).alias("Date")
        )

    return df

def combine_datetime_cols(df : pl.DataFrame) -> pl.DataFrame:
    """
    Combine our date and our time column
    """

    df = df.with_columns(
        pl.datetime(
            pl.col("Date").dt.year(),
            pl.col("Date").dt.month(),
            pl.col("Date").dt.day(),
            pl.col("Time").dt.hour(),
            pl.col("Time").dt.minute(),
            pl.col("Time").dt.second(),
        ).alias("Datetime")
        )

    df= df.drop("Date","Time","Year","Month","Day")

    return df

def get_cols_to_process(df : pl.DataFrame
                       ,colnames_init : list[str]) -> list[str]:
    """
    Filter out the columns we want to process for date information
    """
    return [col for col in df.select(cs.by_dtype(pl.Utf8)).columns if col not in colnames_init]

def create_max_dicts(df : pl.DataFrame
                    ,cols_to_process : list[str]
                    ) -> tuple[dict[str,int],dict[str,int]]:
    """
    Generates statistics for the columns we want to process: maximum chars (helps 
    to work our which column is year), maximum value (helps to work out which 
    column is day)
    """
    # This section here needs wrapping up in a function 

    # First thing to do is get the max character width of them all
    processing_df = df.select(*cols_to_process)

    max_chars_dict = processing_df.with_columns(
        [pl.col(colname).str.len_chars().max() for colname in cols_to_process]
    ).max().to_dict(as_series=False)

    max_chars_dict = {
        key : val[0] if val else None for key,val in max_chars_dict.items()
    }


    max_val_dict = processing_df.with_columns(
        [pl.col(colname).cast(pl.Int32).max() for colname in cols_to_process]
    ).max().to_dict(as_series=False)

    max_val_dict = {
        key : val[0] if val else None for key,val in max_val_dict.items()
    }   

    return max_chars_dict,max_val_dict

df = split_datetimes(df,datetime_col=DATETIME_COL)
df = convert_time(df)

df = split_dates(df,datetime_col=DATETIME_COL)

cols_to_process = get_cols_to_process(df,colnames_init)
max_chars_dict,max_val_dict = create_max_dicts(df,cols_to_process)

mappings = assign_datetype(cols_to_process,max_chars_dict,max_val_dict)

df = (df.rename(mappings)
        .with_columns(
            pl.col("Day").cast(pl.Int32),
            pl.col("Month").cast(pl.Int32),
    )
)

df = year_to_int(df)
df = combine_date_cols(df)
df = combine_datetime_cols(df)

print(df)