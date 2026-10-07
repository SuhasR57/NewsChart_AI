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


def write_new_file(filename, content):
    """Save output without overwriting an existing file."""
    path = Path(filename)

    with path.open("x", encoding="utf-8") as output_file:
        output_file.write(content)

    print(f"\nSaved: {path.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="Inspect, validate, chart, and report on CSV data."
    )
    parser.add_argument("file", help="Path to the CSV file")
    parser.add_argument("--metric", help="Numeric measurement column")
    parser.add_argument("--time", help="Time column")
    parser.add_argument(
        "--time-kind",
        choices=["year", "date"],
        default="year",
    )
    parser.add_argument("--date-format", default="%Y-%m-%d")
    parser.add_argument("--unit", default="unspecified")

    parser.add_argument("--facts", action="store_true")
    parser.add_argument("--output", help="New facts JSON filename")

    parser.add_argument("--chart", choices=["line", "bar"])
    parser.add_argument("--chart-output", help="New chart HTML filename")

    parser.add_argument(
        "--narrative",
        choices=["summary", "news", "business"],
        help="Generate a report through one Bedrock request",
    )
    parser.add_argument(
        "--report-output",
        help="New JSON filename for narrative text and metadata",
    )
    parser.add_argument("--aws-profile", default="newschart")
    parser.add_argument("--aws-region", default="us-east-1")
    parser.add_argument(
        "--model-id",
        default="us.amazon.nova-lite-v1:0",
    )

    args = parser.parse_args()

    needs_analysis = (
        args.facts
        or args.chart is not None
        or args.narrative is not None
    )

    if args.time is not None and args.metric is None:
        parser.error("--time requires --metric.")

    if needs_analysis and (
        args.time is None or args.metric is None
    ):
        parser.error(
            "Facts, charts, and narratives require --time and --metric."
        )

    if args.output is not None and not args.facts:
        parser.error("--output requires --facts.")

    if args.chart_output is not None and args.chart is None:
        parser.error("--chart-output requires --chart.")

    if args.chart is not None and args.chart_output is None:
        parser.error("--chart requires --chart-output.")

    if args.report_output is not None and args.narrative is None:
        parser.error("--report-output requires --narrative.")

    try:
        # Check all destinations before making a model request.
        destinations = []

        for filename, extension in (
            (args.output, ".json"),
            (args.chart_output, ".html"),
            (args.report_output, ".json"),
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
                    f"Output '{path}' already exists. "
                    "Choose a new filename."
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
            validation = validate_data(
                df,
                time_column=args.time,
                metric_column=args.metric,
                time_kind=args.time_kind,
                date_format=args.date_format,
            )

            if not validation.is_valid:
                print("\nVALIDATION FAILED")
                print(*validation.errors, sep="\n")
                raise SystemExit(1)

            validated_data = validation.data
            facts = None
            facts_payload = None
            chart_payload = None
            report = None
            report_payload = None

            # Compute facts once, whether displayed or sent to Bedrock.
            if args.facts or args.narrative is not None:
                facts = calculate_facts(
                    validated_data,
                    time_column=args.time,
                    metric_column=args.metric,
                    time_kind=args.time_kind,
                    unit=args.unit,
                )
                facts_payload = json.dumps(
                    facts, indent=2, allow_nan=False
                )

            if args.chart is not None:
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

            if args.narrative is not None:
                # AWS dependencies are needed only for narratives.
                from src.narrative_generator import generate_narrative

                print("\nRequesting a narrative from Bedrock...")

                report = generate_narrative(
                    facts,
                    style=args.narrative,
                    model_id=args.model_id,
                    profile_name=args.aws_profile,
                    region_name=args.aws_region,
                )

                # Save the evidence alongside the generated report.
                report_payload = json.dumps(
                    {
                        "facts": facts,
                        **report,
                    },
                    indent=2,
                    allow_nan=False,
                )

            # Generate all requested results before writing exports.
            if args.output is not None:
                write_new_file(args.output, facts_payload + "\n")

            if args.chart_output is not None:
                write_new_file(args.chart_output, chart_payload)

            if args.report_output is not None:
                write_new_file(
                    args.report_output, report_payload + "\n"
                )

            if args.facts:
                print("\nSTATISTICAL FACTS")
                print(facts_payload)

            if report is not None:
                print("\nGENERATED REPORT")
                print(report["text"])

                print("\nREQUEST METADATA")
                print(json.dumps(report["metadata"], indent=2))

                for warning in report["warnings"]:
                    print(f"\nWarning: {warning}")

            if not needs_analysis:
                print("\nVALIDATION PASSED")
                print(validated_data.to_string(index=False))

            return

        # Day 1 inspection.
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
        print("Error: An output already exists. Choose a new filename.")
        raise SystemExit(1)
    except ImportError as exc:
        print(
            f"Missing dependency: {exc}. Install requirements using "
            r".\.venv\Scripts\python.exe -m pip install -r requirements.txt"
        )
        raise SystemExit(1)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)



if __name__ == "__main__":
    main()