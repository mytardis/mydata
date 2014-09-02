import os
import sys
import shutil

if len(sys.argv) < 3:
    print "Usage: package_windows_version.py <certificate.pfx> <password>"
    sys.exit(1)

code_signing_certificate = sys.argv[1]
code_signing_certificate_password = sys.argv[2]

os.system('del /Q dist\\*.*')

os.system('C:\\Python27\\python.exe .\\pyinstaller\\pyinstaller.py --icon favicon.ico --windowed MyData.py')
# os.system('python pyinstaller/pyinstaller.py --icon favicon.ico --windowed MyData.py')

os.system('copy /Y favicon.ico dist\\MyData\\')
# os.system('copy /Y /c/Python27\\Lib\\site-packages\\wx-2.8-msw-unicode\\wx\\gdiplus.dll dist\\MyData\\')
shutil.copytree(r'png-normal', r'dist\MyData\png-normal')
shutil.copytree(r'png-hot', r'dist\MyData\png-hot')

os.system('copy /Y GPL.txt dist\\MyData\\')
os.system('copy /Y "Exit MyData.exe" dist\\MyData\\')

os.system("signtool sign -f \"" + code_signing_certificate + "\" -p " + code_signing_certificate_password + " dist\MyData\*.exe")
os.system("signtool sign -f \"" + code_signing_certificate + "\" -p " + code_signing_certificate_password + " dist\MyData\*.dll")

# Only one of these will work...
os.system(r""""C:\Program Files (x86)\Inno Setup 5\Compil32.exe" /cc .\\MyData.iss""")
os.system(r""""C:\Program Files\Inno Setup 5\Compil32.exe" /cc .\\MyData.iss""")
os.system("signtool sign -f \"" + code_signing_certificate + "\" -p " + code_signing_certificate_password + " setup.exe")

