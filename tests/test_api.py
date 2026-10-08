import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import app
from src.upload_loader import MAX_UPLOAD_BYTES


CLEAN_CSV = (
    b"year,sales\n"
    b"2021,120\n"
    b"2022,150\n"
    b"2023,175\n"
    b"2024,160\n"
    b"2025,210\n"
)

FORM = {
    "time_column": "year",
    "metric_column": "sales",
    "metric_name": "Annual sales",
    "unit": "sales units",
    "chart_type": "line",
    "time_kind": "year",
    "date_format": "%Y-%m-%d",
}

GENERATED_REPORT = {
    "report": {
        "headline": "Sales increased overall",
        "summary": "Sales rose from 120 to 210 sales units.",
        "key_findings": [
            "Overall sales increased by 90 sales units."
        ],
        "report": (
            "Between 2021 and 2025, sales increased overall by 75%."
        ),
    },
    "metadata": {"model_id": "mock-model"},
    "content_review_required": True,
}


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

        patcher = patch(
            "src.analysis_pipeline.generate_structured_report"
        )
        self.mock_generator = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_generator.return_value = GENERATED_REPORT

    def analyze(self, contents=CLEAN_CSV, **overrides):
        settings = {**FORM, **overrides}
        return self.client.post(
            "/analyze",
            data=settings,
            files={"file": ("sample.csv", contents, "text/csv")},
        )

    def test_health_does_not_call_model(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.mock_generator.assert_not_called()

    def test_preview_returns_columns_and_rows(self):
        response = self.client.post(
            "/preview",
            files={"file": ("sample.csv", CLEAN_CSV, "text/csv")},
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["columns"], ["year", "sales"])
        self.assertEqual(result["inspection"]["row_count"], 5)
        self.assertEqual(result["preview"][0]["sales"], 120)
        self.mock_generator.assert_not_called()

    def test_preview_missing_values_are_json_null(self):
        response = self.client.post(
            "/preview",
            files={
                "file": (
                    "missing.csv",
                    b"year,sales\n2021,120\n2022,\n",
                    "text/csv",
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["preview"][1]["sales"])
        self.mock_generator.assert_not_called()

    def test_valid_analysis_returns_all_results(self):
        response = self.analyze()

        self.assertEqual(response.status_code, 200)
        result = response.json()

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["facts"]["metric_name"], "Annual sales")
        self.assertEqual(result["facts"]["last_value"], 210)
        self.assertEqual(
            result["chart"]["data"][0]["y"],
            [120, 150, 175, 160, 210],
        )
        self.assertEqual(
            result["report"], GENERATED_REPORT["report"]
        )
        self.assertFalse(result["report_retry_available"])

        self.mock_generator.assert_called_once()
        sent_facts = self.mock_generator.call_args.args[0]
        self.assertEqual(sent_facts, result["facts"])

    def test_bar_chart_selection(self):
        response = self.analyze(chart_type="bar")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["chart"]["data"][0]["type"], "bar"
        )

    def test_invalid_columns_never_call_model(self):
        response = self.analyze(metric_column="profit")

        self.assertEqual(response.status_code, 422)
        self.assertIn(
            "does not exist",
            " ".join(response.json()["detail"]["errors"]),
        )
        self.mock_generator.assert_not_called()

    def test_invalid_datasets_never_call_model(self):
        cases = {
            "invalid_number": b"year,sales\n2021,120\n2022,abc\n",
            "missing_value": b"year,sales\n2021,120\n2022,\n",
            "duplicate_year": b"year,sales\n2021,120\n2021,150\n",
            "single_row": b"year,sales\n2021,120\n",
        }

        for name, contents in cases.items():
            with self.subTest(name=name):
                response = self.analyze(contents)
                self.assertEqual(response.status_code, 422)

        self.mock_generator.assert_not_called()

    def test_empty_and_headers_only_files(self):
        for contents in (b"", b"year,sales\n"):
            with self.subTest(contents=contents):
                response = self.analyze(contents)
                self.assertEqual(response.status_code, 400)

        self.mock_generator.assert_not_called()

    def test_invalid_chart_type_never_calls_model(self):
        response = self.analyze(chart_type="pie")

        self.assertEqual(response.status_code, 422)
        self.mock_generator.assert_not_called()

    def test_missing_upload(self):
        response = self.client.post("/analyze", data=FORM)

        self.assertEqual(response.status_code, 422)
        self.mock_generator.assert_not_called()

    def test_non_csv_upload(self):
        response = self.client.post(
            "/analyze",
            data=FORM,
            files={"file": ("sample.txt", CLEAN_CSV, "text/plain")},
        )

        self.assertEqual(response.status_code, 400)
        self.mock_generator.assert_not_called()

    def test_upload_size_limit(self):
        contents = b"x" * (MAX_UPLOAD_BYTES + 1)
        response = self.analyze(contents)

        self.assertEqual(response.status_code, 413)
        self.mock_generator.assert_not_called()

    def test_row_limit(self):
        contents = b"year,sales\n" + b"2021,1\n" * 10_001
        response = self.analyze(contents)

        self.assertEqual(response.status_code, 413)
        self.mock_generator.assert_not_called()

    def test_unsorted_data_and_negative_values(self):
        response = self.analyze(
            b"year,sales\n2023,-25\n2021,120\n2022,0\n"
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        trace = result["chart"]["data"][0]

        self.assertEqual(trace["x"], [2021, 2022, 2023])
        self.assertEqual(trace["y"], [120, 0, -25])
        self.assertEqual(result["facts"]["last_value"], -25)

    def test_model_failure_preserves_facts_and_chart(self):
        self.mock_generator.side_effect = RuntimeError(
            "Simulated model failure"
        )

        response = self.analyze()

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "report_failed")
        self.assertEqual(result["facts"]["last_value"], 210)
        self.assertTrue(result["chart"]["data"])
        self.assertIsNone(result["report"])
        self.assertTrue(result["analysis_id"])
        self.assertTrue(result["report_retry_available"])
        self.assertIn(
            "Simulated model failure", result["report_error"]
        )

    def test_successful_report_retry(self):
        self.mock_generator.side_effect = RuntimeError(
            "Simulated model failure"
        )
        original = self.analyze().json()

        # Retry looks up the generator in api.py, so patch it there.
        with patch(
            "api.generate_structured_report",
            return_value=GENERATED_REPORT,
        ) as retry_generator:
            response = self.client.post(
                original["report_retry_url"]
            )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["facts"], original["facts"])
        self.assertEqual(result["chart"], original["chart"])
        self.assertEqual(
            result["report"], GENERATED_REPORT["report"]
        )
        self.assertFalse(result["report_retry_available"])
        self.assertIsNone(result["report_retry_url"])
        retry_generator.assert_called_once_with(original["facts"])

    def test_failed_retry_preserves_results(self):
        self.mock_generator.side_effect = RuntimeError(
            "Initial failure"
        )
        original = self.analyze().json()

        with patch(
            "api.generate_structured_report",
            side_effect=RuntimeError("Retry failed"),
        ):
            response = self.client.post(
                original["report_retry_url"]
            )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "report_failed")
        self.assertEqual(result["facts"], original["facts"])
        self.assertEqual(result["chart"], original["chart"])
        self.assertTrue(result["report_retry_available"])

    def test_completed_report_cannot_be_retried(self):
        self.mock_generator.side_effect = RuntimeError(
            "Initial failure"
        )
        original = self.analyze().json()
        retry_url = original["report_retry_url"]

        with patch(
            "api.generate_structured_report",
            return_value=GENERATED_REPORT,
        ) as retry_generator:
            self.assertEqual(
                self.client.post(retry_url).status_code, 200
            )
            self.assertEqual(
                self.client.post(retry_url).status_code, 409
            )
            retry_generator.assert_called_once()

    def test_unknown_analysis_id(self):
        with patch("api.generate_structured_report") as generator:
            response = self.client.post(
                "/analysis/nonexistent-id/report/retry"
            )

        self.assertEqual(response.status_code, 404)
        generator.assert_not_called()


if __name__ == "__main__":
    unittest.main()