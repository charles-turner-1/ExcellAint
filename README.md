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

Currently, excellaint exposes a single callable parser class, accessible as
`excellaint.Parser`.

Defaults aim to be sane but depending on locale you will probably need to change 
them. 

Since this project is in its infancy, you are likely to run into errors. Please 
send the date columns in question to me if/when you run into errors to help 
improve this package.

The parser class **does not** save any dataframe info, and so you will need to 
assign the output of the `parse_datetime_column` method to a variable. This 
also means it is safe to reuse the parser object for multiple dataframes, 
provided their date columns are (meant to be) in the same format.


```python
import pandas as pd

test_file = "./test/test_data/2_digit_yr.xlsx"
test_df = pd.read_excel(test_file)

print(test_df)
```

```output
          mangled_dates  row_id
0        01/01/20 12:00       0
1        01/01/20 01:00       1
2        01/01/20 02:00       2
3        01/01/20 03:00       3
4        01/01/20 04:00       4
...                 ...     ...
17539  31/12/2021 19:00   17539
17540  31/12/2021 20:00   17540
17541  31/12/2021 21:00   17541
17542  31/12/2021 22:00   17542
17543  31/12/2021 23:00   17543

[17544 rows x 2 columns]
```
```python

import excellaint as ea 
ea_parser = ea.Parser()

%%timeit 
df = ea_parser(test_df,"mangled_dates")
print(df)
```

```output
shape: (17_544, 2)
┌────────┬─────────────────────┐
│ row_id ┆ Datetime            │
│ ---    ┆ ---                 │
│ i64    ┆ datetime[μs]        │
╞════════╪═════════════════════╡
│ 0      ┆ 2020-01-01 12:00:00 │
│ 1      ┆ 2020-01-01 01:00:00 │
│ 2      ┆ 2020-01-01 02:00:00 │
│ 3      ┆ 2020-01-01 03:00:00 │
│ 4      ┆ 2020-01-01 04:00:00 │
│ …      ┆ …                   │
│ 17539  ┆ 2021-12-31 19:00:00 │
│ 17540  ┆ 2021-12-31 20:00:00 │
│ 17541  ┆ 2021-12-31 21:00:00 │
│ 17542  ┆ 2021-12-31 22:00:00 │
│ 17543  ┆ 2021-12-31 23:00:00 │
└────────┴─────────────────────┘

63.7 ms ± 1.14 ms per loop (mean ± std. dev. of 7 runs, 10 loops each)
```

The package should be relatively performant - future versions will be quite significantly faster as the current approach is not very sophisticated.

## Future Work

- [ ] Add more date formats
- [ ] Add more tests
- [ ] Performace


