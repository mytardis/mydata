"""
mydata/__init__.py
"""

__version__ = "0.4.0"

import sys

try:
    if hasattr(sys, "frozen"):
        from mydata.commitdef import LATEST_COMMIT
    else:
        with open(".git/logs/HEAD") as gitlog:
            for line in gitlog:
                pass
        LATEST_COMMIT = line.split(" ")[1]
        with open("mydata/commitdef.py", 'w') as commitdef: 
            commitdef.write('LATEST_COMMIT = "%s"\n' % LATEST_COMMIT)
except:
    LATEST_COMMIT = "Couldn't determine LATEST_COMMIT."
