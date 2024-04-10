import warnings
from datetime import date
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

This file is going to reimplement the parse_datetime_column from the file 
`./excellaint.py`, but using a parser class where we've also added a .__call__()
method to keep everything bundled together.


In the future, we might rewrite stuff to make it more 'polarsy', but for now, I 
just want to sketch out the basic functionality. Once we have it working we can 
then think about how to make it more efficient, and maybe generating an interface
which is more congruent with polars and its plugin ecosystem.
"""

class Parser():
    def __init__(self
                ,mode : str = "date"
                ,date_sep : str = "/"
                ,time_sep : str = ":"
                ,datetime_sep : str = " "
                ,year : bool = True
                ,month : bool = True
                ,day : bool = True
                ,hour : bool = True
                ,minute : bool = True
                ,second : bool = True
                ,allow_monthfirst : bool = False
                ,allow_dayfirst : bool = True
                ,allow_yearfirst : bool = True
                ,verbose_config : bool = False
                ):
        """
        Parser class. This class will parse a column of strings into a datetime
        column. It will also allow you to specify the format of the datetime
        string that you expect to see, and make some sane guesses about how excel 
        has mangled it in order to get you back something useful.

        If you set 'verbose_config' to True, the parser will let you know of any
        assumptions it has made about the data it is parsing.

        """

        match mode:
            case "date":
                self.mode = "date"
                allow_times = False
            case "datetime":
                self.mode = "datetime"
                allow_times = True
            case _:
                raise ValueError(f"mode must be one of 'date', 'time', or 'datetime'. Got: {mode}")

        self.verbose_config = verbose_config

        self.mode = mode
        self.date_sep = date_sep
        self.time_sep = time_sep
        self.datetime_sep = datetime_sep

        self.year = year
        self.month = month
        self.day = day

        self.set_time_vars(allow_times,hour,minute,second,verbose_config)

        self.allow_monthfirst = allow_monthfirst
        self.allow_dayfirst = allow_dayfirst
        self.allow_yearfirst = allow_yearfirst

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

    def __call__(self
                ,df : pl.DataFrame | pd.DataFrame
                ,date_column : str
                ,check_sorted : bool = True
                ) -> pl.DataFrame:
        
        """
        Parse an excel date column. This will take a column of dates that have 
        been mangled by excel, and return a column of dates that are in a clean 
        format.

        Parameters:
        - df: The dataframe that contains the column you want to parse. Must be 
            either a polars dataframe or a pandas dataframe.
        - column_name: The name of the column that you want to parse
        - check_sorted: Whether to check if the column is sorted. If the column 
            is not sorted, then we will not be able to parse it - since we will 
            not be able to determine the order of the date, month, and year.

        Returns:
        - A new dataframe with the column parsed, with the datatype converted to 
            a datetime. You can then choose how to write this back out to a file
             - either as a datetime, or as a string, etc.
        """


        if isinstance(df, pd.DataFrame):
            df = pl.from_pandas(df)
        elif not isinstance(df, pl.DataFrame):
            raise TypeError("df must be either a polars or pandas dataframe")

        if date_column not in df.columns:
            raise ValueError(f"Column {date_column} not found in dataframe")

        if check_sorted:
            raise NotImplementedError(" *** UNDER CONSTRUCTION ***")

        # Get the column that we want to parse
        df = self._split_datetimes(df,datetime_col=date_column)
        df = self._convert_time(df)

        df = self._split_dates(df,datetime_col=date_column)

        cols_to_process = self._get_cols_to_process(df,date_column)
        max_chars_dict,max_val_dict = self._create_max_dicts(df,cols_to_process)

        mappings = self._assign_datetype(max_chars_dict
                                        ,max_val_dict
                                        ,cols_to_process)


        df = (df.rename(mappings)
                .with_columns(
                    pl.col("Day").cast(pl.Int32),
                    pl.col("Month").cast(pl.Int32),
            )
        )

        df = self._year_to_int(df)
        df = self._combine_date_cols(df)
        df = self._combine_datetime_cols(df)

        return df

    def set_time_vars(self
                     ,allow_times : bool
                     ,hour : bool
                     ,minute : bool
                     ,second : bool
                     ,verbose_config : bool
                     ) -> None:
        """
        If we have set the mode to "date", we should not allow the user to set
        the hour, minute, and second variables to True. This function will check
        if the mode is set to "date" and if so, it will set all those values to 
        False. If not, it just passes through the values that the user has set.
        """

        if allow_times: 
            self.hour = hour
            self.minute = minute
            self.second = second

        self.hour = False
        self.minute = False
        self.second = False

        if verbose_config:
            warnings.warn("Mode is set to 'date'"
                         ". Disabling hour, minute, and second options."
                         ,category=UserWarning,stacklevel=2)

    def set_date_fmt_american(self, allowed : bool) -> None:
        """
        If the date is intended to be in an American format, then we will *always* 
        expect the month to come before the day - whether its written as 
        MM/DD/YYYY or YYYY/MM/DD. 

        We also expect the separator to be a forward slash.

        Parameters:
        - allowed: Whether the date can be in an American format.
        """

        self.allow_monthfirst = allowed
        self.allow_dayfirst = not allowed
        self.date_sep = "/"

    # Internal functions - these are the functions that will be used to parse the 
    # datetime column. I'll stick these somewhere else in the future, but for now
    # lets just dump them here for simplicity.

    def _split_datetimes(self
                        ,df : pl.DataFrame 
                        ,datetime_col : str = "mangled_dates"
                        ) -> pl.DataFrame:
        """
        Type union between pl.Dataframe and pd.DataFrame should be removed.

        To be honest, I haven't got a particularly good idea as to how this works. I
        copied it from stackoverflow 
        (https://stackoverflow.com/questions/73699500/python-polars-split-string-column-into-many-columns-by-delimiter)
        and it seems to do what I wanted.

        """


        if not isinstance(df, pl.DataFrame):
            raise TypeError("df must be a pandas or polars DataFrame")

        return (
            df
            .with_columns(
                pl.col(datetime_col).str.split(self.datetime_sep)
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

    def _split_dates(self
                    ,df : pl.DataFrame
                    ,datetime_col : str = "mangled_dates"
                    ) -> pl.DataFrame:
        """
        Type union between pl.Dataframe and pd.DataFrame should be removed.

        To be honest, I haven't got a particularly good idea as to how this works. I
        copied it from stackoverflow 
        (https://stackoverflow.com/questions/73699500/python-polars-split-string-column-into-many-columns-by-delimiter)
        and it seems to do what I wanted.

        """

        return (
            df
            .with_columns(
                pl.col(datetime_col).str.split(self.date_sep)
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

    def _convert_time(self
                     ,df : pl.DataFrame
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
                .to_time(f"%H{self.time_sep}%M")
                .alias("Time")
            )
        )

    def _assign_datetype(self
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

                if not self.allow_monthfirst:
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

        # warnings.warn("Did not use the following arguments: {max_val_dict}, {cols_to_process}."
                    # " We probably need to make this function a bit smarter."
                    # ,stacklevel=2)

        return mappings
        
    def _year_to_int(self
                    ,df : pl.DataFrame
                    ,year_col : str = "Year"
                    ) -> pl.DataFrame:
        """
        This gets a bit stupid, because we need to generate a new column which 
        is a boolean: is the year column four characters. If so, we can cast it
        to an int.  If not, we want to check if the two characters we have are 
        less than or equal to the current year. If so, we prepend "20". If not, 
        we prepend "19".

        + This assumption will fail if you are doing strange things with the 
        date:
            - If you are trying to parse a date like "15/01/22" and you mean
        the 15th of January 1922, then this will fail.
            - Similarly, imagine the date is April 10th, 2024, and you provide a 
            date like "21/06/24", but you mean the 21st of June 1924. This will 
            also fail, making the vaguely reasonable assumption you are 
            interested in the current year.
        """

        CURRENT_YEAR = date.today().year

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

    def _combine_date_cols(self
                          ,df : pl.DataFrame
                          ) -> pl.DataFrame:
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

    def _combine_datetime_cols(self
                              ,df : pl.DataFrame
                              ) -> pl.DataFrame:
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

    def _get_cols_to_process(self
                            ,df : pl.DataFrame
                            ,colnames_init : list[str]) -> list[str]:
        """
        Filter out the columns we want to process for date information
        """
        return [col for col in df.select(cs.by_dtype(pl.Utf8)).columns if col not in colnames_init]

    def _create_max_dicts(self
                         ,df : pl.DataFrame
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