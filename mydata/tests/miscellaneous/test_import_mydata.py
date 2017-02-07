"""
Test importing mydata/__init__.py which saves the latest git
commit hash to mydata/commitdef.py if running from source,
or reads it from the same file if running frozen.
"""
import os
import sys
import unittest


class ImportMyDataTester(unittest.TestCase):
    """
    Test ability to import mydata/__init__.py and update mydata/commitdef.py
    """
    def test_mydata_online_docs(self):
        """
        Test ability to import mydata/__init__.py and update mydata/commitdef.py
        """
        if "mydata" in sys.modules:
            sys.modules.pop("mydata")
            if os.path.exists("mydata/commitdef.py"):
                os.remove("mydata/commitdef.py")
        from mydata import LATEST_COMMIT
        self.assertNotEqual(LATEST_COMMIT, "Couldn't determine LATEST_COMMIT.")
        self.assertTrue(os.path.exists("mydata/commitdef.py"))

        frozen = getattr(sys, "frozen", None)
        sys.frozen = True
        sys.modules.pop("mydata")
        commitHash = LATEST_COMMIT
        from mydata import LATEST_COMMIT  # pylint: disable=reimported
        self.assertEqual(LATEST_COMMIT, commitHash)
        if frozen:
            sys.frozen = frozen
        else:
            delattr(sys, "frozen")
