import json
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile

from src.data_loader import inspect_data
from src.upload_loader import (
    MAX_UPLOAD_BYTES,
    UploadValidationError,
    load_uploaded_csv,
)

from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from src.analysis_pipeline import (
    MAX_ROWS,
    PipelineValidationError,
    run_analysis,
)

from src.analysis_store import (
    AnalysisStoreError,
    claim_report_retry,
    finish_report_retry,
    release_report_retry,
    store_failed_analysis,
)
from src.structured_report_generator import generate_structured_report

app = FastAPI(
    title="NewsChart AI",
    description="Preview CSV uploads and analyze time-series data.",
    version="0.7.0",
)


@app.get("/health")
def health():
    """Check that the API process is running."""
    return {
        "status": "ok",
        "limits": {
            "max_upload_bytes": MAX_UPLOAD_BYTES,
            "max_rows": MAX_ROWS,
        },
    }


@app.post("/preview")
def preview_csv(
    file: Annotated[
        UploadFile,
        File(description="UTF-8 CSV, up to 2 MiB and 10,000 rows"),
    ],
):
    """Return available columns, inspection details, and five rows."""
    try:
        df = load_uploaded_csv(file.file, file.filename)

        # Pandas converts missing preview values into JSON null.
        preview = json.loads(
            df.head(5).to_json(orient="records")
        )

        return {
            "filename": file.filename,
            "columns": df.columns.tolist(),
            "inspection": inspect_data(df),
            "preview": preview,
        }

    except UploadValidationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc

    finally:
        file.file.close()

@app.post("/analyze")
def analyze_csv(
    file: Annotated[
        UploadFile,
        File(description="UTF-8 CSV, up to 2 MiB and 10,000 rows"),
    ],
    time_column: Annotated[
        str,
        Form(min_length=1, description="Time column in the CSV"),
    ],
    metric_column: Annotated[
        str,
        Form(min_length=1, description="Measurement column in the CSV"),
    ],
    metric_name: Annotated[
        str,
        Form(
            min_length=1,
            max_length=100,
            description="Display name, such as Annual sales",
        ),
    ],
    unit: Annotated[
        str,
        Form(
            min_length=1,
            max_length=100,
            description="Measurement unit, such as sales units",
        ),
    ],
    chart_type: Annotated[
        Literal["line", "bar"],
        Form(),
    ] = "line",
    time_kind: Annotated[
        Literal["year", "date"],
        Form(),
    ] = "year",
    date_format: Annotated[
        str,
        Form(min_length=1, max_length=100),
    ] = "%Y-%m-%d",
):
    """Return facts, chart data, and a structured report."""
    try:
        df = load_uploaded_csv(file.file, file.filename)

        result = run_analysis(
            df,
            time_column=time_column,
            metric_column=metric_column,
            metric_name=metric_name,
            unit=unit,
            chart_type=chart_type,
            time_kind=time_kind,
            date_format=date_format,
        )

        if result["status"] == "report_failed":
            analysis_id = store_failed_analysis(result)

            if analysis_id is None:
                result["report_retry_available"] = False
                result["retry_unavailable_reason"] = (
                    "The temporary result store is full. "
                    "Upload the CSV again later."
                )
            else:
                result["analysis_id"] = analysis_id
                result["report_retry_url"] = (
                    f"/analysis/{analysis_id}/report/retry"
                )

        return result

        

    except UploadValidationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc

    except PipelineValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"errors": exc.errors},
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"errors": [str(exc)]},
        ) from exc

    finally:
        file.file.close()

@app.post("/analysis/{analysis_id}/report/retry")
def retry_report(analysis_id: str):
    """Generate a report from facts retained by the server."""
    try:
        result = claim_report_retry(analysis_id)
    except AnalysisStoreError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc

    try:
        try:
            generated = generate_structured_report(result["facts"])
        except RuntimeError as exc:
            result["status"] = "report_failed"
            result["report_error"] = str(exc)
            result["report_retry_available"] = True
        else:
            result["status"] = "complete"
            result["report"] = generated["report"]
            result["report_metadata"] = generated["metadata"]
            result["report_error"] = None
            result["report_retry_available"] = False

        finish_report_retry(analysis_id, result)

    finally:
        release_report_retry(analysis_id)

    result["analysis_id"] = analysis_id
    result["report_retry_url"] = (
        f"/analysis/{analysis_id}/report/retry"
        if result["report_retry_available"]
        else None
    )

    return result
