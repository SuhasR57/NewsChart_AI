import math

import pandas as pd


def calculate_facts(
    data,
    time_column,
    metric_column,
    time_kind="year",
    unit="unspecified",
):
    """Calculate facts from validated, chronologically sorted data."""
    if time_kind not in ("year", "date"):
        raise ValueError("time_kind must be 'year' or 'date'.")

    if time_column == metric_column:
        raise ValueError("Time and metric columns must be different.")

    for column in (time_column, metric_column):
        if column not in data.columns:
            raise ValueError(f"Column '{column}' does not exist.")

    if len(data) < 2:
        raise ValueError("At least two observations are required.")

    times = data[time_column]
    values = data[metric_column]

    if times.isna().any() or values.isna().any():
        raise ValueError("Pass validated data without missing values.")

    if times.duplicated().any() or not times.is_monotonic_increasing:
        raise ValueError("Time values must be unique and sorted.")

    if not pd.api.types.is_numeric_dtype(values):
        raise ValueError("Metric values must be numeric.")

    numbers = [float(value) for value in values]

    if not all(math.isfinite(value) for value in numbers):
        raise ValueError("Metric values must be finite.")

    if time_kind == "year":
        if not pd.api.types.is_numeric_dtype(times):
            raise ValueError("Year values must be numeric.")

        if not all(
            math.isfinite(float(value))
            and 1 <= value <= 9999
            and float(value).is_integer()
            for value in times
        ):
            raise ValueError("Years must be whole numbers from 1 to 9999.")

        periods = [int(value) for value in times]
    else:
        if not pd.api.types.is_datetime64_any_dtype(times):
            raise ValueError("Date values must be parsed datetimes.")

        periods = [value.isoformat() for value in times]

    first = numbers[0]
    last = numbers[-1]
    minimum = min(numbers)
    maximum = max(numbers)
    absolute_change = last - first

    # Divide before summing to reduce overflow risk.
    mean = math.fsum(value / len(numbers) for value in numbers)

    changes = [
        {
            "from_period": periods[index - 1],
            "to_period": periods[index],
            "absolute_change": numbers[index] - numbers[index - 1],
        }
        for index in range(1, len(numbers))
    ]

    increases = [
        change for change in changes
        if change["absolute_change"] > 0
    ]
    decreases = [
        change for change in changes
        if change["absolute_change"] < 0
    ]

    def largest_changes(candidates, direction):
        if not candidates:
            return []

        amounts = [
            change["absolute_change"] for change in candidates
        ]
        target = max(amounts) if direction == "increase" else min(amounts)

        return [
            change for change in candidates
            if change["absolute_change"] == target
        ]

    consecutive_years = (
        time_kind == "year"
        and all(
            current - previous == 1
            for previous, current in zip(periods, periods[1:])
        )
    )

    limitations = [
        "Facts describe the supplied observations; they do not explain causes.",
        "The mean gives each observation equal weight.",
        "Adjacent changes are absolute differences, not rates per elapsed time.",
        "All tied extrema and largest adjacent changes are included.",
        "Calculations use floating-point arithmetic.",
        "Metric unit is supplied by the user; it is not inferred.",
    ]

    if not consecutive_years:
        limitations.append(
            "Adjacent changes are not labeled year-over-year because "
            "the observations are not consecutive annual values."
        )

    facts = {
        "metric_name": metric_column,
        "unit": unit,
        "time_kind": time_kind,
        "observation_count": len(numbers),
        "period_covered": {
            "start": periods[0],
            "end": periods[-1],
        },
        "first_value": first,
        "last_value": last,
        "mean": mean,
        "minimum": {
            "value": minimum,
            "periods": [
                period
                for period, value in zip(periods, numbers)
                if value == minimum
            ],
        },
        "maximum": {
            "value": maximum,
            "periods": [
                period
                for period, value in zip(periods, numbers)
                if value == maximum
            ],
        },
        "overall_absolute_change": absolute_change,
        "adjacent_change_label": (
            "year-over-year" if consecutive_years else "adjacent-period"
        ),
        "largest_adjacent_increases": largest_changes(
            increases, "increase"
        ),
        "largest_adjacent_decreases": largest_changes(
            decreases, "decrease"
        ),
        "limitations": limitations,
    }

    if first > 0:
        percentage_change = (absolute_change / first) * 100
        facts["overall_percentage_change"] = percentage_change
    else:
        limitations.append(
            "Overall percentage change is omitted because the starting "
            "value is zero or negative. Use the absolute change."
        )

    # Prevent non-finite calculation results from entering JSON.
    calculated = [
        mean,
        absolute_change,
        *[change["absolute_change"] for change in changes],
    ]
    if first > 0:
        calculated.append(percentage_change)

    if not all(math.isfinite(value) for value in calculated):
        raise ValueError(
            "Calculations exceeded the supported numeric range."
        )

    return facts