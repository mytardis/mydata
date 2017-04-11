r"""
setup.py

Build binary executable with:

    python setup.py build

    On Windows, additional arguments are required to configure code-signing:

    python setup.py build unsigned
    python setup.py build C:\path\to\certificate.pfx password

Build binary distributable (Setup Wizard / DMG / RPM) with:

    python setup.py bdist

    On Windows, additional arguments are required to configure code-signing:

    python setup.py bdist unsigned
    python setup.py bdist C:\path\to\certificate.pfx password

Run tests with:

    python setup.py nosetests
"""
import os
import sys
import tempfile
import commands
import subprocess
import shutil

from distutils.command.build import build
from distutils.command.bdist import bdist
from distutils.command.install import install
import distutils.dir_util

import requests
from setuptools import setup

# pylint: disable=invalid-name

# Ensure latest commit hash is recorded, so that
# it is available in the About dialog when MyData
# is frozen into a platform-specific bundle:
import mydata

if sys.platform.startswith("darwin"):
    from py2app.build_app import py2app


app_name = "MyData"
package_name = "mydata"

if sys.platform.startswith("win"):
    # On Windows, we require the code-signing certificate filename (or path)
    # to be specified and the password associated with the certificate.
    if len(sys.argv) == 4:
        whether_to_sign_on_windows = True
        certificate_path = sys.argv[2]
        certificate_password = sys.argv[3]
        del sys.argv[2:4]
    elif len(sys.argv) == 3 and sys.argv[2] == 'unsigned':
        whether_to_sign_on_windows = False
        del sys.argv[2:3]
    elif len(sys.argv) >= 2 and sys.argv[1] == 'nosetests':
        pass
    else:
        print "\nUsage: python setup.py [build|bdist|install] " \
            "<cert.pfx> <cert_passwd>"
        print "       python setup.py [build|bdist|install] unsigned\n"
        sys.exit(1)
elif sys.platform.startswith("darwin"):
    if len(sys.argv) >= 2 and sys.argv[1] == "build":
        sys.argv[1] = "py2app"

resourceFiles = ["mydata/media/MyData.icns",
                 ("media", ["mydata/media/favicon.ico"]),
                 ("media/Aha-Soft", ["mydata/media/Aha-Soft/LICENSE.txt"]),
                 requests.certs.where()]

for icon_files_path in ("media/Aha-Soft/png-normal/icons16x16",
                        "media/Aha-Soft/png-normal/icons24x24",
                        "media/Aha-Soft/png-disabled/icons16x16",
                        "media/Aha-Soft/png-disabled/icons24x24",
                        "media/Aha-Soft/png-hot/icons24x24"):
    for icon_file in os.listdir(os.path.join(package_name, icon_files_path)):
        icon_file_path = os.path.join(package_name, icon_files_path, icon_file)
        if os.path.isfile(icon_file_path):
            resourceFile = (icon_files_path, [icon_file_path])
            resourceFiles.append(resourceFile)

# wxPython not included below because it is difficult to install automatically.
install_requires = ['appdirs', 'lxml', 'poster', 'psutil',
                    'requests', 'validate_email']

if sys.platform.startswith("darwin"):
    setup_requires = ["nose", "coverage", "py2app"]
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
            LSArchitecturePriority=["x86_64"],
            LSUIElement=True)
        ))
else:
    setup_requires = ["nose", "coverage"]
    options = {}


class CustomBuildCommand(build):
    """
    Custom "python setup.py build" command

    On Windows, create dist/MyData/*.*, including dist/MyData/MyData.exe
    On macOS, create dist/MyData.app/*
    """
    # pylint: disable=too-many-branches
    def run(self):
        """
        Custom "python setup.py build" command

        On Windows, create dist/MyData/*.*, including dist/MyData/MyData.exe
        On macOS, create dist/MyData.app/*
        """
        if sys.platform.startswith("win"):
            # The forward slashes and backslashes below should work in
            # both a DOS environment and a Unix-like environment (e.g. MSYS)
            # running on Windows.  Some commands are particularly sensitive
            # to this, so please test in both DOS and MSYS if/when changing
            # the slashes.
            if os.path.exists("dist"):
                os.system(r"DEL /Q dist\*.*")

            exitCode = \
                os.system(sys.executable +
                          r" .\pyinstaller\pyinstaller.py -y "
                          r"--name=MyData --icon=mydata\media\MyData.ico "
                          r"--windowed run.py")
            if exitCode != 0:
                print "\nPyInstaller failed to build MyData.exe\n"
                sys.exit(1)

            exitCode = \
                os.system(sys.executable +
                          r" .\pyinstaller\pyinstaller.py -y "
                          r"--name=MyData-console "
                          r"--icon=mydata\media\MyData.ico "
                          r"--console run.py")
            if exitCode != 0:
                print "\nPyInstaller failed to build MyData-console.exe\n"
                sys.exit(1)
            os.system(r"COPY /Y dist\MyData-console\MyData-console.exe "
                      r"dist\MyData\MyData.com")

            # favicon.ico and MyData.ico are really the same thing. favicon.ico
            # is the original from the MyTardis repository, and MyData.ico is
            # the result of converting it to PNG and then back to ICO, which
            # fixed a # problem with the Windows build.
            if not os.path.exists("dist/MyData/media"):
                os.makedirs("dist/MyData/media")
            os.system(r"COPY /Y mydata\media\favicon.ico "
                      r"dist\MyData\media")
            os.system(r"COPY /Y mydata\media\MyData.ico "
                      r"dist\MyData\media")
            distutils.dir_util.copy_tree("mydata/media/Aha-Soft",
                                         "dist/MyData/media/Aha-Soft")

            distutils.dir_util\
                .copy_tree("resources/win64/openssh-7.3p1-cygwin-2.6.0",
                           "dist/MyData/win64/openssh-7.3p1-cygwin-2.6.0")
            cygwin64HomeDir = \
                "dist/MyData/win64/openssh-7.3p1-cygwin-2.6.0/home"
            for subdir in os.listdir(cygwin64HomeDir):
                subdirpath = os.path.join(cygwin64HomeDir, subdir)
                if os.path.isdir(subdirpath):
                    shutil.rmtree(subdirpath)
            distutils.dir_util.copy_tree(
                "resources/win32/openssh-7.3p1-cygwin-2.8.0",
                "dist/MyData/win32/openssh-7.3p1-cygwin-2.8.0")
            cygwin32HomeDir = \
                "dist/MyData/win32/openssh-7.3p1-cygwin-2.8.0/home"
            for subdir in os.listdir(cygwin32HomeDir):
                subdirpath = os.path.join(cygwin32HomeDir, subdir)
                if os.path.isdir(subdirpath):
                    shutil.rmtree(subdirpath)

            os.system(r"COPY /Y GPL.txt dist\MyData")

            cacert = requests.certs.where()
            os.system(r"COPY /Y %s dist\MyData" % cacert)

            if whether_to_sign_on_windows:
                sign_exe_cmd = 'signtool sign -f "%s" -p "%s" %s' \
                    % (certificate_path, certificate_password,
                       r" dist\MyData\*.exe")
                os.system(sign_exe_cmd)
                sign_dll_cmd = 'signtool sign -f "%s" -p "%s" %s' \
                    % (certificate_path, certificate_password,
                       r" dist\MyData\*.dll")
                os.system(sign_dll_cmd)
        elif sys.platform.startswith("darwin"):
            print "\nCreating dist/MyData.app using py2app...\n"
            os.system("rm -fr build/*")
            os.system("rm -fr dist/*")
        elif sys.platform.startswith("linux"):
            os.system("cd linux; ./package_linux_version.sh")
        else:
            print "Custom build command."


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
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        # bdist.run(self)
        if sys.platform.startswith("win"):
            self.run_command("build")
            print "Building binary distributable for Windows..."
            innosetup_script = r"""
;MyData InnoSetup script
;Change OutputDir to suit your build environment

#define Organization "Monash University"
#define MyDataAppName "MyData"
#define MyDataAppExeName "MyData.exe"

[Setup]
AppName={#MyDataAppName}
AppVersion=<version>
DefaultDirName={pf}\{#MyDataAppName}
DefaultGroupName={#MyDataAppName}
UninstallDisplayIcon={app}\{#MyDataAppExeName}
Compression=lzma2
SolidCompression=yes
OutputDir=.

[Files]
Source: "MyData\*.*"; DestDir: "{app}"; Flags: recursesubdirs

[Dirs]
Name: "{commonappdata}\{#Organization}\{#MyDataAppName}"; Permissions: "everyone-modify"
Name: "{app}\win64\openssh-7.3p1-cygwin-2.6.0\home"; Permissions: "users-modify"
Name: "{app}\win32\openssh-7.3p1-cygwin-2.8.0\home"; Permissions: "users-modify"

[Tasks]
Name: startup; Description: "{cm:AutoStartProgram,{#MyDataAppName}}"; GroupDescription: "Start Automatically On Login:"

[Icons]
Name: "{commonstartup}\{#MyDataAppName}"; Filename: "{app}\{#MyDataAppExeName}"; Tasks: startup

[Icons]
Name: "{group}\{#MyDataAppName}"; Filename: "{app}\{#MyDataAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyDataAppName}}"; Filename: "{uninstallexe}"
            """.replace("<version>", mydata.__version__)
            with open("dist/MyData.iss", 'w') as innosetup_script_file:
                innosetup_script_file.write(innosetup_script)
            if os.path.exists(r"C:\Program Files (x86)\Inno Setup 5"
                              r"\ISCC.exe"):
                cmd = r'CALL "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" ' \
                    r'/O"dist" /F"MyData_v%s" dist\MyData.iss' \
                    % mydata.__version__
            else:
                cmd = r'CALL "C:\Program Files\Inno Setup 5\ISCC.exe" ' \
                    r'/O"dist" /F"MyData_v%s" dist\MyData.iss' \
                    % mydata.__version__
            os.system(cmd)
            if whether_to_sign_on_windows:
                os.system(r'signtool sign -f "%s" -p "%s" dist\MyData_v%s.exe'
                          % (certificate_path, certificate_password,
                             mydata.__version__))
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
            certificateName = None
            try:
                certificateName = certificateLine.split(": ", 1)[1]
                print "certificateName: " + certificateName
                whether_to_sign = True
            except IndexError:
                whether_to_sign = False

            # Digitally sign application:
            if whether_to_sign:
                cmd = ("codesign --force -i org.mytardis.MyData "
                       "--sign \"%s\" "
                       "--verbose=4 "
                       "dist/MyData.app/Contents/Frameworks/*.dylib*"
                       % certificateName)
                print cmd
                os.system(cmd)
                cmd = "codesign --force -i org.mytardis.MyData " \
                    "--sign \"%s\" " \
                    "--verbose=4 dist/MyData.app/Contents/Frameworks/" \
                    "Python.framework/Versions/2.7" % certificateName
                print cmd
                os.system(cmd)
                cmd = "codesign --force -i org.mytardis.MyData " \
                    "--sign \"%s\" " \
                    "--verbose=4 dist/MyData.app/Contents/Frameworks/" \
                    "Python.framework" % certificateName
                print cmd
                os.system(cmd)
                cmd = "codesign --force -i org.mytardis.MyData " \
                    "--sign \"%s\" " \
                    "--verbose=4 dist/MyData.app/Contents/MacOS/" \
                    "python" % certificateName
                print cmd
                os.system(cmd)
                cmd = "codesign --force -i org.mytardis.MyData " \
                    "--sign \"%s\" " \
                    "--verbose=4 \"dist/MyData.app/Contents/MacOS/" \
                    "MyData Notifications\"" % certificateName
                print cmd
                os.system(cmd)
                cmd = "codesign --force -i org.mytardis.MyData " \
                    "--sign \"%s\" " \
                    "--verbose=4 dist/MyData.app/Contents/MacOS/" \
                    "MyData" % certificateName
                print cmd
                os.system(cmd)
                cmd = "codesign -vvvv dist/MyData.app"
                print cmd
                os.system(cmd)
                cmd = "spctl --assess --raw --type execute --verbose=4 " \
                    "dist/MyData.app"
                print cmd
                os.system(cmd)

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
                % temp_dmg_filename
            print cmd
            device = commands.getoutput(cmd)

            cmd = 'sleep 2'
            print cmd
            os.system(cmd)

            cmd = 'mkdir "/Volumes/%s/.background/"' % title
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
             """ % title
            if ATTEMPT_TO_SET_ICON_SIZE_IN_DMG:
                applescript += """
        set icon size of theViewOptions to 96
        delay 1
"""
            if ATTEMPT_TO_LAY_OUT_ICONS_ON_DMG:
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
            if ATTEMPT_TO_SET_BACKGROUND_IMAGE:
                applescript += """
           set background picture of theViewOptions to file ".background:%s"
""" % dmg_background_picture_filename
            applescript += """
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

            # Digitally sign DMG:
            if whether_to_sign:
                cmd = "codesign --force -i org.mytardis.MyData " \
                    "--sign \"%s\" " \
                    "--verbose=4 dist/%s.dmg" \
                    % (certificateName, final_dmg_name)
                print cmd
                os.system(cmd)

            cmd = 'ls -lh "dist/%s.dmg"' % final_dmg_name
            print "\n" + cmd
            os.system(cmd)
        elif sys.platform.startswith("linux"):
            os.system("cd linux; ./package_centos_version.sh")
        else:
            print "Custom bdist command."


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
        # install.run(self)
        self.run_command("bdist")
        if sys.platform.startswith("win"):
            print "\nLaunching MyData_v%s.exe...\n" % mydata.__version__
            installer_filename = "%s_v%s.exe" % (app_name, mydata.__version__)
            cmd = r'dist\%s' % installer_filename
            os.system(cmd)
        elif sys.platform.startswith("darwin"):
            print "\nOpening dist/MyData_v%s.dmg...\n" % mydata.__version__
            dmg_filename = "%s_v%s.dmg" % (app_name, mydata.__version__)
            cmd = 'open "dist/%s"' % dmg_filename
            os.system(cmd)
            print "Drag MyData.app into the Applications folder to complete " \
                "the installation.\n"
        else:
            print "Custom install command."


setup_args = dict(name=app_name,
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
                  setup_requires=setup_requires,
                  install_requires=install_requires,
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
if sys.platform.startswith("darwin"):

    class CustomPy2appCommand(py2app):
        """
        On macOS, copy "MyData Notifications", add-loginitem, delete-loginitem,
        and loginitem-exists binaries into MyData.app bundle.
        """
        def run(self):
            """
            On macOS, copy "MyData Notifications", add-loginitem, delete-loginitem,
            and loginitem-exists binaries into MyData.app bundle.
            """
            py2app.run(self)
            shutil.copy(
                "resources/macOS/MyData Notifications.app/Contents/MacOS"
                "/MyData Notifications", "dist/MyData.app/Contents/MacOS/")
            distutils.dir_util\
                .copy_tree("resources/macOS/MyData Notifications.app/Contents"
                           "/Resources/en.lproj",
                           "dist/MyData.app/Contents/Resources/en.lproj")
            shutil.copy("resources/macOS/ObjectiveC/bin/add-loginitem",
                        "dist/MyData.app/Contents/MacOS/")
            shutil.copy("resources/macOS/ObjectiveC/bin/delete-loginitem",
                        "dist/MyData.app/Contents/MacOS/")
            shutil.copy("resources/macOS/ObjectiveC/bin/loginitem-exists",
                        "dist/MyData.app/Contents/MacOS/")

    setup_args['app'] = ["run.py"]  # Used by py2app
    setup_args['cmdclass']['py2app'] = CustomPy2appCommand
setup(**setup_args)
