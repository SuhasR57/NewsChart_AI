from io import BytesIO
from pathlib import Path

import pandas as pd

from src.analysis_pipeline import MAX_ROWS


MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MiB


class UploadValidationError(ValueError):
    def __init__(self, message, status_code=400):
        self.status_code = status_code
        super().__init__(message)


def load_uploaded_csv(file_stream, filename):
    """Read a bounded CSV upload without saving it in the project."""
    if not filename or Path(filename).suffix.lower() != ".csv":
        raise UploadValidationError("Upload a file with a .csv extension.")

    # Read one extra byte to detect an oversized file.
    contents = file_stream.read(MAX_UPLOAD_BYTES + 1)

    if len(contents) > MAX_UPLOAD_BYTES:
        raise UploadValidationError(
            "The CSV exceeds the 2 MiB upload limit.",
            status_code=413,
        )

    if not contents:
        raise UploadValidationError("The CSV file is empty.")

    try:
        df = pd.read_csv(
            BytesIO(contents),
            encoding="utf-8-sig",
            nrows=MAX_ROWS + 1,
        )
    except pd.errors.EmptyDataError as exc:
        raise UploadValidationError(
            "The CSV file is empty."
        ) from exc
    except pd.errors.ParserError as exc:
        raise UploadValidationError(
            "The CSV could not be parsed. Check its delimiters and rows."
        ) from exc
    except UnicodeDecodeError as exc:
        raise UploadValidationError(
            "Save the CSV using UTF-8 encoding."
        ) from exc

    if df.empty:
        raise UploadValidationError("The CSV contains no data rows.")

    if len(df) > MAX_ROWS:
        raise UploadValidationError(
            f"The CSV exceeds the {MAX_ROWS:,}-row limit.",
            status_code=413,
        )

    return df