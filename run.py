"""
run.py

MyData can be launched by running "python run.py"
assuming that the Python module dependencies
have been installed, see:
requirements.txt
requirements-windows.txt

Only the very latest pre-release wxPython (3.0.3.dev)
is pip-installable.  For earlier versions (2.9.5 or
3.0.2), use the installer from http://wxpython.org
"""
import sys
import os
from mydata import MyData

STDERR_FILE_PATH = os.path.join(os.path.expanduser("~"), ".MyData_stderr.txt")
with open(STDERR_FILE_PATH, 'w') as stderrFile:
    os.dup2(stderrFile.fileno(), sys.stderr.fileno())
    MyData.Run(sys.argv)
