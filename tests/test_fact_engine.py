import json
import unittest

import pandas as pd

from src.data_validator import validate_data
from src.fact_engine import calculate_facts


class TestFactEngine(unittest.TestCase):
    def facts(self, periods, values, time_kind="year"):
        df = pd.DataFrame({
            "time": periods,
            "sales": values,
        })

        result = validate_data(
            df,
            "time",
            "sales",
            time_kind=time_kind,
        )
        self.assertTrue(result.is_valid, result.errors)

        return calculate_facts(
            result.data,
            "time",
            "sales",
            time_kind=time_kind,
            unit="USD",
        )

    def test_clean_sales(self):
        facts = self.facts(
            [2021, 2022, 2023, 2024, 2025],
            [120, 150, 175, 160, 210],
        )

        self.assertEqual(facts["metric_name"], "sales")
        self.assertEqual(facts["unit"], "USD")
        self.assertEqual(facts["observation_count"], 5)
        self.assertEqual(
            facts["period_covered"],
            {"start": 2021, "end": 2025},
        )
        self.assertEqual(facts["first_value"], 120)
        self.assertEqual(facts["last_value"], 210)
        self.assertAlmostEqual(facts["mean"], 163)
        self.assertEqual(
            facts["minimum"],
            {"value": 120, "periods": [2021]},
        )
        self.assertEqual(
            facts["maximum"],
            {"value": 210, "periods": [2025]},
        )
        self.assertEqual(facts["overall_absolute_change"], 90)
        self.assertAlmostEqual(
            facts["overall_percentage_change"], 75
        )
        self.assertEqual(
            facts["largest_adjacent_increases"],
            [{
                "from_period": 2024,
                "to_period": 2025,
                "absolute_change": 50,
            }],
        )
        self.assertEqual(
            facts["largest_adjacent_decreases"],
            [{
                "from_period": 2023,
                "to_period": 2024,
                "absolute_change": -15,
            }],
        )
        self.assertEqual(
            facts["adjacent_change_label"], "year-over-year"
        )

    def test_zero_start_omits_percentage(self):
        facts = self.facts([2021, 2022], [0, 20])

        self.assertNotIn("overall_percentage_change", facts)
        self.assertEqual(facts["overall_absolute_change"], 20)
        self.assertTrue(
            any(
                "zero or negative" in message
                for message in facts["limitations"]
            )
        )

    def test_negative_start_omits_percentage(self):
        facts = self.facts([2021, 2022], [-10, 20])

        self.assertNotIn("overall_percentage_change", facts)
        self.assertEqual(facts["overall_absolute_change"], 30)

    def test_positive_start_negative_end(self):
        facts = self.facts([2021, 2022], [10, -5])

        self.assertEqual(facts["overall_absolute_change"], -15)
        self.assertAlmostEqual(
            facts["overall_percentage_change"], -150
        )

    def test_year_gaps_are_not_year_over_year(self):
        facts = self.facts([2021, 2023], [10, 30])

        self.assertEqual(
            facts["adjacent_change_label"], "adjacent-period"
        )
        self.assertEqual(
            facts["largest_adjacent_increases"],
            [{
                "from_period": 2021,
                "to_period": 2023,
                "absolute_change": 20,
            }],
        )

    def test_dates_are_adjacent_periods(self):
        facts = self.facts(
            ["2025-03-01", "2025-01-01"],
            [30, 10],
            time_kind="date",
        )

        self.assertEqual(
            facts["adjacent_change_label"], "adjacent-period"
        )
        self.assertEqual(facts["first_value"], 10)
        self.assertEqual(facts["last_value"], 30)
        self.assertEqual(
            facts["period_covered"],
            {
                "start": "2025-01-01T00:00:00",
                "end": "2025-03-01T00:00:00",
            },
        )

    def test_tied_extrema_and_changes(self):
        facts = self.facts(
            [2021, 2022, 2023, 2024, 2025],
            [10, 20, 10, 20, 10],
        )

        self.assertEqual(
            facts["minimum"]["periods"], [2021, 2023, 2025]
        )
        self.assertEqual(
            facts["maximum"]["periods"], [2022, 2024]
        )
        self.assertEqual(
            [
                (item["from_period"], item["to_period"])
                for item in facts["largest_adjacent_increases"]
            ],
            [(2021, 2022), (2023, 2024)],
        )
        self.assertEqual(
            [
                (item["from_period"], item["to_period"])
                for item in facts["largest_adjacent_decreases"]
            ],
            [(2022, 2023), (2024, 2025)],
        )

    def test_increasing_series_has_no_decrease(self):
        facts = self.facts([2021, 2022, 2023], [10, 20, 40])
        self.assertEqual(facts["largest_adjacent_decreases"], [])

    def test_decreasing_series_has_no_increase(self):
        facts = self.facts([2021, 2022, 2023], [40, 20, 10])
        self.assertEqual(facts["largest_adjacent_increases"], [])

    def test_constant_series_has_no_increase_or_decrease(self):
        facts = self.facts([2021, 2022, 2023], [10, 10, 10])

        self.assertEqual(facts["overall_absolute_change"], 0)
        self.assertEqual(facts["overall_percentage_change"], 0)
        self.assertEqual(facts["largest_adjacent_increases"], [])
        self.assertEqual(facts["largest_adjacent_decreases"], [])

    def test_original_data_is_preserved(self):
        df = pd.DataFrame({
            "year": [2021, 2022],
            "sales": [10, 20],
        })
        original = df.copy(deep=True)

        calculate_facts(df, "year", "sales")

        pd.testing.assert_frame_equal(df, original)

    def test_json_round_trip(self):
        facts = self.facts([2021, 2022], [10, 20])

        exported = json.dumps(facts, allow_nan=False)
        restored = json.loads(exported)

        self.assertEqual(restored, facts)

    def test_unsorted_input_is_rejected(self):
        df = pd.DataFrame({
            "year": [2022, 2021],
            "sales": [20, 10],
        })

        with self.assertRaisesRegex(ValueError, "unique and sorted"):
            calculate_facts(df, "year", "sales")

    def test_non_finite_calculation_is_rejected(self):
        df = pd.DataFrame({
            "year": [2021, 2022],
            "sales": [-1e308, 1e308],
        })

        with self.assertRaisesRegex(ValueError, "numeric range"):
            calculate_facts(df, "year", "sales")


if __name__ == "__main__":
    unittest.main()