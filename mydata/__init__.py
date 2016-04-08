"""
mydata/__init__.py
"""
import sys

__version__ = "0.5.2-beta1"


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
except:  # pylint: disable=bare-except
    LATEST_COMMIT = "Couldn't determine LATEST_COMMIT."
