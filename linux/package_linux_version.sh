#!/bin/bash

# Utility for packaging the Linux version of the installer.
#
# You may have to change PYINSTALLERDIR to point to the directory where
# pyinstaller was unpacked.

PYINSTALLERDIR=`pwd`/../pyinstaller

set -o nounset
set -e

# Ensure latest commit hash is recorded, so that
# it is available in the About dialog when MyData
# is frozen into a platform-specific bundle:
python mydata/__init__.py

VERSION=`grep '^__version__' ../mydata/__init__.py | cut -f 2 -d '"'`
ARCHITECTURE=`uname -m | sed s/x86_64/amd64/g | sed s/i686/i386/g`

rm -fr dist

# PyInstaller 2.1
PATHS=`python -c 'import appdirs ; import os ; print os.path.dirname(appdirs.__file__)'`
python ${PYINSTALLERDIR}/pyinstaller.py --paths=$PATHS --name=MyData --icon=../mydata/media/MyData.ico --windowed ../run.py

cp "MyData.desktop" 	dist/MyData/
cp MyData.sh 		dist/MyData/
cp README_LINUX dist/MyData/

mkdir dist/MyData/media
cp -r ../mydata/media/* dist/MyData/media/

cp `python -c 'import requests; print requests.certs.where()'` dist/MyData/

mkdir dist/MyData-${VERSION}_${ARCHITECTURE}
cp MyData.sh    dist/MyData-${VERSION}_${ARCHITECTURE}
mv dist/MyData dist/MyData-${VERSION}_${ARCHITECTURE}/bin

cd dist
tar zcf MyData_v${VERSION}_${ARCHITECTURE}.tar.gz MyData-${VERSION}_${ARCHITECTURE}
cd ..

ls -lh dist/MyData_v${VERSION}_${ARCHITECTURE}.tar.gz

