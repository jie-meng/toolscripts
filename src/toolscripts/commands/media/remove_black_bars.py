"""``video-remove-black-bars`` - auto-detect and crop black bars from videos.

Requires ``ffmpeg`` and ``ffprobe`` on PATH.

Detection samples frames across the video with ffmpeg's cropdetect and
aggregates the per-frame boxes with a mode + tolerance strategy. Three
cropdetect pitfalls are deliberately avoided:

- Accumulation mode (``reset=0``, the positional default trap) merges every
  decoded frame into one ever-widening box, so a single noisy frame poisons
  the crop for the whole video. We force ``reset=1`` and aggregate ourselves.
- ``round`` defaults to 16, which snaps the box inward and can cut real
  content. We force ``round=0`` and only ever shrink to even dimensions.
- ``skip`` defaults to 2, which swallows the only frame when sampling
  single frames per seek point. We force ``skip=0``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, capture, require

from ._ffmpeg_quality import encode, prompt_quality

log = get_logger(__name__)

_CROP_RE = re.compile(r"crop=(\d+):(\d+):(\d+):(\d+)")

Box = tuple[int, int, int, int]  # w, h, x, y


def _probe(path: Path) -> tuple[int, int, float]:
    """Return (width, height, duration_seconds) of the first video stream."""
    out = capture(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            str(path),
        ]
    )
    data = json.loads(out)
    stream = data["streams"][0]
    width, height = int(stream["width"]), int(stream["height"])
    duration = float(data.get("format", {}).get("duration") or stream.get("duration") or 0.0)
    return width, height, duration


# Audio codecs that are safe to stream-copy into an mp4/mov/mkv output.
_COPYABLE_AUDIO = {"aac", "mp3"}


def _audio_codec(path: Path) -> str | None:
    """Codec name of the first audio stream, or None when there is none."""
    out = capture(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=False,
    ).strip()
    return out or None


def _detect_boxes(path: Path, duration: float, limit: int, samples: int) -> list[Box]:
    """Sample ``samples`` frames spread over the video and cropdetect each one."""
    if duration > 0:
        samples = max(1, min(samples, int(duration)))
    else:
        samples = 1
    boxes: list[Box] = []
    for i in range(samples):
        t = (i + 0.5) * duration / samples if duration > 0 else 0
        result = capture(
            [
                "ffmpeg",
                "-hide_banner",
                "-ss",
                f"{t:.3f}",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-vf",
                f"cropdetect=limit={limit}:round=0:reset=1:skip=0",
                "-f",
                "null",
                "-",
            ],
            check=False,
            merge_stderr=True,
        )
        match = _CROP_RE.search(result)
        if match:
            boxes.append(tuple(int(g) for g in match.groups()))  # type: ignore[arg-type]
        if samples >= 10 and (i + 1) % max(1, samples // 10) == 0:
            log.debug("detected %d/%d sample frames", i + 1, samples)
    return boxes


def _aggregate(boxes: list[Box], frame_w: int, frame_h: int, tolerance: float) -> tuple[Box, int]:
    """Union of boxes close to the dominant box; returns (crop, outlier_count)."""
    dominant = Counter(boxes).most_common(1)[0][0]
    dw, dh, dx, dy = dominant
    tol_w = max(4.0, tolerance * frame_w)
    tol_h = max(4.0, tolerance * frame_h)

    close: list[Box] = []
    outliers = 0
    for w, h, x, y in boxes:
        if (
            abs(x - dx) <= tol_w
            and abs(y - dy) <= tol_h
            and abs(w - dw) <= tol_w
            and abs(h - dh) <= tol_h
        ):
            close.append((w, h, x, y))
        else:
            outliers += 1

    x1 = min(x for _, _, x, _ in close)
    y1 = min(y for _, _, _, y in close)
    x2 = max(x + w for w, _, x, _ in close)
    y2 = max(y + h for _, h, _, y in close)
    crop_w, crop_h = x2 - x1, y2 - y1

    # libx264 needs even dimensions; shrink (never grow) to stay inside content.
    crop_w -= crop_w % 2
    crop_h -= crop_h % 2
    crop_w = max(2, min(crop_w, frame_w))
    crop_h = max(2, min(crop_h, frame_h))
    x1 = max(0, min(x1, frame_w - crop_w))
    y1 = max(0, min(y1, frame_h - crop_h))
    return (crop_w, crop_h, x1, y1), outliers


def _parse_crop(text: str) -> Box:
    """Parse a manual ``WxH+X+Y`` crop string."""
    match = re.fullmatch(r"(\d+)x(\d+)([+-]\d+)([+-]\d+)", text.replace(" ", ""))
    if not match:
        raise ValueError(f"invalid --crop format {text!r} (expected WxH+X+Y, e.g. 408x720+436+0)")
    w, h, x, y = (int(g) for g in match.groups())
    return w, h, x, y


def _process(
    path: Path,
    output: Path | None,
    *,
    limit: int,
    samples: int,
    tolerance: float,
    quality: str,
    crop_override: Box | None,
    dry_run: bool,
) -> bool:
    try:
        frame_w, frame_h, duration = _probe(path)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        log.error("cannot probe %s: %s", path, exc)
        return False

    if crop_override is not None:
        crop = crop_override
    else:
        log.info(
            "detecting black bars in %s (%dx%d, %.1fs)...", path.name, frame_w, frame_h, duration
        )
        boxes = _detect_boxes(path, duration, limit, samples)
        if not boxes:
            log.error("detection produced no results for %s", path)
            return False
        crop, outliers = _aggregate(boxes, frame_w, frame_h, tolerance)
        if outliers and outliers / len(boxes) > 0.01:
            widest = max(boxes, key=lambda b: b[0] * b[1])
            log.warning(
                "%d/%d sampled frames have content outside the dominant area (widest box "
                "%dx%d+%d+%d); cropped conservatively. Use --crop to force a different area.",
                outliers,
                len(boxes),
                *widest,
            )

    w, h, x, y = crop
    if (w, h, x, y) == (frame_w, frame_h, 0, 0):
        log.success("no black bars detected in %s; nothing to do", path.name)
        return True

    log.info("cropping %s: %dx%d -> %dx%d+%d+%d", path.name, frame_w, frame_h, w, h, x, y)
    if dry_run:
        print(f"{path}\t{w}x{h}+{x}+{y}")
        return True

    out = output or path.with_name(f"{path.stem}_decropped{path.suffix}")
    if out.suffix.lower() == ".webm":
        # The encoder is libx264, which cannot be muxed into webm.
        log.warning("%s: h264 does not fit webm; writing .mkv instead", out.name)
        out = out.with_suffix(".mkv")
    codec = _audio_codec(path)
    audio_copy = codec is None or codec in _COPYABLE_AUDIO
    if not audio_copy:
        log.info("audio codec %r not copy-safe here; re-encoding to aac", codec)
    if not encode(
        path, out, quality=quality, video_filter=f"crop={w}:{h}:{x}:{y}", audio_copy=audio_copy
    ):
        return False
    log.success("created: %s (%dx%d)", out, w, h)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="video-remove-black-bars",
        description="Auto-detect black bars (letterbox/pillarbox) and crop them away.",
    )
    parser.add_argument("videos", nargs="+", help="video files to process")
    parser.add_argument(
        "--quality",
        choices=("1", "2", "3"),
        help="encode quality: 1=low, 2=medium, 3=high (will prompt if omitted)",
    )
    parser.add_argument(
        "-o", "--output", help="output file (only valid when processing a single video)"
    )
    parser.add_argument(
        "--crop",
        help="skip detection and crop this area, e.g. 408x720+436+0",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=24,
        help="cropdetect black threshold, 8-bit units (default: 24)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=24,
        help="frames sampled across the video for detection (default: 24)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.10,
        help="fraction of frame size a sample box may deviate from the dominant one "
        "and still be trusted (default: 0.10)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the detected crop area without encoding"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("ffmpeg")
        require("ffprobe")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    crop_override: Box | None = None
    if args.crop:
        try:
            crop_override = _parse_crop(args.crop)
        except ValueError as exc:
            log.error("%s", exc)
            sys.exit(1)

    if args.output and len(args.videos) > 1:
        log.warning("--output ignored when processing multiple videos")
        args.output = None

    # --dry-run never encodes, so don't block on the quality prompt there.
    quality = args.quality or ("2" if args.dry_run else prompt_quality())

    successes = 0
    for raw in args.videos:
        path = Path(raw).expanduser()
        if not path.is_file():
            log.warning("skipping missing file: %s", raw)
            continue
        if _process(
            path,
            Path(args.output).expanduser() if args.output else None,
            limit=args.limit,
            samples=args.samples,
            tolerance=args.tolerance,
            quality=quality,
            crop_override=crop_override,
            dry_run=args.dry_run,
        ):
            successes += 1

    log.success("processed %d/%d video(s)", successes, len(args.videos))


if __name__ == "__main__":
    main()
