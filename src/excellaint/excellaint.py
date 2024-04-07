import datetime
from pprint import pformat

import inquirer as inq
import polars as pl

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

def parse_datetime_column(df: pl.DataFrame
                         ,column_name: str
                         ,check_sorted: bool = False
                         ) -> pl.DataFrame: 
    """
    Parse an excel date column. This will take a column of dates that have been
    mangled by excel, and return a column of dates that are in a clean format.

    This function will read from the configuration to determine how to parse the
    dates. 

    Parameters:
    - df: The dataframe that contains the column you want to parse
    - column_name: The name of the column that you want to parse
    - check_sorted: Whether to check if the column is sorted. If the column is
        not sorted, then we will not be able to parse it - since we will not be
        able to determine the order of the date, month, and year.

    Returns:
    - A new dataframe with the column parsed, with the datatype converted to a 
        datetime. You can then choose how to write this back out to a file -
        either as a datetime, or as a string, etc.
    """
    
    config = ExcellAintConfig.__instance__

    print(config)
    # Get the column that we want to parse







class ExcellAintConfig():
    __instance__ = None


    mode = "date"
    intended_fmt = "%Y-%m-%d %H:%M:%S"

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
            "target_fmt": self.target_fmt,
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "hour": self.hour,
            "minute": self.minute,
            "second": self.second,
            "date_sep": self.date_sep,
            "time_sep": self.time_sep,
            "allow_monthfirst": self.allow_monthfirst,
            "allow_dayfirst": self.allow_dayfirst,
            "allow_yearfirst": self.allow_yearfirst
        }
        print(f"ExcellAint Configuration:\n\t{pformat(cfg_dict,indent=4)}")

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
        
    def set_intended_format(self
                           ,fmt: str
                           ,interactive : bool = False
                           ) -> None:
        """
        Set the target format for the datetime column. This will determine how
        the datetime column is written out. 

        Parameters:
        - fmt: The format string to use. This should be a valid format string
        for the `strftime` function in Python. 
        """

        # Check that the format string is valid
        try:
            datetime.datetime(2010,10,20,13,30,45).strftime(fmt)
        except ValueError:
            raise ValueError("Invalid format string")

        self.target_fmt = fmt

    def _set_intended_format_interactive(self):
        """
        Use inquirer to set the target format for the datetime column. 
        This will first prompt the user to select date or datetime, and then
        prompt the user to select the format string based on . 
        """

        # First, ask the user to select the mode
        mode_prompt = inq.List("mode"
                              ,message="Select mode:"
                              ,choices=["date","datetime"]
                              )
        mode = inq.prompt(mode_prompt)["mode"]
        self.set_mode(mode)

        # Next, ask the user to select the intended separator - this will be for

        fmt_prompt = inq.Text("fmt"
                             ,message="Enter the format string for the datetime column"
                             )
        fmt = inq.prompt(fmt_prompt)["fmt"]
        self.set_intended_format(fmt)

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