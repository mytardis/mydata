"""
Test ability to scan folders.
"""
import unittest
# import logging
# import wx
from nose.plugins.skip import SkipTest

# from mydata.models.settings import SettingsModel
# from mydata.dataviewmodels.folders import FoldersModel

# logger = logging.getLogger(__name__)


class ScanFoldersTester(unittest.TestCase):
    """
    Test ability to scan folders.
    """
    def test_folders_view(self):
        """
        Test ability to scan folders.
        """
        # pylint: disable=no-self-use

        raise SkipTest("ScanFoldersTester is not implemented yet.")

        # app = wx.App(redirect=False)  # pylint: disable=unused-variable
        # usersModel = None
        # groupsModel = None
        # pathToTestConfig = "???"
        # settingsModel = SettingsModel(pathToTestConfig)
        # foldersModel = FoldersModel(usersModel, groupsModel, settingsModel)
        # foldersModel.ScanFolders()
