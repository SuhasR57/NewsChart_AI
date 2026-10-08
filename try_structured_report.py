import json

from src.data_loader import load_csv
from src.data_validator import validate_data
from src.fact_engine import calculate_facts
from src.structured_report_generator import generate_structured_report


def main():
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

        result = generate_structured_report(facts)

        print("\nSTRUCTURED REPORT")
        print(json.dumps(result["report"], indent=2))

        print("\nMETADATA")
        print(json.dumps(result["metadata"], indent=2))

        print("\nReview every factual claim against the supplied facts.")

    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()