import argparse
import json

from src.data_loader import (
    find_invalid_numeric_values,
    inspect_data,
    load_csv,
)


def main():
    parser = argparse.ArgumentParser(
        description="Inspect a CSV for NewsChart AI."
    )
    parser.add_argument("file", help="Path to the CSV file")
    parser.add_argument(
        "--metric",
        help="Optional column expected to contain numeric values",
    )
    args = parser.parse_args()

    try:
        df = load_csv(args.file)

        if args.metric and args.metric not in df.columns:
            raise ValueError(
                f"Column '{args.metric}' does not exist."
            )

        print("\nDATA PREVIEW")
        print(df.head().to_string(index=False))

        print("\nINSPECTION SUMMARY")
        print(json.dumps(inspect_data(df), indent=2))

        if args.metric:
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