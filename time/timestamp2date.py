import sys
from datetime import datetime, timedelta

def convert_timestamp_to_date(milliseconds):
    """Converts a millisecond timestamp into the current timezone's date and time, including milliseconds."""
    # Convert milliseconds to seconds and separate the integer part for seconds
    seconds = int(milliseconds) // 1000
    # Calculate the remainder of milliseconds and convert to microseconds
    microseconds = (int(milliseconds) % 1000) * 1000
    # Create a datetime object, then add the microsecond part
    dt = datetime.fromtimestamp(seconds) + timedelta(microseconds=microseconds)
    # Format output to include milliseconds
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python timestamp2date.py <milliseconds>")
        sys.exit(1)

    milliseconds = sys.argv[1]
    date_str = convert_timestamp_to_date(milliseconds)
    print(date_str)
