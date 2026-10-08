import json
import unittest
from unittest.mock import patch

from botocore.exceptions import ClientError

from src.report_schema import ReportFormatError, parse_report
from src.structured_report_generator import generate_structured_report


def valid_report():
    return {
        "headline": "Sales increased between 2021 and 2022",
        "summary": "Sales rose from 120 to 150 units.",
        "key_findings": [
            "The absolute increase was 30 units.",
            "The percentage increase was 25%.",
        ],
        "report": (
            "Sales were 120 units in 2021 and 150 units in 2022. "
            "The overall increase was 30 units, or 25%."
        ),
    }


def model_response(text, stop_reason="end_turn"):
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": text}],
            }
        },
        "usage": {
            "inputTokens": 200,
            "outputTokens": 100,
            "totalTokens": 300,
        },
        "stopReason": stop_reason,
        "ResponseMetadata": {"RequestId": "test-request"},
    }


class TestReportSchema(unittest.TestCase):
    def test_valid_report(self):
        expected = valid_report()
        self.assertEqual(
            parse_report(json.dumps(expected)),
            expected,
        )

    def test_invalid_json(self):
        with self.assertRaisesRegex(ReportFormatError, "Invalid JSON"):
            parse_report('{"headline":')

    def test_markdown_fences_are_rejected(self):
        text = "```json\n" + json.dumps(valid_report()) + "\n```"

        with self.assertRaises(ReportFormatError):
            parse_report(text)

    def test_non_object_is_rejected(self):
        with self.assertRaisesRegex(
            ReportFormatError, "JSON object"
        ):
            parse_report("[]")

    def test_missing_field(self):
        report = valid_report()
        del report["summary"]

        with self.assertRaisesRegex(
            ReportFormatError, "Missing fields: summary"
        ):
            parse_report(json.dumps(report))

    def test_extra_field(self):
        report = valid_report()
        report["explanation"] = "Advertising caused growth."

        with self.assertRaisesRegex(
            ReportFormatError, "Unexpected fields"
        ):
            parse_report(json.dumps(report))

    def test_wrong_types_and_blank_strings(self):
        for field in ("headline", "summary", "report"):
            for value in (123, None, [], "   "):
                with self.subTest(field=field, value=value):
                    report = valid_report()
                    report[field] = value

                    with self.assertRaises(ReportFormatError):
                        parse_report(json.dumps(report))

    def test_invalid_key_findings(self):
        for findings in (
            "One finding",
            [],
            ["a", "b", "c", "d"],
            [123],
            ["   "],
        ):
            with self.subTest(findings=findings):
                report = valid_report()
                report["key_findings"] = findings

                with self.assertRaises(ReportFormatError):
                    parse_report(json.dumps(report))

    def test_word_limits(self):
        for field, limit in (
            ("headline", 15),
            ("summary", 60),
            ("report", 180),
        ):
            with self.subTest(field=field):
                report = valid_report()
                report[field] = " ".join(["word"] * limit)
                parse_report(json.dumps(report))

                report[field] += " extra"
                with self.assertRaisesRegex(
                    ReportFormatError, "at most"
                ):
                    parse_report(json.dumps(report))

        report = valid_report()
        report["key_findings"] = [" ".join(["word"] * 36)]

        with self.assertRaisesRegex(ReportFormatError, "at most"):
            parse_report(json.dumps(report))

    def test_duplicate_keys(self):
        text = (
            '{"headline":"First", "headline":"Second",'
            '"summary":"Summary", "key_findings":["Finding"],'
            '"report":"Report"}'
        )

        with self.assertRaisesRegex(
            ReportFormatError, "Duplicate JSON field"
        ):
            parse_report(text)

    def test_nonstandard_numbers(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                text = json.dumps(valid_report())
                text = text.replace(
                    '"summary": "Sales rose from 120 to 150 units."',
                    f'"summary": {value}',
                )

                with self.assertRaisesRegex(
                    ReportFormatError, "Nonstandard JSON number"
                ):
                    parse_report(text)

    def test_format_validation_does_not_prove_accuracy(self):
        report = valid_report()
        report["summary"] = "Sales rose because of advertising."

        # This is correctly formatted but unsupported.
        # Content review must catch it separately.
        self.assertEqual(
            parse_report(json.dumps(report)),
            report,
        )


class TestStructuredReportGenerator(unittest.TestCase):
    def setUp(self):
        self.facts = {
            "metric_name": "sales",
            "unit": "units",
            "period_covered": {"start": 2021, "end": 2022},
            "first_value": 120,
            "last_value": 150,
            "overall_absolute_change": 30,
            "overall_percentage_change": 25,
        }

        patcher = patch(
            "src.structured_report_generator.boto3.Session"
        )
        self.mock_session = patcher.start()
        self.addCleanup(patcher.stop)

        self.client = (
            self.mock_session.return_value.client.return_value
        )
        self.good_response = model_response(
            json.dumps(valid_report())
        )

    def test_valid_first_response_needs_one_call(self):
        self.client.converse.return_value = self.good_response

        result = generate_structured_report(self.facts)

        self.client.converse.assert_called_once()
        self.assertEqual(result["report"], valid_report())
        self.assertEqual(result["metadata"]["attempt_count"], 1)
        self.assertTrue(result["content_review_required"])

    def test_malformed_then_valid_retries_once(self):
        self.client.converse.side_effect = [
            model_response("This is not JSON."),
            self.good_response,
        ]

        result = generate_structured_report(self.facts)

        self.assertEqual(self.client.converse.call_count, 2)
        self.assertEqual(result["metadata"]["attempt_count"], 2)
        self.assertIn(
            "format_error",
            result["metadata"]["attempts"][0],
        )

        request = self.client.converse.call_args.kwargs
        self.assertEqual(
            [message["role"] for message in request["messages"]],
            ["user", "assistant", "user"],
        )
        correction = request["messages"][-1]["content"][0]["text"]
        self.assertIn("failed validation", correction)

    def test_two_malformed_responses_fail(self):
        self.client.converse.return_value = model_response("Not JSON")

        with self.assertRaisesRegex(
            RuntimeError, "after two attempts"
        ):
            generate_structured_report(self.facts)

        self.assertEqual(self.client.converse.call_count, 2)

    def test_wrong_schema_triggers_retry(self):
        malformed = valid_report()
        malformed["key_findings"] = "Should be a list"

        self.client.converse.side_effect = [
            model_response(json.dumps(malformed)),
            self.good_response,
        ]

        result = generate_structured_report(self.facts)

        self.assertEqual(self.client.converse.call_count, 2)
        self.assertEqual(result["report"], valid_report())

    def test_excessive_length_triggers_retry(self):
        malformed = valid_report()
        malformed["headline"] = " ".join(["word"] * 16)

        self.client.converse.side_effect = [
            model_response(json.dumps(malformed)),
            self.good_response,
        ]

        generate_structured_report(self.facts)

        self.assertEqual(self.client.converse.call_count, 2)

    def test_empty_response_can_be_corrected(self):
        self.client.converse.side_effect = [
            model_response(""),
            self.good_response,
        ]

        result = generate_structured_report(self.facts)

        self.assertEqual(result["metadata"]["attempt_count"], 2)
        request = self.client.converse.call_args.kwargs
        self.assertEqual(len(request["messages"]), 1)
        self.assertIn(
            "previous attempt returned no text",
            request["messages"][0]["content"][0]["text"],
        )

    def test_truncated_response_triggers_retry(self):
        self.client.converse.side_effect = [
            model_response(
                json.dumps(valid_report()),
                stop_reason="max_tokens",
            ),
            self.good_response,
        ]

        generate_structured_report(self.facts)

        self.assertEqual(self.client.converse.call_count, 2)

    def test_service_error_is_not_retried(self):
        self.client.converse.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "Access denied",
                }
            },
            "Converse",
        )

        with self.assertRaisesRegex(
            RuntimeError, "AccessDeniedException"
        ):
            generate_structured_report(self.facts)

        self.client.converse.assert_called_once()

    def test_blocked_response_is_not_retried(self):
        self.client.converse.return_value = model_response(
            "Blocked",
            stop_reason="guardrail_intervened",
        )

        with self.assertRaisesRegex(
            RuntimeError, "did not complete"
        ):
            generate_structured_report(self.facts)

        self.client.converse.assert_called_once()

    def test_facts_and_usage_are_preserved(self):
        self.client.converse.return_value = self.good_response
        original = json.loads(json.dumps(self.facts))

        result = generate_structured_report(self.facts)

        self.assertEqual(self.facts, original)
        self.assertEqual(
            result["metadata"]["attempts"][0]["usage"],
            self.good_response["usage"],
        )

        request = self.client.converse.call_args.kwargs
        prompt = request["messages"][0]["content"][0]["text"]
        sent_facts = json.loads(
            prompt.split("FACT DICTIONARY:\n", 1)[1]
        )
        self.assertEqual(sent_facts, original)


if __name__ == "__main__":
    unittest.main()