import os
import sys
import subprocess
from android_utils import select_device


def send_text_to_device(device_id, text):
    """
    Send a text string to the specified Android device.
    """
    print(f"Sending text to device {device_id}: {text}")
    result = subprocess.run(
        ['adb', '-s', device_id, 'shell', 'input', 'text', text],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    if result.returncode == 0:
        print("Text input successfully.")
    else:
        print(f"Failed to input text. Error: {result.stderr.decode('utf-8')}")


def main():
    selected_device = select_device()
    if not selected_device:
        print("No device selected.")
        sys.exit(-1)

    text_to_send = input("Enter the text to send: ")

    send_text_to_device(selected_device, text_to_send)


if __name__ == "__main__":
    main()
