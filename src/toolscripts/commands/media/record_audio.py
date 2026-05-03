"""``record-audio`` - record system audio (what's playing on speakers, not mic)."""

from __future__ import annotations

import argparse
import atexit
import contextlib
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import is_linux, is_macos, is_windows
from toolscripts.core.shell import require

log = get_logger(__name__)

VIRTUAL_AUDIO_KEYWORDS = [
    "blackhole",
    "background music",
    "soundflower",
    "loopback",
    "virtual audio",
    "cable input",
    "vb-audio",
]

_SWIFT_AUDIO_TOOL = """\
import CoreAudio
import Foundation

func findOutputDevices() -> [(AudioDeviceID, String)] {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDevices,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    var dataSize: UInt32 = 0
    AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &dataSize)
    let count = Int(dataSize) / MemoryLayout<AudioDeviceID>.size
    var devices = [AudioDeviceID](repeating: 0, count: count)
    AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &dataSize, &devices)

    var result: [(AudioDeviceID, String)] = []
    for did in devices {
        var streamAddr = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyStreams,
            mScope: kAudioObjectPropertyScopeOutput,
            mElement: kAudioObjectPropertyElementMain
        )
        var streamSize: UInt32 = 0
        let streamErr = AudioObjectGetPropertyDataSize(did, &streamAddr, 0, nil, &streamSize)
        if streamErr != 0 || streamSize == 0 { continue }

        var nameAddr = AudioObjectPropertyAddress(
            mSelector: kAudioDevicePropertyDeviceNameCFString,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        var cfName: Unmanaged<CFString>?
        var nameSize = UInt32(MemoryLayout<CFString>.size)
        AudioObjectGetPropertyData(did, &nameAddr, 0, nil, &nameSize, &cfName)
        if let name = cfName?.takeRetainedValue() as String? {
            result.append((did, name))
        }
    }
    return result
}

func getDefaultOutput() -> (AudioDeviceID, String) {
    var outAddr = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDefaultOutputDevice,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    var defaultID: AudioDeviceID = 0
    var size = UInt32(MemoryLayout<AudioDeviceID>.size)
    AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &outAddr, 0, nil, &size, &defaultID)

    var nameAddr = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyDeviceNameCFString,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    var cfName: Unmanaged<CFString>?
    var nameSize = UInt32(MemoryLayout<CFString>.size)
    AudioObjectGetPropertyData(defaultID, &nameAddr, 0, nil, &nameSize, &cfName)
    let name = (cfName?.takeRetainedValue() as String?) ?? "unknown"
    return (defaultID, name)
}

func setDefaultOutput(_ deviceID: AudioDeviceID) -> Int32 {
    var outAddr = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDefaultOutputDevice,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    var devID = deviceID
    return AudioObjectSetPropertyData(
        AudioObjectID(kAudioObjectSystemObject),
        &outAddr, 0, nil,
        UInt32(MemoryLayout<AudioDeviceID>.size), &devID
    )
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    print("Usage: audio-helper <command> [args]")
    print("  list                  - list output devices")
    print("  default               - show default output device")
    print("  set-default <name>    - set default output device by name")
    exit(1)
}

let command = args[1]
switch command {
case "list":
    for (did, name) in findOutputDevices() {
        print("\\(did)\\t\\(name)")
    }
case "default":
    let (did, name) = getDefaultOutput()
    print("\\(did)\\t\\(name)")
case "set-default":
    guard args.count >= 3 else {
        print("Error: device name required")
        exit(1)
    }
    let targetName = args[2]
    let devices = findOutputDevices()
    if let match = devices.first(where: { $0.1 == targetName }) {
        let status = setDefaultOutput(match.0)
        if status == 0 {
            print("OK")
        } else {
            print("ERROR: status=\\(status)")
            exit(1)
        }
    } else {
        print("ERROR: device '\\(targetName)' not found")
        exit(1)
    }
default:
    print("Unknown command: \\(command)")
    exit(1)
}
"""


# ---------------------------------------------------------------------------
# macOS: Swift-based CoreAudio helpers
# ---------------------------------------------------------------------------


def _get_swift_helper_path() -> Path:
    cache_dir = Path.home() / ".cache" / "toolscripts"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "audio-helper"


def _ensure_swift_helper() -> Path | None:
    if not shutil.which("swift"):
        return None
    helper = _get_swift_helper_path()
    source = helper.with_suffix(".swift")
    source.write_text(_SWIFT_AUDIO_TOOL)
    if not helper.exists() or source.stat().st_mtime > helper.stat().st_mtime:
        log.debug("compiling Swift audio helper...")
        result = subprocess.run(
            ["swiftc", "-O", "-o", str(helper), str(source)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log.debug("swiftc failed: %s", result.stderr)
            return None
    return helper


def _run_audio_helper(*args: str) -> str | None:
    helper = _ensure_swift_helper()
    if not helper:
        return None
    try:
        result = subprocess.run(
            [str(helper), *args],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _macos_get_default_output_name() -> str | None:
    out = _run_audio_helper("default")
    if out and "\t" in out:
        return out.split("\t", 1)[1]
    return None


def _macos_list_output_devices() -> list[str]:
    out = _run_audio_helper("list")
    if not out:
        return []
    names: list[str] = []
    for line in out.splitlines():
        if "\t" in line:
            names.append(line.split("\t", 1)[1])
    return names


def _macos_set_output_device(name: str) -> bool:
    out = _run_audio_helper("set-default", name)
    return out is not None and out.strip() == "OK"


# ---------------------------------------------------------------------------
# macOS: Background Music auto-launch
# ---------------------------------------------------------------------------


def _macos_ensure_background_music() -> None:
    """Launch Background Music app if it's installed but not running."""
    result = subprocess.run(
        ["pgrep", "-x", "Background Music"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return  # already running

    app_path = Path("/Applications/Background Music.app")
    if not app_path.exists():
        return

    log.info("launching Background Music app...")
    subprocess.Popen(
        ["open", str(app_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Give it a moment to initialize its audio device
    time.sleep(2)


# ---------------------------------------------------------------------------
# Output device restore guard
# ---------------------------------------------------------------------------

_restore_target: str | None = None


def _restore_output_device() -> None:
    """Restore the original output device. Called via atexit and signal handlers."""
    global _restore_target
    if _restore_target is None:
        return
    name = _restore_target
    _restore_target = None  # prevent double-restore
    with contextlib.suppress(Exception):
        if _macos_set_output_device(name):
            log.info("audio output restored → %s", name)
        else:
            log.warning("could not restore audio output to '%s'", name)


def _signal_handler(signum: int, frame: object) -> None:
    _restore_output_device()
    # Re-raise with default handler
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


# ---------------------------------------------------------------------------
# Platform audio input detection
# ---------------------------------------------------------------------------


def _list_macos_audio_devices() -> dict[int, str]:
    try:
        result = subprocess.run(
            ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return {}

    audio_devices: dict[int, str] = {}
    in_audio = False
    for line in result.stderr.splitlines():
        if "audio devices:" in line.lower():
            in_audio = True
            continue
        if in_audio:
            m = re.search(r"\[(\d+)]\s+(.+)", line)
            if m:
                audio_devices[int(m.group(1))] = m.group(2).strip()
    return audio_devices


def _is_virtual_audio(name: str) -> bool:
    lower = name.lower()
    return any(kw in lower for kw in VIRTUAL_AUDIO_KEYWORDS)


def _setup_macos_audio() -> list[str]:
    """Find a virtual audio device, switch output if needed, return ffmpeg args."""
    _macos_ensure_background_music()

    audio_devices = _list_macos_audio_devices()
    virtual: list[tuple[int, str]] = []
    for idx, name in audio_devices.items():
        if _is_virtual_audio(name):
            virtual.append((idx, name))

    if not virtual:
        log.error(
            "no virtual audio device found.\n"
            "  Install one of the following to record system audio on macOS:\n"
            "    • BlackHole:        brew install blackhole-2ch\n"
            "    • Background Music:  brew install --cask background-music\n\n"
            "  Then set it as the output device (or create a multi-output device)\n"
            "  in System Settings → Sound → Output."
        )
        sys.exit(1)

    current_output = _macos_get_default_output_name()
    virtual_names = {name.lower() for _, name in virtual}

    if current_output and current_output.lower() not in virtual_names:
        log.warning("current audio output: %s", current_output)
        target_name = virtual[0][1]
        log.info("switching audio output → %s", target_name)
        if _macos_set_output_device(target_name):
            log.info("audio output switched successfully")
            global _restore_target
            _restore_target = current_output
            # Register restore on normal exit and signals
            atexit.register(_restore_output_device)
            for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
                signal.signal(sig, _signal_handler)
            time.sleep(0.5)
        else:
            log.warning(
                "could not switch audio output automatically.\n"
                "  Please go to System Settings → Sound → Output\n"
                "  and select '%s' manually.",
                target_name,
            )

    device_idx, device_name = virtual[0]
    return ["-f", "avfoundation", "-i", f":{device_idx}:{device_name}"]


def _get_audio_input_args() -> list[str]:
    if is_linux():
        return ["-f", "pulse", "-i", "default"]
    if is_windows():
        return ["-f", "dshow", "-i", "audio=virtual-audio-capturer"]
    if is_macos():
        return _setup_macos_audio()
    log.error("unsupported platform for system audio recording")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------


def _print_elapsed(stop_event: threading.Event) -> None:
    start = time.monotonic()
    while not stop_event.is_set():
        elapsed = int(time.monotonic() - start)
        mm, ss = divmod(elapsed, 60)
        sys.stderr.write(f"\r  ⏺  recording... {mm:02d}:{ss:02d}")
        sys.stderr.flush()
        time.sleep(1)
    sys.stderr.write("\r  ✅  recording stopped            \n")
    sys.stderr.flush()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="audio-record",
        description="Record system audio (speakers output, not microphone). Press Enter to stop.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="recording.wav",
        help="output file path (default: recording.wav). Format inferred from extension.",
    )
    parser.add_argument(
        "-f",
        "--format",
        help="force ffmpeg output format (e.g. wav, mp3). By default inferred from file extension.",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="list available virtual audio devices and exit",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if args.list_devices:
        if is_macos():
            devices = _list_macos_audio_devices()
            current = _macos_get_default_output_name()
            for idx, name in devices.items():
                marker = " ← current" if name == current else ""
                virtual = "  (virtual)" if _is_virtual_audio(name) else ""
                print(f"  [{idx}] {name}{virtual}{marker}")
        else:
            print("device listing is only supported on macOS currently")
        return

    try:
        require("ffmpeg")
    except Exception as exc:
        log.error("%s", exc)
        sys.exit(1)

    output_path = Path(args.output).expanduser()
    input_args = _get_audio_input_args()

    cmd = ["ffmpeg", "-y", *input_args]
    if args.format:
        cmd += ["-f", args.format]
    cmd.append(str(output_path))

    log.info("recording system audio → %s", output_path)
    log.info("press Enter to stop recording")

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    stop_event = threading.Event()
    timer_thread = threading.Thread(target=_print_elapsed, args=(stop_event,), daemon=True)
    timer_thread.start()

    with contextlib.suppress(KeyboardInterrupt, EOFError):
        input()

    stop_event.set()
    timer_thread.join(timeout=2)

    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    _restore_output_device()

    if output_path.exists():
        size_kb = output_path.stat().st_size / 1024
        log.success("saved: %s (%.0f KB)", output_path, size_kb)
    else:
        log.error("recording failed — output file not created")
        sys.exit(1)


if __name__ == "__main__":
    main()
