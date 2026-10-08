import json

from src.chart_builder import build_chart
from src.data_validator import validate_data
from src.fact_engine import calculate_facts
from src.structured_report_generator import generate_structured_report


MAX_ROWS = 10_000


class PipelineValidationError(ValueError):
    """Input data or settings are unsuitable for analysis."""

    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(errors))


def run_analysis(
    df,
    time_column,
    metric_column,
    metric_name,
    unit,
    chart_type="line",
    time_kind="year",
    date_format="%Y-%m-%d",
    report_generator=None,
):
    """Analyze a loaded dataset and retain results if generation fails."""
    errors = []

    if len(df) > MAX_ROWS:
        errors.append(
            f"The dataset exceeds {MAX_ROWS:,} rows. "
            "Upload a smaller dataset."
        )

    if chart_type not in ("line", "bar"):
        errors.append("Choose 'line' or 'bar'.")

    if time_kind not in ("year", "date"):
        errors.append("Choose 'year' or 'date'.")

    if not isinstance(metric_name, str) or not metric_name.strip():
        errors.append("Provide a nonempty metric name.")

    if not isinstance(unit, str) or not unit.strip():
        errors.append("Provide a nonempty unit.")

    if errors:
        raise PipelineValidationError(errors)

    validation = validate_data(
        df,
        time_column=time_column,
        metric_column=metric_column,
        time_kind=time_kind,
        date_format=date_format,
    )

    if not validation.is_valid:
        raise PipelineValidationError(validation.errors)

    data = validation.data
    metric_name = metric_name.strip()
    unit = unit.strip()

    facts = calculate_facts(
        data,
        time_column=time_column,
        metric_column=metric_column,
        time_kind=time_kind,
        unit=unit,
    )

    # The CSV column name and human-readable metric name can differ.
    facts["metric_name"] = metric_name
    facts["metric_column"] = metric_column

    figure = build_chart(
        data,
        time_column=time_column,
        metric_column=metric_column,
        time_kind=time_kind,
        unit=unit,
        chart_type=chart_type,
    )

    metric_label = f"{metric_name} ({unit})"

    figure.update_layout(
        title=f"{metric_label} over time",
        yaxis_title=metric_label,
    )
    figure.update_traces(name=metric_name)

    # Convert Plotly-specific values into ordinary JSON-compatible data.
    chart = json.loads(figure.to_json())

    result = {
        "status": "complete",
        "facts": facts,
        "chart": chart,
        "report": None,
        "report_metadata": None,
        "report_error": None,
        "report_retry_available": False,
        "content_review_required": True,
    }

    if report_generator is None:
        report_generator = generate_structured_report

    try:
        generated = report_generator(facts)
    except RuntimeError as exc:
        result["status"] = "report_failed"
        result["report_error"] = str(exc)
        result["report_retry_available"] = True
    else:
        result["report"] = generated["report"]
        result["report_metadata"] = generated["metadata"]

    return result