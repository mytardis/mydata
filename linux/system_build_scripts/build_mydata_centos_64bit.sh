#!/bin/bash

if [ $# -lt 1 ]; then
    echo "Usage: build_mydata_centos_64bit.sh <build_directory>"
    exit 1
fi

#WDIR=${HOME}/${1}
WDIR=${1}

if [ -d $WDIR ]; then
    echo "Error: Please remove the existing \"$WDIR\" directory. It will be created automatically."
    exit 1
fi

mkdir $WDIR
cd $WDIR

git clone --recursive git@github.com:mytardis/mydata.git
if [ $? -ne 0 ]; then
    echo ""
    echo "*** Attempting to use git with SSH keys failed. ***"
    echo "*** Cloning the Launcher's repository as read-only instead. ***"
    echo ""
    git clone --recursive git://github.com/mytardis/mydata
fi
cd mydata

module load python wxwidgets
./package_centos_version.sh

