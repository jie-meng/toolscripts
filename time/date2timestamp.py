import sys
from datetime import datetime

def convert_date_to_timestamp(date_str):
    """Converts a date string in the format 'YYYY-MM-DD HH:MM:SS.fff' to a millisecond timestamp."""
    # Parse the date string to a datetime object
    dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
    # Convert the datetime object to a timestamp in milliseconds
    timestamp = int(dt.timestamp() * 1000)
    return timestamp

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python date2timestamp.py 'YYYY-MM-DD HH:MM:SS.fff'")
        sys.exit(1)

    date_str = sys.argv[1]
    timestamp = convert_date_to_timestamp(date_str)
    print(timestamp)

