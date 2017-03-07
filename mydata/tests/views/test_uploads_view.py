"""
Test ability to open uploads view.
"""
import unittest
import wx

from ...dataviewmodels.uploads import UploadsModel
from ...views.dataview import MyDataDataView


class UploadsViewTester(unittest.TestCase):
    """
    Test ability to open uploads view.
    """
    def setUp(self):
        self.app = wx.App(redirect=False)  # pylint: disable=unused-variable
        self.frame = wx.Frame(None, title='UploadsViewTester')

    def test_uploads_view(self):
        """
        Test ability to open uploads view.
        """
        uploadsModel = UploadsModel()
        MyDataDataView(self.frame, uploadsModel)

    def tearDown(self):
        self.frame.Hide()
        self.frame.Destroy()
