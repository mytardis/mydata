import os
import sys
import shutil

if len(sys.argv) < 3:
    print "Usage: buildExitMyData.py <certificate.pfx> <password>"
    sys.exit(1)

code_signing_certificate = sys.argv[1]
code_signing_certificate_password = sys.argv[2]

os.system("del /Q dist\\*.*")

os.system("C:\\Python27\\python.exe .\\pyinstaller\\pyinstaller.py "
          "--name \"Exit MyData\" "
          "--icon=favicon.ico --windowed ExitMyData.py")

os.system("signtool sign -f \"" + code_signing_certificate + "\" -p " +
          code_signing_certificate_password + " \"dist\Exit MyData\*.exe\"")
os.system("signtool sign -f \"" + code_signing_certificate + "\" -p " +
          code_signing_certificate_password + " \"dist\Exit MyData\*.dll\"")
