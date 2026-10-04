import unittest

import pandas as pd

from src.data_validator import validate_data


class TestDataValidator(unittest.TestCase):
    def validate(self, years, sales):
        df = pd.DataFrame({"year": years, "sales": sales})
        return validate_data(df, "year", "sales")

    def assert_rejected(self, result, message):
        self.assertFalse(result.is_valid)
        self.assertIsNone(result.data)
        self.assertTrue(
            any(message in error for error in result.errors),
            result.errors,
        )

    def test_missing_column(self):
        df = pd.DataFrame({"year": [2021, 2022]})
        result = validate_data(df, "year", "sales")
        self.assert_rejected(result, "does not exist")

    def test_same_column(self):
        df = pd.DataFrame({"year": [2021, 2022]})
        result = validate_data(df, "year", "year")
        self.assert_rejected(result, "different columns")

    def test_invalid_number(self):
        result = self.validate([2021, 2022], [120, "abc"])
        self.assert_rejected(result, "invalid numbers")

    def test_infinite_numbers(self):
        for value in ("inf", "-inf"):
            with self.subTest(value=value):
                result = self.validate([2021, 2022], [120, value])
                self.assert_rejected(result, "finite numeric values")

    def test_unsorted_years_and_original_preserved(self):
        df = pd.DataFrame({
            "year": [2023, 2021, 2022],
            "sales": ["175", "120", "150"],
        })
        original = df.copy(deep=True)

        result = validate_data(df, "year", "sales")

        self.assertTrue(result.is_valid, result.errors)
        self.assertEqual(
            result.data["year"].tolist(),
            [2021, 2022, 2023],
        )
        self.assertEqual(
            result.data["sales"].tolist(),
            [120, 150, 175],
        )
        pd.testing.assert_frame_equal(df, original)

    def test_duplicate_years(self):
        result = self.validate([2021, 2021], [120, 150])
        self.assert_rejected(result, "duplicate time values")

    def test_missing_values_in_each_column(self):
        for column in ("year", "sales"):
            for missing in (None, "", "   "):
                with self.subTest(column=column, missing=missing):
                    df = pd.DataFrame({
                        "year": [2021, 2022],
                        "sales": [120, 150],
                    }).astype(object)
                    df.loc[1, column] = missing

                    result = validate_data(df, "year", "sales")

                    self.assert_rejected(
                        result,
                        f"Column '{column}' has missing values",
                    )

    def test_single_observation(self):
        result = self.validate([2021], [120])
        self.assert_rejected(result, "At least two")

    def test_zero_and_negative_values(self):
        result = self.validate([2021, 2022], [0, -25])

        self.assertTrue(result.is_valid, result.errors)
        self.assertEqual(result.data["sales"].tolist(), [0, -25])

    def test_fractional_year(self):
        result = self.validate([2021, 2022.5], [120, 150])
        self.assert_rejected(result, "invalid time values")

    def test_dates_sort_chronologically(self):
        df = pd.DataFrame({
            "date": ["2025-03-01", "2025-01-01"],
            "sales": [150, 120],
        })

        result = validate_data(
            df, "date", "sales", time_kind="date"
        )

        self.assertTrue(result.is_valid, result.errors)
        self.assertEqual(
            result.data["date"].dt.strftime("%Y-%m-%d").tolist(),
            ["2025-01-01", "2025-03-01"],
        )

    def test_invalid_date(self):
        df = pd.DataFrame({
            "date": ["2025-01-01", "2025-02-30"],
            "sales": [120, 150],
        })

        result = validate_data(
            df, "date", "sales", time_kind="date"
        )

        self.assert_rejected(result, "invalid time values")


if __name__ == "__main__":
    unittest.main()