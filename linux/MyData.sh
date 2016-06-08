#!/bin/bash

MYDATA_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ -f MyData ]; then
  LD_LIBRARY_PATH="${MYDATA_DIR}":$LD_LIBRARY_PATH
  "${MYDATA_DIR}"/MyData
elif [ -f bin/MyData ]; then
  LD_LIBRARY_PATH="${MYDATA_DIR}/bin":$LD_LIBRARY_PATH
  "${MYDATA_DIR}"/bin/MyData
else
  echo "ERROR: Cannot find MyData."
fi

