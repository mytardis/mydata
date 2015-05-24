import os
import sys
import requests
import pkgutil
import tempfile
import commands
import subprocess

from setuptools import setup
from distutils.command.build import build
from distutils.command.bdist import bdist
from distutils.command.install import install

import mydata

app_name = "MyData"
package_name = "mydata"

if sys.platform.startswith("darwin"):
    if len(sys.argv) >= 2 and sys.argv[1] == "build":
        sys.argv[1] = "py2app"

resourceFiles = ["mydata/media/MyData.icns",
                 ("media", ["mydata/media/favicon.ico"]),
                 ("media/Aha-Soft", ["mydata/media/Aha-Soft/LICENSE.txt"]),
                 requests.certs.where()]

for icon_files_path in ("media/Aha-Soft/png-normal/icons16x16",
                        "media/Aha-Soft/png-normal/icons24x24",
                        "media/Aha-Soft/png-hot/icons24x24"):
    for icon_file in os.listdir(os.path.join(package_name, icon_files_path)):
        icon_file_path = os.path.join(package_name, icon_files_path, icon_file)
        if os.path.isfile(icon_file_path):
            resourceFile = (icon_files_path, [icon_file_path])
            resourceFiles.append(resourceFile)

if sys.platform.startswith("darwin"):
    setupRequires = ["py2app"]
    options = dict(py2app=dict(
        arch="x86_64",
        plist=dict(
            CFBundleDevelopmentRegion="English",
            CFBundleDisplayName=app_name,
            CFBundleExecutable=app_name,
            CFBundleIconFile="MyData.icns",
            CFBundleIdentifier="org.mytardis.MyData",
            CFBundleName=app_name,
            CFBundlePackageType="APPL",
            CFBundleVersion="Version " + mydata.__version__,
            LSArchitecturePriority=["x86_64"]
            )
        )
    )
else:
    options = []
    setupRequires = []


class CustomBuildCommand(build):
    """
    On Windows, create dist/MyData/*.*, including dist/MyData/MyData.exe
    On Mac OS X, create dist/MyData.app/*
    """
    def run(self):
        # build.run(self)
        if sys.platform.startswith("darwin"):
            print "\nCreating dist/MyData.app using py2app...\n"
            os.system("rm -fr build/*")
            os.system("rm -fr dist/*")
        else:
            print "Custom build command."


class CustomBdistCommand(bdist):
    """
    On Windows, create setup.exe (installation wizard)
    On Mac OS X, created MyData_vX.Y.Z.dmg
    """
    def run(self):
        # bdist.run(self)
        if sys.platform.startswith("win"):
            self.run_command("build")
            print "Building binary distributable for Windows..."
        elif sys.platform.startswith("darwin"):
            os.system("rm -fr dist/*")
            self.run_command("py2app")

            INCLUDE_APPLICATIONS_SYMBOLIC_LINK = True
            ATTEMPT_TO_SET_ICON_SIZE_IN_DMG = True
            ATTEMPT_TO_LAY_OUT_ICONS_ON_DMG = True
            ATTEMPT_TO_SET_BACKGROUND_IMAGE = True

            print "\nSigning dist/MyData.app...\n"

            # This assumes that you only have one Developer ID Application
            # certificate in your key chain.  You need to have a private key
            # attached to the certificate in your key chain, so generally you
            # will need to create a certificate-signing request on the build
            # machine, upload it to the Apple Developer Portal, and download a
            # new certificate with a private key attached.

            cmd = "certtool y | grep \"Developer ID Application\""
            print cmd
            certificateLine = commands.getoutput(cmd)
            print "certificateLine: " + certificateLine
            try:
                certificateName = certificateLine.split(": ", 1)[1]
                print "certificateName: " + certificateName
                sign = True
            except:
                sign = False

            # Digitally sign application:
            cmd = "CODESIGN_ALLOCATE=/Applications/Xcode.app/Contents" \
                "/Developer/Platforms/iPhoneOS.platform/Developer" \
                "/usr/bin/codesign_allocate"
            print cmd
            os.environ['CODESIGN_ALLOCATE'] = \
                "/Applications/Xcode.app/Contents/Developer/Platforms" \
                "/iPhoneOS.platform/Developer/usr/bin/codesign_allocate"
            if sign:
                cmd = "codesign --deep --force -i org.mytardis.MyData " \
                    "--sign \"%s\" " \
                    "--verbose=4 dist/MyData.app" % certificateName
                print cmd
                os.system(cmd)
                cmd = "codesign -vvvv dist/MyData.app/"
                print cmd
                os.system(cmd)
                cmd = "spctl --assess --raw --type execute --verbose=4 " \
                    "dist/MyData.app/"
                print cmd

            print "\nCreating MyData_v%s.dmg...\n" % mydata.__version__

            # Build DMG (disk image) :

            source = os.path.join(os.getcwd(), 'dist')
            title = "%s v%s" % (app_name, mydata.__version__)
            size = "160000"
            final_dmg_name = "%s_v%s" % (app_name, mydata.__version__)

            if os.path.exists("/Volumes/%s" % title):
                cmd = "hdiutil unmount \"/Volumes/%s\"" % title
                print cmd
                os.system(cmd)

            temp_dmg_file = \
                tempfile.NamedTemporaryFile(prefix=final_dmg_name+"_",
                                            suffix=".dmg", delete=True)
            temp_dmg_filename = temp_dmg_file.name
            temp_dmg_file.close()

            dmg_background_picture_filename = "dmgBackgroundMacOSX.png"

            cmd = 'hdiutil create -srcfolder "%s" -volname "%s" ' \
                '-fs HFS+ -fsargs ' \
                '"-c c=64,a=16,e=16" -format UDRW -size %sk "%s"' \
                % (source, title, size, temp_dmg_filename)
            print cmd
            os.system(cmd)

            cmd = "hdiutil attach -readwrite -noverify -noautoopen " \
                "\"%s\" | egrep '^/dev/' | sed 1q | awk '{print $1}'" \
                % (temp_dmg_filename)
            print cmd
            device = commands.getoutput(cmd)

            cmd = 'sleep 2'
            print cmd
            os.system(cmd)

            cmd = 'mkdir "/Volumes/%s/.background/"' % (title)
            print cmd
            os.system(cmd)

            cmd = 'cp mydata/media/%s "/Volumes/%s/.background/"' \
                % (dmg_background_picture_filename, title)
            print cmd
            os.system(cmd)

            if INCLUDE_APPLICATIONS_SYMBOLIC_LINK:
                cmd = 'ln -s /Applications/ "/Volumes/' + title + \
                    '/Applications"'
                print cmd
                os.system(cmd)

            applescript = """
tell application "Finder"
    tell disk "%s"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set theViewOptions to the icon view options of container window
             """ % (title)
            if ATTEMPT_TO_SET_ICON_SIZE_IN_DMG:
                applescript = applescript + """
        set icon size of theViewOptions to 96
        delay 1
"""
            if ATTEMPT_TO_LAY_OUT_ICONS_ON_DMG:
                applescript = applescript + """
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
            if ATTEMPT_TO_SET_BACKGROUND_IMAGE:
                applescript = applescript + """
           set background picture of theViewOptions to file ".background:%s"
""" % (dmg_background_picture_filename)
            applescript = applescript + """
           delay 1
           close
           open
           update without registering applications
           delay 5
     end tell
   end tell
"""
            print applescript
            temp_applescript_file = tempfile.NamedTemporaryFile(delete=False)
            temp_applescript_filename = temp_applescript_file.name
            temp_applescript_file.write(applescript)
            temp_applescript_file.close()
            proc = subprocess.Popen(['/usr/bin/osascript',
                                     temp_applescript_filename],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True)
            stdout, stderr = proc.communicate()
            print stderr
            print stdout
            os.unlink(temp_applescript_filename)

            cmd = 'sleep 1'
            print cmd
            os.system(cmd)

            cmd = 'chmod -Rf go-w /Volumes/"' + title + '"'
            print cmd
            os.system(cmd)

            cmd = 'sync'
            print cmd
            os.system(cmd)

            cmd = 'hdiutil detach ' + device
            print cmd
            os.system(cmd)

            cmd = 'sleep 1'
            print cmd
            os.system(cmd)

            cmd = 'rm -f "dist/' + final_dmg_name + '.dmg"'
            print cmd
            os.system(cmd)

            cmd = 'hdiutil convert "%s" -format UDZO -imagekey zlib-level=9 ' \
                '-o "dist/%s.dmg"' % (temp_dmg_filename, final_dmg_name)
            print cmd
            os.system(cmd)

            cmd = 'rm -f ' + temp_dmg_filename
            print cmd
            os.system(cmd)

            cmd = 'ls -lh "dist/%s.dmg"' % (final_dmg_name)
            print "\n" + cmd
            os.system(cmd)
        else:
            print "Custom bdist command."


class CustomInstallCommand(install):
    """
    On Windows open InnoSetup-generated installation wizard for MyData
    On Mac OS X, open DMG which prompts user to copy MyData.app into
    /Applications/
    """
    def run(self):
        # install.run(self)
        self.run_command("bdist")
        if sys.platform.startswith("win"):
            print "\nOpening MyData_v%s.exe...\n" % mydata.__version__
        elif sys.platform.startswith("darwin"):
            print "\nOpening dist/MyData_v%s.dmg...\n" % mydata.__version__
            dmg_filename = "%s_v%s.dmg" % (app_name, mydata.__version__)
            cmd = 'open "dist/%s"' % dmg_filename
            os.system(cmd)
            print "Drag MyData.app into the Applications folder to complete " \
                "the installation.\n"
        else:
            print "Custom install command."


setup(name=app_name,
      version=mydata.__version__,
      description="GUI for uploading data to MyTardis",
      author="James Wettenhall",
      author_email="James.Wettenhall@monash.edu",
      license="GNU GPLv3",
      url="http://mydata.readthedocs.org/",
      options=options,
      packages=[package_name],
      data_files=resourceFiles,
      cmdclass={
          'build': CustomBuildCommand,
          'bdist': CustomBdistCommand,
          'install': CustomInstallCommand,
      },
      setup_requires=setupRequires,
      app=["run.py"],  # Used by py2app
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
