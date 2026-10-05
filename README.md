# NewsChart AI

NewsChart AI prepares CSV datasets for analysis and calculates
statistical facts that can support future charts and reporting.

The current application runs in the terminal and works independently
of AWS.

## Setup

Open PowerShell in the project folder:

```powershell
cd C:\News_AI
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If the virtual environment already exists, skip its creation.

## Day 1: CSV inspection

Preview data, report column types, count missing values, and identify
values that cannot be converted to numbers.

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --metric sales
```

Inspection describes the data; it does not require the dataset to
pass analysis validation.

## Day 2: Data validation

Select time and metric columns:

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales
```

Validation:

- Requires both columns to exist and be different.
- Rejects missing values, empty strings, and whitespace-only values.
- Converts metric values to finite numbers.
- Preserves zero and negative measurements.
- Supports whole years from 1 to 9999 or explicitly formatted dates.
- Rejects duplicate time values.
- Requires at least two observations.
- Returns normalized data sorted chronologically.

Rejected inputs return explicit errors and no usable data.
Rows are never silently dropped or filled.

For ISO dates:

```powershell
.\.venv\Scripts\python.exe main.py data/sales_dates.csv --time date --metric sales --time-kind date
```

For another date format:

```powershell
.\.venv\Scripts\python.exe main.py data/your_dates.csv --time date --metric sales --time-kind date --date-format "%d/%m/%Y"
```

Date values must fall within the installed Pandas version's supported
date range.

## Day 3: Statistical facts

Calculate facts from validated data:

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales --facts --unit "sales units"
```

The result includes:

- Metric name and user-supplied unit.
- Observation count and period covered.
- First and last values.
- Mean, minimum, and maximum.
- All periods sharing the minimum or maximum.
- Overall absolute change.
- Overall percentage change when the first value is positive.
- Largest adjacent increases and decreases, including tied periods.
- Calculation limitations.

Absolute change is the last value minus the first value.

Percentage change is absolute change divided by the first value,
multiplied by 100. It is omitted when the first value is zero or
negative; the absolute change remains available.

Adjacent changes are labeled "year-over-year" only when the time type
is year and every observation is one year after the previous one.
Otherwise, they are labeled "adjacent-period".

An empty increase or decrease list means no such movement occurred.

## JSON export

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales --facts --unit "sales units" --output sales_facts.json
```

The output must have a .json extension. Its parent folder must exist.
Existing output files are never overwritten; choose a new filename.

Dates are exported as ISO timestamp strings.

## Sample datasets

| File | Purpose |
|---|---|
| sales_clean.csv | Valid consecutive annual observations |
| sales_missing.csv | One missing sales value |
| sales_invalid.csv | An invalid numeric value: abc |
| sales_unsorted.csv | Checks chronological sorting |
| sales_duplicate.csv | Checks duplicate-time rejection |
| sales_single.csv | Checks minimum observation count |
| sales_dates.csv | Unsorted ISO dates, including zero and negative sales |

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover validation, statistical calculations, ties, nonpositive
starting values, time gaps, input preservation, and JSON serialization.

## Project structure

```text
News_AI/
├── data/
├── src/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── data_validator.py
│   └── fact_engine.py
|       chart_builder.py
├── tests/
│   ├── test_data_validator.py
│   └── test_fact_engine.py
|       test_chart_builder.py
├── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Calculation limitations

- Facts describe observations; they do not establish causes.
- The mean weights every observation equally.
- Adjacent changes are differences, not rates per elapsed time.
- Units are supplied by the user and are not inferred.
- Calculations use floating-point arithmetic.
- Non-finite calculation results are rejected.
- Input DataFrames and CSV files are not modified.

## Day 4: Interactive charts

The application supports manually selected line and bar charts.

Charts and statistical facts use the same validated, chronologically
sorted dataset. Chart creation does not aggregate, remove, or modify
observations.

### Line chart

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales --unit "sales units" --chart line --chart-output sales_line.html
```

### Bar chart with dates

```powershell
.\.venv\Scripts\python.exe main.py data/sales_dates.csv --time date --metric sales --time-kind date --unit "sales units" --chart bar --chart-output sales_dates_bar.html
```

### Export facts and a chart together

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales --unit "sales units" --facts --output sales_summary_facts.json --chart line --chart-output sales_summary_line.html
```

### Open a chart

```powershell
Start-Process .\sales_line.html
```

HTML exports embed Plotly and work without an internet connection.
Hover over points or bars to inspect their periods and values.

The title and vertical axis include the metric name and unit.
Zero and negative measurements are preserved.

### Export rules

- Select the chart manually with --chart line or --chart bar.
- Supply an HTML filename using --chart-output.
- The output folder must already exist.
- Existing files are never overwritten.
- When exporting facts and a chart together, both results are generated
  before writing. A file-system error during export may leave one file saved.

### Chart validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_chart_builder.py" -v
```

Chart tests cover plotted values, ordering, labels, negative values,
flat data, larger datasets, input preservation, and agreement with
statistical facts.

Also inspect exported HTML files manually to verify hover behavior,
readability, zooming, and offline operation.