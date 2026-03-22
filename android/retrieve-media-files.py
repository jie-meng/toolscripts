#!/usr/bin/env python3

import os
import sys
import subprocess


def pull_files(remote_dir, local_dir, pattern_filter):
    result = subprocess.getoutput(f"adb shell ls {remote_dir}")
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
        os.system(f'adb pull "{src}" "{dst}"')


def main():
    print("Select media type:")
    print("1. Image (jpg/png from DCIM/Camera)")
    print("2. Video (mp4 from DCIM/Camera)")
    print("3. Screen recording (mp4 from DCIM/ScreenRecorder)")

    choice = input("\nEnter choice (1/2/3): ").strip()

    if choice == "1":
        pull_files("/sdcard/DCIM/Camera", "./", lambda x: x.endswith((".jpg", ".png")))
    elif choice == "2":
        pull_files("/sdcard/DCIM/Camera", "./", lambda x: x.endswith(".mp4"))
    elif choice == "3":
        pull_files("/sdcard/DCIM/ScreenRecorder", "./", lambda x: x.endswith(".mp4"))
    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()
