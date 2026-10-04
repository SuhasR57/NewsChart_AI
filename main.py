import argparse
import json

from src.data_loader import (
    find_invalid_numeric_values,
    inspect_data,
    load_csv,
)
from src.data_validator import validate_data


def main():
    parser = argparse.ArgumentParser(
        description="Inspect and validate a CSV for NewsChart AI."
    )
    parser.add_argument("file", help="Path to the CSV file")
    parser.add_argument(
        "--metric",
        help="Column expected to contain numeric measurements",
    )
    parser.add_argument(
        "--time",
        help="Time column; enables validation and requires --metric",
    )
    parser.add_argument(
        "--time-kind",
        choices=["year", "date"],
        default="year",
        help="Interpret time values as years or dates (default: year)",
    )
    parser.add_argument(
        "--date-format",
        default="%Y-%m-%d",
        help="Date format when using --time-kind date",
    )
    args = parser.parse_args()

    if args.time is not None and args.metric is None:
        parser.error("--time requires --metric.")

    try:
        df = load_csv(args.file)

        # Day 2: validate the selected columns.
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

            print("\nVALIDATION PASSED")
            print(
                f"{len(result.data)} observations, "
                "sorted chronologically."
            )
            print(result.data.to_string(index=False))
            return

        # Day 1: inspect the dataset.
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

    except (ValueError, OSError) as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()