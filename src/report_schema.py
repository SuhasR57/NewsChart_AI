import json
import re


REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "key_findings": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 3,
        },
        "report": {"type": "string"},
    },
    "required": [
        "headline",
        "summary",
        "key_findings",
        "report",
    ],
    "additionalProperties": False,
}

WORD_LIMITS = {
    "headline": 15,
    "summary": 60,
    "key_finding": 35,
    "report": 180,
}


class ReportFormatError(ValueError):
    """The model response does not match the report contract."""


def word_count(text):
    """Count whitespace-separated words."""
    return len(text.split())


def reject_duplicate_keys(pairs):
    result = {}

    for key, value in pairs:
        if key in result:
            raise ReportFormatError(
                f"Duplicate JSON field: '{key}'."
            )
        result[key] = value

    return result


def reject_nonstandard_number(value):
    raise ReportFormatError(
        f"Nonstandard JSON number: {value}."
    )


def parse_report(raw_text):
    """Validate JSON structure and length, not factual accuracy."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ReportFormatError(
            "The response must contain JSON text."
        )

    raw_text = raw_text.strip()

    # Accept one complete outer Markdown fence.
    # Extra commentary before or after the fence remains invalid.
    fenced = re.fullmatch(
        r"```(?:json)?[ \t]*\r?\n(.*?)\r?\n```",
        raw_text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if fenced:
        raw_text = fenced.group(1).strip()

    try:
        report = json.loads(
            raw_text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonstandard_number,
        )
    except json.JSONDecodeError as exc:
        raise ReportFormatError(
            f"Invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}. Return only a JSON object."
        ) from exc

    if not isinstance(report, dict):
        raise ReportFormatError(
            "The response must be a JSON object."
        )

    required = set(REPORT_SCHEMA["required"])
    actual = set(report)

    missing = required - actual
    extra = actual - required

    if missing:
        raise ReportFormatError(
            f"Missing fields: {', '.join(sorted(missing))}."
        )

    if extra:
        raise ReportFormatError(
            f"Unexpected fields: {', '.join(sorted(extra))}."
        )

    for field in ("headline", "summary", "report"):
        value = report[field]

        if not isinstance(value, str) or not value.strip():
            raise ReportFormatError(
                f"'{field}' must be a nonempty string."
            )

        limit = WORD_LIMITS[field]

        if word_count(value) > limit:
            raise ReportFormatError(
                f"'{field}' must contain at most {limit} words."
            )

    findings = report["key_findings"]

    if not isinstance(findings, list) or not 1 <= len(findings) <= 3:
        raise ReportFormatError(
            "'key_findings' must be a list of 1 to 3 strings."
        )

    for position, finding in enumerate(findings, start=1):
        if not isinstance(finding, str) or not finding.strip():
            raise ReportFormatError(
                f"Key finding {position} must be a nonempty string."
            )

        limit = WORD_LIMITS["key_finding"]

        if word_count(finding) > limit:
            raise ReportFormatError(
                f"Key finding {position} must contain at most "
                f"{limit} words."
            )

    return report