# NewsChart AI

NewsChart AI is a project for inspecting datasets before analysis
and chart creation.

## Current functionality

The Day 1 terminal tool can:

- Load a CSV file.
- Preview its first five rows.
- Report row counts, column names, and data types.
- Count missing values.
- Find invalid values in a column expected to contain numbers.

## Setup

Open PowerShell in the project folder:

```powershell
cd C:\News_AI
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Usage

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --metric sales
```

The file path is required. The `--metric` argument is optional.

## Sample datasets

| File | Expected result |
|---|---|
| sales_clean.csv | Five rows; no missing or invalid sales values |
| sales_missing.csv | One missing sales value; no invalid numeric values |
| sales_invalid.csv | No missing sales values; abc is invalid for numeric conversion |

## Project structure

- data/: sample CSV datasets.
- src/data_loader.py: reusable loading and inspection functions.
- main.py: terminal arguments and output.
- tests/: reserved for future automated tests.
- requirements.txt: required Python packages.

The tool reads input files without modifying them.