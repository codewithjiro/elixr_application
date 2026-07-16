"""Bottle smoother must not keep stale boxes after a miss."""

from vision.bottle_detector import BottleBox
from vision.smoothing import Smoother


def test_push_bottle_clears_on_miss():
    smoother = Smoother(window=5)
    box = BottleBox(10, 20, 40, 80, 0.9)

    assert smoother.push_bottle(box) is not None
    assert smoother.push_bottle(None) is None
    assert smoother.push_bottle(None) is None
