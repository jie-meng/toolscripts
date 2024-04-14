#!/bin/sh

set -e
DIR=$(dirname $0)

# 确保传递了参数
if [ $# -ne 1 ]; then
    echo "Usage: $0 <milliseconds>"
    exit 1
fi

python ${DIR}/../time/timestamp2date.py $1

