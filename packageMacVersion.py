import os
import sys
import tempfile
import commands
import subprocess

# This script is for automated builds. In
# order to try to support a nice-looking
# DMG background, which involves an Apple Script
# which can experience race conditions, some
# "sleep" and "delay" commands are included.
# If the script doesn't sleep for long enough,
# then the layout of the icons within the
# DMG window can appear incorrectly.

# The method for creating the DMG is loosely
# based on the accepted answer to this
# Stack Overflow question:
# http://stackoverflow.com/questions/96882/how-do-i-create-a-nice-looking-dmg-for-mac-os-x-using-command-line-tools

defaultCertificateName = "Developer ID Application: James Wettenhall"
certificateName = defaultCertificateName

# This script assumes that you only have one
# Developer ID Application certificate in
# your key chain.  You need to have a private
# key attached to the certificate in your key
# chain, so generally you will need to create
# a certificate-signing request on the build
# machine, upload it to the Apple Developer
# Portal, and download a new certificate with
# a private key attached.

# If you want to obtain your own Apple code-signing
# certificate, you will probably need to pay
# $99 per year to join the Apple Developer Program.
# So far, I haven't had any luck with using a
# generic (non-Apple) code-signing certificate.

cmd = 'certtool y | grep "Developer ID Application"'
print cmd
certificateLine = commands.getoutput(cmd)
print "certificateLine: " + certificateLine
try:
    certificateName = certificateLine.split(": ", 1)[1]
    print "certificateName: " + certificateName
    sign = True
except:
    sign = False

INCLUDE_APPLICATIONS_SYMBOLIC_LINK = True
ATTEMPT_TO_SET_ICON_SIZE_IN_DMG = True
ATTEMPT_TO_LAY_OUT_ICONS_ON_DMG = True
ATTEMPT_TO_SET_BACKGROUND_IMAGE = True

# The python-32 below refers to the 32-bit-only Python binary
# included within the combined 64-bit/32-bit Python
# distribution for Mac OS X from Python.Org.  The reason to
# use the combined 64-bit/32-bit Python, rather than the
# 32-bit/PPC Python is so you can use a modern version of
# gcc (v4.2) for building Python modules, instead of using
# gcc v4.0 (used to build the 32-bit/PPC Python).
#
# For more information on why you might need to use "python-32", see:
# http://stackoverflow.com/questions/9205317/how-do-i-install-wxpython-on-mac-os-x
# http://stackoverflow.com/questions/4798759/cant-import-wxpython-on-mac-os-x

if len(sys.argv) < 2:
    print "Usage: python packageMacVersion.py <version>"
    print "Or: python-32 packageMacVersion.py <version>"
    sys.exit(1)

version = sys.argv[1]

os.system('rm -fr build/*')
os.system('rm -fr dist/*')

# Build "MyData.app"
os.system('python createMacBundle.py py2app')

# Digitally sign application:
cmd = "CODESIGN_ALLOCATE=/Applications/Xcode.app/Contents/Developer" \
    "/Platforms/iPhoneOS.platform/Developer/usr/bin/codesign_allocate"
print cmd
os.environ['CODESIGN_ALLOCATE'] = \
    "/Applications/Xcode.app/Contents/Developer/Platforms" \
    "/iPhoneOS.platform/Developer/usr/bin/codesign_allocate"
# The bundle identifier (org.mytardis.MyData) referenced below is set in createMacBundle.py:
if sign:
    cmd = 'codesign --force -i "org.mytardis.MyData" --sign "%s" ' \
        '--verbose=4 dist/MyData.app' % certificateName
    print cmd
    os.system(cmd)
    cmd = 'codesign -vvvv dist/MyData.app/'
    print cmd
    os.system(cmd)
    cmd = 'spctl --assess --raw --type execute --verbose=4 dist/MyData.app/'
    print cmd
    os.system(cmd)

# Build DMG (disk image) :

source = os.path.join(os.getcwd(), 'dist')
applicationName = "MyData"
title = applicationName + " " + version
size = "160000"
finalDmgName = applicationName + " " + version

tempDmgFile = tempfile.NamedTemporaryFile(prefix=finalDmgName+"_",
                                          suffix=".dmg", delete=True)
tempDmgFileName = tempDmgFile.name
tempDmgFile.close()

backgroundPictureFileName = "dmgBackgroundMacOSX.png"

cmd = 'hdiutil create -srcfolder "%s" -volname "%s" -fs HFS+ -fsargs ' \
    '"-c c=64,a=16,e=16" -format UDRW -size %sk "%s"' \
    % (source, title, size, tempDmgFileName)
print cmd
os.system(cmd)

cmd = "hdiutil attach -readwrite -noverify -noautoopen \"%s\" " \
    "| egrep '^/dev/' | sed 1q | awk '{print $1}'" % (tempDmgFileName)
print cmd
device = commands.getoutput(cmd)

cmd = 'sleep 2'
print cmd
os.system(cmd)

cmd = 'mkdir "/Volumes/%s/.background/"' % (title)
print cmd
os.system(cmd)

cmd = 'cp %s "/Volumes/%s/.background/"' % (backgroundPictureFileName, title)
print cmd
os.system(cmd)

if INCLUDE_APPLICATIONS_SYMBOLIC_LINK:
    cmd = 'ln -s /Applications/ "/Volumes/' + title + '/Applications"'
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
""" % (backgroundPictureFileName)
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
tempAppleScriptFile = tempfile.NamedTemporaryFile(delete=False)
tempAppleScriptFileName = tempAppleScriptFile.name
tempAppleScriptFile.write(applescript)
tempAppleScriptFile.close()
proc = subprocess.Popen(['/usr/bin/osascript', tempAppleScriptFileName],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        universal_newlines=True)
stdout, stderr = proc.communicate()
print stderr
print stdout
os.unlink(tempAppleScriptFileName)

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

cmd = 'rm -f "' + finalDmgName + '.dmg"'
print cmd
os.system(cmd)

cmd = 'hdiutil convert "%s" -format UDZO -imagekey zlib-level=9 -o "%s.dmg"' \
    % (tempDmgFileName, finalDmgName)
print cmd
os.system(cmd)

cmd = 'rm -f ' + tempDmgFileName
print cmd
os.system(cmd)

cmd = 'ls -lh "%s.dmg"' % (finalDmgName)
print cmd
os.system(cmd)
