from assessment.tracking_confidence import compute_tracking_confidence
from assessment.status_reasons import (
    CAMERA_READ_FAILED,
    CAMERA_UNAVAILABLE,
    INTERNAL_ERROR,
    LOW_TRACKING_CONFIDENCE,
    BODY_NOT_VISIBLE,
    pick_status_reason,
    merge_checks_while_unable,
)
from assessment.low_confidence import LowConfidenceGate
from assessment.live_session import (
    LiveAssessmentSession,
    should_freeze_assessor,
    update_validated_checks,
)
from assessment.movement_state import CheckResult
from config import (
    MIN_TRACKING_CONFIDENCE,
    LOW_CONFIDENCE_FRAMES_REQUIRED,
    LOW_CONFIDENCE_RECOVERY_FRAMES,
)
from schemas.frame_event import FrameEvent


def test_confidence_formula():
    assert compute_tracking_confidence(body=False, bottle=False, calibrated=False) == 0.0
    assert compute_tracking_confidence(body=True, bottle=False, calibrated=False) == 0.5
    assert compute_tracking_confidence(body=True, bottle=True, calibrated=False) == 0.9
    assert compute_tracking_confidence(body=True, bottle=True, calibrated=True) == 1.0


def test_reason_priority_camera_beats_low_confidence():
    assert (
        pick_status_reason([LOW_TRACKING_CONFIDENCE, CAMERA_UNAVAILABLE, BODY_NOT_VISIBLE])
        == CAMERA_UNAVAILABLE
    )


def test_reason_priority_internal_error_above_low_confidence():
    assert (
        pick_status_reason([LOW_TRACKING_CONFIDENCE, INTERNAL_ERROR])
        == INTERNAL_ERROR
    )


def test_low_confidence_debounce_enter_and_recover():
    gate = LowConfidenceGate(
        min_confidence=MIN_TRACKING_CONFIDENCE,
        enter_frames=LOW_CONFIDENCE_FRAMES_REQUIRED,
        recovery_frames=LOW_CONFIDENCE_RECOVERY_FRAMES,
    )
    low = MIN_TRACKING_CONFIDENCE - 0.1
    high = MIN_TRACKING_CONFIDENCE + 0.1
    for _ in range(LOW_CONFIDENCE_FRAMES_REQUIRED - 1):
        assert gate.update(low) is False
    assert gate.update(low) is True
    for _ in range(LOW_CONFIDENCE_RECOVERY_FRAMES - 1):
        assert gate.update(high) is True
    assert gate.update(high) is False


def test_merge_preserves_passed_blocks_new_passes():
    previous = [
        CheckResult("a", "A", "passed", "ok"),
        CheckResult("b", "B", "in_progress", "working"),
    ]
    template = [
        CheckResult("a", "A", "passed", "ok"),
        CheckResult("b", "B", "passed", "should not promote"),
        CheckResult("c", "C", "passed", "new pass blocked"),
    ]
    merged = merge_checks_while_unable(previous, template)
    by_key = {c.key: c for c in merged}
    assert by_key["a"].status == "passed"
    assert by_key["b"].status != "passed"
    assert by_key["c"].status != "passed"


def test_frame_event_optional_fields_omitted():
    ev = FrameEvent(
        movement_id="arm_extension",
        assessment_state="calibrating",
        body_detected=True,
        bottle_detected=False,
        tracking_confidence=0.5,
        current_step="calibration",
        frame_jpeg_base64="",
    )
    data = ev.to_dict()
    assert data.get("status_reason") in (None,)
    assert data.get("status_message") in (None,)


def test_frame_event_optional_fields_set():
    ev = FrameEvent(
        movement_id="arm_extension",
        assessment_state="unable_to_assess",
        body_detected=False,
        bottle_detected=False,
        tracking_confidence=0.2,
        current_step="unable_to_assess",
        frame_jpeg_base64="",
        status_reason=LOW_TRACKING_CONFIDENCE,
        status_message="Improve lighting and framing, then hold steady.",
    )
    assert ev.status_reason == LOW_TRACKING_CONFIDENCE


def test_should_freeze_assessor_for_latch_or_hard_unable():
    assert should_freeze_assessor(latched=False, hard_unable=False) is False
    assert should_freeze_assessor(latched=True, hard_unable=False) is True
    assert should_freeze_assessor(latched=False, hard_unable=True) is True
    assert should_freeze_assessor(latched=True, hard_unable=True) is True


def test_update_validated_checks_preserves_cumulative_passes():
    prior_a = CheckResult("a", "A", "passed", "first pass")
    previous = [
        prior_a,
        CheckResult("b", "B", "in_progress", "not validated"),
    ]
    current = [
        CheckResult("a", "A", "in_progress", "must not erase pass"),
        CheckResult("b", "B", "passed", "second pass"),
        CheckResult("c", "C", "failed", "not validated"),
    ]

    updated = update_validated_checks(previous, current)

    assert [check.key for check in updated] == ["a", "b"]
    assert updated[0] is prior_a
    assert all(check.status == "passed" for check in updated)


def test_camera_read_failure_preserves_assessment_state():
    class FailedCapture:
        released = False

        def read(self):
            return False, None

        def release(self):
            self.released = True

    session = LiveAssessmentSession.__new__(LiveAssessmentSession)
    capture = FailedCapture()
    pose = object()
    assessor = object()
    calibration = object()
    validated = [CheckResult("a", "A", "passed", "preserved")]
    session._cap = capture
    session._pose = pose
    session._assessor = assessor
    session._calibration = calibration
    session._last_validated_checks = validated
    session.mirror_camera = True
    session.camera_source = "webcam"
    session.detection_interruptions = 0
    session.movement_id = "arm_extension"

    session._read_frame()

    assert capture.released is True
    assert session._cap is None
    assert session._camera_failure_reason == CAMERA_READ_FAILED
    assert session._pose is pose
    assert session._assessor is assessor
    assert session._calibration is calibration
    assert session._last_validated_checks is validated


def test_model_init_retry_preserves_assessor_state():
    session = LiveAssessmentSession.__new__(LiveAssessmentSession)
    assessor = object()
    calibration = object()
    validated = [CheckResult("a", "A", "passed", "preserved")]
    session._models_ok = False
    session._pose = None
    session._bottle_det = None
    session._assessor = assessor
    session._calibration = calibration
    session._last_validated_checks = validated
    session.detection_interruptions = 0

    attempts = {"n": 0}

    def fake_init():
        attempts["n"] += 1
        if attempts["n"] < 2:
            session._models_ok = False
            session.detection_interruptions += 1
        else:
            session._models_ok = True
            session._pose = object()
            session._bottle_det = object()

    session._init_models = fake_init

    session._ensure_models()
    assert session._models_ok is False
    assert session._assessor is assessor
    assert session._calibration is calibration
    assert session._last_validated_checks is validated

    session._ensure_models()
    assert session._models_ok is True
    assert session._assessor is assessor
    assert session._calibration is calibration
    assert session._last_validated_checks is validated
