"""Low-latency OpenCV webcam capture for ELIXR on Windows."""

from __future__ import annotations

import os
import threading
import time
from typing import Any

import cv2
import numpy as np

from config import CAMERA_INDEX, FRAME_HEIGHT, FRAME_WIDTH


class Camera:
    """
    Continuously captures webcam frames in a background thread.

    Only the newest frame is stored. Older frames are replaced instead
    of being placed in a queue, which helps prevent camera delay.
    """

    def __init__(
        self,
        index: int = CAMERA_INDEX,
        width: int = FRAME_WIDTH,
        height: int = FRAME_HEIGHT,
        fps: int = 30,
    ) -> None:
        self._index = index
        self._width = width
        self._height = height
        self._fps = fps

        self._cap: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None

        self._latest_frame: np.ndarray | None = None
        self._capture_time = 0.0
        self._frame_id = 0

        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        self._running = False
        self._backend_name = "Unknown"

    def open(self) -> None:
        """
        Open the webcam and start the background capture thread.

        Calling this method more than once has no effect when the
        camera is already running.
        """

        if self._running:
            return

        self._cap = self._open_video_capture()
        self._configure_camera(self._cap)

        self._stop_event.clear()
        self._running = True

        self._thread = threading.Thread(
            target=self._capture_loop,
            name="ElixrCameraThread",
            daemon=True,
        )
        self._thread.start()

        # Wait briefly for the first camera frame.
        if not self.wait_until_ready(timeout=3.0):
            self.release()
            raise RuntimeError(
                f"Camera index {self._index} opened, "
                "but no frames were received."
            )

        self._print_camera_information()

    def _open_video_capture(self) -> cv2.VideoCapture:
        """
        Try suitable OpenCV webcam backends.

        DirectShow is attempted first on Windows because it commonly
        provides better webcam latency. Media Foundation and the
        default backend are used as fallbacks.
        """

        if os.name == "nt":
            backend_candidates = [
                ("DirectShow", cv2.CAP_DSHOW),
                ("Media Foundation", cv2.CAP_MSMF),
                ("Default", cv2.CAP_ANY),
            ]
        else:
            backend_candidates = [
                ("Default", cv2.CAP_ANY),
            ]

        for backend_name, backend in backend_candidates:
            if backend == cv2.CAP_ANY:
                cap = cv2.VideoCapture(self._index)
            else:
                cap = cv2.VideoCapture(
                    self._index,
                    backend,
                )

            if cap.isOpened():
                self._backend_name = backend_name
                return cap

            cap.release()

        raise RuntimeError(
            f"Cannot open camera index {self._index}. "
            "Check whether another application is using the webcam."
        )

    def _configure_camera(
        self,
        cap: cv2.VideoCapture,
    ) -> None:
        """
        Request low-latency camera settings.

        Some webcams may ignore unsupported settings. The actual
        accepted values are printed after startup.
        """

        # MJPEG can reduce USB bandwidth usage for supported webcams.
        cap.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*"MJPG"),
        )

        cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self._width,
        )
        cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self._height,
        )
        cap.set(
            cv2.CAP_PROP_FPS,
            self._fps,
        )

        # Not all camera backends support this property.
        cap.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1,
        )

    def _capture_loop(self) -> None:
        """
        Continuously read frames from the webcam.

        Each new frame replaces the previous frame. No frame queue is
        created, so slow AI processing does not cause a growing delay.
        """

        cap = self._cap

        if cap is None:
            return

        consecutive_failures = 0

        while not self._stop_event.is_set():
            ok, frame = cap.read()

            if not ok or frame is None:
                consecutive_failures += 1

                # Avoid using all CPU resources when frame reading fails.
                time.sleep(0.01)

                if consecutive_failures >= 100:
                    print(
                        "Warning: Camera has failed to return "
                        "frames repeatedly."
                    )
                    consecutive_failures = 0

                continue

            consecutive_failures = 0
            capture_time = time.perf_counter()

            with self._lock:
                self._latest_frame = frame
                self._capture_time = capture_time
                self._frame_id += 1

    def read(
        self,
    ) -> tuple[bool, np.ndarray | None]:
        """
        Return the newest camera frame.

        This method is compatible with the original Camera class.
        For latency tracking, prefer read_latest().
        """

        ok, frame, _, _ = self.read_latest()
        return ok, frame

    def read_latest(
        self,
    ) -> tuple[
        bool,
        np.ndarray | None,
        float,
        int,
    ]:
        """
        Return the newest frame and its metadata.

        Returns:
            ok:
                True when a frame is available.

            frame:
                A copy of the newest BGR camera frame.

            capture_time:
                The time the frame was captured, using
                time.perf_counter().

            frame_id:
                An increasing identifier for each captured frame.
        """

        with self._lock:
            if self._latest_frame is None:
                return False, None, 0.0, -1

            return (
                True,
                self._latest_frame.copy(),
                self._capture_time,
                self._frame_id,
            )

    def wait_until_ready(
        self,
        timeout: float = 3.0,
    ) -> bool:
        """Wait until the camera has produced its first frame."""

        deadline = time.perf_counter() + timeout

        while time.perf_counter() < deadline:
            with self._lock:
                if self._latest_frame is not None:
                    return True

            time.sleep(0.01)

        return False

    def frame_age_ms(self) -> float | None:
        """
        Return the age of the newest camera frame in milliseconds.

        A high value means the application is using an old frame.
        """

        with self._lock:
            if self._latest_frame is None:
                return None

            capture_time = self._capture_time

        return (
            time.perf_counter() - capture_time
        ) * 1000.0

    def get_camera_information(
        self,
    ) -> dict[str, Any]:
        """Return the actual camera settings accepted by OpenCV."""

        cap = self._cap

        if cap is None:
            return {
                "opened": False,
                "backend": self._backend_name,
            }

        codec_number = int(
            cap.get(cv2.CAP_PROP_FOURCC)
        )

        codec = "".join(
            chr((codec_number >> (8 * index)) & 0xFF)
            for index in range(4)
        )

        return {
            "opened": cap.isOpened(),
            "backend": self._backend_name,
            "width": int(
                cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            ),
            "height": int(
                cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            ),
            "fps": float(
                cap.get(cv2.CAP_PROP_FPS)
            ),
            "codec": codec,
            "requested_width": self._width,
            "requested_height": self._height,
            "requested_fps": self._fps,
        }

    def _print_camera_information(self) -> None:
        """Print the camera settings for debugging."""

        info = self.get_camera_information()

        print(
            "Camera opened:"
            f" index={self._index},"
            f" backend={info.get('backend')},"
            f" resolution={info.get('width')}x"
            f"{info.get('height')},"
            f" reported_fps={info.get('fps', 0):.1f},"
            f" codec={info.get('codec')}"
        )

    @property
    def is_open(self) -> bool:
        """Return whether the camera capture thread is running."""

        return self._running

    @property
    def frame_id(self) -> int:
        """Return the identifier of the newest captured frame."""

        with self._lock:
            return self._frame_id

    def release(self) -> None:
        """Stop camera capture and release all webcam resources."""

        if not self._running and self._cap is None:
            return

        self._running = False
        self._stop_event.set()

        thread = self._thread
        cap = self._cap

        # Give the capture loop a chance to exit normally.
        if thread is not None:
            thread.join(timeout=1.0)

        # Releasing the camera can unblock cap.read() on some backends.
        if cap is not None:
            cap.release()

        if thread is not None and thread.is_alive():
            thread.join(timeout=0.5)

        self._thread = None
        self._cap = None

        with self._lock:
            self._latest_frame = None
            self._capture_time = 0.0
            self._frame_id = 0

    def __enter__(self) -> Camera:
        """Allow Camera to be used with a with statement."""

        self.open()
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.release()