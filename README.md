# NewsChart AI

NewsChart AI turns a CSV dataset into an interactive chart, calculated
statistical facts, and an AI-generated report.

The application includes a React browser interface, a FastAPI backend,
and a command-line tool. Python computes the facts; Amazon Bedrock
generates text from those supplied facts.

## Features

- CSV upload and data preview.
- Time-column and metric-column selection.
- Custom metric names and units.
- Validation of numbers, missing values, and duplicate periods.
- Chronological sorting without modifying input files.
- Statistical facts with explicit calculation limitations.
- Interactive line and bar charts.
- Structured AI reports with format validation.
- Report retry that preserves calculated facts and chart data.
- JSON report downloads.
- Automated tests and repeatable accuracy evaluation.

## Requirements

- Python 3.10 or newer.
- Node.js compatible with the installed Vite version.
- npm.
- AWS CLI v2 supporting `aws login`.
- An AWS account with permission to invoke the configured Bedrock model.

The default model is `us.amazon.nova-lite-v1:0`, accessed through
`us-east-1`.

Model availability and permissions must be confirmed in your AWS account.
Generation can incur AWS charges.

## Project structure

```text
News_AI/
├── data/
│   ├── sales_clean.csv
│   ├── sales_missing.csv
│   ├── sales_invalid.csv
│   ├── sales_unsorted.csv
│   ├── sales_duplicate.csv
│   ├── sales_single.csv
│   ├── sales_dates.csv
│   ├── sales_increasing.csv
│   ├── sales_decreasing.csv
│   ├── sales_flat.csv
│   └── sales_fluctuating.csv
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── data_validator.py
│   ├── fact_engine.py
│   ├── chart_builder.py
│   ├── narrative_generator.py
│   ├── report_schema.py
│   ├── structured_report_generator.py
│   ├── analysis_pipeline.py
│   ├── analysis_store.py
│   └── upload_loader.py
│
├── frontend/
│   ├── public/
│   │   └── vite.svg
│   ├── src/
│   │   ├── assets/
│   │   │   └── react.svg
│   │   ├── components/
│   │   │   ├── AnalysisChart.jsx
│   │   │   └── FactsPanel.jsx
│   │   ├── api.js
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── .gitignore
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── eslint.config.js
│   └── vite.config.js
│
├── tests/
│   ├── test_data_validator.py
│   ├── test_fact_engine.py
│   ├── test_chart_builder.py
│   ├── test_narrative_generator.py
│   ├── test_structured_reports.py
│   ├── test_api.py
│   └── test_evaluation_cases.py
│
├── evaluation/
│   ├── __init__.py
│   ├── cases.py
│   ├── run_reports.py
│   ├── check_review.py
│   └── runs/
│       └── <run timestamp>/
│           ├── <case>_<repeat>.json
│           └── review.csv
│
├── api.py
├── main.py
├── bedrock_smoke_test.py
├── try_narrative.py
├── try_structured_report.py
├── requirements.txt
├── .gitignore
└── README.md
```

The SVG files are optional Vite starter assets and may be removed if
unused. Evaluation run folders exist after running the evaluation.

Local `.venv/`, `frontend/node_modules/`, and `frontend/dist/` directories
are generated and excluded from Git. Command-line exports can also
appear in the project root.

## Installation

Clone the repository and open a terminal in its root directory.
The examples below assume the checkout is at `C:\News_AI`.

### Backend

```powershell
cd C:\News_AI
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

If the virtual environment already exists, skip its creation.

Python dependencies:

```text
pandas
plotly
boto3>=1.41.0
botocore[crt]
fastapi
uvicorn
python-multipart
httpx
```

### Frontend

```powershell
cd C:\News_AI\frontend
npm ci
```

Frontend dependencies and their resolved versions are recorded in
`package.json` and `package-lock.json`.

## AWS configuration

Install AWS CLI v2 and create or use an AWS identity with permission
to invoke the configured Bedrock inference profile and its underlying
foundation models.

For browser-based local login, the identity needs the
`SignInLocalDevelopmentAccess` permission.

Configure and authenticate the profile:

```powershell
aws configure set region us-east-1 --profile newschart
aws configure set output json --profile newschart
aws login --profile newschart
aws sts get-caller-identity --profile newschart
```

Confirm that the returned identity is the intended project identity.

If authentication expires, run `aws login` again. Organizations using
IAM Identity Center should configure their assigned SSO profile instead.

Check AWS connectivity with one model request:

```powershell
cd C:\News_AI
.\.venv\Scripts\python.exe bedrock_smoke_test.py
```

This is a real, potentially billable request.

Credentials belong outside the repository. Never put AWS keys in
React source code or frontend environment variables.

The API's AWS profile, Region, and model defaults currently come from
`structured_report_generator.py`. The command-line tool also supports
explicit AWS configuration arguments.

## Start the application

### Backend terminal

```powershell
cd C:\News_AI
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000
```

For development, add `--reload` to restart the backend when source
files change. Restarting clears temporary retry results.

### Frontend terminal

```powershell
cd C:\News_AI\frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open:

- Application: http://127.0.0.1:5173
- API documentation: http://127.0.0.1:8000/docs
- API health: http://127.0.0.1:8000/health

Both servers must remain running. Press Ctrl+C in each terminal to stop.

Users interact through the browser once the servers are running.

## Browser workflow

1. Upload a CSV.
2. Inspect the preview and available columns.
3. Select different time and metric columns.
4. Enter a descriptive metric name and measurement unit.
5. Select years or dates and choose a line or bar chart.
6. Click Generate.
7. Inspect the chart and calculated facts.
8. Review the AI report against those facts.
9. Download the complete analysis as JSON.

Changing a file or setting clears earlier results. Inputs are disabled
during generation, and rapid duplicate submissions are blocked.

If report generation fails, calculated facts and chart data remain
available. Use Retry report when the response offers it.

## Supported CSV format

Files must:

- Use UTF-8 encoding, with or without a byte-order mark.
- Have a header row.
- Use comma-separated fields.
- Contain at least two usable observations.
- Stay within 2 MiB and 10,000 data rows for API uploads.

Example annual data:

```csv
year,sales
2021,120
2022,150
2023,175
2024,160
2025,210
```

Example date data:

```csv
date,sales
2025-01-01,120
2025-02-01,0
2025-03-01,175
2025-04-01,160
2025-05-01,-25
```

Selected columns must satisfy these rules:

- Both columns exist and are different.
- Neither contains missing, blank, or whitespace-only values.
- Metric values convert to finite numbers.
- Zero and negative measurements are accepted.
- Year values are whole numbers from 1 to 9999.
- Dates parse using the selected format and fit Pandas' supported range.
- Parsed time values are unique.

The default date format is `%Y-%m-%d`.
For dates such as `31/12/2025`, use `%d/%m/%Y`.

Additional CSV columns are allowed but do not enter the selected analysis.

Validation sorts a copy chronologically. It does not silently remove
rows, fill missing values, combine duplicates, or modify the source CSV.

## Architecture

```text
React browser interface
          |
          | CSV and multipart form settings
          v
FastAPI endpoints
          |
          v
Upload loader
  Checks file size, encoding, parsing, and row count
          |
          v
Data validator
  Checks selected columns, numbers, times, and duplicates
          |
          v
One validated, chronologically sorted dataset
          |
          +---------------------+
          |                     |
          v                     v
Statistical fact engine    Plotly chart builder
          |                     |
          v                     |
Verified fact dictionary        |
          |                     |
          v                     |
Bedrock structured-report generator
  JSON parsing, schema checks, length checks, one correction retry
          |                     |
          +---------------------+
          |
          v
API response
  Facts, chart, report, metadata, or report error
          |
          v
Browser display and JSON download
```

### Module responsibilities

| Module | Responsibility |
|---|---|
| data_loader.py | Local CSV loading and inspection |
| upload_loader.py | Bounded uploaded CSV loading |
| data_validator.py | Selected-column and observation validation |
| fact_engine.py | Statistical calculations |
| chart_builder.py | Line and bar figures |
| report_schema.py | Report parsing, field types, and length checks |
| narrative_generator.py | Free-form narrative generation |
| structured_report_generator.py | Structured generation and correction retry |
| analysis_pipeline.py | Coordinates analysis stages |
| analysis_store.py | Temporarily retains failed analyses for retry |
| api.py | HTTP endpoints |
| main.py | Command-line workflows |

## Statistical facts

The application calculates:

- Observation count and period covered.
- First and last values.
- Mean.
- Minimum and maximum, including all tied periods.
- Overall absolute change.
- Overall percentage change when the starting value is positive.
- Largest adjacent increases and decreases, including tied intervals.

Absolute change:

```text
last value - first value
```

Percentage change:

```text
((last value - first value) / first value) × 100
```

Percentage change is omitted when the starting value is zero or negative.

Adjacent changes are labeled year-over-year only when all observations
are consecutive annual values. Otherwise, they are adjacent-period changes.

An empty increase or decrease list means no such movement occurred.

## Sample result

For `sales_clean.csv`:

| Fact | Expected result |
|---|---|
| Observations | 5 |
| Period | 2021–2025 |
| First value | 120 |
| Last value | 210 |
| Mean | 163 |
| Minimum | 120 in 2021 |
| Maximum | 210 in 2025 |
| Absolute change | +90 |
| Percentage change | +75% |
| Largest adjacent increase | +50, 2024–2025 |
| Largest adjacent decrease | -15, 2023–2024 |

An acceptable report might state:

> Sales increased from 120 to 210 sales units between 2021 and 2025,
> an overall increase of 90 units, or 75%.

Exact generated wording varies. The report must not claim that sales
increased every year, because the supplied series includes a decline.

## Structured reports

Required fields:

| Field | Type | Length limit |
|---|---|---|
| headline | Nonempty string | 15 words |
| summary | Nonempty string | 60 words |
| key_findings | List of 1–3 nonempty strings | 35 words each |
| report | Nonempty string | 180 words |

Word counts use whitespace-separated words.

The configured Nova Lite workflow requests JSON and validates it locally.

One complete outer Markdown code fence is accepted. Surrounding
commentary, invalid JSON, duplicate keys, unexpected fields, incorrect
types, empty text, and excessive lengths are rejected.

Malformed or truncated output receives one correction retry.
A second malformed response produces a clear failure.

Authentication, service, timeout, and blocked-response failures do not
trigger the formatting retry.

Each structured generation can make up to two billable model requests.

Correct structure does not guarantee correct content. Review numbers,
units, periods, direction of change, and unsupported explanations.

## API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Process health and configured limits |
| POST | /preview | Columns, inspection, and five preview rows |
| POST | /analyze | Facts, chart data, and structured report |
| POST | /analysis/{analysis_id}/report/retry | Retry from retained facts |

### Analysis form fields

| Field | Required | Default |
|---|---|---|
| file | Yes | — |
| time_column | Yes | — |
| metric_column | Yes | — |
| metric_name | Yes | — |
| unit | Yes | — |
| chart_type | No | line |
| time_kind | No | year |
| date_format | No | %Y-%m-%d |

The API returns Plotly chart data and layout, not an HTML chart file.

### Response behavior

- `complete`: facts, chart, and report are available.
- `report_failed`: facts and chart remain available; report_error explains
  the generation failure.
- `content_review_required`: indicates generated claims need review.

Failed analyses receive an analysis ID and retry URL when temporary
storage is available. Successful initial analyses do not receive an ID.

| HTTP status | Meaning |
|---|---|
| 200 | Successful request, including partial analysis after report failure |
| 400 | Unsuitable CSV upload |
| 413 | File-size or row limit exceeded |
| 422 | Invalid data, settings, or missing request fields |
| 404 | Retry result unavailable or expired |
| 409 | Retry already running or report already completed |

### Retry storage

Failed analyses are kept in process memory:

- Maximum 50 stored results.
- Expiration after 30 minutes.
- Older inactive results may be evicted.
- One retry at a time per analysis.

Restarting the backend clears the store.
Use one backend worker for this local version.

## Command-line usage

Run commands from the project root.

### Inspect

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --metric sales
```

### Validate

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales
```

### Export facts and a chart

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales --unit "sales units" --facts --output sample_facts.json --chart line --chart-output sample_chart.html
```

Chart HTML embeds Plotly for offline viewing.

### Generate a structured report

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales --unit "sales units" --structured-report --report-output sample_report.json
```

### Generate a free-form narrative

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales --unit "sales units" --narrative summary
```

Other narrative styles are `news` and `business`.
--narrative and --structured-report are mutually exclusive.

Optional AWS arguments:

```text
--aws-profile
--aws-region
--model-id
```

Changing models may require different permissions and supported parameters.

Output folders must exist. Existing output files are never overwritten.

## Sample datasets

| File | Purpose |
|---|---|
| sales_clean.csv | Valid annual data |
| sales_missing.csv | Missing metric value |
| sales_invalid.csv | Invalid numeric entry |
| sales_unsorted.csv | Chronological sorting |
| sales_duplicate.csv | Duplicate-time rejection |
| sales_single.csv | Minimum observation count |
| sales_dates.csv | Dates, zero, and negative values |
| sales_increasing.csv | Increasing series |
| sales_decreasing.csv | Decreasing series |
| sales_flat.csv | Constant series |
| sales_fluctuating.csv | Mixed increases and decreases |

## Tests and evaluation

### Backend tests

```powershell
cd C:\News_AI
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Model integration tests mock AWS and make no paid requests.

### Frontend checks

```powershell
cd C:\News_AI\frontend
npm run lint
npm run build
```

These checks do not replace browser workflow testing.

### Accuracy evaluation

Fixed inputs and expected answers are in `evaluation/cases.py`.

```powershell
cd C:\News_AI
.\.venv\Scripts\python.exe -m evaluation.run_reports
```

The default plan records 16 generations, potentially up to 32 requests
including formatting retries.

Review generated claims and complete the run's review.csv:

```powershell
.\.venv\Scripts\python.exe -m evaluation.check_review evaluation/runs/YOUR_RUN_FOLDER/review.csv
```

Rerun selected cases after fixes:

```powershell
.\.venv\Scripts\python.exe -m evaluation.run_reports --only fluctuating instruction_label
```

Document reviewed results and failures in `evaluation/RESULTS.md`.
Passing evaluation applies to the recorded cases and responses, not
every future output.

## Troubleshooting

| Problem | Action |
|---|---|
| Browser cannot connect to API | Start the backend and verify port 8000 |
| Frontend port is occupied | Stop the conflicting process or update frontend URL and CORS together |
| AWS profile missing or expired | Configure the profile and run aws login |
| Bedrock access denied | Check model availability and invocation permissions |
| Report generation fails | Inspect report_error; retry when available |
| Retry ID not found | Result expired, was evicted, or backend restarted; upload again |
| Output file exists | Choose a new export filename |
| Virtual environment cannot start | Recreate it with an installed supported Python and reinstall requirements |
| Plotly missing | Install Python requirements or frontend dependencies in the relevant environment |

## Known limitations

- Local development application; no external deployment is included.
- No authentication or per-user access control.
- Retry storage is temporary and does not support multiple workers.
- Upload checks occur after multipart parsing; request-level limits
  require additional configuration.
- No automatic handling of missing values or duplicate periods.
- Statistics use floating-point arithmetic.
- The mean weights observations equally.
- Adjacent differences are not rates per elapsed time.
- Units are supplied by the user and are not inferred.
- Percentage growth is omitted for nonpositive starting values.
- AI instructions reduce errors but cannot guarantee factual accuracy.
- Instruction-like labels require continued robustness evaluation.
- Charts connect adjacent observations without filling missing periods.
- Browser cancellation does not guarantee a running model call stops.
- Multiple exports are not transactional; a write failure can leave
  some outputs saved.
- API URL, CORS origins, and model settings require configuration
  changes for other environments.

## Credential handling

Keep AWS credentials outside the repository.
