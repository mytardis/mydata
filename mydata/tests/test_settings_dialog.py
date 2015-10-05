"""
Test ability to open settings dialog.
"""
import unittest
import logging
import wx

from mydata.models.settings import SettingsModel
from mydata.views.settings import SettingsDialog

logger = logging.getLogger(__name__)


class SettingsDialogTester(unittest.TestCase):
    """
    Test ability to open settings dialog.
    """
    def test_settings_dialog(self):
        """
        Test ability to open settings dialog.
        """
        # pylint: disable=no-self-use

        app = wx.App(redirect=False)  # pylint: disable=unused-variable
        parent = None
        title = "Settings"
        settingsModel = SettingsModel(configPath=None)
        settingsDialog = SettingsDialog(parent, title, settingsModel)
        settingsDialog.Show()
        settingsDialog.Destroy()

