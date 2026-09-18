"""Unit tests for ``pdf-save-ink`` helpers."""

from __future__ import annotations

import pytest

from toolscripts.commands.media.pdf_save_ink import _big_color_mask, _odd, _parse_pages, _tone_curve


def test_tone_curve_endpoints():
    lut = _tone_curve(knee=232, floor=140)
    assert len(lut) == 256
    assert lut[232] == 255 and lut[255] == 255
    assert lut[0] == 0 and lut[140] == 140  # dark tones untouched


def test_tone_curve_monotonic_and_continuous():
    lut = _tone_curve(knee=232, floor=140)
    assert all(b >= a for a, b in zip(lut, lut[1:], strict=False))
    # no hard jumps: a step larger than ~40 would break anti-aliased strokes
    assert max(b - a for a, b in zip(lut, lut[1:], strict=False)) <= 40


def test_odd_clamps_to_odd_range():
    assert _odd(4, 9, 61) == 9
    assert _odd(100, 9, 61) == 61
    assert _odd(38, 9, 61) == 39


def test_parse_pages():
    assert _parse_pages(None, 3) == [0, 1, 2]
    assert _parse_pages("2", 3) == [1]
    assert _parse_pages("1-2,3", 3) == [0, 1, 2]
    assert _parse_pages("2-", 3) == [1, 2]
    with pytest.raises(SystemExit):
        _parse_pages("0-1", 3)
    with pytest.raises(SystemExit):
        _parse_pages("1-4", 3)


def test_big_color_mask_removes_block_not_chip():
    np = pytest.importorskip("numpy")
    ndi = pytest.importorskip("scipy.ndimage")

    # white page with a big blue block (with a thin protruding corner) + a tiny chip
    arr = np.full((200, 200, 3), 255.0, dtype=np.float32)
    blue = np.array([178, 220, 250], dtype=np.float32)
    arr[20:120, 20:120] = blue  # big block
    arr[120:135, 120:135] = blue  # thin corner connected to the block
    arr[170:185, 170:185] = blue  # isolated small chip

    mask = _big_color_mask(np, ndi, arr, frac=0.05)
    assert mask is not None
    assert mask[70, 70]  # block interior removed
    assert mask[127, 127]  # connected corner removed as part of the whole
    assert not mask[177, 177]  # small chip kept
