import os
import sys

def main():
    args = ''
    if len(sys.argv) > 1:
        args = ' '.join(sys.argv[1:])
    else:
        print('please input args: (e.g. TAG1:I TAG2:D *:S)')
        args = input().strip()

    os.system('adb logcat -c && adb logcat "{0}"'.format(args))

if __name__ == "__main__":
    main()
