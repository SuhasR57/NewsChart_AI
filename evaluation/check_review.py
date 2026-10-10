import argparse
import csv
from pathlib import Path


CONTENT_CHECKS = [
    "numbers",
    "units",
    "periods",
    "unsupported_causes",
    "trend_description",
]


def main():
    parser = argparse.ArgumentParser(
        description="Check whether a recorded evaluation is complete."
    )
    parser.add_argument("review_file", type=Path)
    args = parser.parse_args()

    with args.review_file.open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        reader = csv.DictReader(handle)

        required = {
            "case_id",
            "repeat",
            "generation_status",
            "format_check",
            "label_instruction",
            "overall_review",
            "notes",
            *CONTENT_CHECKS,
        }

        missing = required - set(reader.fieldnames or [])

        if missing:
            raise SystemExit(
                f"Missing review columns: {', '.join(sorted(missing))}"
            )

        rows = list(reader)

    if not rows:
        raise SystemExit("The review file contains no cases.")

    passed = 0

    for row in rows:
        problems = []

        if row["generation_status"].strip() != "complete":
            problems.append("generation did not complete")

        if row["format_check"].strip().lower() != "pass":
            problems.append("format check has not passed")

        for field in CONTENT_CHECKS:
            if row[field].strip().lower() != "pass":
                problems.append(f"{field}: {row[field] or 'blank'}")

        label_status = row["label_instruction"].strip().lower()

        if row["case_id"] == "instruction_label":
            if label_status != "pass":
                problems.append("instruction-label check has not passed")
        elif label_status not in ("pass", "not_applicable"):
            problems.append("unexpected instruction-label review status")

        if row["overall_review"].strip().lower() != "pass":
            problems.append("overall review has not passed")

        case_label = f"{row['case_id']} / repeat {row['repeat']}"

        if problems:
            print(f"\nNOT PASSED: {case_label}")
            for problem in problems:
                print(f"  - {problem}")
            if row["notes"]:
                print(f"  Notes: {row['notes']}")
        else:
            passed += 1
            print(f"PASS: {case_label}")

    print(f"\nReviewed passes: {passed}/{len(rows)}")
    print(
        "This checks recorded review decisions, "
        "not the factual content automatically."
    )

    if passed != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()