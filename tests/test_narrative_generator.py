import copy
import unittest
from unittest.mock import patch

from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    ProfileNotFound,
    ReadTimeoutError,
)

from src.narrative_generator import (
    PROMPT_VERSION,
    generate_narrative,
)


class TestNarrativeGenerator(unittest.TestCase):
    def setUp(self):
        self.facts = {
            "metric_name": "sales",
            "unit": "sales units",
            "time_kind": "year",
            "observation_count": 2,
            "period_covered": {
                "start": 2021,
                "end": 2022,
            },
            "first_value": 120,
            "last_value": 150,
            "overall_absolute_change": 30,
            "overall_percentage_change": 25,
            "adjacent_change_label": "year-over-year",
            "limitations": [],
        }

        # Patch where the function looks up boto3.Session.
        session_patcher = patch(
            "src.narrative_generator.boto3.Session"
        )
        self.mock_session = session_patcher.start()
        self.addCleanup(session_patcher.stop)

        self.client = (
            self.mock_session.return_value.client.return_value
        )

        self.response = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "text": (
                                "Sales increased from 120 to 150 "
                                "sales units between 2021 and 2022."
                            )
                        }
                    ],
                }
            },
            "usage": {
                "inputTokens": 250,
                "outputTokens": 30,
                "totalTokens": 280,
            },
            "stopReason": "end_turn",
            "ResponseMetadata": {
                "RequestId": "test-request-123"
            },
        }
        self.client.converse.return_value = self.response

    def test_returns_text_and_metadata(self):
        result = generate_narrative(self.facts)

        self.assertIn("120 to 150", result["text"])
        metadata = result["metadata"]

        self.assertEqual(
            metadata["model_id"], "us.amazon.nova-lite-v1:0"
        )
        self.assertEqual(metadata["prompt_version"], PROMPT_VERSION)
        self.assertEqual(metadata["style"], "summary")
        self.assertEqual(metadata["usage"], self.response["usage"])
        self.assertEqual(metadata["request_id"], "test-request-123")
        self.assertEqual(result["warnings"], [])
        self.client.converse.assert_called_once()

    def test_sends_facts_and_instructions(self):
        generate_narrative(self.facts)

        request = self.client.converse.call_args.kwargs
        prompt = request["messages"][0]["content"][0]["text"]
        instructions = request["system"][0]["text"]

        # Decode the transmitted facts to check all values,
        # rather than looking for selected numbers.
        import json

        sent_facts = json.loads(
            prompt.split("FACT DICTIONARY:\n", 1)[1]
        )
        self.assertEqual(sent_facts, self.facts)
        self.assertIn("Do not invent causes", instructions)
        self.assertIn(
            "If percentage change is absent", instructions
        )

    def test_three_prompt_styles(self):
        expected_phrases = {
            "summary": "one short paragraph",
            "news": "neutral news report",
            "business": "business briefing",
        }

        for style, phrase in expected_phrases.items():
            with self.subTest(style=style):
                result = generate_narrative(
                    self.facts, style=style
                )
                request = self.client.converse.call_args.kwargs
                prompt = request["messages"][0]["content"][0]["text"]

                self.assertIn(phrase, prompt)
                self.assertEqual(result["metadata"]["style"], style)

    def test_configuration_and_duration(self):
        with patch(
            "src.narrative_generator.perf_counter",
            side_effect=[10.0, 12.5],
        ):
            result = generate_narrative(
                self.facts,
                profile_name="test-profile",
                region_name="us-east-2",
                model_id="test-model",
            )

        self.mock_session.assert_called_once_with(
            profile_name="test-profile",
            region_name="us-east-2",
        )

        client_call = (
            self.mock_session.return_value.client.call_args
        )
        self.assertEqual(client_call.args, ("bedrock-runtime",))

        config = client_call.kwargs["config"]
        self.assertEqual(config.connect_timeout, 10)
        self.assertEqual(config.read_timeout, 60)
        self.assertEqual(config.retries["total_max_attempts"], 1)

        request = self.client.converse.call_args.kwargs
        self.assertEqual(request["modelId"], "test-model")
        self.assertEqual(
            request["inferenceConfig"],
            {"maxTokens": 500, "temperature": 0.1},
        )
        self.assertEqual(
            result["metadata"]["request_duration_seconds"], 2.5
        )

    def test_invalid_style_makes_no_request(self):
        with self.assertRaisesRegex(ValueError, "Choose"):
            generate_narrative(self.facts, style="fiction")

        self.mock_session.assert_not_called()

    def test_invalid_facts_make_no_request(self):
        for facts in ({}, [], None, {"value": float("nan")}):
            with self.subTest(facts=facts):
                with self.assertRaises(ValueError):
                    generate_narrative(facts)

        self.mock_session.assert_not_called()

    def test_missing_profile_has_readable_error(self):
        self.mock_session.side_effect = ProfileNotFound(
            profile="newschart"
        )

        with self.assertRaisesRegex(
            RuntimeError, "AWS profile.*was not found"
        ):
            generate_narrative(self.facts)

    def test_missing_credentials_has_readable_error(self):
        self.client.converse.side_effect = NoCredentialsError()

        with self.assertRaisesRegex(
            RuntimeError, "AWS credentials were not found"
        ):
            generate_narrative(self.facts)

    def test_timeout_has_readable_error(self):
        self.client.converse.side_effect = ReadTimeoutError(
            endpoint_url="https://example.invalid"
        )

        with self.assertRaisesRegex(RuntimeError, "timed out"):
            generate_narrative(self.facts)

    def test_service_error_preserves_code_and_message(self):
        self.client.converse.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "Model invocation is not permitted.",
                }
            },
            "Converse",
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "AccessDeniedException.*Model invocation is not permitted",
        ):
            generate_narrative(self.facts)

    def test_empty_response_is_rejected(self):
        self.response["output"]["message"]["content"] = [
            {"text": "   "}
        ]

        with self.assertRaisesRegex(
            RuntimeError, "no narrative text"
        ):
            generate_narrative(self.facts)

    def test_multiple_text_blocks_are_combined(self):
        self.response["output"]["message"]["content"] = [
            {"text": "First sentence."},
            {"text": "Second sentence."},
        ]

        result = generate_narrative(self.facts)

        self.assertEqual(
            result["text"], "First sentence.\nSecond sentence."
        )

    def test_output_limit_returns_warning(self):
        self.response["stopReason"] = "max_tokens"

        result = generate_narrative(self.facts)

        self.assertTrue(
            any("incomplete" in warning for warning in result["warnings"])
        )

    def test_missing_usage_is_allowed(self):
        del self.response["usage"]

        result = generate_narrative(self.facts)

        self.assertIsNone(result["metadata"]["usage"])

    def test_input_facts_are_not_modified(self):
        original = copy.deepcopy(self.facts)

        generate_narrative(self.facts)

        self.assertEqual(self.facts, original)


if __name__ == "__main__":
    unittest.main()