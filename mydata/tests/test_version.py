"""
Test ability to query version.
"""
import sys
import unittest
import logging
import subprocess

from mydata.MyData import Run
from mydata import __version__ as VERSION
from mydata import LATEST_COMMIT

logger = logging.getLogger(__name__)


class VersionTester(unittest.TestCase):
    """
    Test ability to query version.
    """
    def test_version(self):
        """
        Test ability to query version.
        """
        # pylint: disable=no-self-use
        proc = subprocess.Popen([sys.executable, "run.py", "--version"], stdout=subprocess.PIPE)
        output, _ = proc.communicate()
        assert output.strip() == ("MyData %s (%s)" % (VERSION, LATEST_COMMIT))

