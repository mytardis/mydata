"""
mydata/__init__.py

This module updates mydata/commitdef.py to record the latest commit hash
for the About dialog in frozen platform-specific bundles.
"""
import sys

__version__ = "0.7.0-beta5"


try:
    if hasattr(sys, "frozen"):
        # pylint: disable=import-error
        # pylint: disable=wrong-import-position
        from mydata.commitdef import LATEST_COMMIT
    else:
        line = None  # pylint: disable=invalid-name
        with open(".git/logs/HEAD") as gitlog:
            for line in gitlog:
                pass
        if not line:
            raise Exception("Couldn't read .git/logs/HEAD")
        LATEST_COMMIT = line.split(" ")[1]
        with open("mydata/commitdef.py", 'w') as commitdef:
            commitdef.write('"""\n')
            commitdef.write('commitdef.py\n')
            commitdef.write('"""\n')
            commitdef.write('LATEST_COMMIT = "%s"\n' % LATEST_COMMIT)
except:
    LATEST_COMMIT = "Couldn't determine LATEST_COMMIT."
