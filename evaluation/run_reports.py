import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import argparse

from evaluation.cases import CASES, INSTRUCTION_LABEL, load_case
from src.analysis_pipeline import run_analysis
from src.report_schema import ReportFormatError, parse_report


REPRESENTATIVE_CASES = {"flat", "fluctuating", "zero_start"}

REVIEW_FIELDS = [
    "case_id",
    "repeat",
    "output_file",
    "generation_status",
    "format_check",
    "numbers",
    "units",
    "periods",
    "unsupported_causes",
    "trend_description",
    "label_instruction",
    "overall_review",
    "notes",
]


def save_review(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_plan():
    plan = []

    for case in CASES:
        if case["rejection"] is not None:
            continue

        repeats = 3 if case["id"] in REPRESENTATIVE_CASES else 1

        for repeat in range(1, repeats + 1):
            plan.append({
                "case": case,
                "case_id": case["id"],
                "repeat": repeat,
                "metric_name": "Annual sales",
                "instruction_label": False,
            })

    increasing = next(
        case for case in CASES
        if case["id"] == "increasing"
    )

    for repeat in range(1, 4):
        plan.append({
            "case": increasing,
            "case_id": "instruction_label",
            "repeat": repeat,
            "metric_name": INSTRUCTION_LABEL,
            "instruction_label": True,
        })

    return plan


def main():
    parser = argparse.ArgumentParser(
        description="Record real reports for fixed evaluation cases."
    )
    parser.add_argument(
        "--only",
        nargs="+",
        help="Generate only these case IDs.",
    )
    args = parser.parse_args()

    plan = build_plan()

    if args.only:
        available = {item["case_id"] for item in plan}
        unknown = set(args.only) - available

        if unknown:
            parser.error(
                f"Unknown generation cases: {', '.join(sorted(unknown))}"
            )

        selected = set(args.only)
        plan = [
            item for item in plan
            if item["case_id"] in selected
        ]


    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    run_folder = (
        Path(__file__).resolve().parent
        / "runs"
        / timestamp
    )
    run_folder.mkdir(parents=True, exist_ok=False)

   
    review_path = run_folder / "review.csv"

    rows = [
        {
            "case_id": item["case_id"],
            "repeat": item["repeat"],
            "output_file": (
                f"{item['case_id']}_{item['repeat']}.json"
            ),
            "generation_status": "not_run",
            "format_check": "not_run",
            "numbers": "pending",
            "units": "pending",
            "periods": "pending",
            "unsupported_causes": "pending",
            "trend_description": "pending",
            "label_instruction": (
                "pending" if item["instruction_label"]
                else "not_applicable"
            ),
            "overall_review": "pending",
            "notes": "",
        }
        for item in plan
    ]

    # Record the full plan before the first paid request.
    save_review(review_path, rows)

    print(f"Planned generations: {len(plan)}")
    print("Each generation can make up to two Bedrock requests.")
    print(f"Results folder: {run_folder}")

    for index, (item, row) in enumerate(zip(plan, rows), start=1):
        print(
            f"[{index}/{len(plan)}] "
            f"{item['case_id']} — repeat {item['repeat']}",
            flush=True,
        )

        record = {
            "case_id": item["case_id"],
            "repeat": item["repeat"],
            "input_csv": item["case"]["csv"],
            "metric_name": item["metric_name"],
            "unit": "sales units",
            "expected": item["case"]["expected"],
            "result": None,
        }

        try:
            result = run_analysis(
                load_case(item["case"]),
                time_column="year",
                metric_column="sales",
                metric_name=item["metric_name"],
                unit="sales units",
                chart_type="line",
            )
            record["result"] = result
            row["generation_status"] = result["status"]

            if result["report"] is None:
                row["format_check"] = "not_available"
                row["notes"] = result["report_error"] or ""
            else:
                try:
                    parse_report(
                        json.dumps(
                            result["report"],
                            allow_nan=False,
                        )
                    )
                except (ReportFormatError, ValueError) as exc:
                    row["format_check"] = "fail"
                    row["notes"] = str(exc)
                else:
                    row["format_check"] = "pass"

        except (ValueError, RuntimeError) as exc:
            record["error"] = str(exc)
            row["generation_status"] = "error"
            row["format_check"] = "not_available"
            row["notes"] = str(exc)

        output_path = run_folder / row["output_file"]

        with output_path.open("x", encoding="utf-8") as handle:
            json.dump(
                record,
                handle,
                indent=2,
                allow_nan=False,
            )
            handle.write("\n")

        # Save progress after every generation.
        save_review(review_path, rows)

    print(f"\nReview checklist: {review_path}")
    print("Content review remains pending until you inspect the reports.")


if __name__ == "__main__":
    main()