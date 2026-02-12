import sys
from datetime import datetime, timedelta

def calculate_offset(days):
    """Calculate the timestamp offset from now by given days."""
    now = datetime.now()
    target = now + timedelta(days=days)
    timestamp = int(target.timestamp() * 1000)
    return timestamp, target

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python timestamp_offset.py <days>")
        sys.exit(1)

    try:
        days = int(sys.argv[1])
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid integer")
        sys.exit(1)

    timestamp, target = calculate_offset(days)
    print(f"Days offset: {days:+d}")
    print(f"Target time: {target.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}")
    print(f"Timestamp:   {timestamp}")
