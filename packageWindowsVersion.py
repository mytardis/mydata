import os
import sys
import distutils.dir_util
import shutil

import CreateCommitDef

if len(sys.argv) < 3:
    print "Usage: packageWindowsVersion.py <certificate.pfx> <password>"
    sys.exit(1)

code_signing_certificate = sys.argv[1]
code_signing_certificate_password = sys.argv[2]

if os.path.exists("dist"):
    os.system("del /Q dist\\*.*")

os.system("C:\\Python27\\python.exe .\\pyinstaller\\pyinstaller.py "
          "--icon=mydata\\media\\MyData.ico --windowed mydata/MyData.py")

# favicon.ico and MyData.ico are really the same thing - favicon.ico
# is the original from the MyTardis repository, and MyData.ico is the
# result of converting it to PNG and then back to ICO, which fixed a
# problem with the Windows build.
os.system("copy /Y mydata\\media\\favicon.ico dist\\MyData\\")
os.system("copy /Y mydata\\media\\MyData.ico dist\\MyData\\")
distutils.dir_util.copy_tree(r"mydata/media/png-normal", r"dist\MyData\mydata\media\png-normal")
distutils.dir_util.copy_tree(r"mydata/media/png-hot", r"dist\MyData\mydata\media\png-hot")

distutils.dir_util.copy_tree(r"openssh-5.4p1-1-msys-1.0.13",
                             r"dist\MyData\openssh-5.4p1-1-msys-1.0.13")
msysHomeDir = r"dist\MyData\openssh-5.4p1-1-msys-1.0.13\home"
for subdir in os.listdir(msysHomeDir):
    subdirpath = os.path.join(msysHomeDir, subdir)
    if os.path.isdir(subdirpath):
        shutil.rmtree(subdirpath)

os.system('copy /Y GPL.txt dist\\MyData\\')
os.system('copy /Y "Exit MyData.exe" dist\\MyData\\')

import requests
cacert = requests.certs.where()
os.system('copy /Y ' + cacert + ' dist\\MyData\\')

os.system("signtool sign -f \"" + code_signing_certificate + "\" -p " +
          code_signing_certificate_password + " dist\MyData\*.exe")
os.system("signtool sign -f \"" + code_signing_certificate + "\" -p " +
          code_signing_certificate_password + " dist\MyData\*.dll")

# Only one of these will work...
cmd1 = \
    r""""C:\Program Files (x86)\Inno Setup 5\Compil32.exe" /cc .\\MyData.iss"""
os.system(cmd1)
cmd2 = \
    r""""C:\Program Files\Inno Setup 5\Compil32.exe" /cc .\\MyData.iss"""
os.system(cmd2)
os.system("signtool sign -f \"" + code_signing_certificate + "\" -p " +
          code_signing_certificate_password + " setup.exe")
