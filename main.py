import argparse
import json
from pathlib import Path

from src.data_loader import (
    find_invalid_numeric_values,
    inspect_data,
    load_csv,
)
from src.data_validator import validate_data
from src.fact_engine import calculate_facts


def main():
    parser = argparse.ArgumentParser(
        description="Inspect, validate, and summarize CSV data."
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
        "--facts",
        action="store_true",
        help="Calculate statistical facts from validated data",
    )
    parser.add_argument(
        "--unit",
        default="unspecified",
        help="Metric unit, such as USD, people, or units",
    )
    parser.add_argument(
        "--output",
        help="Save facts to a new JSON file; requires --facts",
    )
    args = parser.parse_args()

    if args.time is not None and args.metric is None:
        parser.error("--time requires --metric.")

    if args.facts and (args.time is None or args.metric is None):
        parser.error("--facts requires --time and --metric.")

    if args.output is not None and not args.facts:
        parser.error("--output requires --facts.")

    try:
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

            if args.facts:
                facts = calculate_facts(
                    result.data,
                    time_column=args.time,
                    metric_column=args.metric,
                    time_kind=args.time_kind,
                    unit=args.unit,
                )
                payload = json.dumps(
                    facts,
                    indent=2,
                    allow_nan=False,
                )

                if args.output is not None:
                    output_path = Path(args.output)

                    if output_path.suffix.lower() != ".json":
                        raise ValueError(
                            "The output file must have a .json extension."
                        )

                    # Exclusive creation protects existing files,
                    # including the input dataset.
                    with output_path.open(
                        "x", encoding="utf-8"
                    ) as output_file:
                        output_file.write(payload + "\n")

                    print(f"\nFacts saved to: {output_path.resolve()}")

                print("\nSTATISTICAL FACTS")
                print(payload)
                return

            print("\nVALIDATION PASSED")
            print(
                f"{len(result.data)} observations, "
                "sorted chronologically."
            )
            print(result.data.to_string(index=False))
            return

        # Preserve the Day 1 inspection workflow.
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
            if invalid.empty:
                print("None found.")
            else:
                print(invalid.to_string(index=False))

    except FileExistsError:
        print("Error: Output file already exists. Choose a new filename.")
        raise SystemExit(1)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()