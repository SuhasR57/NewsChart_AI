from collections import OrderedDict
from copy import deepcopy
from threading import Lock
from time import monotonic
from uuid import uuid4


MAX_STORED_RESULTS = 50
RESULT_TTL_SECONDS = 30 * 60

_results = OrderedDict()
_lock = Lock()


class AnalysisStoreError(ValueError):
    def __init__(self, message, status_code):
        self.status_code = status_code
        super().__init__(message)


def _remove_expired():
    """Called only while holding the lock."""
    now = monotonic()

    expired = [
        analysis_id
        for analysis_id, entry in _results.items()
        if entry["expires_at"] <= now and not entry["busy"]
    ]

    for analysis_id in expired:
        del _results[analysis_id]


def store_failed_analysis(result):
    """Keep a copy of a failed analysis for a possible retry."""
    with _lock:
        _remove_expired()

        if len(_results) >= MAX_STORED_RESULTS:
            # Evict the oldest result that is not being retried.
            removable = next(
                (
                    analysis_id
                    for analysis_id, entry in _results.items()
                    if not entry["busy"]
                ),
                None,
            )

            if removable is None:
                return None

            del _results[removable]

        analysis_id = uuid4().hex

        _results[analysis_id] = {
            "result": deepcopy(result),
            "expires_at": monotonic() + RESULT_TTL_SECONDS,
            "busy": False,
        }

        return analysis_id


def claim_report_retry(analysis_id):
    """Reserve a retry and return a copy of the retained result."""
    with _lock:
        _remove_expired()
        entry = _results.get(analysis_id)

        if entry is None:
            raise AnalysisStoreError(
                "Analysis is unavailable or expired. Upload the CSV again.",
                404,
            )

        if entry["busy"]:
            raise AnalysisStoreError(
                "A report retry is already running for this analysis.",
                409,
            )

        if not entry["result"]["report_retry_available"]:
            raise AnalysisStoreError(
                "This analysis already has a generated report.",
                409,
            )

        snapshot = deepcopy(entry["result"])
        entry["busy"] = True
        return snapshot


def finish_report_retry(analysis_id, result):
    with _lock:
        entry = _results[analysis_id]
        entry["result"] = deepcopy(result)
        entry["busy"] = False


def release_report_retry(analysis_id):
    """Release the reservation if an unexpected error occurs."""
    with _lock:
        entry = _results.get(analysis_id)

        if entry is not None:
            entry["busy"] = False