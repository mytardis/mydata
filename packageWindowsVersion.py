import os
import sys
import distutils.dir_util

if len(sys.argv) < 3:
    print "Usage: packageWindowsVersion.py <certificate.pfx> <password>"
    sys.exit(1)

code_signing_certificate = sys.argv[1]
code_signing_certificate_password = sys.argv[2]

os.system("del /Q dist\\*.*")

os.system("C:\\Python27\\python.exe .\\pyinstaller\\pyinstaller.py "
          "--icon=favicon.ico --windowed MyData.py")

os.system("copy /Y favicon.ico dist\\MyData\\")
distutils.dir_util.copy_tree(r"png-normal", r"dist\MyData\png-normal")
distutils.dir_util.copy_tree(r"png-hot", r"dist\MyData\png-hot")

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
