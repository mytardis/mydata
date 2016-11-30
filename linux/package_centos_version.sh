#!/bin/bash

VERSION=$(grep '^__version__' ../mydata/__init__.py | cut -f 2 -d '"')
RPM_VERSION=$(echo ${VERSION} | tr -d '-')
ARCHITECTURE=$(uname -m | sed s/x86_64/amd64/g | sed s/i686/i386/g)

./package_linux_version.sh

rm -fr rpmbuild
mkdir -p rpmbuild
cd rpmbuild
mkdir  BUILD BUILDROOT RPMS SOURCES SPECS SRPMS tmp

rm -f ~/.rpmmacros
echo "%_topdir  "$(pwd)     >> ~/.rpmmacros
echo "%_tmppath "$(pwd)/tmp >> ~/.rpmmacros

sed s/VERSION/${RPM_VERSION}/g ../mydata.spec.template > SPECS/mydata.spec

if [ "$ARCHITECTURE" == "amd64" ]
then
    sed -i s/libc.so.6\(GLIBC_PRIVATE\)/libc.so.6\(GLIBC_PRIVATE\)\(64bit\)/g SPECS/mydata.spec
fi

rm -fr mydata-${RPM_VERSION}

mkdir -p mydata-${RPM_VERSION}/opt/mydata
mkdir -p mydata-${RPM_VERSION}/usr/share/applications
rm -f mydata-${RPM_VERSION}.tar.gz SOURCES/mydata-${RPM_VERSION}.tar.gz 

cp ../MyData.desktop mydata-${RPM_VERSION}/usr/share/applications/
cp -r ../dist/MyData-${VERSION}_${ARCHITECTURE}/* mydata-${RPM_VERSION}/opt/mydata

tar zcf mydata-${RPM_VERSION}.tar.gz mydata-${RPM_VERSION}
cp mydata-${RPM_VERSION}.tar.gz SOURCES/

rpmbuild -ba SPECS/mydata.spec
cd ..

find rpmbuild/ -iname '*rpm' -exec ls -lh {} \;


