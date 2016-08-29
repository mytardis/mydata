"""
Test ability to open uploads view.
"""
import unittest
import wx

from mydata.dataviewmodels.uploads import UploadsModel
from mydata.views.uploads import UploadsView


class UploadsViewTester(unittest.TestCase):
    """
    Test ability to open uploads view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)  # pylint: disable=unused-variable
        self.frame = wx.Frame(None, title='UploadsViewTester')
        self.uploadsModel = UploadsModel()
        self.foldersController = None
        self.uploadsView = UploadsView(self.frame, self.uploadsModel, self.foldersController)
        self.frame.Show()

    def test_uploads_view(self):
        """
        Test ability to open uploads view.
        """
        # pylint: disable=no-self-use
        pass

    def tearDown(self):
        self.frame.Destroy()
