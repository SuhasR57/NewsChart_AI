from copy import deepcopy
import unittest
from unittest.mock import Mock

import pandas as pd

from evaluation.cases import CASES, INSTRUCTION_LABEL, load_case
from src.analysis_pipeline import (
    PipelineValidationError,
    run_analysis,
)


def change_tuples(changes):
    return [
        (
            change["from_period"],
            change["to_period"],
            change["absolute_change"],
        )
        for change in changes
    ]


class TestEvaluationCases(unittest.TestCase):
    def make_generator(self):
        return Mock(
            return_value={
                "report": {
                    "headline": "Reference report",
                    "summary": "A mock response for pipeline testing.",
                    "key_findings": [
                        "Real report claims are reviewed separately."
                    ],
                    "report": "This test makes no model request.",
                },
                "metadata": {"model_id": "mock"},
                "content_review_required": True,
            }
        )

    def assert_expected_facts(self, facts, expected):
        values = expected["values"]
        years = list(range(2021, 2021 + len(values)))

        self.assertEqual(facts["metric_name"], "Annual sales")
        self.assertEqual(facts["unit"], "sales units")
        self.assertEqual(facts["observation_count"], len(values))
        self.assertEqual(
            facts["period_covered"],
            {"start": years[0], "end": years[-1]},
        )
        self.assertEqual(facts["first_value"], values[0])
        self.assertEqual(facts["last_value"], values[-1])
        self.assertAlmostEqual(facts["mean"], expected["mean"])
        self.assertEqual(
            facts["minimum"],
            {
                "value": expected["minimum"],
                "periods": expected["minimum_periods"],
            },
        )
        self.assertEqual(
            facts["maximum"],
            {
                "value": expected["maximum"],
                "periods": expected["maximum_periods"],
            },
        )
        self.assertEqual(
            facts["overall_absolute_change"],
            expected["absolute_change"],
        )

        if expected["percentage_change"] is None:
            self.assertNotIn("overall_percentage_change", facts)
            self.assertTrue(
                any(
                    "zero or negative" in limitation
                    for limitation in facts["limitations"]
                )
            )
        else:
            self.assertAlmostEqual(
                facts["overall_percentage_change"],
                expected["percentage_change"],
            )

        self.assertEqual(
            change_tuples(facts["largest_adjacent_increases"]),
            expected["increases"],
        )
        self.assertEqual(
            change_tuples(facts["largest_adjacent_decreases"]),
            expected["decreases"],
        )
        self.assertEqual(
            facts["adjacent_change_label"], "year-over-year"
        )

    def test_valid_cases_match_reference_answers(self):
        for case in CASES:
            if case["rejection"] is not None:
                continue

            for chart_type in ("line", "bar"):
                with self.subTest(
                    case=case["id"], chart_type=chart_type
                ):
                    df = load_case(case)
                    original = df.copy(deep=True)
                    generator = self.make_generator()

                    result = run_analysis(
                        df,
                        time_column="year",
                        metric_column="sales",
                        metric_name="Annual sales",
                        unit="sales units",
                        chart_type=chart_type,
                        report_generator=generator,
                    )

                    expected = case["expected"]
                    values = expected["values"]
                    years = list(
                        range(2021, 2021 + len(values))
                    )

                    self.assertEqual(result["status"], "complete")
                    self.assert_expected_facts(
                        result["facts"], expected
                    )

                    trace = result["chart"]["data"][0]
                    self.assertEqual(trace["x"], years)
                    self.assertEqual(trace["y"], values)
                    self.assertEqual(
                        trace["type"],
                        "scatter" if chart_type == "line" else "bar",
                    )
                    self.assertEqual(
                        result["chart"]["layout"]["yaxis"]["title"]["text"],
                        "Annual sales (sales units)",
                    )

                    generator.assert_called_once_with(
                        result["facts"]
                    )
                    pd.testing.assert_frame_equal(df, original)

    def test_invalid_cases_never_reach_generation(self):
        for case in CASES:
            if case["rejection"] is None:
                continue

            with self.subTest(case=case["id"]):
                generator = self.make_generator()

                with self.assertRaises(
                    PipelineValidationError
                ) as raised:
                    run_analysis(
                        load_case(case),
                        time_column="year",
                        metric_column="sales",
                        metric_name="Annual sales",
                        unit="sales units",
                        report_generator=generator,
                    )

                self.assertIn(
                    case["rejection"],
                    " ".join(raised.exception.errors),
                )
                generator.assert_not_called()

    def test_instruction_like_label_preserves_calculations(self):
        case = next(
            case for case in CASES
            if case["id"] == "increasing"
        )

        baseline = run_analysis(
            load_case(case),
            "year",
            "sales",
            "Annual sales",
            "sales units",
            report_generator=self.make_generator(),
        )
        generator = self.make_generator()

        labeled = run_analysis(
            load_case(case),
            "year",
            "sales",
            INSTRUCTION_LABEL,
            "sales units",
            report_generator=generator,
        )

        # The label changes; the numerical evidence must not.
        baseline_facts = deepcopy(baseline["facts"])
        labeled_facts = deepcopy(labeled["facts"])
        del baseline_facts["metric_name"]
        del labeled_facts["metric_name"]

        self.assertEqual(baseline_facts, labeled_facts)
        self.assertEqual(
            labeled["facts"]["metric_name"], INSTRUCTION_LABEL
        )
        self.assertEqual(
            baseline["chart"]["data"][0]["x"],
            labeled["chart"]["data"][0]["x"],
        )
        self.assertEqual(
            baseline["chart"]["data"][0]["y"],
            labeled["chart"]["data"][0]["y"],
        )
        generator.assert_called_once_with(labeled["facts"])


if __name__ == "__main__":
    unittest.main()