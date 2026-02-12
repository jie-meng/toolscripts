from datetime import datetime

if __name__ == "__main__":
    now = datetime.now()
    timestamp = int(now.timestamp() * 1000)
    print(f"Current time: {now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}")
    print(f"Timestamp:    {timestamp}")
