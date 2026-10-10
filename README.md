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
C:\News_AI\
├── data\
│   ├── sales_clean.csv
│   ├── sales_missing.csv
│   ├── sales_invalid.csv
│   ├── sales_unsorted.csv
│   ├── sales_duplicate.csv
│   ├── sales_single.csv
│   └── sales_dates.csv
│
├── src\
│   ├── __init__.py
│   ├── data_loader.py
│   ├── data_validator.py
│   ├── fact_engine.py
│   ├── chart_builder.py
│   └── narrative_generator.py
│
├── tests\
│   ├── test_data_validator.py
│   ├── test_fact_engine.py
│   ├── test_chart_builder.py
│   └── test_narrative_generator.py
│
├── main.py
├── bedrock_smoke_test.py
├── try_narrative.py
├── requirements.txt
├── .gitignore
├── README.md
│
└── .venv\     
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── AnalysisChart.jsx
│   │   └── FactsPanel.jsx
│   ├── api.js
│   ├── App.jsx
│   ├── App.css
│   ├── index.css
│   └── main.jsx
├── index.html
├── package.json
├── package-lock.json
├── eslint.config.js
└── vite.config.js

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

## Day 5: AI-generated narratives

The application sends computed statistical facts to Amazon Bedrock
and generates a short, neutral report.

Available styles:

- summary: one short paragraph.
- news: a factual headline and paragraph.
- business: three factual briefing bullets.

### AWS authentication

Configure the newschart profile using AWS CLI v2:

```powershell
aws configure set region us-east-1 --profile newschart
aws login --profile newschart
aws sts get-caller-identity --profile newschart
```

The selected identity must have permission to invoke the model.
If the login expires, run aws login again.

Python dependencies include boto3>=1.41.0 and botocore[crt]
for browser-login credential support.

### Generate a narrative

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales --unit "sales units" --narrative summary
```

### Export a report and its evidence

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales --unit "sales units" --narrative news --report-output sales_news_report.json
```

The report JSON contains:

- The fact dictionary supplied to the model.
- Generated text.
- Requested model identifier and AWS Region.
- Prompt version and selected style.
- Request duration.
- Token usage when available.
- Completion reason and request ID.
- Warnings, including possible output truncation.

Existing output files are never overwritten.

### Generate facts, a chart, and a report together

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales --unit "sales units" --facts --output day5_facts.json --chart line --chart-output day5_chart.html --narrative business --report-output day5_report.json
```

Validation runs once. Charts and statistics use the same sorted data,
and the narrative receives the computed facts.

### Model configuration

Defaults:

- AWS profile: newschart
- AWS Region: us-east-1
- Model: us.amazon.nova-lite-v1:0
- Maximum output tokens: 500
- Temperature: 0.1

Profile, Region, and model can be selected using --aws-profile,
--aws-region, and --model-id.

Changing models may require different permissions, availability,
or inference parameters. The defaults were chosen for Nova Lite.

### Timeouts and errors

The client uses a 10-second connection timeout and a 60-second read
timeout. These are network-operation timeouts, not an exact overall
execution deadline.

Automatic invocation retries are disabled. Authentication failures,
service errors, and timeouts produce readable messages.

### Cost and factual limitations

Each command containing --narrative makes one real model request
and may incur charges. Other workflows do not invoke Bedrock.

Instructions ask the model to preserve supplied facts and avoid
invented causes, quotes, recommendations, or forecasts.

Generated text still requires review. Low temperature does not
guarantee factual accuracy or identical repeated responses.

For each factual claim, check:

- Does its number match the fact dictionary?
- Does its period match?
- Is the unit correct?
- Is the direction of change correct?
- Does it introduce an unsupported explanation?
- Does it mention percentage change when that fact was omitted?

### Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_narrative_generator.py" -v
```

These tests mock AWS and do not make paid requests. They verify
prompt construction, request configuration, response handling,
metadata, and readable errors.

Real narrative accuracy is checked separately against computed facts.

## Day 6: Structured reports

Generate a report with four required fields:

- headline: nonempty string, maximum 15 words.
- summary: nonempty string, maximum 60 words.
- key_findings: 1–3 nonempty strings, maximum 35 words each.
- report: nonempty string, maximum 180 words.

Word counts use whitespace-separated words.

### Generate and export

```powershell
.\.venv\Scripts\python.exe main.py data/sales_clean.csv --time year --metric sales --unit "sales units" --structured-report --report-output day6_clean_report.json
```

The exported JSON contains the supplied facts, structured report,
request metadata, and a content_review_required flag.

--structured-report and --narrative cannot be used together.

### Formatting validation and retry

For the configured Nova Lite model, the application requests JSON
and validates it locally.

Validation rejects:

- Invalid JSON or surrounding Markdown.
- Missing or unexpected fields.
- Duplicate JSON keys.
- Incorrect field types or empty text.
- Excessive word counts.
- Nonstandard JSON constants such as NaN and Infinity.
- Responses truncated by the output token limit.

One correction retry is allowed for malformed output. If both
attempts fail, the application reports a clear failure.

Authentication, timeout, service, and blocked-response failures
do not trigger the formatting retry.

Each structured-report command can make up to two billable requests.
Metadata records each completed attempt's duration, token usage
when available, completion reason, and request ID.

### Content review

Correct JSON does not guarantee correct claims.

Compare every claim against the supplied facts, including:

- Numbers, periods, units, and change directions.
- Overall change versus changes in individual periods.
- Tied extrema and adjacent changes.
- Unsupported causes, recommendations, or forecasts.

Formatting retries do not automatically correct factual errors.

### Reference datasets

| File | Expected overall change |
|---|---|
| sales_increasing.csv | +80 sales units; +80% |
| sales_decreasing.csv | -80 sales units; -40% |
| sales_flat.csv | 0 sales units; 0% |
| sales_fluctuating.csv | +20 sales units; +20% |

All four contain five observations covering 2021–2025.

### Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_structured_reports.py" -v
```

Tests mock AWS and verify schema validation, length limits, correction
retries, the two-attempt limit, and failure handling without paid calls.

Real report content must be reviewed separately.

## Day 7: Analysis API

FastAPI connects CSV loading, validation, statistics, chart creation,
and structured report generation.

### Start the local server

```powershell
cd C:\News_AI
.\.venv\Scripts\python.exe -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs for interactive API documentation.

Press Ctrl+C in the terminal to stop the server.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | /health | Check the API process and configured limits |
| POST | /preview | Return CSV columns, inspection details, and five rows |
| POST | /analyze | Return facts, Plotly chart data, and a structured report |
| POST | /analysis/{analysis_id}/report/retry | Retry a failed report using retained facts |

Health and preview do not invoke Bedrock.

### Analysis inputs

Upload a CSV and supply these multipart form fields:

- time_column: CSV time column.
- metric_column: CSV measurement column.
- metric_name: human-readable display name.
- unit: measurement unit.
- chart_type: line or bar.
- time_kind: year or date.
- date_format: defaults to %Y-%m-%d.

Example: year, sales, Annual sales, sales units, line, year.

### Limits

- Maximum CSV file size: 2 MiB (2,097,152 bytes).
- Maximum dataset size: 10,000 rows.

These are application-level checks. The multipart upload is received
before the file-size check; incoming HTTP-body limits require
additional configuration before external deployment.

### Responses

Successful analysis returns:

- status: complete.
- facts: computed statistical facts.
- chart: Plotly data and layout.
- report: headline, summary, key_findings, and report.
- report_metadata: model request details.
- content_review_required: true.

Invalid uploads or analysis settings are rejected before model invocation.

HTTP status codes:

- 200: preview, complete analysis, or analysis with a report failure.
- 400: unsuitable CSV upload.
- 413: file-size or row limit exceeded.
- 422: invalid settings, data, or missing request fields.
- 404: retry analysis ID unavailable or expired.
- 409: retry already running or report already generated.

### Report failure and retry

If generation fails, the response preserves facts and chart data
and returns status: report_failed.

When temporary storage is available, the response includes
analysis_id and report_retry_url. Successful initial analyses
do not receive an analysis ID.

The retry endpoint uses server-retained facts. It does not reload
the CSV, recalculate statistics, or rebuild the chart.

Each generation operation can make up to two billable model requests,
including one correction retry for malformed output.

### Temporary storage

Failed analyses are retained in process memory:

- Maximum 50 results.
- Results expire after 30 minutes.
- Older inactive entries may be evicted.
- Concurrent retries for the same analysis are rejected.

Restarting or reloading the server clears stored results.
Use one server worker for this local MVP. Persistent storage and
user access controls are needed before deployment.

### Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api.py" -v
```

API tests mock model generation and do not make paid requests.
They check uploads, validation, chart and fact responses, report
failures, and retries.

Generated report claims still require comparison with supplied facts.

## Day 8: React user interface

The browser interface supports:

- CSV upload and five-row preview.
- Time-column and metric-column selection.
- Metric name and unit inputs.
- Year or date interpretation.
- Manual line/bar chart selection.
- Interactive charts and calculated fact cards.
- Structured reports and JSON downloads.
- Clear errors and report retry when available.

Changing the file or analysis settings clears previous results.
Inputs and submission are disabled during generation.
Outdated preview responses are ignored.

AWS credentials and model calls remain in the backend.

### Frontend setup

Install a Node.js version compatible with the project's Vite version.

```powershell
cd C:\News_AI\frontend
npm ci
```

npm ci installs dependencies using the committed package-lock.json.

### Start the backend

In one terminal:

```powershell
cd C:\News_AI
.\.venv\Scripts\python.exe -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

If AWS authentication has expired:

```powershell
aws login --profile newschart
```

### Start the frontend

In another terminal:

```powershell
cd C:\News_AI\frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open http://127.0.0.1:5173.

The local application requires both servers to be running.

### Browser workflow

1. Upload a UTF-8 CSV.
2. Inspect its preview.
3. Select different time and metric columns.
4. Enter a metric name and unit.
5. Choose the time interpretation and chart type.
6. Click Generate.
7. Inspect the chart and facts.
8. Review every report claim against those facts.
9. Download the report JSON.

Downloads contain the complete analysis response, including facts,
chart data, report, and metadata.

Generation may incur Bedrock charges. Chart rendering and downloading
an existing result do not invoke the model.

### Validation

```powershell
cd C:\News_AI\frontend
npm run lint
npm run build
```

Backend tests:

```powershell
cd C:\News_AI
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Manually verify:

- Correct plotted values, units, and periods.
- Zero, negative, flat, and fluctuating measurements.
- Clearing results when files or settings change.
- Ignoring outdated preview responses.
- One analysis request after rapid double clicks.
- Readable validation and connection errors.
- Report downloads and responsive layout.

### Deployment status

This is a local development interface. The API URL and allowed
frontend origins are configured for local development.

External deployment, authentication, persistent retry storage,
and request-level upload limits require further work.