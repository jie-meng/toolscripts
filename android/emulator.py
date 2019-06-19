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

selection = input()
os.system('emulator -avd {0}'.format(avds[int(selection) - 1]))
