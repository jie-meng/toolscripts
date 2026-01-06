#!/usr/bin/env python
import sys
import os

if len(sys.argv) < 2:
    print("Error: Please provide a filter parameter")
    print("Usage: python ios_log.py <filter_parameter>")
    sys.exit(1)

filter_pattern = sys.argv[1]

cmd = f'xcrun simctl spawn booted log stream --level debug --style compact | grep "{filter_pattern}"'
os.system(cmd)
