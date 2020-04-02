import os
import sys

p = os.popen('emulator -list-avds')
output = p.read()
avds = list(filter(lambda x: x.strip() != '', output.split('\n')))

if len(avds) == 0:
    print('No emulator')
    sys.exit(0)

print('Please select emulator:')

idx = 1
for a in avds:
    print('{0}. {1}'.format(idx, a))
    idx += 1

selection = int(input())
emulator = avds[int(selection) - 1]

print('{0} selected.\n'.format(emulator))

print('start with -writable-system? (y/n)')
writable_system = ''
ans = input()
if ans.lower().startswith('y'):
    writable_system = '-writable-system'

os.system('emulator -avd {0} {1}'.format(emulator, writable_system))
