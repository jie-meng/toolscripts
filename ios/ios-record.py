import time
import subprocess
import os
import signal


def main():
    # Get the current timestamp in the format YYYYMMDD_hhmmss
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_file = f"ios-video-{timestamp}.mp4"  # Relative path

    # Start screen recording
    print("Starting screen recording on the booted simulator...")
    record_process = subprocess.Popen(
        ['xcrun', 'simctl', 'io', 'booted', 'recordVideo', video_file]
    )

    input("Press Enter to stop recording.")

    # Stop screen recording by sending SIGINT
    os.kill(record_process.pid, signal.SIGINT)
    record_process.wait()

    print(f"Video file saved as: {os.path.abspath(video_file)}")
    print("Done.")


if __name__ == "__main__":
    main()
