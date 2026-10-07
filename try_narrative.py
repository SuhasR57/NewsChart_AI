import argparse
import json

from src.data_loader import load_csv
from src.data_validator import validate_data
from src.fact_engine import calculate_facts
from src.narrative_generator import generate_narrative


def main():
    parser = argparse.ArgumentParser(
        description="Generate a report from verified sales facts."
    )
    parser.add_argument(
        "--style",
        choices=["summary", "news", "business"],
        default="summary",
    )
    args = parser.parse_args()

    try:
        df = load_csv("data/sales_clean.csv")
        validation = validate_data(df, "year", "sales")

        if not validation.is_valid:
            print("VALIDATION FAILED")
            print(*validation.errors, sep="\n")
            raise SystemExit(1)

        facts = calculate_facts(
            validation.data,
            "year",
            "sales",
            unit="sales units",
        )

        result = generate_narrative(
            facts,
            style=args.style,
        )

        print("\nGENERATED REPORT")
        print(result["text"])

        print("\nREQUEST METADATA")
        print(json.dumps(result["metadata"], indent=2))

        for warning in result["warnings"]:
            print(f"\nWarning: {warning}")

    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()