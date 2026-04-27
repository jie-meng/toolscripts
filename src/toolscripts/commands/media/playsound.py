"""``playsound`` / ``stopsound`` - play and stop audio files (afplay/ffplay/ogg123)."""

from __future__ import annotations

import argparse
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import is_macos
from toolscripts.core.shell import which

log = get_logger(__name__)

_PROCESSES = ("afplay", "ffplay", "ogg123")


def _stop_all() -> int:
    stopped = 0
    if sys.platform == "win32":
        return 0
    for proc in _PROCESSES:
        if which(proc):
            try:
                subprocess.run(["pkill", "-x", proc], check=False, capture_output=True)
                stopped += 1
            except FileNotFoundError:
                pass
    return stopped


def _play(file: Path, *, ext: str, pcm_format: str, pcm_rate: int) -> bool:
    if ext == "ogg":
        if which("ffplay"):
            return subprocess.run(
                ["ffplay", "-nodisp", "-autoexit", str(file)], check=False
            ).returncode == 0
        if which("ogg123"):
            return subprocess.run(["ogg123", str(file)], check=False).returncode == 0
        log.error("install ffmpeg or vorbis-tools to play .ogg")
        return False
    if ext == "pcm":
        if not which("ffplay"):
            log.error("install ffmpeg (ffplay) to play .pcm")
            return False
        return subprocess.run(
            [
                "ffplay", "-f", pcm_format, "-ar", str(pcm_rate),
                "-nodisp", "-autoexit", str(file),
            ],
            check=False,
        ).returncode == 0
    if is_macos() and which("afplay"):
        return subprocess.run(["afplay", str(file)], check=False).returncode == 0
    if which("ffplay"):
        return subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", str(file)], check=False
        ).returncode == 0
    log.error("no suitable audio player found (afplay/ffplay)")
    return False


def play_main() -> None:
    parser = argparse.ArgumentParser(
        prog="playsound",
        description="Play an audio file (.wav/.ogg/.pcm/etc.) via afplay/ffplay/ogg123.",
    )
    parser.add_argument("file", help="path to the audio file")
    parser.add_argument(
        "loop",
        nargs="?",
        type=int,
        default=1,
        help="number of loops; 0 = infinite (default: 1)",
    )
    parser.add_argument("--pcm-format", default="s16le", help=".pcm format (default: s16le)")
    parser.add_argument(
        "--pcm-rate", type=int, default=16000, help=".pcm sample rate (default: 16000)"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    _stop_all()
    path = Path(args.file).expanduser()
    if not path.is_file():
        log.error("file not found: %s", path)
        sys.exit(1)

    ext = path.suffix.lstrip(".").lower()

    def _stop_handler(_sig: int, _frame: object) -> None:
        _stop_all()
        sys.exit(130)

    signal.signal(signal.SIGINT, _stop_handler)

    if args.loop == 0:
        while True:
            _play(path, ext=ext, pcm_format=args.pcm_format, pcm_rate=args.pcm_rate)
    else:
        for _ in range(max(1, args.loop)):
            _play(path, ext=ext, pcm_format=args.pcm_format, pcm_rate=args.pcm_rate)


def stop_main() -> None:
    parser = argparse.ArgumentParser(
        prog="stopsound",
        description="Stop any audio currently playing via playsound (afplay/ffplay/ogg123).",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if sys.platform == "win32" or shutil.which("pkill") is None:
        log.warning("stopsound currently requires `pkill` (macOS/Linux)")
        sys.exit(0)

    stopped = 0
    for name in _PROCESSES:
        if which(name):
            result = subprocess.run(["pkill", "-x", name], check=False, capture_output=True)
            if result.returncode == 0:
                log.success("stopped %s", name)
                stopped += 1
    if stopped == 0:
        log.info("no sound is playing")


if __name__ == "__main__":
    play_main()
