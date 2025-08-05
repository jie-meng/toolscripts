import os
import sys

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
