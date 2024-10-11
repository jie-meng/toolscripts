import os
import sys
import time
import subprocess


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

    # Get the current timestamp in the format YYYYMMDD_hhmmss
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_file = f"/sdcard/video-{timestamp}.mp4"

    # Start screen recording
    print(f"Starting screen recording on device {selected_device}...")
    record_process = subprocess.Popen(
        ['adb', '-s', selected_device, 'shell', 'screenrecord', video_file])

    input("Press Enter to stop recording.")

    # Stop screen recording
    record_process.terminate()
    record_process.wait()

    # Wait 2 seconds to ensure the recording is stopped
    print("Stopping recording...")
    time.sleep(2)

    # Pull the recorded video to the current directory
    local_file = f"video-{timestamp}.mp4"
    print(
        f"Pulling the video file {video_file} to the current directory as {local_file}...")
    ret = os.system(f"adb -s {selected_device} pull {video_file} {local_file}")
    if ret == 0:
        print(f"Video file downloaded successfully: {local_file}")
    else:
        print(f"Failed to download video file. Error: {ret}")

    # Delete the video file from the device
    print(f"Deleting the video file {video_file} from the device...")
    os.system(f"adb -s {selected_device} shell rm {video_file}")

    print("Done.")

if __name__ == "__main__":
    main()
