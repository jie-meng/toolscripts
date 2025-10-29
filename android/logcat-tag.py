import os
import sys
from android_utils import select_device


def select_process(device):
    application_id = input('please input applicationId: ')
    if len(application_id) == 0:
        return ''

    pid_info = ''
    p = os.popen('adb -s {0} shell ps'.format(device))
    output = p.read()
    process_lines = list(filter(
        lambda x: application_id in x, output.split('\n')))
    for process_line in process_lines:
        format_line = '\t'.join(process_line.split())
        items = format_line.split('\t')
        if len(items) >= 9 and items[8] == application_id:
            print('pid = {0}'.format(items[1]))
            pid_info = '--pid={0}'.format(items[1])
            break

    return pid_info


def main():
    device = select_device()
    if device is None:
        print('No device connected.')
        sys.exit(-1)

    print('{0} selected.\n'.format(device))

    process_info = select_process(device)
    print('please input args: (e.g. TAG1:I TAG2:D *:S)')
    args = input().strip()

    if len(args) != 0:
        args = '"{0}"'.format(args)

    command = 'adb -s {0} logcat -c && adb -s {0} logcat {1} {2}'.format(
        device, process_info, args)
    print(command)
    os.system(command)


if __name__ == "__main__":
    main()
