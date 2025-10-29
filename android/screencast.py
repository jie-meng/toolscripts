import os
import sys
import subprocess
from android_utils import select_device

def main():
    selected_device = select_device()
    if not selected_device:
        print("No device selected.")
        sys.exit(-1)

    # Launch scrcpy with the selected device
    print(f"Launching scrcpy for device {selected_device}...")
    try:
        subprocess.run(['scrcpy', '-s', selected_device], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to launch scrcpy. Error: {e}")

if __name__ == "__main__":
    main()
