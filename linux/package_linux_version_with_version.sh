#!/bin/sh
VERSION=$(grep '^__version__' ../mydata/__init__.py | cut -f 2 -d '"')
ARCHITECTURE=$(uname -m | sed s/x86_64/amd64/g | sed s/i686/i386/g)

./package_linux_version.sh $VERSION $ARCHITECTURE
