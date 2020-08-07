"""
mydata/__init__.py

This module updates mydata/commitdef.py to record the latest commit hash
for the About dialog in frozen platform-specific bundles.
"""
import distutils.spawn
import subprocess
import sys

__version__ = "0.9.1"


if hasattr(sys, "frozen"):
    # pylint: disable=import-error
    from .commitdef import LATEST_COMMIT
    from .commitdef import LATEST_COMMIT_DATETIME
else:
    LINE = None
    with open(".git/logs/HEAD") as gitlog:
        for LINE in gitlog:
            pass
    LATEST_COMMIT = LINE.split(" ")[1]
    GIT = distutils.spawn.find_executable("git")
    LATEST_COMMIT_DATETIME = subprocess.check_output(
        [GIT, "log", "-1", "--pretty=format:%ci"])
    with open("mydata/commitdef.py", 'w') as commitdef:
        commitdef.write('"""\n')
        commitdef.write('commitdef.py\n')
        commitdef.write('"""\n')
        commitdef.write('LATEST_COMMIT = "%s"\n' % LATEST_COMMIT)
        commitdef.write(
            'LATEST_COMMIT_DATETIME = "%s"\n' % LATEST_COMMIT_DATETIME)
