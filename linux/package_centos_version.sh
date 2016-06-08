#!/bin/bash

SRC=`pwd`

VERSION=`grep '^__version__' ../mydata/__init__.py | cut -f 2 -d '"'`
ARCHITECTURE=`uname -m | sed s/x86_64/amd64/g | sed s/i686/i386/g`

./package_linux_version.sh

mkdir -p rpmbuild
cd rpmbuild

rm -fr BUILD BUILDROOT RPMS SOURCES SRPMS tmp
mkdir  BUILD BUILDROOT RPMS SOURCES SRPMS tmp

rm -f ~/.rpmmacros
echo "%_topdir  "`pwd`     >> ~/.rpmmacros
echo "%_tmppath "`pwd`/tmp >> ~/.rpmmacros


sed s/VERSION/${VERSION}/g SPECS/MyData.spec.template > SPECS/MyData.spec

if [ "$ARCHITECTURE" == "amd64" ]
then
    sed -i s/libc.so.6\(GLIBC_PRIVATE\)/libc.so.6\(GLIBC_PRIVATE\)\(64bit\)/g SPECS/MyData.spec
fi

rm -fr mydata-${VERSION}

mkdir -p mydata-${VERSION}/opt/MyData
mkdir -p mydata-${VERSION}/usr/share/applications
rm -f mydata-${VERSION}.tar.gz SOURCES/mydata-${VERSION}.tar.gz 

cp ../MyData.desktop mydata-${VERSION}/usr/share/applications/
cp -r ../dist/MyData-${VERSION}_${ARCHITECTURE}/* mydata-${VERSION}/opt/MyData

tar zcf mydata-${VERSION}.tar.gz mydata-${VERSION}
cp mydata-${VERSION}.tar.gz SOURCES/

rpmbuild -ba SPECS/MyData.spec
cd ..

find rpmbuild/ -iname '*rpm' -exec ls -lh {} \;


