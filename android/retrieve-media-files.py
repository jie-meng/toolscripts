#!/usr/bin/env python3

import os
import sys
import subprocess
from android_utils import select_device


def pull_files(device, remote_dir, local_dir, pattern_filter):
    result = subprocess.getoutput(f"adb -s {device} shell ls {remote_dir}")
    items = result.split("\n")
    items = list(filter(lambda x: pattern_filter(x), items))
    items.sort(reverse=True)

    print(f"\nFound {len(items)} files matching pattern.")
    try:
        count = int(input("How many files to retrieve (latest)?\n"))
    except ValueError:
        print("Invalid number.")
        return

    files = items[:count]

    for f in files:
        src = f"{remote_dir}/{f}"
        dst = f"{local_dir}/{f}"
        print(f"Pulling: {f}")
        os.system(f'adb -s {device} pull "{src}" "{dst}"')


def main():
    selected_device = select_device()
    if not selected_device:
        print("No device selected.")
        sys.exit(-1)

    print("Select media type:")
    print("1. Image (jpg/png from DCIM/Camera)")
    print("2. Video (mp4 from DCIM/Camera)")
    print("3. Screen recording (mp4 from DCIM/ScreenRecorder)")

    choice = input("\nEnter choice (1/2/3): ").strip()

    if choice == "1":
        pull_files(
            selected_device,
            "/sdcard/DCIM/Camera",
            "./",
            lambda x: x.startswith("IMG_") and x.endswith((".jpg", ".png")),
        )
    elif choice == "2":
        pull_files(
            selected_device,
            "/sdcard/DCIM/Camera",
            "./",
            lambda x: x.startswith("VID_") and x.endswith(".mp4"),
        )
    elif choice == "3":
        pull_files(
            selected_device,
            "/sdcard/DCIM/ScreenRecorder",
            "./",
            lambda x: x.endswith(".mp4"),
        )
    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()
