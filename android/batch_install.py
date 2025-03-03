#!/usr/bin/env python3
import subprocess
import re
import os
import json
import sys


def exit_with_error(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


# Check that a JSON mapping filename is provided as the first parameter.
if len(sys.argv) < 2:
    exit_with_error("Please provide a JSON mapping filename as the first argument.")

mapping_filename = sys.argv[1]

# Verify mapping file exists.
if not os.path.exists(mapping_filename):
    exit_with_error(f"Mapping file '{mapping_filename}' not found.")


def get_adb_devices():
    """Get a list of valid adb device IDs (status must be 'device')."""
    try:
        output = subprocess.check_output(["adb", "devices"], encoding="utf-8")
    except subprocess.CalledProcessError:
        exit_with_error("Failed to run 'adb devices'.")
    devices = []
    for line in output.strip().splitlines():
        # Skip header or empty lines.
        if line.startswith("List of devices attached") or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def load_device_mapping(filename):
    """Load the device mapping JSON file. Expected format: an array of objects
    each having keys "deviceName" and "apkRegex". Returns a lookup dict."""
    with open(filename, "r", encoding="utf-8") as f:
        mapping_list = json.load(f)
    # Build a lookup mapping: key=deviceName, value=apkRegex.
    lookup = {}
    for entry in mapping_list:
        dn = entry.get("deviceName")
        ar = entry.get("apkRegex")
        if dn and ar:
            lookup[dn] = ar
    return lookup


def find_apk_file(apk_regex):
    """Search for the first APK file in the current directory that fully matches the
    provided regular expression pattern."""
    pattern = re.compile(apk_regex)
    for file in os.listdir("."):
        if file.endswith(".apk") and pattern.fullmatch(file):
            return file
    return None


def install_apk_on_device(device, apk_file):
    """Install the given APK file on the specified device using adb."""
    print(f"Installing APK '{apk_file}' on device '{device}'...")
    result = subprocess.run(["adb", "-s", device, "install", apk_file])
    if result.returncode == 0:
        print(f"Installation succeeded on device '{device}'.")
    else:
        print(f"Installation failed on device '{device}'.")


def main():
    devices = get_adb_devices()
    if not devices:
        exit_with_error("No valid adb devices found.")

    mapping_lookup = load_device_mapping(mapping_filename)

    for device in devices:
        print(f"Processing device: {device}")
        # Check if there is a mapping for this device.
        if device not in mapping_lookup:
            print(f"No mapping found for device '{device}', skipping...")
            continue
        apk_regex = mapping_lookup[device]
        apk_file = find_apk_file(apk_regex)
        if not apk_file:
            print(f"No APK file found matching regex '{apk_regex}' for device '{device}'.")
            continue
        install_apk_on_device(device, apk_file)

    print("done")


if __name__ == "__main__":
    main()
