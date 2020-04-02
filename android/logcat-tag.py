import os
import sys

def select_device():
    p = os.popen('adb devices')
    output = p.read()
    device_lines = filter(lambda x: '\t' in x, output.split('\n'))
    devices = list(map(lambda x: x.split('\t')[0], device_lines))

    if len(devices) == 0:
        return None

    if len(devices) == 1:
        return devices[0]

    print('Please select emulator:')

    idx = 1
    for a in devices:
        print('{0}. {1}'.format(idx, a))
        idx += 1

    selection = int(input())
    if selection < 1 or selection > len(devices):
        print('Invalid selection')
        sys.exit(-1)

    return devices[selection - 1]

def main():
    device = select_device()
    if device == None:
        print('No device connected.')
        sys.exit(-1)

    print('{0} selected.\n'.format(device))

    args = ''
    if len(sys.argv) > 1:
        args = ' '.join(sys.argv[1:])
    else:
        print('please input args: (e.g. TAG1:I TAG2:D *:S)')
        args = input().strip()

    os.system('adb -s {0} logcat -c && adb -s {0} logcat "{1}"'.format(device, args))

if __name__ == "__main__":
    main()
