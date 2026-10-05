import plotly.graph_objects as go


def build_chart(
    data,
    time_column,
    metric_column,
    time_kind="year",
    unit="unspecified",
    chart_type="line",
):
    """Build a figure from validated, chronologically sorted data."""
    if chart_type not in ("line", "bar"):
        raise ValueError("Choose 'line' or 'bar'.")

    if time_kind not in ("year", "date"):
        raise ValueError("Choose 'year' or 'date'.")

    for column in (time_column, metric_column):
        if column not in data.columns:
            raise ValueError(f"Column '{column}' does not exist.")

    if len(data) < 2:
        raise ValueError("At least two observations are required.")

    times = data[time_column]
    values = data[metric_column]

    if times.duplicated().any() or not times.is_monotonic_increasing:
        raise ValueError("Pass data with unique, sorted time values.")

    metric_label = f"{metric_column} ({unit})"

    if time_kind == "year":
        period_labels = [str(int(value)) for value in times]
    else:
        period_labels = [
            value.strftime("%Y-%m-%d") for value in times
        ]

    trace_options = {
        "x": times.tolist(),
        "y": values.tolist(),
        "customdata": period_labels,
        "name": metric_column,
        "hovertemplate": (
            "%{customdata}<br>"
            "Value: %{y}"
            "<extra></extra>"
        ),
    }

    if chart_type == "line":
        trace = go.Scatter(
            **trace_options,
            mode="lines+markers",
        )
    else:
        trace = go.Bar(**trace_options)

    figure = go.Figure(trace)

    figure.update_layout(
        title=f"{metric_label} over time",
        xaxis_title=time_column,
        yaxis_title=metric_label,
        template="plotly_white",
        showlegend=False,
        hoverlabel={"namelength": -1},
    )

    if time_kind == "year":
        figure.update_xaxes(
            type="linear",
            tickformat="d",
        )
    else:
        figure.update_xaxes(type="date")

    # Keep zero visible so negative and flat values have context.
    figure.update_yaxes(
        rangemode="tozero",
        zeroline=True,
    )

    return figure