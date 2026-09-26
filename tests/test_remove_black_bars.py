"""Unit tests for ``video-remove-black-bars`` helpers."""

from __future__ import annotations

import pytest

from toolscripts.commands.media.remove_black_bars import _aggregate, _parse_crop


def test_parse_crop_valid():
    assert _parse_crop("408x720+436+0") == (408, 720, 436, 0)
    assert _parse_crop(" 400x480 -10 +20 ".replace(" ", "")) == (400, 480, -10, 20)


@pytest.mark.parametrize(
    "bad",
    ["408:720:436:0", "408x720", "408x720+436", "x", "abc"],
)
def test_parse_crop_invalid(bad: str):
    with pytest.raises(ValueError):
        _parse_crop(bad)


def test_aggregate_jitter_unioned_outliers_dropped():
    # Dominant pillarbox box with small per-frame jitter, plus one wildly
    # different box (bright flash in the bar area) that must not widen the crop.
    boxes = [(400, 720, 440, 0)] * 20 + [(400, 704, 440, 8)] * 2 + [(642, 720, 320, 0)]
    crop, outliers = _aggregate(boxes, frame_w=1280, frame_h=720, tolerance=0.10)
    assert crop == (400, 720, 440, 0)
    assert outliers == 1


def test_aggregate_union_of_close_boxes():
    boxes = [(400, 720, 440, 0), (400, 720, 436, 0), (402, 720, 440, 0)]
    crop, outliers = _aggregate(boxes, frame_w=1280, frame_h=720, tolerance=0.10)
    # union: x 436..842 -> w 406, even
    assert crop == (406, 720, 436, 0)
    assert outliers == 0


def test_aggregate_forces_even_dimensions():
    boxes = [(405, 719, 437, 1)]
    crop, _ = _aggregate(boxes, frame_w=1280, frame_h=720, tolerance=0.10)
    w, h, x, y = crop
    assert w % 2 == 0 and h % 2 == 0
    assert w <= 405 and h <= 719  # shrunk, never grown
    assert x + w <= 1280 and y + h <= 720


def test_aggregate_full_frame_means_no_bars():
    crop, outliers = _aggregate([(640, 480, 0, 0)], frame_w=640, frame_h=480, tolerance=0.10)
    assert crop == (640, 480, 0, 0)
    assert outliers == 0


def test_aggregate_vertical_letterbox():
    boxes = [(640, 360, 0, 60)] * 10 + [(640, 358, 0, 61)]
    crop, _ = _aggregate(boxes, frame_w=640, frame_h=480, tolerance=0.10)
    # union over y: 60..420 -> h 360
    assert crop == (640, 360, 0, 60)
