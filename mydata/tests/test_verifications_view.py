"""
Test ability to open verifications view.
"""
import unittest
import logging
import wx

from mydata.dataviewmodels.verifications import VerificationsModel
from mydata.views.verifications import VerificationsView

logger = logging.getLogger(__name__)


class VerificationsViewTester(unittest.TestCase):
    """
    Test ability to open verifications view.
    """
    def test_verifications_view(self):
        """
        Test ability to open verifications view.
        """
        # pylint: disable=no-self-use

        app = wx.App(redirect=False)  # pylint: disable=unused-variable
        frame = wx.Frame(None)
        verificationsModel = VerificationsModel()
        VerificationsView(frame, verificationsModel=verificationsModel)
        frame.Show()
        frame.Destroy()
