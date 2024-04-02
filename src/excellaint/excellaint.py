import inquirer as inq
import polars as pl

"""
Excellaint - A Python toolbox for dealing with some of the oddities that Excel 
can introduce introduce

This module will give you a couple of functions that help you parse, clean, and
then write date columns that excel has helpfully mangled for you back to a clean
dataframe. 

Right now, it is going to expose a single function that will parse a date column
and return a new dataframe with the dates cleaned up, which will have two columns:
- Input Column: The original column that was passed in
- Parsed Column: The column that has been cleaned up

Configuration can be set through a singleton config class, which will contain all
of the options you might want to set. `excellaint` then reads from this 
configuration to determine how to parse and write dates.

"""

def parse_date_column(df: pl.DataFrame
                     ,column_name: str
                     ) -> pl.DataFrame:
    """
    Parse an excel date column. This will take a column of dates that have been
    mangled by excel, and return a column of dates that are in a clean format.

    This function will read from the configuration to determine how to parse the
    dates. 

    Parameters:
    - df: The dataframe that contains the column you want to parse
    - column_name: The name of the column that you want to parse

    Returns:
    - A new dataframe with the column parsed
    """
    pass



class ExcellAintConfig():
    __instance__ = None
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
