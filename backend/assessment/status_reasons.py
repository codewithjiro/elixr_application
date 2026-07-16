"""Fixed status_reason enum values, priority selection, and unable-to-assess check merge."""

from __future__ import annotations

from assessment.movement_state import CheckResult

CAMERA_UNAVAILABLE = "camera_unavailable"
CAMERA_READ_FAILED = "camera_read_failed"
MODELS_UNAVAILABLE = "models_unavailable"
INTERNAL_ERROR = "internal_error"
LOW_TRACKING_CONFIDENCE = "low_tracking_confidence"
BODY_NOT_VISIBLE = "body_not_visible"
BOTTLE_NOT_VISIBLE = "bottle_not_visible"

REASON_PRIORITY: list[str] = [
    CAMERA_UNAVAILABLE,
    CAMERA_READ_FAILED,
    MODELS_UNAVAILABLE,
    INTERNAL_ERROR,
    LOW_TRACKING_CONFIDENCE,
    BODY_NOT_VISIBLE,
    BOTTLE_NOT_VISIBLE,
]

UNABLE_ASSESS_MESSAGE = "Unable to assess — tracking interrupted."


def pick_status_reason(candidates: list[str | None]) -> str | None:
    present = {c for c in candidates if c is not None}
    for reason in REASON_PRIORITY:
        if reason in present:
            return reason
    return None


def merge_checks_while_unable(
    previous: list[CheckResult],
    template: list[CheckResult],
) -> list[CheckResult]:
    passed_keys = {c.key for c in previous if c.status == "passed"}
    previous_by_key = {c.key: c for c in previous}
    template_by_key = {c.key: c for c in template}
    all_keys = list(dict.fromkeys([c.key for c in previous] + [c.key for c in template]))

    merged: list[CheckResult] = []
    for key in all_keys:
        if key in passed_keys:
            merged.append(previous_by_key[key])
            continue

        src = template_by_key.get(key) or previous_by_key[key]
        if src.status == "passed":
            merged.append(
                CheckResult(
                    key=src.key,
                    label=src.label,
                    status="not_assessed",
                    message=UNABLE_ASSESS_MESSAGE,
                    measured_value=src.measured_value,
                    expected_range=src.expected_range,
                )
            )
        else:
            merged.append(src)

    return merged
