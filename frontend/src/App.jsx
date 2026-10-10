import { useEffect, useRef, useState } from "react";
import { analyzeCSV, previewCSV, retryReport } from "./api";

import AnalysisChart from "../components/AnalysisChart";
import FactsPanel from "../components/FactsPanel";

import "./App.css";

const INITIAL_SETTINGS = {
  time_column: "",
  metric_column: "",
  metric_name: "",
  unit: "",
  chart_type: "line",
  time_kind: "year",
  date_format: "%Y-%m-%d",
};

export default function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [settings, setSettings] = useState(INITIAL_SETTINGS);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [phase, setPhase] = useState("idle");

  const controller = useRef(null);
  const requestVersion = useRef(0);
  const submissionLocked = useRef(false);

  useEffect(() => {
    return () => {
      requestVersion.current += 1;
      controller.current?.abort();
    };
  }, []);

  const generating = phase === "analyzing" || phase === "retrying";
  const columns = preview?.columns ?? [];

  function invalidateResults() {
    requestVersion.current += 1;
    controller.current?.abort();
    controller.current = null;
    setResult(null);
    setError("");
  }

  async function handleFileChange(event) {
    const selected = event.target.files?.[0] ?? null;

    invalidateResults();
    setFile(selected);
    setPreview(null);
    setSettings({ ...INITIAL_SETTINGS });
    setPhase("idle");

    if (!selected) return;

    if (!selected.name.toLowerCase().endsWith(".csv")) {
      setError("Choose a CSV file.");
      return;
    }

    if (selected.size > 2 * 1024 * 1024) {
      setError("The CSV exceeds the 2 MiB upload limit.");
      return;
    }

    const version = requestVersion.current;
    const abortController = new AbortController();
    controller.current = abortController;
    setPhase("previewing");

    try {
      const response = await previewCSV(
        selected,
        abortController.signal
      );

      if (version !== requestVersion.current) return;

      setPreview(response);
    } catch (err) {
      if (
        version === requestVersion.current &&
        err.name !== "AbortError"
      ) {
        setError(err.message);
      }
    } finally {
      if (version === requestVersion.current) {
        controller.current = null;
        setPhase("idle");
      }
    }
  }

  function handleSettingChange(event) {
    const { name, value } = event.target;

    invalidateResults();
    setSettings((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function handleGenerate(event) {
    event.preventDefault();

    // Ref blocks a second click before React updates the button.
    if (submissionLocked.current) return;

    if (!file || !preview) {
      setError("Upload a valid CSV first.");
      return;
    }

    if (settings.time_column === settings.metric_column) {
      setError("Choose different time and metric columns.");
      return;
    }

    if (!settings.metric_name.trim() || !settings.unit.trim()) {
      setError("Enter a metric name and unit.");
      return;
    }

    submissionLocked.current = true;
    invalidateResults();

    const version = requestVersion.current;
    const abortController = new AbortController();
    controller.current = abortController;
    setPhase("analyzing");

    try {
      const response = await analyzeCSV(
        file,
        settings,
        abortController.signal
      );

      if (version !== requestVersion.current) return;

      setResult(response);
    } catch (err) {
      if (
        version === requestVersion.current &&
        err.name !== "AbortError"
      ) {
        setError(err.message);
      }
    } finally {
      submissionLocked.current = false;

      if (version === requestVersion.current) {
        controller.current = null;
        setPhase("idle");
      }
    }
  }

  async function handleRetry() {
    if (submissionLocked.current || !result?.analysis_id) return;

    submissionLocked.current = true;
    setError("");

    const version = requestVersion.current;
    const abortController = new AbortController();
    controller.current = abortController;
    setPhase("retrying");

    try {
      const response = await retryReport(
        result.analysis_id,
        abortController.signal
      );

      if (version !== requestVersion.current) return;

      setResult(response);
    } catch (err) {
      if (
        version === requestVersion.current &&
        err.name !== "AbortError"
      ) {
        setError(err.message);
      }
    } finally {
      submissionLocked.current = false;

      if (version === requestVersion.current) {
        controller.current = null;
        setPhase("idle");
      }
    }
  }

  function downloadReport() {
    if (!result?.report) return;

    const blob = new Blob(
      [JSON.stringify(result, null, 2)],
      { type: "application/json" }
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "newschart-report.json";
    document.body.appendChild(link);
    link.click();
    link.remove();

    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <main className="app">
      <header>
        <h1>NewsChart AI</h1>
        <p>Turn a CSV into a chart, calculated facts, and a report.</p>
      </header>

      <form onSubmit={handleGenerate}>
        <fieldset disabled={generating}>
          <legend>Dataset and analysis settings</legend>

          <label>
            CSV file
            <input
              type="file"
              accept=".csv"
              onChange={handleFileChange}
            />
          </label>
          <small>UTF-8 CSV · Maximum 2 MiB and 10,000 rows</small>

          {phase === "previewing" && (
            <p role="status">Loading data preview…</p>
          )}

          {preview && (
            <section>
              <h2>Data preview</h2>
              <p>
                {preview.inspection.row_count} rows ·{" "}
                {preview.inspection.column_count} columns
              </p>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      {columns.map((column) => (
                        <th key={column} scope="col">{column}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.preview.map((row, index) => (
                      <tr key={index}>
                        {columns.map((column) => (
                          <td key={column}>
                            {row[column] == null
                              ? "Missing"
                              : String(row[column])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <div className="form-grid">
            {[
              ["time_column", "Time column"],
              ["metric_column", "Metric column"],
            ].map(([name, label]) => (
              <label key={name}>
                {label}
                <select
                  name={name}
                  value={settings[name]}
                  onChange={handleSettingChange}
                  disabled={!preview}
                  required
                >
                  <option value="">Select a column</option>
                  {columns.map((column) => (
                    <option key={column} value={column}>
                      {column}
                    </option>
                  ))}
                </select>
              </label>
            ))}

            <label>
              Metric name
              <input
                name="metric_name"
                value={settings.metric_name}
                onChange={handleSettingChange}
                placeholder="Annual sales"
                maxLength={100}
                required
              />
            </label>

            <label>
              Unit
              <input
                name="unit"
                value={settings.unit}
                onChange={handleSettingChange}
                placeholder="sales units"
                maxLength={100}
                required
              />
            </label>

            <label>
              Chart type
              <select
                name="chart_type"
                value={settings.chart_type}
                onChange={handleSettingChange}
              >
                <option value="line">Line chart</option>
                <option value="bar">Bar chart</option>
              </select>
            </label>

            <label>
              Time type
              <select
                name="time_kind"
                value={settings.time_kind}
                onChange={handleSettingChange}
              >
                <option value="year">Years</option>
                <option value="date">Dates</option>
              </select>
            </label>

            {settings.time_kind === "date" && (
              <label>
                Date format
                <input
                  name="date_format"
                  value={settings.date_format}
                  onChange={handleSettingChange}
                  maxLength={100}
                  required
                />
                <small>Use %Y-%m-%d for dates like 2025-03-01.</small>
              </label>
            )}
          </div>

          <button type="submit" disabled={!preview || generating}>
            {phase === "analyzing" ? "Generating…" : "Generate"}
          </button>
          <p className="hint">
            Generation sends calculated facts to the AI service.
          </p>
        </fieldset>
      </form>

      {error && <p className="error" role="alert">{error}</p>}

      {generating && (
        <p role="status">
          {phase === "retrying"
            ? "Retrying the report…"
            : "Calculating facts, creating a chart, and writing the report…"}
        </p>
      )}

      {result && (
        <section className="results" aria-label="Analysis results">
          <AnalysisChart chart={result.chart} />
          <FactsPanel facts={result.facts} />

          {result.status === "report_failed" && (
            <div className="error" role="alert">
              <p>
                Your facts and chart are available, but the report
                could not be generated.
              </p>
              <p>{result.report_error}</p>
              {result.report_retry_available && result.analysis_id ? (
                <button
                  type="button"
                  onClick={handleRetry}
                  disabled={generating}
                >
                  {phase === "retrying" ? "Retrying…" : "Retry report"}
                </button>
              ) : (
                <p>
                  {result.retry_unavailable_reason ||
                    "Generate again to request a new report."}
                </p>
              )}
            </div>
          )}

          {result.report && (
            <article>
              <h2>{result.report.headline}</h2>
              <p>{result.report.summary}</p>

              <h3>Key findings</h3>
              <ul>
                {result.report.key_findings.map((finding, index) => (
                  <li key={index}>{finding}</li>
                ))}
              </ul>

              <h3>Report</h3>
              <p className="report-text">{result.report.report}</p>

              <p className="hint">
                Review generated claims against the calculated facts.
              </p>
              <button type="button" onClick={downloadReport}>
                Download report JSON
              </button>
            </article>
          )}
        </section>
      )}
    </main>
  );
}