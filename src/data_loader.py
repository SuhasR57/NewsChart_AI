from pathlib import Path

import pandas as pd


def load_csv(file_path):
    """Load a CSV file into a Pandas DataFrame."""
    path = Path(file_path)

    if not path.is_file():
        raise ValueError(f"File not found: {path}")

    if path.suffix.lower() != ".csv":
        raise ValueError("Please provide a CSV file.")

    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError("The CSV file is empty.") from exc
    except pd.errors.ParserError as exc:
        raise ValueError("The CSV could not be parsed.") from exc
    except UnicodeDecodeError as exc:
        raise ValueError("The CSV must use UTF-8 encoding.") from exc

    if df.empty:
        raise ValueError("The CSV contains no data rows.")

    return df

# validation and inspection of data
def inspect_data(df):
    """Describe a dataset without changing it."""
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": df.columns.tolist(),
        "data_types": {
            column: str(dtype)
            for column, dtype in df.dtypes.items()
        },
        "missing_values": {
            column: int(count)
            for column, count in df.isna().sum().items()
        },
        "numeric_columns": (
            df.select_dtypes(include="number").columns.tolist()
        ),
    }

def find_invalid_numeric_values(df, column):
    """Find present values that cannot be converted to numbers."""
    converted = pd.to_numeric(df[column], errors="coerce")

    invalid = df[column].notna() & converted.isna()

    return df.loc[invalid, [column]]