"""
mydata/__init__.py
"""
import sys

__version__ = "0.6.1-beta1"


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

if __name__ == "__main__":
    print "Please use run.py in MyData.py's parent directory to launch MyData."
    print "This module can be run directly to update mydata/commitdef.py to "
    print "record the latest commit hash for the About dialog in frozen "
    print "platform-specific bundles."
