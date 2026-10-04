from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ValidationResult:
    data: pd.DataFrame | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self):
        return self.data is not None and not self.errors

#validation of data
def validate_data(
    df,
    time_column,
    metric_column,
    time_kind="year",
    date_format="%Y-%m-%d",
):
    """Validate selected columns without modifying the input."""
    errors = []

    for column in (time_column, metric_column):
        if column not in df.columns:
            errors.append(
                f"Column '{column}' does not exist. "
                "Choose a column from the dataset."
            )

    if time_column == metric_column:
        errors.append(
            "Choose different columns for time and metric."
        )

    if errors:
        return ValidationResult(errors=errors)

    selected = df[[time_column, metric_column]].copy()

    # Treat empty strings and whitespace as missing too.
    missing_masks = {}

    for column in (time_column, metric_column):
        values = selected[column]
        blank = values.astype("string").str.strip().eq("").fillna(False)
        missing = values.isna() | blank
        missing_masks[column] = missing

        if missing.any():
            rows = [
                position
                for position, is_missing in enumerate(missing, start=1)
                if is_missing
            ]
            errors.append(
                f"Column '{column}' has missing values at data rows "
                f"{rows}. Fill in those values before continuing."
            )

    # Convert into a temporary Series to identify invalid entries.
    converted = pd.to_numeric(
        selected[metric_column],
        errors="coerce",
    )


    invalid = (
        ~missing_masks[metric_column]
        & (
            converted.isna()
            | converted.isin([float("inf"), float("-inf")])
        )
    )

    if invalid.any():
        entries = [
            f"row {position}: {value!r}"
            for position, (value, is_invalid) in enumerate(
                zip(selected[metric_column], invalid),
                start=1,
            )
            if is_invalid
        ]
        errors.append(
            f"Column '{metric_column}' contains invalid numbers "
            f"({'; '.join(entries)}). Replace them with finite numeric values."
        )

    if errors:
        return ValidationResult(errors=errors)

    if time_kind == "year":
        parsed_time = pd.to_numeric(
            selected[time_column],
            errors="coerce",
        )

        # Years must be whole numbers between 1 and 9999.
        valid_time = (
            parsed_time.notna()
            & parsed_time.between(1, 9999)
            & parsed_time.mod(1).eq(0)
        )
        expected = "whole years between 1 and 9999"

    elif time_kind == "date":
        parsed_time = pd.to_datetime(
            selected[time_column].astype("string"),
            format=date_format,
            errors="coerce",
            exact=True,
        )

        valid_time = parsed_time.notna()
        expected = (
            f"dates matching {date_format!r} "
            "within Pandas' supported date range"
        )

    else:
        return ValidationResult(
            errors=[
                "Unsupported time type. Choose 'year' or 'date'."
            ]
        )

    if not valid_time.all():
        entries = [
            f"row {position}: {value!r}"
            for position, (value, is_valid) in enumerate(
                zip(selected[time_column], valid_time),
                start=1,
            )
            if not is_valid
        ]

        return ValidationResult(
            errors=[
                f"Column '{time_column}' contains invalid time values "
                f"({'; '.join(entries)}). Use {expected}."
            ]
        )

    selected[metric_column] = converted

    if time_kind == "year":
        selected[time_column] = parsed_time.astype("int64")
    else:
        selected[time_column] = parsed_time

        # Check duplicates after parsing so equivalent times match.
    duplicate_mask = selected[time_column].duplicated(keep=False)

    if duplicate_mask.any():
        duplicate_times = (
            selected.loc[duplicate_mask, time_column]
            .drop_duplicates()
        )

        if time_kind == "date":
            labels = duplicate_times.dt.strftime("%Y-%m-%d").tolist()
        else:
            labels = duplicate_times.astype(str).tolist()

        errors.append(
            f"Column '{time_column}' contains duplicate time values: "
            f"{', '.join(labels)}. Keep one observation per time value."
        )

    if len(selected) < 2:
        errors.append(
            "At least two valid observations are required. "
            "Add another observation with a different time value."
        )

    if errors:
        return ValidationResult(errors=errors)

    selected = selected.sort_values(
        time_column,
        kind="stable",
    )


    return ValidationResult(data=selected)