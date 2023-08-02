"""https://gs.statcounter.com/"""

import csv
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import os

def get_file_path():
    file_path = input("请输入CSV文件的路径（可以是绝对路径或相对路径）：").strip()
    return os.path.abspath(file_path)


def get_min_version():
    while True:
        min_version_input = input("请输入最低的大版本号，低于此版本的将被归入 'Other' 类别：").strip()
        if min_version_input.isdigit():
            return int(min_version_input)
        else:
            print("错误：请输入一个有效的数字版本号。请重新输入。")


def get_percentage_threshold():
    while True:
        percentage_threshold_input = input("请输入占比阈值（默认为0.1，按回车使用默认值）：").strip()
        if not percentage_threshold_input:
            return 0.1
        try:
            percentage_threshold = float(percentage_threshold_input)
            if 0 <= percentage_threshold <= 100:
                return percentage_threshold
            else:
                print("错误：占比阈值必须在0到100之间。请重新输入。")
        except ValueError:
            print("错误：请输入一个有效的数字。请重新输入。")


def read_data(file_path, min_version, percentage_threshold):
    ios_versions = defaultdict(float)
    with open(file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        title = next(reader)[1]
        for row in reader:
            version, percentage = row
            version_number = re.findall(r'\d+\.\d+|\d+', version)
            major_version = version_number[0].split('.')[0] if version_number else version

            if float(percentage) < percentage_threshold or (major_version.isdigit() and int(major_version) < int(min_version)):
                major_version = 'Other'

            ios_versions[major_version] += float(percentage)

    return ios_versions, title


def draw_pie_chart(ios_versions, title):
    def version_sort_key(v):
        return int(v) if v.isdigit() else float('inf')

    versions = sorted(ios_versions.keys(), key=version_sort_key)
    percentages = [ios_versions[v] for v in versions]

    fig, ax = plt.subplots()
    ax.pie(percentages, labels=versions, autopct='%1.1f%%', startangle=90)
    plt.title(title, y=1.08)
    plt.axis('equal')
    plt.subplots_adjust(top=0.85)
    plt.show()


if __name__ == "__main__":
    file_path = get_file_path()
    if not os.path.exists(file_path):
        print("文件不存在，请检查路径。")
        exit()

    min_version = get_min_version()
    percentage_threshold = get_percentage_threshold()
    ios_versions, title = read_data(file_path, min_version, percentage_threshold)
    draw_pie_chart(ios_versions, title)
