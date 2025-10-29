import os
import sys
from android_utils import select_device

def main():
    selected_device = select_device()
    if not selected_device:
        print("No device selected.")
        sys.exit(-1)

    if len(sys.argv) > 1:
        deeplink = sys.argv[1].strip()
    else:
        deeplink = input("Enter the deeplink URL: ").strip()
    if not deeplink:
        print("No deeplink entered.")
        sys.exit(-1)

    cmd = f'adb -s {selected_device} shell am start -d "{deeplink}"'
    print(f"Executing: {cmd}")
    ret = os.system(cmd)
    if ret == 0:
        print("Deeplink launched successfully.")
    else:
        print(f"Failed to launch deeplink. Error: {ret}")

if __name__ == "__main__":
    main()
