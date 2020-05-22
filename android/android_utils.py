import os

def selectAdbDevice():
    p = os.popen('adb devices')
    output = p.read()
    devices = list(map(lambda line: line.split('\t')[0], filter(lambda x: x.endswith('device'), output.split('\n'))))

    if len(devices) == 0:
        print('No device found')
        return None
    elif len(devices) == 1:
        print('{0} selected.\n'.format(devices[0]))
        return devices[0]

    print('Please select device:')

    idx = 1
    for a in devices:
        print('{0}. {1}'.format(idx, a))
        idx += 1

    selection = int(input())
    device = devices[int(selection) - 1]
    print('{0} selected.\n'.format(device))

    return device
