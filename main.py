import argparse
import json
from pathlib import Path

from src.chart_builder import build_chart
from src.data_loader import (
    find_invalid_numeric_values,
    inspect_data,
    load_csv,
)
from src.data_validator import validate_data
from src.fact_engine import calculate_facts


def main():
    parser = argparse.ArgumentParser(
        description="Inspect, validate, summarize, and chart CSV data."
    )
    parser.add_argument("file", help="Path to the CSV file")
    parser.add_argument("--metric", help="Numeric measurement column")
    parser.add_argument("--time", help="Time column")
    parser.add_argument(
        "--time-kind",
        choices=["year", "date"],
        default="year",
    )
    parser.add_argument(
        "--date-format",
        default="%Y-%m-%d",
        help="Date format when using --time-kind date",
    )
    parser.add_argument(
        "--unit",
        default="unspecified",
        help="Measurement unit, such as USD or people",
    )
    parser.add_argument(
        "--facts",
        action="store_true",
        help="Calculate statistical facts",
    )
    parser.add_argument(
        "--output",
        help="Save facts to a new JSON file; requires --facts",
    )
    parser.add_argument(
        "--chart",
        choices=["line", "bar"],
        help="Manually select a chart type",
    )
    parser.add_argument(
        "--chart-output",
        help="Save a standalone HTML chart; requires --chart",
    )
    args = parser.parse_args()

    if args.time is not None and args.metric is None:
        parser.error("--time requires --metric.")

    if (args.facts or args.chart) and (
        args.time is None or args.metric is None
    ):
        parser.error("--facts and --chart require --time and --metric.")

    if args.output is not None and not args.facts:
        parser.error("--output requires --facts.")

    if args.chart_output is not None and args.chart is None:
        parser.error("--chart-output requires --chart.")

    if args.chart is not None and args.chart_output is None:
        parser.error("--chart requires --chart-output.")

    try:
        # Check export destinations before calculating or writing.
        destinations = []

        for filename, extension in (
            (args.output, ".json"),
            (args.chart_output, ".html"),
        ):
            if filename is None:
                continue

            path = Path(filename)

            if path.suffix.lower() != extension:
                raise ValueError(
                    f"Output '{path}' must have a {extension} extension."
                )

            if path.exists():
                raise ValueError(
                    f"Output '{path}' already exists. Choose a new filename."
                )

            if not path.parent.is_dir():
                raise ValueError(
                    f"Output folder '{path.parent}' does not exist."
                )

            destinations.append(path.resolve())

        if len(destinations) != len(set(destinations)):
            raise ValueError("Choose different output filenames.")

        df = load_csv(args.file)

        if args.time is not None:
            result = validate_data(
                df,
                time_column=args.time,
                metric_column=args.metric,
                time_kind=args.time_kind,
                date_format=args.date_format,
            )

            if not result.is_valid:
                print("\nVALIDATION FAILED")
                for error in result.errors:
                    print(f"- {error}")
                raise SystemExit(1)

            # Both features receive this exact validated dataset.
            validated_data = result.data

            facts_payload = None
            chart_payload = None

            if args.facts:
                facts = calculate_facts(
                    validated_data,
                    time_column=args.time,
                    metric_column=args.metric,
                    time_kind=args.time_kind,
                    unit=args.unit,
                )
                facts_payload = json.dumps(
                    facts,
                    indent=2,
                    allow_nan=False,
                )

            if args.chart:
                figure = build_chart(
                    validated_data,
                    time_column=args.time,
                    metric_column=args.metric,
                    time_kind=args.time_kind,
                    unit=args.unit,
                    chart_type=args.chart,
                )
                chart_payload = figure.to_html(
                    include_plotlyjs=True,
                    full_html=True,
                )

            # Generate both results before starting exports.
            if args.output is not None:
                path = Path(args.output)
                with path.open("x", encoding="utf-8") as output_file:
                    output_file.write(facts_payload + "\n")
                print(f"\nFacts saved to: {path.resolve()}")

            if args.chart_output is not None:
                path = Path(args.chart_output)
                with path.open("x", encoding="utf-8") as output_file:
                    output_file.write(chart_payload)
                print(f"\nChart saved to: {path.resolve()}")

            if facts_payload is not None:
                print("\nSTATISTICAL FACTS")
                print(facts_payload)

            if not args.facts and args.chart is None:
                print("\nVALIDATION PASSED")
                print(
                    f"{len(validated_data)} observations, "
                    "sorted chronologically."
                )
                print(validated_data.to_string(index=False))

            return

        # Day 1 inspection remains available.
        if args.metric is not None and args.metric not in df.columns:
            raise ValueError(
                f"Column '{args.metric}' does not exist."
            )

        print("\nDATA PREVIEW")
        print(df.head().to_string(index=False))

        print("\nINSPECTION SUMMARY")
        print(json.dumps(inspect_data(df), indent=2))

        if args.metric is not None:
            invalid = find_invalid_numeric_values(df, args.metric)
            print(f"\nINVALID NUMERIC VALUES: {args.metric}")
            print(
                "None found."
                if invalid.empty
                else invalid.to_string(index=False)
            )

    except FileExistsError:
        print("Error: An output file already exists. Choose a new filename.")
        raise SystemExit(1)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()