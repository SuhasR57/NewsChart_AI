import json
from time import perf_counter

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    NoCredentialsError,
    ProfileNotFound,
    ReadTimeoutError,
)


MODEL_ID = "us.amazon.nova-lite-v1:0"
PROMPT_VERSION = "smoke-test-v1"


def main():
    started = perf_counter()

    try:
        session = boto3.Session(
            profile_name="newschart",
            region_name="us-east-1",
        )

        client = session.client(
            "bedrock-runtime",
            config=Config(
                connect_timeout=10,
                read_timeout=60,
                retries={
                    "mode": "standard",
                    "total_max_attempts": 1,
                },
            ),
        )

        started = perf_counter()

        response = client.converse(
            modelId=MODEL_ID,
            system=[
                {
                    "text": (
                        "Write neutral factual text. "
                        "Use only the supplied facts. "
                        "Do not invent causes, forecasts, or context."
                    )
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": (
                                "Write two short sentences using these facts: "
                                "sales were 120 units in 2021 and "
                                "210 units in 2025. The absolute change "
                                "was 90 units and the percentage change "
                                "was 75%."
                            )
                        }
                    ],
                }
            ],
            inferenceConfig={
                "maxTokens": 200,
                "temperature": 0.1,
            },
        )

        duration = perf_counter() - started

        text = "\n".join(
            block["text"]
            for block in response["output"]["message"]["content"]
            if "text" in block
        ).strip()

        if not text:
            raise ValueError("The model returned no text.")

        print("\nGENERATED TEXT")
        print(text)

        print("\nREQUEST METADATA")
        print(
            json.dumps(
                {
                    "model_id": MODEL_ID,
                    "prompt_version": PROMPT_VERSION,
                    "request_duration_seconds": round(duration, 3),
                    "usage": response.get("usage"),
                    "stop_reason": response.get("stopReason"),
                    "request_id": response.get(
                        "ResponseMetadata", {}
                    ).get("RequestId"),
                },
                indent=2,
            )
        )

        if response.get("stopReason") == "max_tokens":
            print("\nNotice: Output may be incomplete due to the token limit.")

    except ProfileNotFound:
        print(
            "AWS profile 'newschart' was not found. "
            "Run aws login --profile newschart."
        )
        raise SystemExit(1)

    except NoCredentialsError:
        print(
            "AWS credentials were not found. "
            "Run aws login --profile newschart."
        )
        raise SystemExit(1)

    except (ConnectTimeoutError, ReadTimeoutError):
        print(
            "The Bedrock connection or response timed out. "
            "Check your connection before retrying."
        )
        raise SystemExit(1)

    except ClientError as exc:
        error = exc.response.get("Error", {})
        print(
            f"Bedrock request failed "
            f"({error.get('Code', 'Unknown')}): "
            f"{error.get('Message', 'No details supplied')}"
        )
        raise SystemExit(1)

    except (BotoCoreError, ValueError) as exc:
        print(f"Request failed: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()