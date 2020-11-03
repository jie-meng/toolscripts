#!/bin/sh

set -e
DIR=$(dirname $0)

python3 ${DIR}/../image/kindle-pdf-cropper.py $@
