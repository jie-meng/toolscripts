import sys
from datetime import datetime

def convert_timestamp_to_date(milliseconds):
    """将毫秒时间戳转换为当前时区的日期和时间。"""
    seconds = int(milliseconds) / 1000
    dt = datetime.fromtimestamp(seconds)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python timestamp2date.py <milliseconds>")
        sys.exit(1)

    milliseconds = sys.argv[1]
    date_str = convert_timestamp_to_date(milliseconds)
    print(date_str)

