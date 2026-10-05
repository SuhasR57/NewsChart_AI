import unittest

import pandas as pd

from src.chart_builder import build_chart
from src.data_validator import validate_data
from src.fact_engine import calculate_facts


class TestChartBuilder(unittest.TestCase):
    def prepare(self, times, values, time_kind="year"):
        df = pd.DataFrame({
            "time": times,
            "sales": values,
        })
        result = validate_data(
            df,
            "time",
            "sales",
            time_kind=time_kind,
        )
        self.assertTrue(result.is_valid, result.errors)
        return result.data

    def chart(self, data, chart_type="line", time_kind="year"):
        return build_chart(
            data,
            "time",
            "sales",
            time_kind=time_kind,
            unit="USD",
            chart_type=chart_type,
        )

    def test_both_charts_preserve_every_value(self):
        data = self.prepare(
            [2021, 2022, 2023, 2024, 2025],
            [120, 150, 175, 160, 210],
        )

        for chart_type in ("line", "bar"):
            with self.subTest(chart_type=chart_type):
                figure = self.chart(data, chart_type)
                trace = figure.data[0]

                self.assertEqual(
                    list(trace.x), data["time"].tolist()
                )
                self.assertEqual(
                    list(trace.y), data["sales"].tolist()
                )

    def test_manual_chart_selection(self):
        data = self.prepare([2021, 2022], [10, 20])

        line = self.chart(data, "line").data[0]
        bar = self.chart(data, "bar").data[0]

        self.assertEqual(line.type, "scatter")
        self.assertEqual(line.mode, "lines+markers")
        self.assertEqual(bar.type, "bar")

    def test_chronological_order(self):
        data = self.prepare(
            [2023, 2021, 2022],
            [175, 120, 150],
        )

        for chart_type in ("line", "bar"):
            with self.subTest(chart_type=chart_type):
                trace = self.chart(data, chart_type).data[0]
                self.assertEqual(list(trace.x), [2021, 2022, 2023])
                self.assertEqual(list(trace.y), [120, 150, 175])

    def test_labels_and_hover(self):
        data = self.prepare([2021, 2022], [10, 20])
        figure = self.chart(data)

        self.assertIn("sales", figure.layout.title.text)
        self.assertIn("USD", figure.layout.title.text)
        self.assertEqual(figure.layout.xaxis.title.text, "time")
        self.assertEqual(
            figure.layout.yaxis.title.text, "sales (USD)"
        )
        self.assertEqual(
            list(figure.data[0].customdata), ["2021", "2022"]
        )
        self.assertIn("%{y}", figure.data[0].hovertemplate)

    def test_negative_and_zero_values(self):
        data = self.prepare([2021, 2022, 2023], [-25, 0, 15])

        for chart_type in ("line", "bar"):
            with self.subTest(chart_type=chart_type):
                figure = self.chart(data, chart_type)
                self.assertEqual(
                    list(figure.data[0].y), [-25, 0, 15]
                )
                self.assertEqual(
                    figure.layout.yaxis.rangemode, "tozero"
                )

    def test_flat_data(self):
        data = self.prepare([2021, 2022, 2023], [10, 10, 10])

        for chart_type in ("line", "bar"):
            with self.subTest(chart_type=chart_type):
                trace = self.chart(data, chart_type).data[0]
                self.assertEqual(list(trace.y), [10, 10, 10])

    def test_larger_dataset(self):
        years = list(range(1900, 2100))
        values = [index - 100 for index in range(200)]
        data = self.prepare(years, values)

        for chart_type in ("line", "bar"):
            with self.subTest(chart_type=chart_type):
                trace = self.chart(data, chart_type).data[0]
                self.assertEqual(list(trace.x), years)
                self.assertEqual(list(trace.y), values)

    def test_date_order_and_labels(self):
        data = self.prepare(
            ["2025-03-01", "2025-01-01", "2025-02-01"],
            [30, 10, 20],
            time_kind="date",
        )

        for chart_type in ("line", "bar"):
            with self.subTest(chart_type=chart_type):
                figure = self.chart(
                    data, chart_type, time_kind="date"
                )
                self.assertEqual(
                    list(figure.data[0].x), data["time"].tolist()
                )
                self.assertEqual(
                    list(figure.data[0].y), [10, 20, 30]
                )
                self.assertEqual(
                    list(figure.data[0].customdata),
                    ["2025-01-01", "2025-02-01", "2025-03-01"],
                )
                self.assertEqual(figure.layout.xaxis.type, "date")

    def test_chart_and_facts_agree(self):
        data = self.prepare(
            [2021, 2022, 2023, 2024, 2025],
            [120, 150, 175, 160, 210],
        )
        facts = calculate_facts(
            data, "time", "sales", unit="USD"
        )

        for chart_type in ("line", "bar"):
            with self.subTest(chart_type=chart_type):
                trace = self.chart(data, chart_type).data[0]
                times = list(trace.x)
                values = list(trace.y)

                self.assertEqual(
                    len(values), facts["observation_count"]
                )
                self.assertEqual(
                    times[0], facts["period_covered"]["start"]
                )
                self.assertEqual(
                    times[-1], facts["period_covered"]["end"]
                )
                self.assertEqual(values[0], facts["first_value"])
                self.assertEqual(values[-1], facts["last_value"])
                self.assertAlmostEqual(
                    sum(values) / len(values), facts["mean"]
                )
                self.assertEqual(
                    min(values), facts["minimum"]["value"]
                )
                self.assertEqual(
                    max(values), facts["maximum"]["value"]
                )
                self.assertEqual(
                    values[-1] - values[0],
                    facts["overall_absolute_change"],
                )
                self.assertEqual(
                    [
                        period
                        for period, value in zip(times, values)
                        if value == min(values)
                    ],
                    facts["minimum"]["periods"],
                )
                self.assertEqual(
                    [
                        period
                        for period, value in zip(times, values)
                        if value == max(values)
                    ],
                    facts["maximum"]["periods"],
                )

    def test_original_data_is_preserved(self):
        data = self.prepare([2021, 2022], [10, 20])
        original = data.copy(deep=True)

        self.chart(data, "line")
        self.chart(data, "bar")

        pd.testing.assert_frame_equal(data, original)

    def test_unsupported_chart_type(self):
        data = self.prepare([2021, 2022], [10, 20])

        with self.assertRaisesRegex(ValueError, "line.*bar"):
            self.chart(data, "pie")


if __name__ == "__main__":
    unittest.main()