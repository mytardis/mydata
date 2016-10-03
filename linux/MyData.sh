#!/bin/bash

MYDATA_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PATH=/sbin:$PATH
LD_LIBRARY_PATH="${MYDATA_DIR}/bin":$LD_LIBRARY_PATH
nice -n 15 "${MYDATA_DIR}"/bin/MyData
