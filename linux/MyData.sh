#!/bin/bash

MYDATA_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

LD_LIBRARY_PATH="${MYDATA_DIR}/bin":$LD_LIBRARY_PATH
"${MYDATA_DIR}"/bin/MyData

