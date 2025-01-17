import os
import sys
import subprocess


def select_device():
    """
    Select an Android device from the list of connected devices.
    """
    p = os.popen('adb devices')
    output = p.read()
    device_lines = filter(lambda x: '\t' in x, output.split('\n'))
    devices = list(map(lambda x: x.split('\t')[0], device_lines))

    if len(devices) == 0:
        print('No devices found.')
        sys.exit(-1)

    if len(devices) == 1:
        return devices[0]

    print('Please select device:')

    idx = 1
    for a in devices:
        print('{0}. {1}'.format(idx, a))
        idx += 1

    try:
        selection = int(input("Enter the number of the device: "))
        if selection < 1 or selection > len(devices):
            raise ValueError("Invalid selection")
    except ValueError as e:
        print(e)
        sys.exit(-1)

    return devices[selection - 1]


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
