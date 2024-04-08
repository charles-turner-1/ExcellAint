import warnings
from pprint import pformat

import pandas as pd
import polars as pl
import polars.selectors as cs

"""
Excellaint - A Python toolbox for dealing with some of the oddities that Excel 
can introduce introduce

This module will give you a couple of functions that help you parse, clean, and
then write datetime columns that excel has helpfully mangled for you back to a 
clean dataframe. 

Right now, it is going to expose a single function that will parse a datetime
column and return a new dataframe with the dates cleaned up, which will have two 
columns:
    - Input Column: The original column that was passed in
    - Parsed Column: The column that has been cleaned up

Configuration can be set through a singleton config class, which will contain all
of the options you might want to set. `excellaint` then reads from this 
configuration to determine how to parse and write datetimes back out.

In the future, we might rewrite stuff to make it more 'polarsy', but for now, I 
just want to sketch out the basic functionality. Once we have it working we can 
then think about how to make it more efficient, and maybe generating an interface
which is more congruent with polars and its plugin ecosystem.

"""

def parse_datetime_column(df: pl.DataFrame | pd.DataFrame
                         ,date_column_name: str
                         ,check_sorted: bool = False
                         ) -> pl.DataFrame: 
    """
    Parse an excel date column. This will take a column of dates that have been
    mangled by excel, and return a column of dates that are in a clean format.

    This function will read from the configuration to determine how to parse the
    dates. 

    Parameters:
    - df: The dataframe that contains the column you want to parse. Must be either
        a polars dataframe or a pandas dataframe.
    - column_name: The name of the column that you want to parse
    - check_sorted: Whether to check if the column is sorted. If the column is
        not sorted, then we will not be able to parse it - since we will not be
        able to determine the order of the date, month, and year.

    Returns:
    - A new dataframe with the column parsed, with the datatype converted to a 
        datetime. You can then choose how to write this back out to a file -
        either as a datetime, or as a string, etc.
    """

    if isinstance(df, pd.DataFrame):
        df = pl.from_pandas(df)
    elif not isinstance(df, pl.DataFrame):
        raise TypeError("df must be either a polars or pandas dataframe")

    if date_column_name not in df.columns:
        raise ValueError(f"Column {date_column_name} not found in dataframe")

    if check_sorted:
        raise NotImplementedError(" *** UNDER CONSTRUCTION ***")
    
    config = ExcellAintConfig.__instance__

    # Get the column that we want to parse
    df = split_datetimes(df,datetime_col=date_column_name,datetime_sep=config.datetime_sep)
    df = convert_time(df,time_sep=config.time_sep)

    df = split_dates(df,datetime_col=date_column_name,date_sep=config.date_sep)

    cols_to_process = get_cols_to_process(df,date_column_name)
    max_chars_dict,max_val_dict = create_max_dicts(df,cols_to_process)

    mappings = assign_datetype(config
                              ,max_chars_dict
                              ,max_val_dict
                              ,cols_to_process)


    df = (df.rename(mappings)
            .with_columns(
                pl.col("Day").cast(pl.Int32),
                pl.col("Month").cast(pl.Int32),
        )
    )

    df = year_to_int(df)
    df = combine_date_cols(df)
    df = combine_datetime_cols(df)

    return df


# Internal functions - these are the functions that will be used to parse the 
# datetime column. I'll stick these somewhere else in the future, but for now
# lets just dump them here for simplicity.

def split_datetimes(df : pl.DataFrame | pd.DataFrame
                   ,datetime_col : str = "mangled_dates"
                   ,datetime_sep : str = 'excellaint.config.datetime_sep'
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
        .drop(datetime_col)
        .rename(
            {
                "string_00": datetime_col,
                "string_01": "time_str"
            }
        )
    )

def split_dates(df : pl.DataFrame | pd.DataFrame
               ,datetime_col : str = "mangled_dates"
               ,date_sep : str = 'excellaint.config.date_sep'
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

def convert_time(df : pl.DataFrame
                ,time_sep : str = 'excellaint.config.time_sep'
                 ) -> pl.DataFrame:
    """
    Takes the time column and converts it to a time object.

    This is somewhat less ambiguous than splitting dates up, so I'm going to 
    keep it simple for now so we can resolve the main issue
    """
    return (
        df.with_columns(
            pl.col("time_str")
            .str
            .to_time(f"%H{time_sep}%M")
            .alias("Time")
        )
    )

def assign_datetype(config : 'ExcellAintConfig'
                   ,max_chars_dict : dict[str,int]
                   ,max_val_dict : dict[str,int]
                   ,cols_to_process : list[str]
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

            if not config.allow_monthfirst:
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

class ExcellAintConfig():
    __instance__ = None


    mode = "date"

    year = True
    month = True
    day = True

    hour = True
    minute = True
    second = True

    date_sep = "-"
    time_sep = ":"

    datetime_sep = " " # This is the separator between the date and the time.
    # I'm not sure if this is the best choice of variable name - maybe we should
    # call it `dt_sep` or something like that.

    # Typically, excel won't bungle the separator - more likely it will just 
    # mess up the order of the date. With that said, if we have an excel driven 
    # date cockup, we might also expect the date separator to have changed.

    allow_monthfirst = False
    allow_dayfirst = True
    allow_yearfirst = True
    
    def __init__(self):
        """
        Constructor for our configuration class. This will set up the default
        values for our configuration. 

        Only one instance of this class should exist, and it should be shared
        across all of the functions in the module. 
        """
        if ExcellAintConfig.__instance__ is None:
            ExcellAintConfig.__instance__ = self
        else:
            raise Exception("You cannot create another ExcellAintConfig instance")

    def __str__(self):
        cfg_dict = {
            "mode": self.mode,
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "hour": self.hour,
            "minute": self.minute,
            "second": self.second,
            "date_sep": self.date_sep,
            "time_sep": self.time_sep,
            "datetime_sep": self.datetime_sep,
            "allow_monthfirst": self.allow_monthfirst,
            "allow_dayfirst": self.allow_dayfirst,
            "allow_yearfirst": self.allow_yearfirst
        }
        return f"ExcellAint Configuration:\n{pformat(cfg_dict,indent=4)}"

    def set_mode(self, mode: str) -> None:
        """
        Set the mode for the datetime column. This will determine whether the
        column is parsed as a date or a datetime. 

        If the mode is set to "date", then hour, minute, and second will be set
        to False.

        Parameters:
        - mode: The mode to set. This should be either "date" or "datetime"
        """
        if mode not in ["date","datetime"]:
            raise ValueError("Mode must be either 'date' or 'datetime'")
        self.mode = mode

        if mode == "date":
            self.hour = False
            self.minute = False
            self.second = False

    @classmethod
    def set_date_fmt_american(cls, allowed : bool) -> None:
        """
        If the date is intended to be in an American format, then we will *always* 
        expect the month to come before the day - whether its written as 
        MM/DD/YYYY or YYYY/MM/DD. 

        We also expect the separator to be a forward slash.

        Parameters:
        - allowed: Whether the date can be in an American format.
        """

        cls.allow_monthfirst = allowed
        cls.allow_dayfirst = not allowed
        cls.date_sep = "/"