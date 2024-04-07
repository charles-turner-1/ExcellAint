# ExcellAint
## A Python toolbox for dealing with some of the oddities that Excel can introduce into your dates.

## ** Under Construction : Library may not work as described **
___

One of the major issues with trying to import data from Excel into Python is that Excel routinely fucks dates, due to its decision to store dates as floats
and then present them in whichever format it is set to. This can lead to all sorts of downstream issues, most commonly (in my experience) the switching of 
month and day. For example, you might wind up with something like the following:

| Date | Very Important Data|
|------|--------------------|
| ...  | ...   |
| 01/11/2020 | abc |
| 01/12/2020 | ijk |
| 13/01/2020 | pqrs |
| 14/01/2020 | xyz |
| ...  | ...   |

The goal of excellaint is to provide some tools which aim to fix these issues.


## Installation
``` pip install excellaint ```

## Usage

Currently, excellaint exposes a configuration class, accessible through 
`excellaint.config`, and a single function: `excellaint.parse_datetime_column`

Configuration is global and aims to take as much of the hassle of setting up how
data ought to be treated out of the function call. It is assumed that generally, the datetime issues excellaint addresses will be common to all excel spreadsheets in a dataset, as they are generally a function of locale.

As such, it is recommended to set up the configuration at the start of your script, like so:

```python
import excellaint as ea
import pandas as pd

ea.config.set_date_format('dd/mm/yyyy')


df = pd.read_excel('path/to/excel.xlsx')

df_dates_fixed = ea.parse_datetime_column(df, 'Date')
```

In the future, options to use per-call configuration will be added - for now if it needs to change multiple times in a script you will need to set it each time.


