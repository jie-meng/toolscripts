#!/bin/sh

set -e
DIR=$(dirname $0)

if [ $# -ne 1 ]; then
    echo "Usage: $0 'YYYY-MM-DDTHH:MM:SS.fff'"
    exit 1
fi

python ${DIR}/../time/date2timestamp.py $1

