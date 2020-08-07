r"""
setup.py

RUNNING TESTS
=============
Run tests with:

    python setup.py nosetests


BUILDING BINARIES
=================
Build a binary executable with:

    python setup.py build

Build a binary distributable (Setup Wizard / DMG / RPM) with:

    python setup.py bdist


SIGNING BINARIES
================

Windows
-------

MyData authors don't sign Windows builds themselves, due to a local I.T. policy
which requires signing to be done by a different I.T. team.

If you have a code-signing certificate, you can sign the resulting build, using
signtool.exe as described here:

    https://msdn.microsoft.com/en-us/library/windows/desktop/aa388170.aspx


Mac OS X
--------

Mac builds are signed automatically, provided that you have a valid
"Develper ID: Application" certificate in your KeyChain.  For further
information, see: setup_helpers/mac_signing.py


Linux
-----

Linux builds are not signed at present, but they can be signed by modifying the
rpmbuild command in linux/package_centos_version.sh to use the --sign option,
as described here:

    http://ftp.rpm.org/max-rpm/rpmbuild.8.html

"""
from __future__ import print_function

import os
import sys
import tempfile
import subprocess
import shutil

from distutils.command.build import build
from distutils.command.bdist import bdist
from distutils.command.install import install
import distutils.dir_util

import PyInstaller.__main__

import requests
from setuptools import setup

# Ensure latest commit hash is recorded, so that
# it is available in the About dialog when MyData
# is frozen into a platform-specific bundle:
import mydata


APP_NAME = "MyData"
APP_VERSION = mydata.__version__
COMPANY_NAME = "Monash University"
PACKAGE_NAME = "mydata"

SETUP_REQUIRES = ["nose", "coverage"]


class CustomBuildCommand(build):
    """
    Custom "python setup.py build" command

    On Windows, create dist/MyData/*.*, including dist/MyData/MyData.exe
    On macOS, create dist/MyData.app/*
    On macOS, copy "MyData Notifications.app", add-loginitem, delete-loginitem,
        and loginitem-exists binaries into MyData.app bundle.
    """
    def run(self):
        """
        Custom "python setup.py build" command

        On Windows, create dist/MyData/*.*, including dist/MyData/MyData.exe
        On macOS, create dist/MyData.app/*
        """
        if sys.platform.startswith("win"):
            sys.stdout.write(
                "Creating dist/MyData.exe using PyInstaller...\n")
            if os.path.exists("build"):
                shutil.rmtree("build")
                os.mkdir("build")
            if os.path.exists("dist"):
                shutil.rmtree("dist")
                os.mkdir("dist")
            if not os.path.exists("dist/MyData"):
                os.makedirs("dist/MyData")
            if not os.path.exists("dist/MyData-console"):
                os.makedirs("dist/MyData-console")
            pyinstallerArgs = [
                '--name=MyData',
                '--icon=mydata/media/MyData.ico',
                '--windowed',
                '--noconfirm',
                'run.py',
                ]
            PyInstaller.__main__.run(pyinstallerArgs)
            pyinstallerArgs = [
                '--name=MyData-console',
                '--icon=mydata/media/MyData.ico',
                '--console',
                '--noconfirm',
                'run.py',
                ]
            PyInstaller.__main__.run(pyinstallerArgs)

            os.system(r"COPY /Y dist\MyData-console\MyData-console.exe "
                      r"dist\MyData\MyData.com")

            # favicon.ico and MyData.ico are really the same thing. favicon.ico
            # is the original from the MyTardis repository, and MyData.ico is
            # the result of converting it to PNG and then back to ICO, which
            # fixed a problem with the Windows build.

            for build_name in ("MyData", "MyData-console"):
                if not os.path.exists("dist/%s/media" % build_name):
                    os.makedirs("dist/%s/media" % build_name)
                os.system(r"COPY /Y mydata\media\favicon.ico "
                          r"dist\%s\media" % build_name)
                os.system(r"COPY /Y mydata\media\MyData.ico "
                          r"dist\%s\media" % build_name)
                distutils.dir_util.copy_tree("mydata/media/Aha-Soft",
                                             "dist/%s/media/Aha-Soft" % build_name)
                distutils.dir_util.copy_tree("mydata/media/DRF",
                                             "dist/%s/media/DRF" % build_name)

                distutils.dir_util\
                    .copy_tree("resources/win64/openssh-7.3p1-cygwin-2.6.0",
                           "dist/%s/win64/openssh-7.3p1-cygwin-2.6.0" % build_name)
                cygwin64HomeDir = \
                    "dist/%s/win64/openssh-7.3p1-cygwin-2.6.0/home" % build_name
                for subdir in os.listdir(cygwin64HomeDir):
                    subdirpath = os.path.join(cygwin64HomeDir, subdir)
                    if os.path.isdir(subdirpath):
                        shutil.rmtree(subdirpath)
                distutils.dir_util.copy_tree(
                    "resources/win32/openssh-7.3p1-cygwin-2.8.0",
                    "dist/%s/win32/openssh-7.3p1-cygwin-2.8.0" % build_name)
                cygwin32HomeDir = \
                    "dist/%s/win32/openssh-7.3p1-cygwin-2.8.0/home" % build_name
                for subdir in os.listdir(cygwin32HomeDir):
                    subdirpath = os.path.join(cygwin32HomeDir, subdir)
                    if os.path.isdir(subdirpath):
                        shutil.rmtree(subdirpath)

                os.system(r"COPY /Y GPL.txt dist\%s" % build_name)

                cacert = requests.certs.where()
                os.system(r"COPY /Y %s dist\%s" % (cacert, build_name))
        elif sys.platform.startswith("darwin"):
            sys.stdout.write(
                "Creating dist/MyData.app using PyInstaller...\n")
            os.system("rm -fr build/*")
            os.system("rm -fr dist/*")
            with open("setup_templates/macOS/mac.spec.template",
                      'r') as macSpecTemplateFile:
                macSpecTemplate = macSpecTemplateFile.read()
            macSpec = macSpecTemplate \
                .replace("<MYDATA_REPO_PATH>", os.path.abspath(".")) \
                .replace("<MYDATA_RUNNER>", os.path.abspath("run.py")) \
                .replace("<APP_VERSION>", APP_VERSION)
            with open("MyData.spec", 'w') as macSpecFile:
                macSpecFile.write(macSpec)
            pyinstallerArgs = ['--windowed', 'MyData.spec']
            PyInstaller.__main__.run(pyinstallerArgs)

            resourceFiles = [
                (requests.certs.where(), ""),
                ("mydata/media/MyData.icns", ""),
                ("mydata/media/favicon.ico", "media"),
                ("mydata/media/Aha-Soft/LICENSE.txt", "media/Aha-Soft")
            ]

            for iconFilesPath in ("media/Aha-Soft/png-normal/icons16x16",
                                  "media/Aha-Soft/png-normal/icons24x24",
                                  "media/Aha-Soft/png-disabled/icons16x16",
                                  "media/Aha-Soft/png-disabled/icons24x24",
                                  "media/Aha-Soft/png-hot/icons24x24",
                                  "media/DRF"):
                for iconFile in os.listdir(os.path.join(PACKAGE_NAME,
                                                        iconFilesPath)):
                    iconFilePath = \
                        os.path.join(PACKAGE_NAME, iconFilesPath, iconFile)
                    if os.path.isfile(iconFilePath):
                        resourceFile = (iconFilePath, iconFilesPath)
                        resourceFiles.append(resourceFile)

            for resourceFile in resourceFiles:
                targetDir = os.path.join(
                    "dist", "%s.app" % APP_NAME, "Contents", "Resources",
                    resourceFile[1])
                if not os.path.exists(targetDir):
                    os.makedirs(targetDir)
                shutil.copy(resourceFile[0], targetDir)

            shutil.copytree(
                "resources/macOS/MyData Notifications.app",
                "dist/MyData.app/Contents/MacOS/MyData Notifications.app")
            shutil.copy("resources/macOS/ObjectiveC/bin/add-loginitem",
                        "dist/MyData.app/Contents/MacOS/")
            shutil.copy("resources/macOS/ObjectiveC/bin/delete-loginitem",
                        "dist/MyData.app/Contents/MacOS/")
            shutil.copy("resources/macOS/ObjectiveC/bin/loginitem-exists",
                        "dist/MyData.app/Contents/MacOS/")

            from setup_helpers.mac_signing import MAC_SIGNING
            MAC_SIGNING.SignApp("dist/MyData.app")
            MAC_SIGNING.VerifySignature("dist/MyData.app")

        elif sys.platform.startswith("linux"):
            os.system("cd linux; ./package_linux_version.sh")


class CustomBdistCommand(bdist):
    r"""
    Custom "python setup.py bdist" command

    On Windows, create dist\MyData_vX.Y.Z.exe (installation wizard)
    On macOS, create dist/MyData_vX.Y.Z.dmg
    """
    def run(self):
        r"""
        Custom "python setup.py bdist" command

        On Windows, create dist\MyData_vX.Y.Z.exe (installation wizard)
        On macOS, create dist/MyData_vX.Y.Z.dmg
        """
        if sys.platform.startswith("win"):
            self.run_command("build")
            print("Building binary distributable for Windows...")
            with open('setup_templates/windows/MyData.iss.template',
                      'r') as issFile:
                innosetupTemplate = issFile.read()
            innosetupScript = innosetupTemplate.replace(
                "<version>", APP_VERSION)
            with open("dist/MyData.iss", 'w') as innosetupScriptFile:
                innosetupScriptFile.write(innosetupScript)
            if os.path.exists(r"C:\Program Files (x86)\Inno Setup 6"
                              r"\ISCC.exe"):
                cmd = r'CALL "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ' \
                    r'/O"dist" /F"MyData_v%s" dist\MyData.iss' \
                    % APP_VERSION
            else:
                cmd = r'CALL "C:\Program Files\Inno Setup 6\ISCC.exe" ' \
                    r'/O"dist" /F"MyData_v%s" dist\MyData.iss' \
                    % APP_VERSION
            os.system(cmd)
        elif sys.platform.startswith("darwin"):
            os.system("rm -fr dist/*")
            self.run_command("build")
            print("\nCreating MyData_v%s.dmg...\n" % APP_VERSION)

            # Build DMG (disk image) :

            source = os.path.join(os.getcwd(), 'dist')
            title = "%s v%s" % (APP_NAME, APP_VERSION)
            size = "160000"
            finalDmgName = "%s_v%s" % (APP_NAME, APP_VERSION)

            if os.path.exists("/Volumes/%s" % title):
                cmd = "hdiutil unmount \"/Volumes/%s\"" % title
                print(cmd)
                os.system(cmd)

            tempDmgFile = \
                tempfile.NamedTemporaryFile(prefix=finalDmgName+"_",
                                            suffix=".dmg", delete=True)
            tempDmgFilename = tempDmgFile.name
            tempDmgFile.close()

            dmgBackgroundPictureFilename = "dmgBackgroundMacOSX.png"

            cmd = 'hdiutil create -srcfolder "%s" -volname "%s" ' \
                '-fs HFS+ -fsargs ' \
                '"-c c=64,a=16,e=16" -format UDRW -size %sk "%s"' \
                % (source, title, size, tempDmgFilename)
            print(cmd)
            os.system(cmd)

            cmds = [
                "hdiutil attach -readwrite -noverify -noautoopen "
                "\"%s\" | egrep '^/dev/' | sed 1q | awk '{print $1}'"
                % tempDmgFilename,
                'sleep 2',
                'mkdir "/Volumes/%s/.background/"' % title,
                'cp mydata/media/%s "/Volumes/%s/.background/"'
                % (dmgBackgroundPictureFilename, title),
                'ln -s /Applications/ "/Volumes/' + title + '/Applications"']

            for cmd in cmds:
                print(cmd)
                if "hdiutil attach" in cmd:
                    device = subprocess.getoutput(cmd)
                else:
                    os.system(cmd)

            applescript = """
tell application "Finder"
    tell disk "%s"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set theViewOptions to the icon view options of container window
             """ % title
            applescript += """
        set icon size of theViewOptions to 96
        delay 1
"""
            applescript += """
        set the bounds of container window to {400, 100, 885, 270}
        delay 1
        set arrangement of theViewOptions to not arranged
        delay 1
        set file_list to every file
        repeat with file_object in file_list
            if the name of file_object ends with ".app" then
                set the position of file_object to {120, 72}
            else if the name of file_object is "Applications" then
                set the position of file_object to {375, 72}
            end if
        end repeat
        delay 1
"""
            applescript += """
           set background picture of theViewOptions to file ".background:%s"
""" % dmgBackgroundPictureFilename
            applescript += """
           delay 1
           close
           open
           update without registering applications
           delay 5
     end tell
   end tell
"""
            print(applescript)
            tempApplescriptFile = tempfile.NamedTemporaryFile(delete=False)
            tempApplescriptFilename = tempApplescriptFile.name
            tempApplescriptFile.write(applescript)
            tempApplescriptFile.close()
            proc = subprocess.Popen(['/usr/bin/osascript',
                                     tempApplescriptFilename],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True)
            stdout, stderr = proc.communicate()
            print(stderr)
            print(stdout)
            os.unlink(tempApplescriptFilename)

            cmds = [
                'sleep 1',
                'chmod -Rf go-w /Volumes/"' + title + '"',
                'sync',
                'hdiutil detach ' + device,
                'sleep 1',
                'rm -f "dist/' + finalDmgName + '.dmg"',
                'hdiutil convert "%s" -format UDZO -imagekey zlib-level=9 '
                '-o "dist/%s.dmg"' % (tempDmgFilename, finalDmgName),
                'rm -f ' + tempDmgFilename,
                'ls -lh "dist/%s.dmg"' % finalDmgName
            ]
            for cmd in cmds:
                print(cmd)
                os.system(cmd)
        elif sys.platform.startswith("linux"):
            os.system("cd linux; ./package_centos_version.sh")
        else:
            print("Custom bdist command.")


class CustomInstallCommand(install):
    """
    Custom "python setup.py install" command

    On Windows open InnoSetup-generated installation wizard for MyData
    On macOS, open DMG which prompts user to copy MyData.app into
    /Applications/
    """
    def run(self):
        """
        Custom "python setup.py install" command

        On Windows open InnoSetup-generated installation wizard for MyData
        On macOS, open DMG which prompts user to copy MyData.app into
        /Applications/
        """
        self.run_command("bdist")
        if sys.platform.startswith("win"):
            print("\nLaunching MyData_v%s.exe...\n" % APP_VERSION)
            installerFilename = "%s_v%s.exe" % (APP_NAME, APP_VERSION)
            cmd = r'dist\%s' % installerFilename
            os.system(cmd)
        elif sys.platform.startswith("darwin"):
            print("\nOpening dist/MyData_v%s.dmg...\n" % APP_VERSION)
            dmgFilename = "%s_v%s.dmg" % (APP_NAME, APP_VERSION)
            cmd = 'open "dist/%s"' % dmgFilename
            os.system(cmd)
            print("Drag MyData.app into the Applications folder to complete "
                  "the installation.\n")
        else:
            raise NotImplementedError(
                "Only implemented for Windows and macOS.")


SETUP_ARGS = dict(name=APP_NAME,
                  version=APP_VERSION,
                  description="GUI for uploading data to MyTardis",
                  author="James Wettenhall",
                  author_email="James.Wettenhall@monash.edu",
                  license="GNU GPLv3",
                  url="http://mydata.readthedocs.org/",
                  packages=[PACKAGE_NAME],
                  cmdclass={
                      'build': CustomBuildCommand,
                      'bdist': CustomBdistCommand,
                      'install': CustomInstallCommand,
                  },
                  setup_requires=SETUP_REQUIRES,
                  scripts=["run.py"],
                  long_description="GUI for uploading data to MyTardis",
                  classifiers=[
                      "Development Status :: 4 - Beta",
                      "Intended Audience :: End Users/Desktop",
                      "Intended Audience :: Science/Research",
                      "Intended Audience :: Developers",
                      "License :: GNU General Public License (GPL)",
                      "Operating System :: Microsoft :: Windows",
                      "Operating System :: MacOS :: MacOS X",
                      "Programming Language :: Python",
                      "Topic :: Database :: Front-Ends",
                      "Topic :: System :: Archiving",
                  ])
setup(**SETUP_ARGS)
