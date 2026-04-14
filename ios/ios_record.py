#!/usr/bin/env python3
import json
import subprocess
import os
import signal
import sys
import time

RED = "\033[0;31m"
GREEN = "\033[0;32m"
NC = "\033[0m"


def compress_video(input_file, quality=1):
    """Compress video with ffmpeg. quality: 1=low, 2=medium, 3=high."""
    if quality == 1:
        crf, preset = 28, "fast"
    elif quality == 2:
        crf, preset = 23, "medium"
    else:
        crf, preset = 18, "slow"

    base, _ = os.path.splitext(input_file)
    output_file = f"{base}_compressed.mp4"

    print(f"Compressing video (quality={quality})...")
    ret = os.system(
        f'ffmpeg -i "{input_file}" -c:v libx264 -crf {crf} -preset {preset} -c:a aac -movflags +faststart "{output_file}"'
    )
    if ret == 0:
        orig_size = os.path.getsize(input_file) / (1024 * 1024)
        comp_size = os.path.getsize(output_file) / (1024 * 1024)
        print(f"{GREEN}Compressed: {orig_size:.1f}MB -> {comp_size:.1f}MB{NC}")
        print(f"Output: {output_file}")
    else:
        print(f"Compression failed.")


def get_booted_simulator():
    """Return (udid, name) of the first booted simulator, or (None, None)."""
    try:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "booted", "-j"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        for devices in data.get("devices", {}).values():
            for dev in devices:
                if dev.get("state") == "Booted":
                    return dev["udid"], dev.get("name", "Unknown")
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        pass
    return None, None


def main():
    udid, sim_name = get_booted_simulator()
    if not udid:
        print(f"{RED}Error: No booted iOS simulator found.{NC}", file=sys.stderr)
        print(
            "Start a simulator first: xcrun simctl boot <device-udid>", file=sys.stderr
        )
        sys.exit(1)

    print(f"Found booted simulator: {GREEN}{sim_name}{NC} ({udid})")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_file = os.path.abspath(f"ios-video-{timestamp}.mp4")

    record_process = subprocess.Popen(
        ["xcrun", "simctl", "io", udid, "recordVideo", "--force", video_file],
        stderr=subprocess.PIPE,
    )

    # simctl writes "Recording started" to stderr once ready; wait for it.
    assert record_process.stderr is not None
    stderr_lines = []
    try:
        for line in record_process.stderr:
            text = line.decode(errors="replace").strip()
            if "Recording started" in text:
                break
            if text:
                stderr_lines.append(text)
        else:
            if record_process.poll() is not None:
                for l in stderr_lines:
                    print(f"{RED}{l}{NC}", file=sys.stderr)
                print(
                    f"{RED}Error: simctl exited without starting recording.{NC}",
                    file=sys.stderr,
                )
                sys.exit(1)
    except KeyboardInterrupt:
        record_process.kill()
        record_process.wait()
        sys.exit(130)

    print(f"{GREEN}Recording... Press Enter or Ctrl-C to stop.{NC}")

    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass

    os.kill(record_process.pid, signal.SIGINT)
    record_process.wait()

    print(f"{GREEN}Video saved: {video_file}{NC}")
    size_mb = os.path.getsize(video_file) / (1024 * 1024)
    print(f"Size: {size_mb:.1f} MB")

    response = input("Compress video? (Y/n, default Y, quality 1): ").strip().lower()
    if response in ("", "y"):
        compress_video(video_file, quality=1)


if __name__ == "__main__":
    main()
