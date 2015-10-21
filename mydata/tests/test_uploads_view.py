"""
Test ability to open uploads view.
"""
import unittest
import logging
import wx

from mydata.dataviewmodels.uploads import UploadsModel
from mydata.views.uploads import UploadsView

logger = logging.getLogger(__name__)


class UploadsViewTester(unittest.TestCase):
    """
    Test ability to open uploads view.
    """
    def test_uploads_view(self):
        """
        Test ability to open uploads view.
        """
        # pylint: disable=no-self-use

        app = wx.App(redirect=False)  # pylint: disable=unused-variable
        frame = wx.Frame(None)
        uploadsModel = UploadsModel()
        foldersController = None
        UploadsView(frame, uploadsModel, foldersController)
        frame.Show()
        frame.Destroy()
