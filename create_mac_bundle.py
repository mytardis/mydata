# MyData - easy data uploads to the MyTardis research data management system
#
# Copyright (c) 2012-2013, Monash e-Research Centre (Monash University,
# Australia). All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# In addition, redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
# -  Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# -  Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# -  Neither the name of the Monash University nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE. SEE THE GNU GENERAL PUBLIC LICENSE FOR MORE
# DETAILS.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  Enquiries: store.star.help@monash.edu

"""
A distutils script to make a standalone .app of MyData for
Mac OS X.  You can get py2app from https://pypi.python.org/pypi/py2app/.
Use this command to build the .app and collect the other needed files:

   python createMacBundle.py py2app

Traditionally, this script would be named setup.py
"""

import sys
sys.path.append('mydata')
from setuptools import setup
import MyDataVersionNumber as MyDataVersionNumber
import requests
import os
import pkgutil

from CreateCommitDef import run
run()

appName = "MyData"

resource_files=["media/MyData.icns", "media/favicon.ico",
                requests.certs.where()]

for iconFilesPath in ("media/png-normal/icons16x16",
                      "media/png-normal/icons24x24",
                      "media/png-hot/icons24x24"):
    for iconFile in os.listdir(os.path.join('mydata', iconFilesPath)):
        iconFilePath = os.path.join('mydata', iconFilesPath, iconFile)
        if os.path.isfile(iconFilePath):
            resource_file = (iconFilesPath, [iconFilePath])
            resource_files.append(resource_file)

mydataVersionNumberModulePath = \
    os.path.dirname(pkgutil.get_loader("mydata.MyDataVersionNumber").filename)

setup(
    options=dict(py2app=dict(
        arch='x86_64',
        plist=dict(
            CFBundleDevelopmentRegion="English",
            CFBundleDisplayName=appName,
            CFBundleExecutable=appName,
            CFBundleIconFile="MyData.icns",
            CFBundleIdentifier="org.mytardis.MyData",
            CFBundleName=appName,
            CFBundlePackageType="APPL",
            CFBundleVersion="Version " + MyDataVersionNumber.versionNumber,
            LSArchitecturePriority=["x86_64"]
            )
        )
    ),
    data_files=resource_files,
    name=appName,
    setup_requires=["py2app"],
    app=['mydata/MyData.py']
)
