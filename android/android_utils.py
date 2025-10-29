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
